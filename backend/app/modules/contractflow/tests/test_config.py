import pytest

from ..config import GroqSettings
from ..errors import ConfigurationError


def test_explicit_environment():
    settings = GroqSettings.from_env({"GROQ_API_KEY": "synthetic-test-key", "GROQ_MODEL": "test-model"})
    assert settings.timeout_seconds == 30
    assert "synthetic-test-key" not in repr(settings)


@pytest.mark.parametrize("overrides", [{"GROQ_API_KEY": ""}, {"GROQ_MODEL": " "},
    {"CONTRACTFLOW_TIMEOUT_SECONDS": "NaN"}, {"CONTRACTFLOW_TIMEOUT_SECONDS": "0"},
    {"CONTRACTFLOW_TIMEOUT_SECONDS": "oops"}])
def test_invalid_environment(overrides):
    env = {"GROQ_API_KEY": "synthetic-test-key", "GROQ_MODEL": "test-model", **overrides}
    with pytest.raises(ConfigurationError):
        GroqSettings.from_env(env)


def test_no_ambient_credentials_needed():
    with pytest.raises(ConfigurationError):
        GroqSettings.from_env({})
