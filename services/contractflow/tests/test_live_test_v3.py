import json
import logging

import pytest

from .. import live_test_v3
from ..errors import InvalidProviderOutput
from .test_v3_schemas import case_output


class ScenarioProvider:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        value = self.results.pop(0)
        if isinstance(value, BaseException):
            raise value
        return json.dumps(value)


def setup(monkeypatch, results=None):
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-key")
    monkeypatch.setenv("GROQ_MODEL", "synthetic-model")
    monkeypatch.setenv("CONTRACTFLOW_TIMEOUT_SECONDS", "5")
    if results is None:
        results = [case_output(name) for name, _ in live_test_v3.SCENARIOS]
    provider = ScenarioProvider(results)
    monkeypatch.setattr(live_test_v3, "GroqProvider", lambda settings: provider)
    return provider


def test_all_scenarios_complete_once(monkeypatch, capsys):
    provider = setup(monkeypatch)
    previous = logging.root.manager.disable
    assert live_test_v3.main() == 0
    assert logging.root.manager.disable == previous
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ALL_EXPECTATIONS_MATCHED"
    assert report["model"] == "synthetic-model"
    assert "HUMAN SEMANTIC REVIEW REQUIRED" in report["review_notice"]
    assert len(provider.calls) == 3
    for case, (name, expected), call in zip(report["scenarios"], live_test_v3.SCENARIOS, provider.calls):
        assert case["scenario"] == name
        assert case["actual_classification"] == expected
        assert case["expected_classification"] == expected
        assert case["classification_comparison"] == "MATCH"
        assert case["deterministic_validation"] == "PASSED"
        assert case["human_review_required"] is True
        assert case["semantic_review_required"] is True
        for field in ("explanation", "source_references", "requested_changes", "potential_impacts", "recommended_action"):
            assert field in case
        assert "expected_classification" not in call["user_prompt"]


def test_valid_classification_mismatch_is_not_passed(monkeypatch, capsys):
    outputs = [case_output(name) for name, _ in live_test_v3.SCENARIOS]
    outputs[0]["classification"] = "OUT_OF_SCOPE"
    provider = setup(monkeypatch, outputs)
    assert live_test_v3.main() == 1
    report = json.loads(capsys.readouterr().out)
    first = report["scenarios"][0]
    assert first["actual_classification"] == "OUT_OF_SCOPE"
    assert first["expected_classification"] == "IN_SCOPE"
    assert first["classification_comparison"] == "MISMATCH"
    assert first["deterministic_validation"] == "PASSED"
    assert first["recommended_action"] == "PROPOSE_AMENDMENT"
    assert report["status"] == "FAILURE_OR_CLASSIFICATION_MISMATCH"
    assert len(provider.calls) == 3


@pytest.mark.parametrize("error,label", [(RuntimeError("synthetic-test-key"), "API/PROVIDER"),
    (TimeoutError("synthetic-test-key"), "TIMEOUT"),
    (InvalidProviderOutput("synthetic-test-key"), "VALIDATION"), ({}, "VALIDATION")])
def test_failure_sanitized_and_remaining_scenarios_attempted(monkeypatch, capsys, error, label):
    provider = setup(monkeypatch, [error, case_output("out_of_scope"), case_output("needs_clarification")])
    assert live_test_v3.main() == 1
    captured = capsys.readouterr()
    assert "synthetic-test-key" not in captured.out + captured.err
    report = json.loads(captured.out)
    first = report["scenarios"][0]
    assert first["error"].startswith(label)
    assert first["actual_classification"] is None
    assert first["classification_comparison"] == "NOT_EVALUATED"
    assert first["deterministic_validation"] == "FAILED"
    assert report["scenarios"][1]["classification_comparison"] == "MATCH"
    assert len(provider.calls) == 3


def test_missing_credentials_no_provider(monkeypatch, capsys):
    def forbidden(settings):
        pytest.fail("Provider must not be constructed without credentials")
    monkeypatch.setattr(live_test_v3, "GroqProvider", forbidden)
    assert live_test_v3.main() == 1
    assert "Configuration error" in capsys.readouterr().err


def test_fixture_preflight_no_requests(monkeypatch, capsys):
    provider = setup(monkeypatch)
    def broken():
        raise ValueError("synthetic-test-key")
    monkeypatch.setattr(live_test_v3, "_load_scenarios", broken)
    assert live_test_v3.main() == 1
    assert not provider.calls
    assert "synthetic-test-key" not in capsys.readouterr().err


def test_defense_in_depth_redacts_before_json_escaping(monkeypatch, capsys):
    setup(monkeypatch)
    monkeypatch.setenv("GROQ_MODEL", 'model-synthetic-test-key')
    assert live_test_v3.main() == 0
    output = capsys.readouterr().out
    assert "synthetic-test-key" not in output
    assert "[REDACTED]" in output
    assert live_test_v3._redact({"nested": ['key"value']}, 'key"value') == {"nested": ["[REDACTED]"]}


def test_keyboard_interrupt_stops_remaining_cases(monkeypatch, capsys):
    provider = setup(monkeypatch, [KeyboardInterrupt()])
    previous = logging.root.manager.disable
    assert live_test_v3.main() == 130
    assert len(provider.calls) == 1
    assert logging.root.manager.disable == previous
    assert "remaining scenarios were not attempted" in capsys.readouterr().err


def test_snapshot_tampering_rejected(monkeypatch, capsys):
    from ..v3.service import ScopeChangeService

    provider = setup(monkeypatch)

    class TamperedService:
        def __init__(self, provider, **kwargs):
            self.delegate = ScopeChangeService(provider, **kwargs)

        async def assess_scope_change(self, data):
            result = await self.delegate.assess_scope_change(data)
            project = result.input_snapshot.original_project.model_copy(update={"title": "Altered fixture title"})
            snapshot = result.input_snapshot.model_copy(update={"original_project": project})
            return result.model_copy(update={"input_snapshot": snapshot})

    monkeypatch.setattr(live_test_v3, "ScopeChangeService", TamperedService)
    assert live_test_v3.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert all(r["deterministic_validation"] == "FAILED" for r in report["scenarios"])
    assert len(provider.calls) == 3


def test_existing_sdk_adapter_three_requests_no_retries(monkeypatch, capsys):
    from ..providers.groq import GroqProvider
    from .test_groq_adapter import adapter, response

    setup(monkeypatch)
    monkeypatch.setattr(live_test_v3, "GroqProvider", GroqProvider)
    _, factory, create, _ = adapter(monkeypatch)
    create.side_effect = [response(json.dumps(case_output(name))) for name, _ in live_test_v3.SCENARIOS]
    assert live_test_v3.main() == 0
    assert create.await_count == 3
    assert factory.call_count == 3
    assert all(call.kwargs["max_retries"] == 0 for call in factory.call_args_list)
    assert json.loads(capsys.readouterr().out)["status"] == "ALL_EXPECTATIONS_MATCHED"


@pytest.mark.parametrize("kind,rule", [("prose", "QUANTIFIED_PROSE"), ("reference", "UNKNOWN_SOURCE_REFERENCE"),
    ("excerpt", "FABRICATED_EXCERPT"), ("schema", "SCHEMA_MISSING")])
def test_live_report_safe_validation_diagnostics(monkeypatch, capsys, kind, rule):
    output = case_output("in_scope")
    if kind == "prose":
        output["explanation"] = "The agreed three-page website includes this request."
    elif kind == "reference":
        output["source_references"][0]["reference"] = "synthetic-test-key-SECRET-REFERENCE"
    elif kind == "excerpt":
        output["source_references"][0]["excerpt"] = "synthetic-test-key-SECRET-EXCERPT"
    else:
        del output["requested_changes"]
    provider = setup(monkeypatch, [output, case_output("out_of_scope"), case_output("needs_clarification")])
    assert live_test_v3.main() == 1
    captured = capsys.readouterr()
    assert "SECRET" not in captured.out + captured.err
    assert "synthetic-test-key" not in captured.out + captured.err
    first = json.loads(captured.out)["scenarios"][0]
    assert first["actual_classification"] is None
    assert first["classification_comparison"] == "NOT_EVALUATED"
    assert first["validation_diagnostics"][0]["rule"] == rule
    assert len(provider.calls) == 3


def test_snapshot_mismatch_diagnostic(monkeypatch, capsys):
    from ..v3.service import ScopeChangeService

    setup(monkeypatch)
    class Changed:
        def __init__(self, provider, **kwargs):
            self.service = ScopeChangeService(provider, **kwargs)

        async def assess_scope_change(self, data):
            result = await self.service.assess_scope_change(data)
            project = data.original_project.model_copy(update={"title": "Different title"})
            return result.model_copy(update={"input_snapshot": data.model_copy(update={"original_project": project})})
    monkeypatch.setattr(live_test_v3, "ScopeChangeService", Changed)
    assert live_test_v3.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert all(s["validation_diagnostics"][0]["rule"] == "SNAPSHOT_MISMATCH" for s in report["scenarios"])
