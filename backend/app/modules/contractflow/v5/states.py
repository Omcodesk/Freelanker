"""Terminal decisions and exactly two distinct-party approvals."""

from .errors import InvalidTransition


def next_state(record, actor, decision):
    if record.state in {"REJECTED", "BOTH_APPROVED", "SUPERSEDED"}:
        raise InvalidTransition("Review cycle is terminal")
    if any(d.role == actor.role or d.actor_id == actor.actor_id for d in record.decisions):
        raise InvalidTransition("A party cannot change or repeat its decision with a new key")
    if decision == "REJECT":
        return "REJECTED"
    return "BOTH_APPROVED" if record.decisions else "PARTIALLY_APPROVED"


def remaining(record):
    if record.state in {"REJECTED", "SUPERSEDED", "BOTH_APPROVED"}:
        return ()
    approved = {d.role for d in record.decisions if d.request.decision == "APPROVE"}
    return tuple(role for role in ("CLIENT", "FREELANCER") if role not in approved)
