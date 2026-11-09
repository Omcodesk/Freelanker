"""Immutable versioned inputs, trusted review receipts and proposed draft output."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from ..schemas import ProjectInput, Schema, UNRESOLVED_TERMS
from ..v3.schemas import ScopeChangeAssessment

Id = Annotated[str, Field(min_length=1, max_length=128)]
Version = Annotated[int, Field(strict=True, ge=1)]
Prose = Annotated[str, Field(min_length=1, max_length=1600)]
NOTICE = "PROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE"
UNRESOLVED = ("additional_scope_confirmation", "proposed_deliverable_details", "revised_timeline",
              "additional_compensation") + UNRESOLVED_TERMS


class AgreementSnapshot(Schema):
    agreement_id: Id
    version: Version
    project: ProjectInput


class ReviewedAssessment(Schema):
    assessment_id: Id
    version: Version
    agreement_id: Id
    agreement_version: Version
    assessment: ScopeChangeAssessment


class AmendmentRequest(Schema):
    original_agreement: AgreementSnapshot
    reviewed_assessment: ReviewedAssessment
    review_reference: Id

    @model_validator(mode="after")
    def consistent_request(self):
        a, r = self.original_agreement, self.reviewed_assessment
        if (a.agreement_id, a.version) != (r.agreement_id, r.agreement_version):
            raise ValueError("Agreement reference/version mismatch")
        if r.assessment.analysis.classification != "OUT_OF_SCOPE":
            raise ValueError("Only OUT_OF_SCOPE assessments can propose amendments")
        if r.assessment.input_snapshot.original_project != a.project:
            raise ValueError("Assessment and agreement project snapshots differ")
        if len(self.model_dump_json().encode("utf-8")) > 128000:
            raise ValueError("Amendment input exceeds size limit")
        return self


class VerifiedReview(Schema):
    review_reference: Id
    reviewer_reference: Id
    assessment_id: Id
    assessment_version: Version
    agreement_id: Id
    agreement_version: Version
    agreement_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    assessment_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    reviewed_at: datetime
    decision: Literal["AUTHORIZE_DRAFT_GENERATION"]
    verification_boundary: Id

    @model_validator(mode="after")
    def aware_timestamp(self):
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("Review timestamp needs timezone")
        return self


class AmendmentEvidence(Schema):
    # V3 Evidence embeds an original.* example and strips whitespace. V4 uses a
    # different catalog and must preserve literal quotation/reference characters.
    model_config = ConfigDict(str_strip_whitespace=False)
    reference: Annotated[str, Field(min_length=1, max_length=200,
        description="Exact V4 sources key, e.g. agreement.scope or assessment.requested_changes/0/description. Never use original.* or invent aliases.")]
    excerpt: Annotated[str, Field(min_length=1, max_length=8000,
        description="Exact source characters. Required request/assessment/deadline/budget quotes must copy the specified complete value. No paraphrasing, ellipses, whitespace changes or Unicode normalization.")]

    @field_validator("reference", "excerpt")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Blank evidence is not allowed")
        return value


class CitedProposal(Schema):
    text: Prose
    citations: Annotated[tuple[AmendmentEvidence, ...], Field(min_length=3, max_length=20)]


class ProposedChange(Schema):
    change_index: Annotated[int, Field(strict=True, ge=0, le=19)]
    additional_scope: CitedProposal
    deliverable_proposal: CitedProposal


class AmendmentWording(Schema):
    changes: Annotated[tuple[ProposedChange, ...], Field(min_length=1, max_length=20)]
    timeline: CitedProposal
    compensation: CitedProposal


class AmendmentDraft(Schema):
    draft_id: UUID
    original_agreement_id: Id
    original_agreement_version: Version
    project_id: Id
    assessment_id: Id
    assessment_version: Version
    original_facts: ProjectInput
    version: Literal["4"] = "4"
    status: Literal["PROPOSED_DRAFT"] = "PROPOSED_DRAFT"
    notice: Literal["PROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE"] = NOTICE
    request_snapshot: AmendmentRequest
    verified_review: VerifiedReview
    proposals: AmendmentWording
    unresolved_terms: tuple[str, ...] = UNRESOLVED
    human_review_required: Literal[True] = True
    semantic_review_required: Literal[True] = True
    effective: Literal[False] = False
    parties_approved: Literal[False] = False
    deterministic_validation: Literal["passed; semantic correctness not established"] = "passed; semantic correctness not established"
    rendered_text: str

    @model_validator(mode="after")
    def invariant_draft(self):
        from .renderer import render_text, render_text_legacy
        from .review import validate_receipt
        from .validation import validate_wording

        validate_receipt(self.request_snapshot, self.verified_review, self.verified_review.verification_boundary)
        a, r = self.request_snapshot.original_agreement, self.request_snapshot.reviewed_assessment
        if (self.original_agreement_id, self.original_agreement_version, self.project_id,
            self.assessment_id, self.assessment_version) != (
                a.agreement_id, a.version, a.project.project_id, r.assessment_id, r.version
        ) or self.original_facts != a.project:
            raise ValueError("Server-authoritative references/facts cannot be changed")
        validate_wording(self.request_snapshot, self.proposals)
        if self.unresolved_terms != UNRESOLVED:
            raise ValueError("Unresolved terms cannot be changed")
        # Preserve byte-identical historical artifacts/digests. New generation
        # uses professional templates, but reads never rewrite legacy text.
        if (self.rendered_text != render_text_legacy(self.draft_id, self.request_snapshot, self.proposals)
                and self.rendered_text != render_text(self.draft_id, self.request_snapshot, self.proposals)):
            raise ValueError("Rendered content must be deterministic")
        return self
