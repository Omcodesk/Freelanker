"""Server-owned audit metadata; rejection text and contract text are excluded."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from .schemas import AuditEvent


def event(subject, actor, action, previous, new, *, decision=None):
    return AuditEvent(event_id=uuid4(), amendment_id=subject.amendment_id,
                      amendment_version=subject.amendment_version, content_digest=subject.content_digest,
                      actor_id=actor.actor_id, role=actor.role, action=action,
                      previous_state=previous, new_state=new,
                      timestamp=decision.timestamp if decision else datetime.now(timezone.utc),
                      idempotency_reference=sha256(decision.request.idempotency_key.encode()).hexdigest() if decision else None,
                      decision_id=decision.decision_id if decision else None)
