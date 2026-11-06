"""Trace grouped proposal-language diagnostics without guessing lost responses."""

import json

import pytest

from ..v4.errors import AmendmentValidationError
from ..v4.prompts import build_prompts
from .test_v4_pipeline import generate
from .v4_support import synthetic_output, synthetic_request


def output_with(text):
    output = synthetic_output()
    output["changes"][0]["deliverable_proposal"]["text"] = text
    return output


@pytest.mark.parametrize("modal", ["could", "may", "might"])
def test_conditional_deliverable_and_closed_vocabulary_are_compatible(modal):
    text = f"A proposed deliverable {modal} cover online ordering with payment integration, subject to negotiation."
    output = output_with(text)
    draft = generate(output=output)
    assert draft.original_facts == synthetic_request().original_agreement.project
    assert draft.human_review_required and draft.semantic_review_required
    assert not draft.effective and not draft.parties_approved
    assert [c.model_dump() for c in draft.proposals.changes[0].deliverable_proposal.citations] == output["changes"][0]["deliverable_proposal"]["citations"]


@pytest.mark.parametrize("text", [
    "The deliverable will cover online ordering with payment integration.",
    "The freelancer shall provide online ordering with payment integration.",
    "The freelancer must provide online ordering with payment integration.",
    "A proposed deliverable could guarantee online ordering with payment integration.",
    "A proposed deliverable could cover online ordering with payment integration, subject to approval.",
    "A proposed deliverable could cover online ordering with payment integration, subject to acceptance.",
    "Both parties agree and approved the proposed online ordering with payment integration.",
    "The proposed online ordering with payment integration is not binding.",
    "The proposed online ordering with payment integration is not effective.",
    "Online ordering with payment integration.",
    "The proposed deliverable could cover online ordering with payment integration for USD 500.",
    "The proposed deliverable could cover online ordering with payment integration by 2027-03-01.",
    "The proposed deadline would extend for online ordering with payment integration.",
    "The proposed deliverable could cover online ordering\nwith payment integration.",
])
def test_all_grouped_language_failure_paths_reject_without_rewriting(text):
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output_with(text))
    assert caught.value.rule == "UNSAFE_PROPOSAL"
    assert caught.value.diagnostics == ({"field": "changes.0.deliverable_proposal.text",
                                       "check": "PROPOSAL_LANGUAGE", "source_category": "NONE"},)


@pytest.mark.parametrize("text,rule", [
    ("A proposed deliverable could not include online ordering with payment integration.", "UNSUPPORTED_CHANGE"),
    ("A proposed deliverable could cover online ordering with payment integration and analytics.", "UNSUPPORTED_WORDING"),
    ("A proposed deliverable could cover online ordering.", "UNSUPPORTED_CHANGE"),
])
def test_conditional_marker_does_not_bypass_scope_checks(text, rule):
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output_with(text))
    assert caught.value.rule == rule


def test_safe_example_does_not_excuse_changed_evidence():
    output = synthetic_output()
    output["changes"][0]["deliverable_proposal"]["citations"][2]["excerpt"] += " and analytics"
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "INVALID_EVIDENCE"


def test_prompt_example_matches_fixture_and_validates():
    system, user = build_prompts(synthetic_request())
    normalized = " ".join(system.split())
    example = synthetic_output()["changes"][0]["deliverable_proposal"]["text"]
    assert example in normalized
    assert "Even negated uses" in system
    assert "server renders" in system
    assert "For other changes use their reviewed terms" in system
    contract = next(c for c in json.loads(user)["wording_contract"] if c["field"].endswith("deliverable_proposal"))
    assert contract["required_material_terms"] == ["integration", "online", "ordering", "payment"]
    assert generate().status == "PROPOSED_DRAFT"
