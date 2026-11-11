"""Explicit, module-local configuration; no environment reads at import."""

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import Field, SecretStr, ValidationError

from .errors import ConfigurationError
from .schemas import Schema, Text


def load_service_env(env_paths: tuple[Path, ...] | None = None) -> list[Path]:
    """Load key=value pairs from local .env files without overriding process env vars."""
    candidates = env_paths or (Path(__file__).resolve().parent / ".env",)
    loaded: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in {"'", '"'}:
                val = val[1:-1]
            os.environ.setdefault(key, val)
        loaded.append(path)
    return loaded


def is_groq_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Return True only when Groq is explicitly enabled and an API key is configured."""
    values = os.environ if env is None else env
    flag = values.get("CONTRACTFLOW_ENABLE_GROQ", "false").strip().lower()
    return flag in {"1", "true", "yes", "on"} and bool(values.get("GROQ_API_KEY", "").strip())


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
