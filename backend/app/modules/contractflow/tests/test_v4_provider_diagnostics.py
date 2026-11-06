"""Offline SDK rejection reproduction through the unchanged adapter and V4 runner."""

import json

import groq
import httpx
import pytest

from .. import live_test_v4
from ..v4.provider_errors import categorize_provider_error
from .test_groq_adapter import adapter, response
from .test_live_test_v4 import configure
from .v4_support import synthetic_output


@pytest.mark.parametrize("status,kind,category,retryable", [
    (400, "BadRequestError", "PROVIDER_REJECTION", False),
    (401, "AuthenticationError", "AUTHENTICATION", False),
    (403, "PermissionDeniedError", "PROVIDER_REJECTION", False),
    (404, "NotFoundError", "PROVIDER_REJECTION", False),
    (422, "UnprocessableEntityError", "PROVIDER_REJECTION", False),
    (429, "RateLimitError", "RATE_LIMIT", True),
])
def test_http_rejection_metadata_one_call_no_retry(monkeypatch, capsys, status, kind, category, retryable):
    configure(monkeypatch)
    error = getattr(groq, kind)("CONFIDENTIAL PROVIDER MESSAGE", response=httpx.Response(
        status, request=httpx.Request("POST", "https://example.invalid",
                                      headers={"Authorization": "Bearer SECRET-HEADER"})),
        body={"error": {"type": "invalid_request_error", "code": "json_validate_failed",
                        "message": "CONFIDENTIAL", "failed_generation": "PRIVATE DRAFT"}})
    _, factory, create, _ = adapter(monkeypatch, error=error)
    assert live_test_v4.main(["--run-live"]) == 1
    output = capsys.readouterr()
    assert category in output.err
    metadata = json.loads(output.err.split("Provider diagnostics: ", 1)[1])
    assert metadata == {"http_status": status, "provider_error_type": "invalid_request_error",
                        "provider_error_code": "json_validate_failed", "retryable": retryable}
    assert all(secret not in output.out + output.err for secret in (
        "CONFIDENTIAL", "SECRET-HEADER", "PRIVATE DRAFT", "synthetic-test-key"))
    create.assert_awaited_once()
    assert factory.call_args.kwargs["max_retries"] == 0


@pytest.mark.parametrize("body", [None, "PRIVATE", {"code": "SECRET", "type": "SECRET"},
    {"error": {"code": ["json_validate_failed"], "type": {"secret": "PRIVATE"}}},
    {"error": "PRIVATE"}])
def test_untrusted_metadata_not_echoed(body):
    error = groq.BadRequestError("PRIVATE", response=httpx.Response(400,
        request=httpx.Request("POST", "https://example.invalid")), body=body)
    result = categorize_provider_error(error)
    assert result.diagnostics() == {"http_status": 400, "provider_error_type": None,
                                    "provider_error_code": None, "retryable": False}
    assert "PRIVATE" not in str(result)


def test_sdk_flat_body_supported():
    error = groq.BadRequestError("PRIVATE", response=httpx.Response(400,
        request=httpx.Request("POST", "https://example.invalid")),
        body={"type": "invalid_request_error", "code": "context_length_exceeded"})
    assert categorize_provider_error(error).error_code == "context_length_exceeded"


def test_v4_actual_call_parameters_and_json_schema_alignment(monkeypatch, capsys):
    configure(monkeypatch)
    _, factory, create, _ = adapter(monkeypatch, response(json.dumps(synthetic_output())))
    assert live_test_v4.main(["--run-live"]) == 0
    kwargs = create.call_args.kwargs
    assert set(kwargs) == {"model", "messages", "response_format", "temperature"}
    assert kwargs["model"] == "openai/gpt-oss-120b"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["temperature"] == 0
    payload = json.loads(kwargs["messages"][1]["content"])
    assert set(payload["output_schema"]["properties"]) == {"changes", "timeline", "compensation"}
    assert "JSON" in kwargs["messages"][0]["content"]
    assert factory.call_args.kwargs["max_retries"] == 0
    capsys.readouterr()
