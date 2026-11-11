"""
Freelanker ContractFlow Standalone Service Entrypoint.

In Phase 1 / Step 1:
- Production adapters are NOT yet wired; runtime is explicitly unconfigured.
- All ContractFlow routes fail closed with 503 UNAVAILABLE until Step 3 production adapters are injected.
- A public health check endpoint `/health` is provided to verify process startup.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import router

app = FastAPI(
    title="Freelanker ContractFlow Service",
    description="Python/FastAPI microservice for AI contract generation, scope change detection, and amendment approval.",
    version="1.0.0",
)

# Standard CORS for internal gateway communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Explicitly ensure runtime is unconfigured (fail closed until production adapters are provided)
app.state.contractflow_runtime = None

# Mount ContractFlow router (/api/v1/contractflow)
app.include_router(router)


@app.get("/health", tags=["System"])
async def health_check():
    """Service health check indicating server liveness and adapter configuration state."""
    runtime = getattr(app.state, "contractflow_runtime", None)
    return {
        "status": "ok",
        "service": "contractflow",
        "runtime_configured": runtime is not None,
    }
