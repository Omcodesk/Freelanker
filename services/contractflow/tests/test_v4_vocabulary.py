import json
import re
import unicodedata

import pytest

from .. import live_test_v4
from ..v4.diagnostics import safe_token_metadata
from ..v4.errors import AmendmentValidationError
from ..v4.prompts import build_prompts
from ..v4.validation import CONNECTIVES, words
from ..v4.vocabulary import assess_vocabulary, content_terms, normalized_words, wording_rules
from .conftest import FakeProvider
from .test_live_test_v4 import configure
from .test_v4_pipeline import generate
from .v4_support import synthetic_output, synthetic_request

CONTENT = "Add online ordering with payment integration. Add an online ordering system with payment integration."


@pytest.mark.parametrize("text", [
    "The proposed additional work could include online ordering with payments integrated, subject to negotiation.",
    "The proposed additional work could integrate online ordering with payment, subject to negotiation.",
    "The proposed additional work may include integrating online ordering with payments, subject to negotiation.",
    "The proposed additional work could include online-ordering with payment integration, subject to negotiation.",
    "The proposed additional work could include online\u2011ordering with payment integration, subject to negotiation.",
    "Proposed additional work, including online ordering with payment integration, could be considered.",
])
def test_explicit_source_conditioned_paraphrases_pass_pipeline(text):
    output = synthetic_output()
    original_citations = output["changes"][0]["additional_scope"]["citations"]
    output["changes"][0]["additional_scope"]["text"] = text
    draft = generate(output=output)
    assert draft.proposals.changes[0].additional_scope.text == text
    assert [c.model_dump() for c in draft.proposals.changes[0].additional_scope.citations] == original_citations
    assert draft.human_review_required and draft.semantic_review_required
    assert not draft.effective and not draft.parties_approved
    assert draft.original_facts == synthetic_request().original_agreement.project


def test_reproduced_inflection_failure_is_narrowly_corrected():
    text = "The proposed additional work could include online ordering with payments integrated, subject to negotiation."
    legacy = set(re.findall(r"[a-z]+", text.casefold())) - (words(CONTENT) | (CONNECTIVES - {"including"}))
    assert legacy == {"payments", "integrated"}
    permitted, metadata = assess_vocabulary(text, CONTENT, CONNECTIVES)
    assert permitted
    assert metadata["source_variant_occurrence_count"] == 2
    assert metadata["unsupported_occurrence_count"] == 0


@pytest.mark.parametrize("content,text", [
    ("Add online ordering.", "The proposed work could include payment integration."),
    ("Add payment support.", "The proposed work could integrate payment."),
    ("Add integration support.", "The proposed work could include payments."),
])
def test_forms_never_introduce_an_unrequested_concept(content, text):
    assert not assess_vocabulary(text, content, CONNECTIVES)[0]


@pytest.mark.parametrize("term", ["analytics", "hosting", "gateway", "Stripe", "API", "processor", "mobile", "cryptocurrency"])
def test_new_features_deliverables_or_payment_methods_rejected(term):
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] += " The proposed work could include " + term + "."
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSUPPORTED_WORDING"
    assert caught.value.diagnostics[0]["check"] == "CONTENT_VOCABULARY"
    metadata = caught.value.diagnostics[0]["token_metadata"]
    assert metadata["unsupported_unique_count"] == 1
    assert term.casefold() not in json.dumps(metadata).casefold()


def test_original_agreement_word_is_not_new_scope_authorization():
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] += " The proposed work could include deployment."
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.diagnostics[0]["token_metadata"]["agreement_only_occurrence_count"] == 1


@pytest.mark.parametrize("text", ["The client must pay USD 500.", "The proposed work could finish by 2027-03-01.",
    "Both parties approved the amendment.", "The proposed online ordering could be free.",
    "The freelancer shall integrate online ordering with payment."])
def test_source_variants_do_not_bypass_financial_deadline_or_approval_safeguards(text):
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] = text
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSAFE_PROPOSAL"


def test_citations_stay_exact_even_when_proposal_inflection_is_permitted():
    output = synthetic_output()
    proposal = output["changes"][0]["additional_scope"]
    proposal["text"] = "The proposed work could integrate online ordering with payments, subject to negotiation."
    proposal["citations"][2]["excerpt"] = "Add online ordering with payments integrated."
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "INVALID_EVIDENCE"
    assert caught.value.diagnostics[0]["check"] == "EXCERPT_NOT_EXACT"


def test_word_matching_handles_unicode_composition_without_transliteration():
    source = "Add café integration."
    text = "The proposed work could include " + unicodedata.normalize("NFD", "café") + " integration."
    assert assess_vocabulary(text, source, CONNECTIVES)[0]
    assert normalized_words("café") == normalized_words(unicodedata.normalize("NFD", "café"))
    assert not assess_vocabulary("The proposed work could include cafe integration.", source, CONNECTIVES)[0]


def test_material_feature_coverage_uses_same_canonical_source_forms():
    required = content_terms("Add online ordering with payment integration.", CONTENT) - CONNECTIVES
    permitted = content_terms("Proposed online ordering with payments integrated.", CONTENT)
    assert required <= permitted
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] = "The proposed work could include online ordering."
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSUPPORTED_CHANGE"


def test_diagnostics_report_positions_and_counts_without_tokens(monkeypatch, capsys):
    configure(monkeypatch)
    output = synthetic_output()
    text = output["changes"][0]["additional_scope"]["text"] + " The proposed work could include PRIVATEWORD."
    output["changes"][0]["additional_scope"]["text"] = text
    provider = FakeProvider(json.dumps(output))
    monkeypatch.setattr(live_test_v4, "GroqProvider", lambda settings: provider)
    assert live_test_v4.main(["--run-live"]) == 1
    captured = capsys.readouterr()
    assert "PRIVATEWORD" not in captured.err + captured.out
    assert "synthetic-test-key" not in captured.err + captured.out
    assert text not in captured.err + captured.out
    assert "unsupported_occurrence_count" in captured.err
    assert "token_index" in captured.err
    assert len(provider.calls) == 1


def test_metadata_is_allowlisted_bounded_and_omits_hashes_or_arbitrary_strings():
    metadata = safe_token_metadata({"unsupported_unique_count": 1, "token": "PRIVATE", "hash": "PRIVATE", "unsupported_positions": [
        {"token_index": 1, "start": 2, "end": 4, "character_class": "ASCII", "text": "PRIVATE"},
        {"token_index": 2, "start": 4, "end": 6, "character_class": "PRIVATE"},
    ]})
    assert "PRIVATE" not in repr(metadata)
    assert len(metadata["unsupported_positions"]) == 1
    assert metadata["unsupported_positions"][0] == {"token_index": 1, "start": 2, "end": 4, "character_class": "ASCII"}


def test_prompt_contract_is_generated_from_specific_reviewed_content():
    system, user = build_prompts(synthetic_request())
    payload = json.loads(user)
    first = payload["wording_contract"][0]
    assert first["preferred_source_terms"] == sorted(normalized_words(CONTENT))
    assert first["required_material_terms"] == ["integration", "online", "ordering", "payment"]
    assert first["permitted_source_conditioned_forms"]["payment"] == ["payment", "payments"]
    assert "gateway" not in first["preferred_source_terms"]
    assert "no\ngeneral synonym permission" in system
    assert wording_rules("Add online ordering.", "Add online ordering.", CONNECTIVES)["permitted_source_conditioned_forms"] == {}
