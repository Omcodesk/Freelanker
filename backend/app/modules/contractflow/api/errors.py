"""Module-local error envelope and streamed body limit; no exception body echo."""

from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.responses import JSONResponse

from ..errors import GenerationTimeout, InvalidProviderOutput, ProviderError
from ..v4.errors import ReviewVerificationError
from ..v5.errors import (AuthorizationError, IntegrityError, NotFound, StaleVersion,
                         InvalidTransition, IdempotencyConflict, PersistenceError)
from ..integrations.contracts import IntegrationError

MAX_BODY_BYTES = 131072


def error_response(status, code):
    return JSONResponse(status_code=status, content={"error": {"code": code}},
                        headers={"WWW-Authenticate": "Bearer"} if status == 401 else None)


class SafeRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            try:
                # Bound actual streamed bytes, not only untrusted Content-Length.
                body = bytearray()
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_BODY_BYTES:
                        return error_response(413, "REQUEST_TOO_LARGE")
                    body.extend(chunk)
                request._body = bytes(body)
                return await original(request)
            except RequestValidationError:
                return error_response(422, "INVALID_REQUEST")
            except IntegrationError as error:
                status = {"UNAUTHENTICATED": 401, "FORBIDDEN": 403, "NOT_FOUND": 404,
                          "STALE_SOURCE": 409, "MISSING_AGREEMENT": 409, "INVALID_SOURCE": 503,
                          "REVIEW_INVALID": 403}.get(error.code, 503)
                return error_response(status, error.code)
            except NotFound:
                return error_response(404, "NOT_FOUND")
            except (AuthorizationError, ReviewVerificationError):
                return error_response(403, "FORBIDDEN")
            except (StaleVersion, InvalidTransition, IdempotencyConflict, IntegrityError):
                return error_response(409, "WORKFLOW_CONFLICT")
            except GenerationTimeout:
                return error_response(503, "PROVIDER_TIMEOUT")
            except (InvalidProviderOutput, ProviderError):
                return error_response(502, "PROVIDER_FAILED")
            except (PersistenceError, ValidationError):
                return error_response(503, "INTEGRATION_UNAVAILABLE")
            except Exception:
                return error_response(503, "INTEGRATION_UNAVAILABLE")
        return handler
