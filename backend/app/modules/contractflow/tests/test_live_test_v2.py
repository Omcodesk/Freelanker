import logging
from pathlib import Path

import pytest

from .. import live_test_v2
from ..errors import InvalidProviderOutput
from .conftest import FakeProvider


def configure(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("GROQ_MODEL", "synthetic-model")
    monkeypatch.setenv("CONTRACTFLOW_TIMEOUT_SECONDS", "5")


def test_success_one_call_complete_render(monkeypatch, capsys):
    configure(monkeypatch)
    output = (Path(__file__).parent / "fixtures/v2_provider_output.json").read_text()
    provider = FakeProvider(output)
    monkeypatch.setattr(live_test_v2, "GroqProvider", lambda settings: provider)
    previous = logging.root.manager.disable
    assert live_test_v2.main() == 0
    assert logging.root.manager.disable == previous
    assert len(provider.calls) == 1
    text = capsys.readouterr().out
    assert "synthetic-model" in text
    assert "synthetic-test-key" not in text
    assert "Deterministic validation PASSED" in text
    assert "HUMAN SEMANTIC REVIEW REQUIRED" in text
    for heading in ("PARTIES", "SCOPE OF WORK", "DELIVERABLES", "MILESTONES AND TIMELINE", "COMPENSATION", "UNRESOLVED TERMS"):
        assert heading in text
    assert "1200.00 USD" in text


def test_missing_configuration_no_request(monkeypatch, capsys):
    def forbidden(settings):
        pytest.fail("Must not construct provider without configuration")
    monkeypatch.setattr(live_test_v2, "GroqProvider", forbidden)
    assert live_test_v2.main() == 1
    assert "Configuration error" in capsys.readouterr().err


@pytest.mark.parametrize("error,message", [(RuntimeError("synthetic-test-key"), "API/provider failure"),
    (TimeoutError("synthetic-test-key"), "timeout"),
    (InvalidProviderOutput("synthetic-test-key"), "validation FAILED")])
def test_errors_are_sanitized(monkeypatch, capsys, error, message):
    configure(monkeypatch)
    provider = FakeProvider(error=error)
    monkeypatch.setattr(live_test_v2, "GroqProvider", lambda settings: provider)
    assert live_test_v2.main() == 1
    captured = capsys.readouterr()
    assert message in captured.err
    assert "synthetic-test-key" not in captured.err + captured.out
    assert len(provider.calls) == 1


def test_invalid_output_is_not_rendered(monkeypatch, capsys):
    configure(monkeypatch)
    monkeypatch.setattr(live_test_v2, "GroqProvider", lambda settings: FakeProvider('{"sections": []}'))
    assert live_test_v2.main() == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "validation FAILED" in captured.err
