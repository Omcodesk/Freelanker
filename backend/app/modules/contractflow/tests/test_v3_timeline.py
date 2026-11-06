import json

import pytest

from ..v3.diagnostics import V3InvalidProviderOutput
from ..v3.prompts import build_prompts
from ..v3.schemas import ScopeChangeInput
from .test_v3_live_regressions import run
from .test_v3_schemas import case_input, case_output

EXACT = "The additional functionality would extend the project beyond the existing deadline of 2027-01-29."
CONDITIONAL = "The additional functionality may affect the existing project timeline and requires human review before any deadline change."


def with_timeline(text):
    output = case_output()
    output["potential_impacts"][1]["explanation"] = text
    return output


def test_exact_live_statement_rejected_despite_correct_original_deadline_citation():
    data, output = case_input(), with_timeline(EXACT)
    assert output["potential_impacts"][1]["source_references"] == [{"reference": "original.deadline", "excerpt": data["original_project"]["deadline"]}]
    with pytest.raises(V3InvalidProviderOutput) as error:
        run(data, output)
    assert error.value.diagnostics[0] == {"rule": "QUANTIFIED_PROSE", "field": "analysis.potential_impacts.1.explanation"}


def test_schedule_assertion_without_date_independently_rejected():
    with pytest.raises(V3InvalidProviderOutput) as error:
        run(case_input(), with_timeline(EXACT.replace(" of 2027-01-29", "")))
    assert error.value.diagnostics[0]["rule"] == "UNSUPPORTED_SCHEDULE_CHANGE"


@pytest.mark.parametrize("text", [CONDITIONAL,
    "The implementation effort could affect the project timeline; review is needed.",
    "Additional functionality might affect the existing timeline, subject to human review.",
    "Potential timeline effects require human review before any change."])
def test_conditional_timeline_effects_with_authoritative_evidence(text):
    data = case_input()
    result = run(data, with_timeline(text))
    assert result.analysis.potential_impacts[1].explanation == text
    assert result.human_review_required and result.semantic_review_required
    assert result.input_snapshot.original_project.model_dump(mode="json") == data["original_project"]


@pytest.mark.parametrize("reference,excerpt", [("original.start_date", "2027-01-04"),
    ("original.deadline", "2027-01-29"), ("original.deliverables/0/deadline", "2027-01-22"),
    ("original.milestones/0/deadline", "2027-01-22")])
def test_supported_timeline_reference_types(reference, excerpt):
    output = with_timeline(CONDITIONAL)
    output["potential_impacts"][1]["source_references"] = [{"reference": reference, "excerpt": excerpt}]
    assert run(case_input(), output).human_review_required


@pytest.mark.parametrize("case", ["scope_only", "budget_only", "partial_date", "unknown", "fabricated"])
def test_missing_or_invalid_local_timeline_evidence(case):
    output = with_timeline(CONDITIONAL)
    evidence = output["potential_impacts"][1]["source_references"]
    if case == "scope_only":
        evidence[:] = [output["source_references"][0].copy()]
    elif case == "budget_only":
        evidence[:] = [{"reference": "original.budget", "excerpt": "1200.00"}]
    elif case == "partial_date":
        evidence[0]["excerpt"] = "2027"
    elif case == "unknown":
        evidence[0]["reference"] = "original.timeline"
    else:
        evidence[0]["excerpt"] = "2027-02-01"
    with pytest.raises(V3InvalidProviderOutput):
        run(case_input(), output)


@pytest.mark.parametrize("text", [
    "The new deadline is 2027-03-01.", "The work may finish by 2027-03-01, subject to review.",
    "The project timeline will be extended.", "The project would extend beyond the existing deadline.",
    "The deadline is extended.", "The schedule has been rescheduled.",
    "The timeline automatically extends.", "The work extends beyond the existing deadline.",
    "The work may affect the timeline. The deadline automatically changes.",
    "The deadline will change, subject to human review.",
    "The client must pay for the extension.", "Payment is due on delivery.", "Charge USD 500 for the delay.",
])
def test_invented_dates_automatic_extensions_and_commercial_obligations_rejected(text):
    with pytest.raises(V3InvalidProviderOutput):
        run(case_input(), with_timeline(text))


def test_prompt_and_schema_document_conditional_timeline_policy():
    system, user = build_prompts(ScopeChangeInput.model_validate(case_input()))
    payload = json.loads(user)
    assert "Keep dates, including original dates, OUT of explanations" in system
    assert "deadline will or would change" in system
    assert "human review before any deadline change" in system
    assert "original.deadline" in payload["allowed_timeline_references"]
    assert "original.budget" not in payload["allowed_timeline_references"]
