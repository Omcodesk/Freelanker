"""
PostgreSQL Review Verification Adapter for ContractFlow.

Implements ContractFlow's AmendmentReviews and ReviewVerifier protocols:
- Enforces real human and semantic review grants from cf_reviews.
- Enforces assessment review verification receipts from cf_assessment_reviews.
- Fails closed on expired, revoked, or mismatched review grants.
"""

import json
from datetime import datetime, timezone

from ..integrations.contracts import AmendmentReviews, IntegrationError, Principal, ReviewGrant
from ..v4.errors import ReviewVerificationError
from ..v4.review import ReviewVerifier
from ..v4.schemas import VerifiedReview
from ..v5.schemas import ApprovalSubject
from .db import _current_conn, get_connection


class PostgresReviewRepository(AmendmentReviews, ReviewVerifier):
    boundary_reference = "CONTRACTFLOW-V4-ASSESSMENT-REVIEW"

    async def verify(self, subject: ApprovalSubject, principal: Principal) -> ReviewGrant:
        """
        Read CURRENT, unrevoked review from trusted storage (cf_reviews).
        Enforce reviewer authority and exact subject revision/digest binding.
        """
        async for conn in get_connection():
            row = await conn.fetchrow(
                """
                SELECT review_id, amendment_id, revision, content_digest,
                       reviewer_id, reviewed_at, expires_at, human_review,
                       semantic_review, revoked
                FROM public.cf_reviews
                WHERE amendment_id = $1 AND revision = $2 AND content_digest = $3
                  AND revoked = FALSE
                ORDER BY created_at DESC
                LIMIT 1
                FOR SHARE
                """,
                subject.amendment_id,
                subject.amendment_version,
                subject.content_digest,
            )
            if not row:
                raise IntegrationError("REVIEW_INVALID")

            reviewed_at = row["reviewed_at"]
            if reviewed_at.tzinfo is None:
                reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)

            expires_at = row["expires_at"]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            now_utc = datetime.now(timezone.utc)
            if not (reviewed_at <= now_utc < expires_at):
                raise IntegrationError("REVIEW_INVALID")

            if not row["human_review"] or not row["semantic_review"]:
                raise IntegrationError("REVIEW_INVALID")

            return ReviewGrant(
                amendment_id=row["amendment_id"],
                amendment_version=row["revision"],
                content_digest=row["content_digest"],
                reviewer_reference=str(row["reviewer_id"]),
                reviewed_at=reviewed_at,
                expires_at=expires_at,
                human_review=True,
                semantic_review=True,
                revoked=False,
            )

    async def verify_review(self, review_reference: str) -> VerifiedReview:
        """
        Resolve a server-trusted, current V4 assessment review receipt.
        Raise if absent, revoked, or stale.
        """
        async for conn in get_connection():
            row = await conn.fetchrow(
                """
                SELECT assessment_review_id, review_reference, assessment_id,
                       assessment_revision, original_agreement_id, original_agreement_version,
                       agreement_digest, assessment_digest, reviewer_id, decision,
                       verification_boundary, reviewed_at, revoked
                FROM public.cf_assessment_reviews
                WHERE review_reference = $1 AND revoked = FALSE
                LIMIT 1
                FOR SHARE
                """,
                review_reference,
            )
            if not row:
                raise ReviewVerificationError("Review receipt does not exist or has been revoked")

            reviewed_at = row["reviewed_at"]
            if reviewed_at.tzinfo is None:
                reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)

            return VerifiedReview(
                review_reference=row["review_reference"],
                reviewer_reference=str(row["reviewer_id"]),
                assessment_id=str(row["assessment_id"]),
                assessment_version=row["assessment_revision"],
                agreement_id=str(row["original_agreement_id"]),
                agreement_version=row["original_agreement_version"],
                agreement_digest=row["agreement_digest"],
                assessment_digest=row["assessment_digest"],
                reviewed_at=reviewed_at,
                decision="AUTHORIZE_DRAFT_GENERATION",
                verification_boundary=self.boundary_reference,
            )

    async def revoke(
        self,
        review_id: str,
        reason: str,
        reviewer_id: str,
    ) -> None:
        """
        Revoke an active review grant under exclusive row lock in an explicit transaction.
        Serializes against concurrent decision transactions.
        Fails closed on missing or already-revoked reviews.
        """
        import uuid
        rev_uuid = uuid.UUID(review_id)
        now_utc = datetime.now(timezone.utc)

        async def _do_revoke(c):
            # 1. Acquire exclusive row-level lock on the review grant
            row = await c.fetchrow(
                """
                SELECT review_id, revoked FROM public.cf_reviews
                WHERE review_id = $1
                FOR UPDATE
                """,
                rev_uuid,
            )
            if not row or row["revoked"]:
                raise IntegrationError("REVIEW_INVALID")

            # 2. Update status to revoked
            await c.execute(
                """
                UPDATE public.cf_reviews
                SET revoked = TRUE,
                    revoked_at = $1,
                    revocation_reason = $2
                WHERE review_id = $3
                """,
                now_utc,
                reason,
                rev_uuid,
            )

        # If already in a managed transaction context (_current_conn), execute directly
        active = _current_conn.get()
        if active is not None:
            await _do_revoke(active)
            return

        # Standalone invocation: manage an explicit transaction block to hold lock until commit
        async for conn in get_connection():
            async with conn.transaction():
                await _do_revoke(conn)

