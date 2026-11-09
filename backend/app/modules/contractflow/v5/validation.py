"""Revalidate storage objects and replay the recorded state, failing closed."""

from .errors import IntegrityError, StaleVersion
from hashlib import sha256
from .schemas import ApprovalRecord


def validate_record(record):
    try:
        result = ApprovalRecord.model_validate_json(record.model_dump_json())
        subject = result.subject
        if not result.events or result.events[0].action != "CREATED":
            raise IntegrityError("Missing creation event")
        state = "PENDING_REVIEW"
        first = result.events[0]
        if first.previous_state is not None or first.new_state != state:
            raise IntegrityError("Invalid initial state")
        roles, actors, keys = set(), set(), set()
        decision_events = []
        event_ids = set()
        for index, item in enumerate(result.events):
            party = subject.draft.original_facts.client if item.role == "CLIENT" else subject.draft.original_facts.freelancer
            if item.event_id in event_ids or item.actor_id != party.id:
                raise IntegrityError("Invalid audit identity")
            event_ids.add(item.event_id)
            if ((item.amendment_id, item.amendment_version, item.content_digest) !=
                    (subject.amendment_id, subject.amendment_version, subject.content_digest)):
                raise IntegrityError("Audit subject mismatch")
            if index and item.timestamp < result.events[index - 1].timestamp:
                raise IntegrityError("Audit order mismatch")
            if not index:
                continue
            if item.previous_state != state or state == "SUPERSEDED":
                raise IntegrityError("Audit state mismatch")
            if item.action == "SUPERSEDED":
                state = "SUPERSEDED"
            elif item.action in {"APPROVE", "REJECT"}:
                if state in {"REJECTED", "BOTH_APPROVED"}:
                    raise IntegrityError("Decision after terminal state")
                state = "REJECTED" if item.action == "REJECT" else (
                    "BOTH_APPROVED" if decision_events else "PARTIALLY_APPROVED")
                decision_events.append(item)
            else:
                raise IntegrityError("Invalid audit action")
            if item.new_state != state:
                raise IntegrityError("Invalid recorded transition")
        if state != result.state or len(decision_events) != len(result.decisions):
            raise IntegrityError("Record state mismatch")
        for decision, audit in zip(result.decisions, decision_events):
            request = decision.request
            party = subject.draft.original_facts.client if decision.role == "CLIENT" else subject.draft.original_facts.freelancer
            if (decision.role in roles or decision.actor_id in actors or request.idempotency_key in keys
                    or decision.actor_id != party.id
                    or (request.amendment_id, request.expected_version, request.expected_digest) !=
                    (subject.amendment_id, subject.amendment_version, subject.content_digest)
                    or (audit.decision_id, audit.actor_id, audit.role, audit.timestamp, audit.action, audit.idempotency_reference) !=
                    (decision.decision_id, decision.actor_id, decision.role, decision.timestamp, request.decision, sha256(request.idempotency_key.encode()).hexdigest())):
                raise IntegrityError("Decision integrity failed")
            roles.add(decision.role)
            actors.add(decision.actor_id)
            keys.add(request.idempotency_key)
        return result
    except IntegrityError:
        raise
    except Exception:
        raise IntegrityError("Stored approval record is invalid") from None


def match_request(request, record):
    if (request.amendment_id, request.expected_version, request.expected_digest) != (
            record.subject.amendment_id, record.subject.amendment_version, record.subject.content_digest):
        raise StaleVersion("Amendment version or content differs")
