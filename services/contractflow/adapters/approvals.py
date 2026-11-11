"""
PostgreSQL Durable Approval Repository for ContractFlow.

Implements ContractFlow's ApprovalRepository protocol:
- Replaces InMemoryApprovalRepository with real PostgreSQL tables.
- Uses SELECT ... FOR UPDATE row-level locking on cf_approval_heads during transactions.
- Enforces strict unique constraints on decisions and append-only audit event logging.
- Guarantees that decision, version transition, and audit log commit together.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from ..v4.schemas import AmendmentDraft
from ..v5.audit import event
from ..v5.errors import IdempotencyConflict, IntegrityError, NotFound, PersistenceError, StaleVersion
from ..v5.repository import ApprovalRepository
from ..v5.schemas import (
    ApprovalRecord,
    ApprovalSubject,
    AuditEvent,
    DecisionRecord,
    DecisionRequest,
    TrustedActor,
)
from ..v5.validation import validate_record
from .db import get_connection


class PostgresApprovalRepository(ApprovalRepository):
    async def load(self, amendment_id: UUID) -> ApprovalRecord:
        """Load current active revision of the amendment approval record."""
        async for conn in get_connection():
            # 1. Resolve current revision from approval head
            head_row = await conn.fetchrow(
                "SELECT current_revision FROM public.cf_approval_heads WHERE amendment_id = $1",
                amendment_id,
            )
            if not head_row:
                raise NotFound("Unknown amendment")
            current_revision = head_row["current_revision"]

            return await self._load_record(conn, amendment_id, current_revision)

    async def _load_record(self, conn, amendment_id: UUID, revision: int) -> ApprovalRecord:
        # Fetch version row
        ver_row = await conn.fetchrow(
            """
            SELECT state, content_digest, review_reference,
                   original_agreement_id, original_agreement_version,
                   client_id, freelancer_id
            FROM public.cf_approval_versions
            WHERE amendment_id = $1 AND revision = $2
            """,
            amendment_id,
            revision,
        )
        if not ver_row:
            raise NotFound("Unknown amendment version")

        # Fetch underlying draft artifact from cf_artifacts
        art_row = await conn.fetchrow(
            """
            SELECT payload_json FROM public.cf_artifacts
            WHERE artifact_id = $1 AND revision = $2
            """,
            amendment_id,
            revision,
        )
        if not art_row:
            raise NotFound("Missing artifact draft for approval version")

        raw_payload = art_row["payload_json"]
        payload_str = raw_payload if isinstance(raw_payload, str) else json.dumps(raw_payload)
        draft = AmendmentDraft.model_validate_json(payload_str)
        subject = ApprovalSubject.from_draft(draft, revision)

        # Fetch decisions for this revision
        decision_rows = await conn.fetch(
            """
            SELECT decision_id, actor_id, role, decision, request_digest,
                   rejection_reason, idempotency_key, created_at
            FROM public.cf_decisions
            WHERE amendment_id = $1 AND revision = $2
            ORDER BY created_at ASC
            """,
            amendment_id,
            revision,
        )
        decisions: list[DecisionRecord] = []
        for d in decision_rows:
            d_time = d["created_at"]
            if d_time.tzinfo is None:
                d_time = d_time.replace(tzinfo=timezone.utc)
            req = DecisionRequest(
                amendment_id=amendment_id,
                expected_version=revision,
                expected_digest=subject.content_digest,
                decision=d["decision"],
                rejection_reason=d["rejection_reason"],
                idempotency_key=d["idempotency_key"],
            )
            decisions.append(
                DecisionRecord(
                    decision_id=d["decision_id"],
                    request=req,
                    actor_id=str(d["actor_id"]),
                    role=d["role"],
                    timestamp=d_time,
                )
            )

        # Fetch audit events for this revision
        audit_rows = await conn.fetch(
            """
            SELECT event_id, action, previous_state, new_state, actor_id, role,
                   content_digest, idempotency_reference, decision_id, created_at
            FROM public.cf_audit
            WHERE amendment_id = $1 AND revision = $2
            ORDER BY append_sequence ASC
            """,
            amendment_id,
            revision,
        )
        events: list[AuditEvent] = []
        for a in audit_rows:
            a_time = a["created_at"]
            if a_time.tzinfo is None:
                a_time = a_time.replace(tzinfo=timezone.utc)
            events.append(
                AuditEvent(
                    event_id=a["event_id"],
                    amendment_id=amendment_id,
                    amendment_version=revision,
                    content_digest=a["content_digest"],
                    actor_id=str(a["actor_id"]),
                    role=a["role"],
                    action=a["action"],
                    previous_state=a["previous_state"],
                    new_state=a["new_state"],
                    timestamp=a_time,
                    idempotency_reference=a["idempotency_reference"],
                    decision_id=a["decision_id"],
                )
            )

        record = ApprovalRecord(
            subject=subject,
            state=ver_row["state"],
            decisions=tuple(decisions),
            events=tuple(events),
        )
        return validate_record(record)

    async def history(self, amendment_id: UUID) -> tuple[AuditEvent, ...]:
        """Fetch complete chronological append-only audit history across all revisions."""
        async for conn in get_connection():
            # Ensure amendment exists
            head_row = await conn.fetchrow(
                "SELECT current_revision FROM public.cf_approval_heads WHERE amendment_id = $1",
                amendment_id,
            )
            if not head_row:
                raise NotFound("Unknown amendment")

            audit_rows = await conn.fetch(
                """
                SELECT event_id, revision, action, previous_state, new_state,
                       actor_id, role, content_digest, idempotency_reference,
                       decision_id, created_at
                FROM public.cf_audit
                WHERE amendment_id = $1
                ORDER BY revision ASC, append_sequence ASC
                """,
                amendment_id,
            )
            events: list[AuditEvent] = []
            for a in audit_rows:
                a_time = a["created_at"]
                if a_time.tzinfo is None:
                    a_time = a_time.replace(tzinfo=timezone.utc)
                events.append(
                    AuditEvent(
                        event_id=a["event_id"],
                        amendment_id=amendment_id,
                        amendment_version=a["revision"],
                        content_digest=a["content_digest"],
                        actor_id=str(a["actor_id"]),
                        role=a["role"],
                        action=a["action"],
                        previous_state=a["previous_state"],
                        new_state=a["new_state"],
                        timestamp=a_time,
                        idempotency_reference=a["idempotency_reference"],
                        decision_id=a["decision_id"],
                    )
                )
            return tuple(events)

    async def publish(self, subject: ApprovalSubject, actor: TrustedActor) -> ApprovalRecord:
        """Register a new amendment or superseding revision into the approval lifecycle."""
        async for conn in get_connection():
            head_row = await conn.fetchrow(
                "SELECT current_revision FROM public.cf_approval_heads WHERE amendment_id = $1 FOR UPDATE",
                subject.amendment_id,
            )

            now_utc = datetime.now(timezone.utc)

            if head_row:
                # Existing amendment: Superseding revision
                old_rev = head_row["current_revision"]
                old_record = await self._load_record(conn, subject.amendment_id, old_rev)
                a, b = old_record.subject.draft, subject.draft

                if (
                    subject.amendment_version != old_record.subject.amendment_version + 1
                    or a.original_facts != b.original_facts
                    or (a.original_agreement_id, a.original_agreement_version, a.project_id)
                    != (b.original_agreement_id, b.original_agreement_version, b.project_id)
                    or a.model_dump(mode="json") == b.model_dump(mode="json")
                ):
                    raise StaleVersion("Revision requires changed content and the next version of the same agreement")

                # Supersede old revision
                superseded_event = event(old_record.subject, actor, "SUPERSEDED", old_record.state, "SUPERSEDED")
                await conn.execute(
                    "UPDATE public.cf_approval_versions SET state = 'SUPERSEDED' WHERE amendment_id = $1 AND revision = $2",
                    subject.amendment_id,
                    old_rev,
                )
                await conn.execute(
                    """
                    INSERT INTO public.cf_audit (
                        event_id, amendment_id, revision, action, previous_state, new_state,
                        actor_id, role, content_digest, idempotency_reference, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7::uuid, $8, $9, $10, $11)
                    """,
                    superseded_event.event_id,
                    subject.amendment_id,
                    old_rev,
                    "SUPERSEDED",
                    old_record.state,
                    "SUPERSEDED",
                    uuid.UUID(actor.actor_id),
                    actor.role,
                    old_record.subject.content_digest,
                    superseded_event.idempotency_reference,
                    now_utc,
                )
            elif subject.amendment_version != 1:
                raise StaleVersion("First amendment version must be one")

            # Insert new approval version
            created_event = event(subject, actor, "CREATED", None, "PENDING_REVIEW")
            draft = subject.draft

            await conn.execute(
                """
                INSERT INTO public.cf_approval_versions (
                    amendment_id, revision, content_digest, state,
                    original_agreement_id, original_agreement_version,
                    client_id, freelancer_id, review_reference, created_at
                ) VALUES ($1, $2, $3, $4, $5::uuid, $6, $7::uuid, $8::uuid, $9, $10)
                """,
                subject.amendment_id,
                subject.amendment_version,
                subject.content_digest,
                "PENDING_REVIEW",
                uuid.UUID(draft.original_agreement_id),
                draft.original_agreement_version,
                uuid.UUID(draft.original_facts.client.id),
                uuid.UUID(draft.original_facts.freelancer.id),
                draft.verified_review.review_reference,
                now_utc,
            )

            # Update or insert approval head
            await conn.execute(
                """
                INSERT INTO public.cf_approval_heads (amendment_id, current_revision, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (amendment_id)
                DO UPDATE SET current_revision = EXCLUDED.current_revision, updated_at = EXCLUDED.updated_at
                """,
                subject.amendment_id,
                subject.amendment_version,
                now_utc,
            )

            # Insert initial CREATED audit event
            await conn.execute(
                """
                INSERT INTO public.cf_audit (
                    event_id, amendment_id, revision, action, previous_state, new_state,
                    actor_id, role, content_digest, idempotency_reference, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7::uuid, $8, $9, $10, $11)
                """,
                created_event.event_id,
                subject.amendment_id,
                subject.amendment_version,
                "CREATED",
                None,
                "PENDING_REVIEW",
                uuid.UUID(actor.actor_id),
                actor.role,
                subject.content_digest,
                created_event.idempotency_reference,
                now_utc,
            )

            result = ApprovalRecord(subject=subject, events=(created_event,))
            return validate_record(result)

    async def transact(
        self,
        amendment_id: UUID,
        operation: Callable[[ApprovalRecord], ApprovalRecord],
    ) -> ApprovalRecord:
        """
        Execute state transition under PostgreSQL row lock (SELECT ... FOR UPDATE).
        Persists decision, state change, and append-only audit event in one commit.
        """
        async for conn in get_connection():
            # 1. Acquire row lock on approval head
            head_row = await conn.fetchrow(
                "SELECT current_revision FROM public.cf_approval_heads WHERE amendment_id = $1 FOR UPDATE",
                amendment_id,
            )
            if not head_row:
                raise NotFound("Unknown amendment")
            current_revision = head_row["current_revision"]

            current = await self._load_record(conn, amendment_id, current_revision)

            # 2. Execute domain transition logic
            result = validate_record(operation(current))

            if result.subject != current.subject or result.events[: len(current.events)] != current.events:
                raise PersistenceError("Transaction cannot replace subject or audit history")

            now_utc = datetime.now(timezone.utc)

            # 3. Identify and insert new decision records
            new_decisions = result.decisions[len(current.decisions) :]
            for d in new_decisions:
                import hashlib
                req_digest = hashlib.sha256(d.request.model_dump_json().encode("utf-8")).hexdigest()
                try:
                    await conn.execute(
                        """
                        INSERT INTO public.cf_decisions (
                            decision_id, amendment_id, revision, actor_id, role,
                            decision, request_digest, rejection_reason, idempotency_key, created_at
                        ) VALUES ($1, $2, $3, $4::uuid, $5, $6, $7, $8, $9, $10)
                        """,
                        d.decision_id,
                        amendment_id,
                        current_revision,
                        uuid.UUID(d.actor_id),
                        d.role,
                        d.request.decision,
                        req_digest,
                        d.request.rejection_reason,
                        d.request.idempotency_key,
                        d.timestamp,
                    )
                except Exception as exc:
                    err_msg = str(exc)
                    if "uq_cf_decisions" in err_msg:
                        raise IdempotencyConflict("Decision conflict or duplicate idempotency key") from None
                    raise

            # 4. Update approval version state
            if result.state != current.state:
                await conn.execute(
                    "UPDATE public.cf_approval_versions SET state = $1 WHERE amendment_id = $2 AND revision = $3",
                    result.state,
                    amendment_id,
                    current_revision,
                )

            # 5. Insert new audit events
            new_events = result.events[len(current.events) :]
            for e in new_events:
                await conn.execute(
                    """
                    INSERT INTO public.cf_audit (
                        event_id, amendment_id, revision, action, previous_state, new_state,
                        actor_id, role, content_digest, idempotency_reference, decision_id, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7::uuid, $8, $9, $10, $11, $12)
                    """,
                    e.event_id,
                    amendment_id,
                    current_revision,
                    e.action,
                    e.previous_state,
                    e.new_state,
                    uuid.UUID(e.actor_id),
                    e.role,
                    e.content_digest,
                    e.idempotency_reference,
                    e.decision_id,
                    e.timestamp,
                )

            # 6. Update head timestamp
            await conn.execute(
                "UPDATE public.cf_approval_heads SET updated_at = $1 WHERE amendment_id = $2",
                now_utc,
                amendment_id,
            )

            return result
