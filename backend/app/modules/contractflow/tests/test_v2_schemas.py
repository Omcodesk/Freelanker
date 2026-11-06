import pytest
from pydantic import ValidationError

from ..v2.schemas import AgreementDraft
from .test_v2_service import generate


@pytest.mark.parametrize("field,value", [("label", "FINAL"), ("requires_human_review", False),
    ("semantic_review_required", False), ("unresolved_terms", []), ("version", "1"),
    ("deterministic_checks", "fully grounded")])
def test_review_invariants(project_data, field, value):
    data = generate(project_data).model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        AgreementDraft.model_validate(data)


def test_tampered_assembled_sections(project_data):
    data = generate(project_data).model_dump(mode="json")
    data["sections"][4]["paragraphs"][0] = "Project budget: 99999 USD."
    with pytest.raises(ValidationError):
        AgreementDraft.model_validate(data)


def test_deep_immutability(project_data):
    draft = generate(project_data)
    with pytest.raises(ValidationError):
        draft.authoritative_data.client.name = "Invented"
    with pytest.raises(TypeError):
        draft.ai_wording.sections[0] = draft.ai_wording.sections[1]
