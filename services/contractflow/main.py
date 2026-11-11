"""
Freelanker ContractFlow Standalone Service Entrypoint.

Manages FastAPI application lifecycle:
- Loads local environment configuration cleanly without exposing credentials.
- On startup: Initializes asyncpg database connection pool if DATABASE_URL is set.
- Wires production PostgreSQL adapters into IntegrationRuntime when DB and JWT auth are configured.
- Keeps GroqProvider disabled unless explicitly enabled and verified via CONTRACTFLOW_ENABLE_GROQ=true.
- Exposes /health with real database connectivity check, JWT config status, runtime status, and Groq status.
- Mounts exported ContractFlow APIRouter (/api/v1/contractflow/*).
- On shutdown: Closes the database pool gracefully.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import router
from .api.workspace_router import workspace_router
from .integrations.workflow import IntegrationRuntime
from .config import GroqSettings, is_groq_enabled, load_service_env
from .providers.groq import GroqProvider
from .adapters import (
    init_db_pool,
    close_db_pool,
    get_database_url,
    get_pool,
    SupabasePostgresAuth,
    SupabaseCoreSource,
    PostgresArtifactRepository,
    PostgresApprovalRepository,
    PostgresApprovalTransactions,
    PostgresReviewRepository,
)

logger = logging.getLogger("contractflow.startup")


def has_jwt_configuration() -> bool:
    """Return True when Supabase URL and either local JWT secret or anon key are configured."""
    supabase_url = (os.environ.get("SUPABASE_URL") or "").strip()
    jwt_secret = (os.environ.get("SUPABASE_JWT_SECRET") or "").strip()
    anon_key = (os.environ.get("SUPABASE_ANON_KEY") or "").strip()
    return bool(supabase_url and (jwt_secret or anon_key))


def _runtime_is_configured(runtime: object) -> bool:
    return isinstance(runtime, IntegrationRuntime) and all(
        getattr(runtime, name, None) is not None
        for name in (
            "auth",
            "workbridge",
            "artifacts",
            "approval_repository",
            "reviews",
            "assessment_reviews",
            "transactions",
        )
    )


async def check_database_connectivity(timeout_seconds: float = 3.0) -> bool:
    """Perform a lightweight database connectivity check without exposing connection strings."""
    try:
        pool = get_pool()
    except Exception:
        return False

    try:
        async def _ping() -> bool:
            async with pool.acquire() as conn:
                return (await conn.fetchval("SELECT 1")) == 1

        return await asyncio.wait_for(_ping(), timeout=timeout_seconds)
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for connection pool and runtime adapter wiring."""
    load_service_env()

    db_url = get_database_url()
    pool = None
    if db_url:
        try:
            pool = await init_db_pool()
        except Exception as exc:
            logger.warning("Database pool initialization failed (%s)", type(exc).__name__)
            pool = None

    jwt_ok = has_jwt_configuration()
    if pool is not None and jwt_ok:
        try:
            auth_adapter = SupabasePostgresAuth()
            source_adapter = SupabaseCoreSource()
            artifact_adapter = PostgresArtifactRepository()
            approval_adapter = PostgresApprovalRepository()
            tx_adapter = PostgresApprovalTransactions()
            review_adapter = PostgresReviewRepository()

            # Optional Groq provider: disabled unless explicitly enabled and verified
            provider = None
            if is_groq_enabled():
                try:
                    groq_settings = GroqSettings.from_env()
                    provider = GroqProvider(groq_settings)
                except Exception as exc:
                    logger.warning("Groq provider disabled due to invalid configuration (%s)", type(exc).__name__)
                    provider = None

            app.state.contractflow_runtime = IntegrationRuntime(
                auth=auth_adapter,
                workbridge=source_adapter,
                artifacts=artifact_adapter,
                approval_repository=approval_adapter,
                reviews=review_adapter,
                assessment_reviews=review_adapter,
                transactions=tx_adapter,
                provider=provider,  # None when disabled; non-AI routes remain operational
                timeout_seconds=float(os.environ.get("CONTRACTFLOW_TIMEOUT_SECONDS", "30")),
            )
        except Exception as exc:
            logger.warning("ContractFlow runtime initialization failed (%s)", type(exc).__name__)
            app.state.contractflow_runtime = None
    else:
        app.state.contractflow_runtime = None

    yield

    await close_db_pool()


app = FastAPI(
    title="Freelanker ContractFlow Service",
    description="Python/FastAPI microservice for AI contract generation, scope change detection, and amendment approval.",
    version="1.0.0",
    lifespan=lifespan,
)

# Standard CORS for internal gateway communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount ContractFlow router (/api/v1/contractflow) and workspace router (/api/v1/contractflow/workspace)
app.include_router(router)
app.include_router(workspace_router)


@app.get("/health", tags=["System"])
async def health_check(request: Request):
    """
    Service readiness and dependency health check.

    Distinguishes service running, DB connectivity, JWT configuration, runtime wiring,
    and optional Groq AI availability. Returns HTTP 503 degraded if essential
    dependencies are unavailable.
    """
    runtime = getattr(request.app.state, "contractflow_runtime", None)
    database_configured = get_database_url() is not None
    database_connected = await check_database_connectivity() if database_configured else False
    jwt_configured = has_jwt_configuration()
    runtime_configured = _runtime_is_configured(runtime)
    groq_enabled = bool(runtime_configured and getattr(runtime, "provider", None) is not None)

    is_healthy = database_connected and jwt_configured and runtime_configured
    payload = {
        "status": "ok" if is_healthy else "degraded",
        "service": "contractflow",
        "service_running": True,
        "database_configured": database_configured,
        "database_connected": database_connected,
        "jwt_configured": jwt_configured,
        "runtime_configured": runtime_configured,
        "groq_enabled": groq_enabled,
        "groq_configured": is_groq_enabled(),
    }
    return JSONResponse(status_code=200 if is_healthy else 503, content=payload)


if __name__ == "__main__":
    import uvicorn

    load_service_env()
    host = os.environ.get("CONTRACTFLOW_HOST", "127.0.0.1")
    port = int(os.environ.get("CONTRACTFLOW_PORT", "8000"))
    uvicorn.run("services.contractflow.main:app", host=host, port=port)
