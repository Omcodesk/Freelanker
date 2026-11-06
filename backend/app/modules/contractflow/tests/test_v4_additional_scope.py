"""Closed vocabulary behavior; examples do not reconstruct lost live wording."""

import json

import pytest

from ..v4.errors import AmendmentValidationError
from ..v4.prompts import build_prompts
from .test_v4_pipeline import generate
from .v4_support import synthetic_output, synthetic_request


def scope_output(text):
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] = text
    return output


@pytest.mark.parametrize("text", [
    "The proposed work could include online ordering with payment integration, subject to negotiation.",
    "Online ordering with payment integration could be considered proposed additional work.",
    "The proposed work may include online ordering with integrated payments, subject to review.",
])
def test_legitimate_closed_vocabulary_wording_preserves_facts_and_evidence(text):
    output = scope_output(text)
    draft = generate(output=output)
    assert draft.original_facts == synthetic_request().original_agreement.project
    assert draft.human_review_required and draft.semantic_review_required
    assert not draft.effective and not draft.parties_approved
    assert [c.model_dump() for c in draft.proposals.changes[0].additional_scope.citations] == output["changes"][0]["additional_scope"]["citations"]


def test_harmless_unlisted_grammar_is_not_semantically_classified():
    # 'together with' changes no functionality here, but the lexical gate cannot
    # establish grammatical role. Document rejection without expanding policy or
    # suggesting this was the unavailable historical token.
    output = scope_output("The proposed work could include online ordering together with payment integration.")
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSUPPORTED_WORDING"
    assert caught.value.diagnostics[0]["token_metadata"]["unsupported_unique_count"] == 1


@pytest.mark.parametrize("suffix", [
    " The proposed work could include inventory.",
    " The proposed work could include subscriptions.",
    " The proposed work could include delivery tracking.",
    " The proposed work could include deployment.",
])
def test_new_functionality_including_agreement_only_words_rejected(suffix):
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] += suffix
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSUPPORTED_WORDING"


@pytest.mark.parametrize("suffix", [" The client must pay USD 500.",
    " Payment is due on delivery.", " The freelancer shall provide ongoing support.",
    " The deadline will change."])
def test_fabricated_obligations_still_fail(suffix):
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] += suffix
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSAFE_PROPOSAL"


def test_detectable_permitted_word_negation_fails():
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=scope_output("The proposed work could not include online ordering with payment integration."))
    assert caught.value.rule == "UNSUPPORTED_CHANGE"


def test_lexical_coverage_cannot_certify_relationships():
    draft = generate(output=scope_output("The proposed work could cover payment ordering with online integration."))
    assert draft.semantic_review_required
    assert "not established" in draft.deterministic_validation


def test_prompt_additional_scope_is_explicitly_closed():
    system, raw = build_prompts(synthetic_request())
    assert "ADDITIONAL SCOPE WORDING" in system
    assert "not permission to" in system
    assert "ordinary grammatical word" in system
    contract = json.loads(raw)["wording_contract"][0]
    assert contract["field"] == "changes.0.additional_scope"
    assert contract["required_material_terms"] == ["integration", "online", "ordering", "payment"]
