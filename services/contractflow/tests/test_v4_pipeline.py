import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ..errors import GenerationTimeout, InvalidProviderOutput, ProviderError
from ..v4.errors import AmendmentValidationError, ReviewVerificationError
from ..v4.renderer import render_amendment
from ..v4.schemas import AmendmentDraft, AmendmentRequest, NOTICE
from ..v4.service import AmendmentDraftService
from .conftest import FakeProvider
from .v4_support import SyntheticReviewVerifier, synthetic_output, synthetic_request


def generate(request=None, output=None, verifier=None, provider=None):
    return asyncio.run(AmendmentDraftService(
        provider or FakeProvider(json.dumps(synthetic_output() if output is None else output)),
        verifier or SyntheticReviewVerifier(),
    ).generate_amendment(synthetic_request() if request is None else request))


def test_valid_generation_preserves_all_facts_and_one_request():
    request = synthetic_request()
    before = request.model_dump(mode="json")
    provider = FakeProvider(json.dumps(synthetic_output()))
    verifier = SyntheticReviewVerifier()
    draft = generate(request, provider=provider, verifier=verifier)
    assert draft.request_snapshot.model_dump(mode="json") == before
    assert len(provider.calls) == len(verifier.calls) == 1
    assert draft.notice == NOTICE
    assert draft.status == "PROPOSED_DRAFT"
    assert draft.effective is False and draft.parties_approved is False
    assert draft.original_facts == request.original_agreement.project
    assert draft.original_agreement_version == request.original_agreement.version
    assert draft.human_review_required and draft.semantic_review_required
    assert AmendmentDraft.model_validate_json(draft.model_dump_json()) == draft
    assert "Example Bakery" not in provider.calls[0]["user_prompt"]


@pytest.mark.parametrize("classification,action", [("IN_SCOPE", "REVIEW_AND_CONFIRM_SCOPE"),
                                                  ("NEEDS_CLARIFICATION", "REQUEST_CLARIFICATION")])
def test_only_out_of_scope_input(classification, action):
    data = synthetic_request().model_dump(mode="json")
    assessment = data["reviewed_assessment"]["assessment"]
    assessment["analysis"]["classification"] = classification
    assessment["recommended_action"] = action
    if classification == "NEEDS_CLARIFICATION":
        assessment["analysis"]["clarification_questions"] = ["Which work is requested?"]
    provider = FakeProvider()
    with pytest.raises(ValidationError):
        generate(data, provider=provider)
    assert not provider.calls


@pytest.mark.parametrize("field", ["review_reference", "reviewed_assessment", "original_agreement"])
def test_missing_required_input(field):
    data = synthetic_request().model_dump(mode="json")
    del data[field]
    with pytest.raises(ValidationError):
        generate(data)


@pytest.mark.parametrize("case", ["wrong_agreement", "stale_agreement", "wrong_project", "boolean_review"])
def test_input_mismatches_and_forged_boolean(case):
    data = synthetic_request().model_dump(mode="json")
    if case == "wrong_agreement":
        data["reviewed_assessment"]["agreement_id"] = "OTHER"
    elif case == "stale_agreement":
        data["reviewed_assessment"]["agreement_version"] = 2
    elif case == "wrong_project":
        data["original_agreement"]["project"]["project_id"] = "OTHER"
    else:
        data["verified_review"] = True
    with pytest.raises(ValidationError):
        generate(data)


@pytest.mark.parametrize("case", ["missing", "stale_versions", "changed_facts", "changed_assessment", "wrong_reviewer_boundary", "future", "wrong_receipt"])
def test_verifier_attests_exact_current_content_before_provider(case):
    data = synthetic_request().model_dump(mode="json")
    verifier, provider = SyntheticReviewVerifier(), FakeProvider()
    if case == "missing":
        data["review_reference"] = "UNKNOWN"
    elif case == "stale_versions":
        data["original_agreement"]["version"] = 2
        data["reviewed_assessment"]["agreement_version"] = 2
    elif case == "changed_facts":
        data["original_agreement"]["project"]["client"]["name"] = "Changed client"
        data["reviewed_assessment"]["assessment"]["input_snapshot"]["original_project"]["client"]["name"] = "Changed client"
    elif case == "changed_assessment":
        data["reviewed_assessment"]["version"] = 2
    elif case == "wrong_reviewer_boundary":
        verifier.record = verifier.record.model_copy(update={"verification_boundary": "UNTRUSTED"})
    elif case == "future":
        verifier.record = verifier.record.model_copy(update={"reviewed_at": datetime.now(timezone.utc) + timedelta(days=1)})
    else:
        verifier.record = verifier.record.model_copy(update={"assessment_id": "OTHER"})
    with pytest.raises(ReviewVerificationError):
        generate(data, verifier=verifier, provider=provider)
    assert not provider.calls


def test_review_verifier_failure_is_sanitized():
    class Broken:
        boundary_reference = "TEST"

        async def verify_review(self, ref):
            raise RuntimeError("PRIVATE-REVIEW-DATA")
    with pytest.raises(ReviewVerificationError) as caught:
        generate(verifier=Broken())
    assert "PRIVATE" not in str(caught.value)


@pytest.mark.parametrize("target", ["additional_scope", "deliverable_proposal", "timeline", "compensation"])
@pytest.mark.parametrize("text", ["The client must pay USD 500.", "The deadline will change to 2027-03-01.",
    "Both parties approved this binding amendment.", "The freelancer shall provide unlimited revisions.",
    "The proposed work could include unrelated analytics hosting."])
def test_unsafe_proposal_in_every_material_field(target, text):
    output = synthetic_output()
    proposal = output["changes"][0][target] if target in {"additional_scope", "deliverable_proposal"} else output[target]
    proposal["text"] = text
    with pytest.raises(AmendmentValidationError):
        generate(output=output)


@pytest.mark.parametrize("case", ["unknown", "fabricated", "duplicate", "missing_request", "wrong_change", "missing_deadline", "missing_budget"])
def test_field_local_evidence(case):
    output = synthetic_output()
    citations = output["changes"][0]["additional_scope"]["citations"]
    if case == "unknown":
        citations[0]["reference"] = "agreement.invented"
    elif case == "fabricated":
        citations[0]["excerpt"] = "Invented original scope"
    elif case == "duplicate":
        citations.append(copy.deepcopy(citations[0]))
    elif case == "missing_request":
        citations.pop(1)
    elif case == "wrong_change":
        citations[2]["reference"] = "assessment.requested_changes/99/description"
    elif case == "missing_deadline":
        output["timeline"]["citations"].pop(0)
    else:
        output["compensation"]["citations"].pop(0)
    with pytest.raises(InvalidProviderOutput):
        generate(output=output)


@pytest.mark.parametrize("case", ["unsupported", "duplicate", "missing", "missing_feature"])
def test_deliverables_and_change_coverage(case):
    output = synthetic_output()
    if case == "unsupported":
        output["changes"][0]["change_index"] = 1
    elif case == "duplicate":
        output["changes"].append(copy.deepcopy(output["changes"][0]))
    elif case == "missing":
        output["changes"] = []
    else:
        output["changes"][0]["deliverable_proposal"]["text"] = "A proposed deliverable could cover online ordering."
    with pytest.raises(InvalidProviderOutput):
        generate(output=output)


@pytest.mark.parametrize("field,value", [("human_review_required", False), ("semantic_review_required", False),
    ("effective", True), ("parties_approved", True), ("status", "ACTIVE"), ("notice", "APPROVED"),
    ("unresolved_terms", []), ("rendered_text", "Forged approved amendment"),
    ("original_agreement_id", "OTHER"), ("original_agreement_version", 2),
    ("project_id", "OTHER"), ("assessment_id", "OTHER"), ("assessment_version", 2)])
def test_draft_review_and_render_invariants(field, value):
    data = generate().model_dump(mode="json")
    data[field] = value
    with pytest.raises((ValidationError, ValueError)):
        AmendmentDraft.model_validate(data)


def test_immutable_models_and_readable_renderer():
    draft = generate()
    with pytest.raises(ValidationError):
        draft.request_snapshot.original_agreement.project.budget = 999
    assert render_amendment(draft) == draft.rendered_text
    for section in ("ORIGINAL AGREEMENT REFERENCE", "PURPOSE OF AMENDMENT", "ORIGINAL SCOPE SUMMARY",
                    "PROPOSED ADDITIONAL WORK", "PROPOSED DELIVERABLE CHANGES", "TIMELINE CONSIDERATIONS",
                    "COMPENSATION CONSIDERATIONS", "UNRESOLVED TERMS", "REVIEW AND APPROVAL NOTICE"):
        assert section in draft.rendered_text
    assert "1200.00 USD" in draft.rendered_text
    assert "2027-01-29" in draft.rendered_text
    assert "CLIENT-REQUESTED CHANGES (NOT AGREED TERMS)" in draft.rendered_text
    assert "No additional amount or payment schedule is established" in draft.rendered_text


@pytest.mark.parametrize("raw", ["not JSON", "null", "{}", "[]", "```json\n{}\n```", "x" * 64001],
                         ids=["invalid", "null", "missing", "array", "fences", "oversized"])
def test_invalid_json_and_malformed_responses(raw):
    with pytest.raises(InvalidProviderOutput):
        generate(provider=FakeProvider(raw))


def test_provider_failures_sanitized():
    with pytest.raises(ProviderError) as caught:
        generate(provider=FakeProvider(error=RuntimeError("PRIVATE-KEY")))
    assert "PRIVATE" not in str(caught.value)


@pytest.mark.parametrize("stage", ["review", "provider"])
def test_timeout_cancels_work(stage):
    class Blocked:
        boundary_reference = "TEST"
        cancelled = False

        async def generate(self, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True

        async def verify_review(self, ref):
            return await self.generate()
    blocked = Blocked()
    service = AmendmentDraftService(blocked if stage == "provider" else FakeProvider(),
                                   blocked if stage == "review" else SyntheticReviewVerifier(), timeout_seconds=0.01)
    with pytest.raises(GenerationTimeout):
        asyncio.run(service.generate_amendment(synthetic_request()))
    assert blocked.cancelled


@pytest.mark.parametrize("stage", ["review", "provider"])
def test_external_cancellation_propagates(stage):
    class Cancelled(SyntheticReviewVerifier):
        async def verify_review(self, ref):
            raise asyncio.CancelledError()
    service = AmendmentDraftService(FakeProvider(error=asyncio.CancelledError()),
                                   Cancelled() if stage == "review" else SyntheticReviewVerifier())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service.generate_amendment(synthetic_request()))


@pytest.mark.parametrize("value", [0, -1, 301, float("nan"), float("inf")])
def test_timeout_configuration(value):
    with pytest.raises(ValueError):
        AmendmentDraftService(FakeProvider(), SyntheticReviewVerifier(), timeout_seconds=value)
