"""Approval orchestration; injected trust and storage, no network integrations."""

from datetime import datetime, timezone
from uuid import uuid4

from ..v4.review import validate_receipt
from ..v4.review import ReviewVerifier
from ..v4.schemas import VerifiedReview
from .audit import event
from .authorization import TrustedActorResolver, verify_actor
from .repository import ApprovalRepository
from .errors import ApprovalError, AuthorizationError, IdempotencyConflict, IntegrityError, PersistenceError
from .schemas import ApprovalRecord, ApprovalStatus, ApprovalSubject, DecisionRecord, DecisionRequest
from .states import next_state, remaining
from .validation import match_request, validate_record


def status(record):
    return ApprovalStatus(amendment_id=record.subject.amendment_id,
                          amendment_version=record.subject.amendment_version,
                          content_digest=record.subject.content_digest, state=record.state,
                          remaining_approvals=remaining(record))


class ApprovalWorkflowService:
    def __init__(self, repository: ApprovalRepository, actor_resolver: TrustedActorResolver,
                 review_verifier: ReviewVerifier):
        self.repository = repository
        self.actor_resolver = actor_resolver
        self.review_verifier = review_verifier

    async def _actor(self, authentication_context, subject):
        try:
            resolved = await self.actor_resolver.resolve(authentication_context, subject)
            return verify_actor(subject, resolved, self.actor_resolver.boundary_reference)
        except Exception:
            raise AuthorizationError("Trusted actor verification failed") from None

    async def _load(self, amendment_id):
        try:
            return validate_record(await self.repository.load(amendment_id))
        except ApprovalError:
            raise
        except Exception:
            raise PersistenceError("Approval storage unavailable") from None

    async def register_amendment(self, draft, amendment_version, authentication_context):
        try:
            subject = ApprovalSubject.from_draft(draft, amendment_version)
            # Unlike validating a self-contained V4 receipt, this resolves CURRENT
            # trusted review. The repository is a trusted immutable artifact store.
            receipt = await self.review_verifier.verify_review(subject.draft.request_snapshot.review_reference)
            receipt = VerifiedReview.model_validate_json(receipt.model_dump_json())
            validate_receipt(subject.draft.request_snapshot, receipt, self.review_verifier.boundary_reference)
            if receipt != subject.draft.verified_review:
                raise IntegrityError("Current trusted review differs from draft")
        except Exception:
            raise IntegrityError("Verified inactive V4 draft required") from None
        actor = await self._actor(authentication_context, subject)
        try:
            return status(validate_record(await self.repository.publish(subject, actor)))
        except ApprovalError:
            raise
        except Exception:
            raise PersistenceError("Approval publication failed") from None

    async def submit_decision(self, request, authentication_context):
        request = DecisionRequest.model_validate_json(request.model_dump_json()) if isinstance(request, DecisionRequest) else DecisionRequest.model_validate(request)
        record = await self._load(request.amendment_id)
        actor = await self._actor(authentication_context, record.subject)

        def apply(current):
            match_request(request, current)
            verify_actor(current.subject, actor, self.actor_resolver.boundary_reference)
            for prior in current.decisions:
                if prior.request.idempotency_key == request.idempotency_key:
                    if prior.request == request and (prior.actor_id, prior.role) == (actor.actor_id, actor.role):
                        return current  # Replays return CURRENT status, never a stale response.
                    raise IdempotencyConflict("Idempotency key was used for a different request or actor")
            state = next_state(current, actor, request.decision)
            decision = DecisionRecord(decision_id=uuid4(), request=request, actor_id=actor.actor_id,
                                      role=actor.role, timestamp=datetime.now(timezone.utc))
            audit = event(current.subject, actor, request.decision, current.state, state, decision=decision)
            return ApprovalRecord(subject=current.subject, state=state, decisions=current.decisions + (decision,),
                                  events=current.events + (audit,))
        try:
            result = await self.repository.transact(request.amendment_id, apply)
            return status(validate_record(result))
        except ApprovalError:
            raise
        except Exception:
            raise PersistenceError("Approval transaction failed") from None

    async def get_status(self, amendment_id, authentication_context):
        record = await self._load(amendment_id)
        await self._actor(authentication_context, record.subject)
        return status(record)

    async def get_history(self, amendment_id, authentication_context):
        record = await self._load(amendment_id)
        await self._actor(authentication_context, record.subject)
        try:
            return await self.repository.history(amendment_id)
        except ApprovalError:
            raise
        except Exception:
            raise PersistenceError("Approval history unavailable") from None
