import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ..v3.schemas import ScopeChangeAssessment, ScopeChangeInput

FIXTURES = Path(__file__).parent / "fixtures"


def case_input(case="out_of_scope"):
    data = json.loads((FIXTURES / "v3" / f"{case}.json").read_text())
    data["original_project"] = json.loads((FIXTURES / "website_project.json").read_text())
    return data


def case_output(case="out_of_scope"):
    return json.loads((FIXTURES / "v3/provider_outputs.json").read_text())[case]


@pytest.mark.parametrize("case", ["in_scope", "out_of_scope", "needs_clarification"])
def test_fixture_input(case):
    data = ScopeChangeInput.model_validate(case_input(case))
    assert ScopeChangeInput.model_validate_json(data.model_dump_json()) == data


@pytest.mark.parametrize("field", ["request_id", "project_id", "original_project", "client_request"])
def test_required_inputs(field):
    data = case_input()
    del data[field]
    with pytest.raises(ValidationError):
        ScopeChangeInput.model_validate(data)


@pytest.mark.parametrize("field,value", [("project_id", "WRONG"), ("request_id", " "),
    ("client_request", "\t"), ("client_request", "x" * 8001), ("budget", "5")])
def test_invalid_input(field, value):
    data = case_input()
    data[field] = value
    with pytest.raises(ValidationError):
        ScopeChangeInput.model_validate(data)


def test_duplicate_context():
    data = case_input("needs_clarification")
    data["supporting_context"] *= 2
    with pytest.raises(ValidationError):
        ScopeChangeInput.model_validate(data)


def test_total_size_limit():
    data = case_input()
    data["supporting_context"] = [{"id": str(i), "text": "é" * 4000} for i in range(10)]
    with pytest.raises(ValidationError, match="64000"):
        ScopeChangeInput.model_validate(data)


def assessment_payload():
    return dict(request_id="SYNTHETIC-REQUEST-OUT", project_id="SYNTHETIC-WEB-001",
                input_snapshot=case_input(), analysis=case_output(), recommended_action="PROPOSE_AMENDMENT")


@pytest.mark.parametrize("field,value", [("human_review_required", False), ("semantic_review_required", False),
    ("recommended_action", "REVIEW_AND_CONFIRM_SCOPE"), ("request_id", "OTHER"),
    ("project_id", "OTHER"), ("version", "2"), ("deterministic_validation", "semantically proven")])
def test_assessment_invariants(field, value):
    data = assessment_payload()
    data[field] = value
    with pytest.raises(ValidationError):
        ScopeChangeAssessment.model_validate(data)


def test_immutable_snapshot_and_roundtrip():
    assessment = ScopeChangeAssessment.model_validate(assessment_payload())
    assert ScopeChangeAssessment.model_validate_json(assessment.model_dump_json()) == assessment
    with pytest.raises(ValidationError):
        assessment.input_snapshot.original_project.budget = 999
    with pytest.raises(ValidationError):
        assessment.input_snapshot.original_project.client.name = "Changed"
