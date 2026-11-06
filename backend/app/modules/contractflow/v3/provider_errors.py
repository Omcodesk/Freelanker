"""Classify SDK exception types without reading messages, headers or bodies."""

from ..errors import ProviderError

CATEGORIES = frozenset({"AUTHENTICATION", "RATE_LIMIT", "PROVIDER_REJECTION", "CONNECTIVITY", "TIMEOUT", "UNKNOWN"})


class V3ProviderError(ProviderError):
    def __init__(self, category="UNKNOWN", status=None):
        self.category = category if category in CATEGORIES else "UNKNOWN"
        self.http_status = status if type(status) is int and 400 <= status <= 599 else None
        super().__init__("Scope assessment provider failed")


def categorize_provider_error(error):
    try:
        from groq import AuthenticationError, RateLimitError, APIStatusError, APITimeoutError, APIConnectionError
    except ImportError:
        return V3ProviderError()
    seen = set()
    # The unchanged adapter sanitizes errors with `from None`; the typed original
    # remains in __context__. Inspect only its TYPE and numeric HTTP status.
    for _ in range(5):
        if error is None or id(error) in seen:
            break
        seen.add(id(error))
        if isinstance(error, V3ProviderError):
            return V3ProviderError(error.category, error.http_status)
        if isinstance(error, APITimeoutError):
            return V3ProviderError("TIMEOUT")
        if isinstance(error, AuthenticationError):
            return V3ProviderError("AUTHENTICATION", error.status_code)
        if isinstance(error, RateLimitError):
            return V3ProviderError("RATE_LIMIT", error.status_code)
        if isinstance(error, APIStatusError):
            return V3ProviderError("PROVIDER_REJECTION", error.status_code)
        if isinstance(error, APIConnectionError):
            return V3ProviderError("CONNECTIVITY")
        error = error.__cause__ or error.__context__
    return V3ProviderError()
