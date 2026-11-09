import json
import logging

import httpx
import pytest

from .. import live_test_v4
from ..v4.review import fingerprint
from .conftest import FakeProvider
from .v4_support import synthetic_output, synthetic_request


def configure(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("CONTRACTFLOW_TIMEOUT_SECONDS", "5")


def test_no_opt_in_no_configuration_or_provider_access(monkeypatch, capsys):
    def forbidden(settings):
        pytest.fail("Live provider constructed without opt-in")
    monkeypatch.setattr(live_test_v4, "GroqProvider", forbidden)
    assert live_test_v4.main() == 2
    assert "No request made" in capsys.readouterr().err


def test_opt_in_one_mocked_call_and_draft_notice(monkeypatch, capsys):
    configure(monkeypatch)
    provider = FakeProvider(json.dumps(synthetic_output()))
    monkeypatch.setattr(live_test_v4, "GroqProvider", lambda settings: provider)
    previous = logging.root.manager.disable
    assert live_test_v4.main(["--run-live", "--scenario", "ordering"]) == 0
    assert logging.root.manager.disable == previous
    assert len(provider.calls) == 1
    captured = capsys.readouterr()
    assert "synthetic-test-key" not in captured.out
    report = json.loads(captured.out)
    assert report["effective"] is False
    assert report["human_review_required"] and report["semantic_review_required"]
    assert "NOT A REAL REVIEW" in report["synthetic_review_notice"]
    assert "NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE" in report["rendered_amendment"]


def test_synthetic_pin_and_forged_input_prevents_requests(monkeypatch, capsys):
    from . import v4_support
    configure(monkeypatch)
    request = synthetic_request()
    assert fingerprint(request) == live_test_v4.SYNTHETIC_INPUT_PIN
    changed = request.model_copy(update={"review_reference": "FORGED"})
    monkeypatch.setattr(v4_support, "synthetic_request", lambda: changed)
    provider = FakeProvider()
    monkeypatch.setattr(live_test_v4, "GroqProvider", lambda settings: provider)
    assert live_test_v4.main(["--run-live"]) == 1
    assert not provider.calls
    assert "configuration failure" in capsys.readouterr().err


@pytest.mark.parametrize("kind,status,category", [("RateLimitError", 429, "RATE_LIMIT"),
    ("AuthenticationError", 401, "AUTHENTICATION")])
def test_actual_adapter_sdk_errors_are_sanitized_and_not_retried(monkeypatch, capsys, kind, status, category):
    import groq
    from .test_groq_adapter import adapter

    configure(monkeypatch)
    error = getattr(groq, kind)("PRIVATE PROVIDER BODY", response=httpx.Response(
        status, request=httpx.Request("POST", "https://example.invalid")), body={"api_key": "PRIVATE"})
    _, factory, create, _ = adapter(monkeypatch, error=error)
    assert live_test_v4.main(["--run-live"]) == 1
    captured = capsys.readouterr()
    assert category in captured.err
    assert "PRIVATE" not in captured.err + captured.out
    create.assert_awaited_once()
    assert factory.call_args.kwargs["max_retries"] == 0


@pytest.mark.parametrize("raw", ["{PRIVATE-KEY}", '{"status":"APPROVED"}'])
def test_live_validation_errors_do_not_expose_raw_output(monkeypatch, capsys, raw):
    configure(monkeypatch)
    monkeypatch.setattr(live_test_v4, "GroqProvider", lambda settings: FakeProvider(raw))
    assert live_test_v4.main(["--run-live"]) == 1
    captured = capsys.readouterr()
    assert "validation failed" in captured.err
    assert "PRIVATE-KEY" not in captured.err + captured.out


def test_invalid_model_no_request(monkeypatch, capsys):
    configure(monkeypatch)
    monkeypatch.setenv("GROQ_MODEL", "different-model")
    provider = FakeProvider()
    monkeypatch.setattr(live_test_v4, "GroqProvider", lambda settings: provider)
    assert live_test_v4.main(["--run-live"]) == 1
    assert not provider.calls
    capsys.readouterr()
