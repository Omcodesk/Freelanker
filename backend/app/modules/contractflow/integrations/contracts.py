"""ContractFlow-owned integration contracts. Implementations are trusted dependencies."""

from datetime import datetime, timezone
from typing import Annotated, Literal, Protocol, Callable, Awaitable
from uuid import UUID

from pydantic import Field, model_validator

from ..schemas import ProjectInput, Schema
from ..v4.schemas import AgreementSnapshot
from ..v5.schemas import ApprovalSubject, Digest

Identifier = Annotated[str, Field(strict=True, min_length=1, max_length=128)]
Version = Annotated[int, Field(strict=True, ge=1)]


class IntegrationError(Exception):
    """Safe codes only; never serialize adapter exception messages."""
    def __init__(self, code="UNAVAILABLE"):
        self.code = code if code in {"UNAVAILABLE", "UNAUTHENTICATED", "FORBIDDEN", "NOT_FOUND", "STALE_SOURCE", "MISSING_AGREEMENT", "INVALID_SOURCE", "REVIEW_INVALID"} else "UNAVAILABLE"
        super().__init__(self.code)


class Principal(Schema):
    user_id: Identifier
    boundary: Identifier


class SharedAuth(Protocol):
    boundary_reference: str

    async def authenticate(self, bearer_token: str) -> Principal:
        """Verify token/session, expiry and revocation; do not log or retain token."""
        ...

    async def authorize(self, principal: Principal, project_id: str, agreement_id: str | None, *, write: bool) -> None:
        """Verify current own-behalf access/permission using trusted records."""
        ...


class SourceSnapshot(Schema):
    source_version: Version
    project: ProjectInput
    agreement: AgreementSnapshot | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.agreement and (self.agreement.project.project_id != self.project.project_id or
                self.agreement.project.client.id != self.project.client.id or
                self.agreement.project.freelancer.id != self.project.freelancer.id):
            raise ValueError("Conflicting authoritative identities")
        return self


class WorkBridgeSource(Protocol):
    async def load(self, project_id: str, principal: Principal) -> SourceSnapshot:
        """Authorize access; return complete immutable versioned data, no fallback.

        Missing/hidden project -> NOT_FOUND; incomplete/malformed source ->
        INVALID_SOURCE. Agreement is the original agreed snapshot, not a newly
        edited project description. All IDs/dates/budgets must be authoritative.
        """
        ...


class ReviewGrant(Schema):
    amendment_id: UUID
    amendment_version: Version
    content_digest: Digest
    reviewer_reference: Identifier
    reviewed_at: datetime
    expires_at: datetime
    human_review: Literal[True]
    semantic_review: Literal[True]
    revoked: Literal[False]

    @model_validator(mode="after")
    def utc(self):
        for date in (self.reviewed_at, self.expires_at):
            if date.utcoffset() is None or date.utcoffset().total_seconds() != 0:
                raise ValueError("Review timestamps must be UTC")
        if not self.reviewed_at < self.expires_at:
            raise ValueError("Invalid review lifetime")
        return self


class AmendmentReviews(Protocol):
    async def verify(self, subject: ApprovalSubject, principal: Principal) -> ReviewGrant:
        """Read CURRENT, unrevoked review from trusted storage; enforce reviewer
        authority. No request-body boolean/reference can establish review.
        """
        ...


class ApprovalTransactions(Protocol):
    async def run(self, operation: Callable[[], Awaitable]):
        """Execute operation in shared SERIALIZABLE/locked transaction.

        Auth/WorkBridge/reviews and V5 repository must use the SAME transaction
        scope, locking current versions, permissions, review and approval rows.
        Check revocation at decision time, serialize review revocation and source
        revision with approvals. Roll back audit + state on any failure. A
        standalone asyncio lock is NOT a production implementation.
        """
        ...


def validate_grant(grant, subject):
    try:
        grant = ReviewGrant.model_validate_json(grant.model_dump_json())
        now = datetime.now(timezone.utc)
        if (grant.amendment_id, grant.amendment_version, grant.content_digest) != (
                subject.amendment_id, subject.amendment_version, subject.content_digest):
            raise ValueError("Wrong reviewed subject")
        if not grant.reviewed_at <= now < grant.expires_at:
            raise ValueError("Stale review")
        return grant
    except Exception:
        raise IntegrationError("REVIEW_INVALID") from None
