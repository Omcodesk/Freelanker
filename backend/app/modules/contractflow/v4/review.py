"""Required trusted dependency; no default verifier or boolean-based approval."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Protocol

from .errors import ReviewVerificationError
from .schemas import AmendmentRequest, VerifiedReview


def fingerprint(model) -> str:
    raw = json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


class ReviewVerifier(Protocol):
    boundary_reference: str

    async def verify_review(self, review_reference: str) -> VerifiedReview:
        """Resolve a server-trusted, current review; raise if absent/revoked/stale.

        Implementations must authenticate the reviewer and check the current
        agreement/assessment version in trusted storage, not accept caller proof.
        """
        ...


def validate_receipt(request: AmendmentRequest, record: VerifiedReview, boundary: str) -> None:
    a, r = request.original_agreement, request.reviewed_assessment
    if (
        record.review_reference != request.review_reference or
        record.verification_boundary != boundary or
        (record.agreement_id, record.agreement_version) != (a.agreement_id, a.version) or
        (record.assessment_id, record.assessment_version) != (r.assessment_id, r.version) or
        record.agreement_digest != fingerprint(a) or record.assessment_digest != fingerprint(r) or
        record.reviewed_at > datetime.now(timezone.utc)
    ):
        raise ReviewVerificationError("Review receipt does not attest this exact current input")
