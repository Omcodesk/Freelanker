import json

import pytest

from ..v4.errors import AmendmentValidationError
from ..v4.prompts import build_prompts
from ..v4.sources import source_registry
from ..v4.validation import CONNECTIVES
from ..v4.vocabulary import assess_vocabulary
from .test_v4_pipeline import generate
from .v4_support import synthetic_output, synthetic_request

PROPOSAL = "A proposed deliverable could cover online ordering with payment integration, subject to negotiation."


def with_existing(reference="agreement.deliverables/0/description", external_period=False):
    registry = source_registry(synthetic_request())
    quote = registry[reference]
    output = synthetic_output()
    proposal = output["changes"][0]["deliverable_proposal"]
    proposal["text"] = f'Existing deliverable: "{quote}"' + ("." if external_period else "") + " " + PROPOSAL
    proposal["citations"].append({"reference": reference, "excerpt": quote})
    return output


@pytest.mark.parametrize("reference", ["agreement.deliverables/0/description", "agreement.deliverables/1/description"])
@pytest.mark.parametrize("external_period", [False, True])
def test_explicit_existing_deliverable_context_is_not_new_scope(reference, external_period):
    output = with_existing(reference, external_period)
    draft = generate(output=output)
    assert draft.proposals.changes[0].deliverable_proposal.text == output["changes"][0]["deliverable_proposal"]["text"]
    assert draft.original_facts == synthetic_request().original_agreement.project
    assert draft.human_review_required and draft.semantic_review_required
    assert not draft.effective and not draft.parties_approved


def test_reproduce_old_flat_vocabulary_false_positive_without_guessing_live_text():
    output = with_existing()
    text = output["changes"][0]["deliverable_proposal"]["text"]
    content = "Add online ordering with payment integration. Add an online ordering system with payment integration."
    permitted, metadata = assess_vocabulary(text, content, CONNECTIVES,
                                          " ".join(source_registry(synthetic_request()).values()))
    assert not permitted
    assert metadata["agreement_only_occurrence_count"] > 0
    assert generate(output=output).status == "PROPOSED_DRAFT"


@pytest.mark.parametrize("case", ["missing_local", "partial_citation", "fabricated_quote", "unlabeled", "unicode_quote"])
def test_existing_context_requires_exact_labeled_field_local_evidence(case):
    output = with_existing()
    proposal = output["changes"][0]["deliverable_proposal"]
    if case == "missing_local":
        proposal["citations"].pop()
    elif case == "partial_citation":
        proposal["citations"][-1]["excerpt"] = "page source files."
    elif case == "fabricated_quote":
        proposal["text"] = proposal["text"].replace("Home, menu", "Inventory, dashboard")
    elif case == "unlabeled":
        proposal["text"] = proposal["text"].replace("Existing deliverable: ", "")
    else:
        proposal["text"] = proposal["text"].replace("page source", "page\u00a0source")
    with pytest.raises(AmendmentValidationError):
        generate(output=output)


@pytest.mark.parametrize("sentence", [
    "The proposed deliverable could include deployment with online ordering and payment integration.",
    "The proposed deliverable could include analytics with online ordering and payment integration.",
    "The proposed deliverable could include a gateway with online ordering and payment integration.",
    "The proposed deliverable could cover menu source files and online ordering with payment integration.",
])
def test_baseline_quote_cannot_authorize_original_or_invented_added_deliverables(sentence):
    output = with_existing("agreement.deliverables/1/description")
    proposal = output["changes"][0]["deliverable_proposal"]
    prefix = proposal["text"].split('" ', 1)[0] + '" '
    proposal["text"] = prefix + sentence
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSUPPORTED_WORDING"


def test_baseline_quote_does_not_replace_material_new_work_coverage():
    output = with_existing()
    proposal = output["changes"][0]["deliverable_proposal"]
    proposal["text"] = proposal["text"].replace(PROPOSAL, "The proposed deliverable could remain unresolved.")
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSUPPORTED_CHANGE"


def test_inline_relabeling_existing_deliverable_as_proposed_work_is_ambiguous():
    output = with_existing()
    proposal = output["changes"][0]["deliverable_proposal"]
    proposal["text"] = proposal["text"].replace('" ' + PROPOSAL, '" could cover online ordering with payment integration.')
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.diagnostics[0]["check"] == "BASELINE_ROLE_AMBIGUOUS"


@pytest.mark.parametrize("text", [
    "The proposed deliverable could not include online ordering with payment integration.",
    "The proposed deliverable could never cover online ordering with payment integration.",
    "The proposed deliverable may not integrate online ordering with payment.",
])
def test_detectable_misleading_combinations_of_permitted_words_rejected(text):
    output = synthetic_output()
    output["changes"][0]["deliverable_proposal"]["text"] = text
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule in {"UNSUPPORTED_CHANGE", "UNSUPPORTED_WORDING"}


@pytest.mark.parametrize("suffix", [" The client must pay USD 500.", " Finish by 2027-03-01.",
    " Both parties approved the amendment.", " Payment is due on delivery."])
def test_reference_context_never_bypasses_financial_date_approval_or_obligation_checks(suffix):
    output = with_existing()
    output["changes"][0]["deliverable_proposal"]["text"] += suffix
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSAFE_PROPOSAL"


def test_remaining_semantic_relationship_limit_is_explicit():
    output = synthetic_output()
    output["changes"][0]["deliverable_proposal"]["text"] = "The proposed deliverable could cover payment ordering with online integration."
    # Same concepts, potentially different relationships: lexical validation
    # cannot establish that this is a faithful contractual paraphrase.
    draft = generate(output=output)
    assert draft.semantic_review_required
    assert "not established" in draft.deterministic_validation


def test_prompt_separates_existing_context_from_new_deliverable_terms():
    system, user = build_prompts(synthetic_request())
    payload = json.loads(user)
    assert "DELIVERABLE ROLE SEPARATION" in system
    assert "not automatically new deliverables" in system
    assert "Do not paraphrase the baseline quote" in system
    for item in payload["baseline_deliverable_context"]:
        assert item["role"] == "EXISTING_ONLY_NOT_NEW_SCOPE"
        assert source_registry(synthetic_request())[item["reference"]] == item["excerpt"]
