"""Explicit, module-local configuration; no environment reads at import."""

import os
from collections.abc import Mapping

from pydantic import Field, SecretStr, ValidationError

from .errors import ConfigurationError
from .schemas import Schema, Text


class GroqSettings(Schema):
    api_key: SecretStr
    model: Text
    timeout_seconds: float = Field(default=30, gt=0, le=300, allow_inf_nan=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None):
        values = os.environ if env is None else env
        key = values.get("GROQ_API_KEY", "").strip()
        if not key:
            raise ConfigurationError("GROQ_API_KEY is required")
        try:
            return cls(api_key=key, model=values.get("GROQ_MODEL", ""),
                       timeout_seconds=values.get("CONTRACTFLOW_TIMEOUT_SECONDS", "30"))
        except ValidationError:
            raise ConfigurationError("Invalid Groq model or timeout configuration") from None
