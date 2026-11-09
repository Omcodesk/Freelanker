"""Immutable approval subject, caller decisions and server-owned records."""

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..schemas import Schema
from ..v4.schemas import AmendmentDraft
from .errors import IntegrityError

Reference = Annotated[str, Field(min_length=1, max_length=128)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Version = Annotated[int, Field(strict=True, ge=1)]
Role = Literal["CLIENT", "FREELANCER"]
State = Literal["PENDING_REVIEW", "PARTIALLY_APPROVED", "BOTH_APPROVED", "REJECTED", "SUPERSEDED"]
Decision = Literal["APPROVE", "REJECT"]


def canonical_digest(version, draft):
    # Deliberately bind the ENTIRE V4 artifact, including rendered text, evidence,
    # original snapshot, terms and verified-review receipt. No Unicode folding.
    material = {"format": "contractflow-approval-v1", "amendment_version": version,
                "draft": draft.model_dump(mode="json")}
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def manifest(draft):
    proposals = [p for c in draft.proposals.changes for p in (c.additional_scope, c.deliverable_proposal)]
    proposals += [draft.proposals.timeline, draft.proposals.compensation]
    return tuple((c.reference, c.excerpt) for p in proposals for c in p.citations)


class ApprovalSubject(Schema):
    amendment_id: UUID
    amendment_version: Version
    draft: AmendmentDraft
    source_manifest: tuple[tuple[str, str], ...]
    content_digest: Digest

    @classmethod
    def from_draft(cls, draft, version):
        # model_copy(update=...) is not validation: always detach and revalidate.
        validated = AmendmentDraft.model_validate_json(draft.model_dump_json())
        return cls(amendment_id=validated.draft_id, amendment_version=version,
                   draft=validated, source_manifest=manifest(validated),
                   content_digest=canonical_digest(version, validated))

    @model_validator(mode="after")
    def integrity(self):
        validated = AmendmentDraft.model_validate_json(self.draft.model_dump_json())
        if (self.amendment_id != validated.draft_id or self.source_manifest != manifest(validated)
                or self.content_digest != canonical_digest(self.amendment_version, validated)):
            raise IntegrityError("Approval subject integrity failed")
        return self


class DecisionRequest(Schema):
    amendment_id: UUID
    expected_version: Version
    expected_digest: Digest
    decision: Decision
    rejection_reason: Annotated[str, Field(strict=True, min_length=1, max_length=1000)] | None = None
    idempotency_key: Reference

    @model_validator(mode="after")
    def rejection_only(self):
        if self.decision != "REJECT" and self.rejection_reason is not None:
            raise ValueError("Only rejections may carry a reason")
        if self.rejection_reason is not None and any(ord(c) < 32 or ord(c) == 127 for c in self.rejection_reason):
            raise ValueError("Control characters are not allowed")
        return self


class TrustedActor(Schema):
    actor_id: Reference
    party_id: Reference
    role: Role
    project_id: str
    agreement_id: str
    amendment_id: UUID
    amendment_version: Version
    content_digest: Digest
    acting_on_own_behalf: Literal[True]
    boundary: Reference


class DecisionRecord(Schema):
    decision_id: UUID
    request: DecisionRequest
    actor_id: Reference
    role: Role
    timestamp: datetime

    @model_validator(mode="after")
    def utc(self):
        if self.timestamp.utcoffset() is None or self.timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("Server timestamp must be UTC")
        return self


class AuditEvent(Schema):
    event_id: UUID
    amendment_id: UUID
    amendment_version: Version
    content_digest: Digest
    actor_id: Reference
    role: Role
    action: Literal["CREATED", "APPROVE", "REJECT", "SUPERSEDED"]
    previous_state: State | None
    new_state: State
    timestamp: datetime
    idempotency_reference: Reference | None = None
    decision_id: UUID | None = None

    @model_validator(mode="after")
    def utc(self):
        if self.timestamp.utcoffset() is None or self.timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("Server timestamp must be UTC")
        return self


class ApprovalRecord(Schema):
    subject: ApprovalSubject
    state: State = "PENDING_REVIEW"
    decisions: tuple[DecisionRecord, ...] = ()
    events: tuple[AuditEvent, ...] = ()


class ApprovalStatus(Schema):
    amendment_id: UUID
    amendment_version: Version
    content_digest: Digest
    state: State
    remaining_approvals: tuple[Role, ...]
    human_review_required: Literal[True] = True
    semantic_review_required: Literal[True] = True
    effective: Literal[False] = False
