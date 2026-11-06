import pytest
from pydantic import ValidationError

from ..v3.schemas import ScopeAnalysis, ScopeChangeAssessment, ScopeChangeInput
from ..v3.validation import validate_analysis, validate_prose
from .test_v3_schemas import assessment_payload, case_input, case_output


def check(output, case="out_of_scope"):
    validate_analysis(ScopeChangeInput.model_validate(case_input(case)), ScopeAnalysis.model_validate(output))


@pytest.mark.parametrize("case", ["in_scope", "out_of_scope", "needs_clarification"])
def test_valid_examples(case):
    check(case_output(case), case)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "unknown", "quote", "context", "request", "only_budget"])
def test_invalid_original_evidence(kind):
    output = case_output()
    refs = output["source_references"]
    if kind == "missing":
        refs.clear()
    elif kind == "duplicate":
        refs.append(refs[0].copy())
    elif kind == "unknown":
        refs[0]["reference"] = "original.deliverables/999/description"
    elif kind == "quote":
        refs[0]["excerpt"] = "Original scope includes ordering."
    elif kind == "context":
        refs[0]["reference"] = "context/0"
    elif kind == "request":
        refs[0]["reference"] = "request.client_request"
    else:
        output["source_references"] = [{"reference": "original.budget", "excerpt": "1200.00"}]
    with pytest.raises((ValueError, ValidationError)):
        check(output)


@pytest.mark.parametrize("field", ["requested_changes", "potential_impacts"])
def test_nested_evidence_cannot_be_fabricated(field):
    output = case_output()
    output[field][0]["source_references"][0]["reference"] = "original.__dict__"
    with pytest.raises(ValueError):
        check(output)


@pytest.mark.parametrize("kind", ["fabricated", "wrong_namespace", "duplicate"])
def test_request_evidence(kind):
    output = case_output()
    if kind == "fabricated":
        output["requested_changes"][0]["request_evidence"]["excerpt"] = "Add free hosting."
    elif kind == "wrong_namespace":
        output["requested_changes"][0]["request_evidence"]["reference"] = "original.scope"
    else:
        output["requested_changes"].append(output["requested_changes"][0].copy())
    with pytest.raises(ValueError):
        check(output)


@pytest.mark.parametrize("text", [
    "Charge USD 500 for the addition.", "The new budget is 1600.", "Charge five hundred dollars.",
    "Finish by 2027-03-01.", "Finish in September.", "Add a 10% deposit.",
    "The client must pay for ordering.", "The freelancer shall implement ordering.",
    "The client will pay an additional fee.", "Payment is due on delivery.",
    "A penalty applies for delay.", "Intellectual property transfers to the client.",
    "The governing law is English law.", "Termination occurs on request.",
    "Acceptance is automatic.", "The budget increases for the addition.",
    "The freelancer guarantees delivery.", "Analysis\nPAYMENTS: invented",
])
def test_detectable_unsupported_values_and_obligations(text):
    with pytest.raises(ValueError):
        validate_prose(text)


@pytest.mark.parametrize("field", ["explanation", "description", "impact", "question"])
def test_every_interpretation_field_checked(field):
    output = case_output()
    text = "Charge USD 900."
    if field == "explanation":
        output["explanation"] = text
    elif field == "description":
        output["requested_changes"][0]["description"] = text
    elif field == "impact":
        output["potential_impacts"][0]["explanation"] = text
    else:
        output["clarification_questions"] = [text]
    with pytest.raises(ValueError):
        check(output)


def test_technical_payments_and_qualitative_effects_allowed():
    validate_prose("Payment integration may affect delivery effort and compensation discussions.")


def test_client_amount_and_legal_request_is_only_attributed_evidence():
    data = case_input()
    data["client_request"] = "Add ordering for USD 500 by 2027-04-01 with IP transfer."
    output = case_output()
    output["requested_changes"][0]["request_evidence"]["excerpt"] = data["client_request"]
    validate_analysis(ScopeChangeInput.model_validate(data), ScopeAnalysis.model_validate(output))
    assert data["original_project"]["budget"] == "1200.00"


@pytest.mark.parametrize("case", ["missing_question", "duplicate_impacts", "unknown_context", "false_context_quote"])
def test_analysis_consistency(case):
    output = case_output("needs_clarification")
    if case == "missing_question":
        output["clarification_questions"] = []
    elif case == "duplicate_impacts":
        output["potential_impacts"] = [case_output()["potential_impacts"][0]] * 2
    elif case == "unknown_context":
        output["context_references"][0]["reference"] = "context/99"
    else:
        output["context_references"][0]["excerpt"] = "Ordering is already agreed."
    with pytest.raises(ValueError):
        check(output, "needs_clarification")


def test_same_source_can_support_different_findings():
    check(case_output())


def test_semantic_false_negative_documented():
    data = assessment_payload()
    data["analysis"]["classification"] = "IN_SCOPE"
    data["analysis"]["explanation"] = "Ordering appears included in the original agreement."
    data["recommended_action"] = "REVIEW_AND_CONFIRM_SCOPE"
    result = ScopeChangeAssessment.model_validate(data)
    # Provenance and enum consistency cannot prove this interpretation follows.
    assert result.semantic_review_required
    assert "not established" in result.deterministic_validation


def test_conservative_false_positive_documented():
    with pytest.raises(ValueError):
        validate_prose("Review the source files one at a time.")
