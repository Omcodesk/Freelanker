"""Bounded provider metadata; never expose messages, headers or response text."""

from ..errors import ProviderError
from ..v3.provider_errors import categorize_provider_error as base_category

# Unknown values are deliberately suppressed, even if syntactically plausible:
# error codes/types are untrusted provider data and may contain request content.
SAFE_TYPES = frozenset({"invalid_request_error", "authentication_error", "permission_error",
                        "rate_limit_error", "server_error", "requests", "tokens"})
SAFE_CODES = frozenset({"json_validate_failed", "tool_use_failed", "context_length_exceeded",
                        "model_not_found", "model_decommissioned", "unsupported_parameter",
                        "invalid_api_key", "invalid_request_error", "rate_limit_exceeded",
                        "insufficient_quota", "permission_denied", "invalid_value"})


class AmendmentProviderError(ProviderError):
    def __init__(self, category, status, error_type=None, code=None):
        self.category = category
        self.http_status = status
        self.error_type = error_type if type(error_type) is str and error_type in SAFE_TYPES else None
        self.error_code = code if type(code) is str and code in SAFE_CODES else None
        self.retryable = (status in {408, 409, 429} or status >= 500) if status is not None else (
            True if category in {"CONNECTIVITY", "TIMEOUT"} else None)
        super().__init__("Amendment provider failed")

    def diagnostics(self):
        return {"http_status": self.http_status, "provider_error_type": self.error_type,
                "provider_error_code": self.error_code, "retryable": self.retryable}


def categorize_provider_error(error):
    if isinstance(error, AmendmentProviderError):
        return error
    base = base_category(error)
    error_type = code = None
    try:
        from groq import APIStatusError
    except ImportError:
        return AmendmentProviderError(base.category, base.http_status)
    seen = set()
    for _ in range(5):
        if error is None or id(error) in seen:
            break
        seen.add(id(error))
        if isinstance(error, APIStatusError):
            # SDK body is already decoded. Never serialize it or inspect messages,
            # failed_generation, headers, request content or arbitrary attributes.
            body = error.body
            if type(body) is dict:
                detail = body.get("error", body)
                if type(detail) is dict:
                    error_type, code = detail.get("type"), detail.get("code")
            break
        error = error.__cause__ or error.__context__
    return AmendmentProviderError(base.category, base.http_status, error_type, code)
