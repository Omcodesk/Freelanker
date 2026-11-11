"""
Freelanker ContractFlow Standalone Service Entrypoint.

Manages FastAPI application lifecycle:
- On startup: Initializes asyncpg database connection pool if DATABASE_URL is set.
- Wires production PostgreSQL adapters into IntegrationRuntime when database is available.
- Wires GroqProvider only if GROQ_API_KEY is configured (otherwise AI generation fails closed).
- Exposes /health indicating pool status, runtime configuration, and Groq status.
- Mounts exported ContractFlow APIRouter (/api/v1/contractflow/*).
- On shutdown: Closes the database pool gracefully.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import router
from .integrations.workflow import IntegrationRuntime
from .config import GroqSettings
from .providers.groq import GroqProvider
from .adapters import (
    init_db_pool,
    close_db_pool,
    get_database_url,
    SupabasePostgresAuth,
    SupabaseCoreSource,
    PostgresArtifactRepository,
    PostgresApprovalRepository,
    PostgresApprovalTransactions,
    PostgresReviewRepository,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for connection pool and runtime adapter wiring."""
    db_url = get_database_url()
    pool = None
    if db_url:
        try:
            pool = await init_db_pool()
        except Exception:
            pool = None

    if pool is not None:
        try:
            auth_adapter = SupabasePostgresAuth()
            source_adapter = SupabaseCoreSource()
            artifact_adapter = PostgresArtifactRepository()
            approval_adapter = PostgresApprovalRepository()
            tx_adapter = PostgresApprovalTransactions()
            review_adapter = PostgresReviewRepository()

            # Optional Groq Provider (only instantiated if GROQ_API_KEY is set)
            provider = None
            if os.environ.get("GROQ_API_KEY", "").strip():
                try:
                    groq_settings = GroqSettings.from_env()
                    provider = GroqProvider(groq_settings)
                except Exception:
                    provider = None

            app.state.contractflow_runtime = IntegrationRuntime(
                auth=auth_adapter,
                workbridge=source_adapter,
                artifacts=artifact_adapter,
                approval_repository=approval_adapter,
                reviews=review_adapter,
                assessment_reviews=review_adapter,
                transactions=tx_adapter,
                provider=provider,  # None if unconfigured
                timeout_seconds=float(os.environ.get("CONTRACTFLOW_TIMEOUT_SECONDS", "30")),
            )
        except Exception:
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

# Mount ContractFlow router (/api/v1/contractflow)
app.include_router(router)


@app.get("/health", tags=["System"])
async def health_check():
    """Service health check indicating database pool, runtime, and Groq status."""
    runtime = getattr(app.state, "contractflow_runtime", None)
    has_db = get_database_url() is not None
    has_groq = bool(os.environ.get("GROQ_API_KEY", "").strip())
    return {
        "status": "ok",
        "service": "contractflow",
        "database_configured": has_db,
        "runtime_configured": runtime is not None,
        "groq_configured": has_groq,
    }
