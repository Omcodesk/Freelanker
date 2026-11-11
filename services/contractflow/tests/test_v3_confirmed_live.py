import json

import httpx
import pytest

from .. import live_test_v3
from ..v3.diagnostics import V3InvalidProviderOutput
from .test_live_test_v3 import setup
from .test_v3_live_regressions import run
from .test_v3_schemas import case_input, case_output

REJECTED_EXPLANATION = (
    "The request to add an online ordering system with payment integration is not covered by the agreed website scope, "
    "which only includes building a responsive three-page bakery website using client-supplied copy and images."
)


def test_exact_confirmed_live_explanation_with_original_evidence():
    data, output = case_input(), case_output()
    output["explanation"] = REJECTED_EXPLANATION
    result = run(data, output)
    assert result.analysis.explanation == REJECTED_EXPLANATION
    assert result.recommended_action == "PROPOSE_AMENDMENT"
    assert result.human_review_required and result.semantic_review_required
    assert result.input_snapshot.original_project.model_dump(mode="json") == data["original_project"]


@pytest.mark.parametrize("text", [
    "The original scope includes a three-page bakery website, while ordering appears additional.",
    "Ordering is not described by the agreed scope covering a three-page bakery website.",
    "The existing website is a three-page bakery website using client-supplied materials.",
])
def test_natural_grounded_count_descriptions(text):
    data, output = case_input(), case_output()
    output["explanation"] = text
    assert run(data, output).human_review_required


@pytest.mark.parametrize("case", ["no_scope_citation", "insufficient_excerpt", "fabricated_excerpt", "wrong_count", "only_context"])
def test_natural_count_requires_authoritative_matching_evidence(case):
    data, output = case_input(), case_output()
    output["explanation"] = REJECTED_EXPLANATION
    if case == "no_scope_citation":
        output["source_references"] = output["source_references"][1:]
    elif case == "insufficient_excerpt":
        output["source_references"][0]["excerpt"] = "bakery website"
    elif case == "fabricated_excerpt":
        output["source_references"][0]["excerpt"] = "The original scope includes an invented website."
    elif case == "wrong_count":
        output["explanation"] = REJECTED_EXPLANATION.replace("three-page", "four-page")
    else:
        output["source_references"] = output["source_references"][1:]
        data["supporting_context"] = [{"id": "test", "text": data["original_project"]["scope"]}]
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("suffix", [" Charge USD 500.", " The new deadline is 2027-03-01.",
    " Add a 10% fee.", " Estimate three days.", " Payment is due on delivery.",
    " The client must pay.", " The freelancer shall deliver.", " Add three more pages."])
def test_natural_count_does_not_whitelist_other_quantities_or_obligations(suffix):
    data, output = case_input(), case_output()
    output["explanation"] = REJECTED_EXPLANATION + suffix
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("text", ["The original scope could add a three-page bakery website.",
    "The agreed scope proposes a three-page bakery website.",
    "The existing scope needs an additional three-page bakery website.",
    "The original scope will include a three-page bakery website."])
def test_prospective_work_does_not_become_a_baseline_fact(text):
    data, output = case_input(), case_output()
    output["explanation"] = text
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("scenario", ["in_scope", "out_of_scope", "needs_clarification"])
@pytest.mark.parametrize("diagnostics", [False, True])
def test_single_selected_scenario_one_provider_call(monkeypatch, capsys, scenario, diagnostics):
    output = case_output(scenario)
    if scenario == "out_of_scope":
        output["explanation"] = REJECTED_EXPLANATION
    provider = setup(monkeypatch, [output])
    args = ["--scenario", scenario] + (["--synthetic-diagnostics"] if diagnostics else [])
    assert live_test_v3.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert len(provider.calls) == 1
    assert report["requested_scenario"] == scenario
    assert len(report["scenarios"]) == 1
    assert report["scenarios"][0]["scenario"] == scenario
    assert report["scenarios"][0]["classification_comparison"] == "MATCH"


def test_selected_synthetic_diagnostics_still_check_all_selected_input_facts(monkeypatch, capsys):
    provider = setup(monkeypatch)
    cases = live_test_v3._load_scenarios()
    name, expected, data = cases[1]
    cases[1] = (name, expected, data.model_copy(update={"client_request": "Private production data"}))
    monkeypatch.setattr(live_test_v3, "_load_scenarios", lambda: cases)
    assert live_test_v3.main(["--scenario", "out_of_scope", "--synthetic-diagnostics"]) == 1
    assert not provider.calls
    assert "Private production data" not in capsys.readouterr().err


def test_selected_rate_limit_does_not_retry_or_call_other_scenarios(monkeypatch, capsys):
    from groq import RateLimitError
    from ..providers.groq import GroqProvider
    from .test_groq_adapter import adapter

    setup(monkeypatch)
    monkeypatch.setattr(live_test_v3, "GroqProvider", GroqProvider)
    error = RateLimitError("private provider body", response=httpx.Response(
        429, request=httpx.Request("POST", "https://example.invalid")), body={"private": "data"})
    _, factory, create, _ = adapter(monkeypatch, error=error)
    assert live_test_v3.main(["--scenario", "needs_clarification"]) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert len(report["scenarios"]) == 1
    result = report["scenarios"][0]
    assert result["provider_error_category"] == "RATE_LIMIT"
    assert result["provider_http_status"] == 429
    assert "--scenario needs_clarification" in result["retry_advice"]
    assert "No automatic retry" in result["retry_advice"]
    assert "private provider body" not in captured.out
    create.assert_awaited_once()
    factory.assert_called_once()
    assert factory.call_args.kwargs["max_retries"] == 0


def test_invalid_scenario_does_not_make_request(monkeypatch, capsys):
    provider = setup(monkeypatch)
    with pytest.raises(SystemExit) as caught:
        live_test_v3.main(["--scenario", "unknown"])
    assert caught.value.code == 2
    assert not provider.calls
    capsys.readouterr()
