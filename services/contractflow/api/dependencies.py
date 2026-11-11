"""No environment-based enable switch and no synthetic fallback."""

from fastapi import Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..integrations.contracts import IntegrationError
from ..integrations.workflow import IntegrationRuntime

bearer = HTTPBearer(auto_error=False)


def get_runtime(request: Request) -> IntegrationRuntime:
    value = getattr(request.app.state, "contractflow_runtime", None)
    if not isinstance(value, IntegrationRuntime) or any(getattr(value, name) is None for name in (
            "auth", "workbridge", "artifacts", "approval_repository", "reviews", "assessment_reviews", "transactions")):
        raise IntegrationError("UNAVAILABLE")
    return value


async def get_principal(request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    if credentials is None or len(credentials.credentials) > 4096:
        raise IntegrationError("UNAUTHENTICATED")
    runtime = get_runtime(request)
    try:
        return runtime.principal(await runtime.auth.authenticate(credentials.credentials))
    except IntegrationError:
        raise
    except Exception:
        raise IntegrationError("UNAUTHENTICATED") from None
