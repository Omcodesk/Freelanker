import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ..demo_v5 import run_demo
from ..v5.errors import (AuthorizationError, IdempotencyConflict, IntegrityError,
                         InvalidTransition, NotFound, PersistenceError, StaleVersion)
from ..v5.repository import InMemoryApprovalRepository
from ..v5.schemas import ApprovalSubject, DecisionRequest, canonical_digest
from ..v5.validation import validate_record
from .v5_support import SyntheticActorResolver, amendment, decision, initialized, workflow


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("first,second", [("client", "freelancer"), ("freelancer", "client")])
def test_both_approval_orders(first, second):
    async def scenario():
        service, initial = await initialized()
        one = await service.submit_decision(decision(initial, key=first), "synthetic-" + first)
        assert one.state == "PARTIALLY_APPROVED"
        assert one.remaining_approvals == (second.upper(),)
        both = await service.submit_decision(decision(initial, key=second), "synthetic-" + second)
        assert both.state == "BOTH_APPROVED" and both.remaining_approvals == ()
        assert not both.effective and both.human_review_required and both.semantic_review_required
        record = await service.repository.load(initial.amendment_id)
        assert record.subject.draft.original_facts == amendment().original_facts
        assert not record.subject.draft.effective and not record.subject.draft.parties_approved
        with pytest.raises(ValidationError):
            record.state = "PENDING_REVIEW"
    run(scenario())


@pytest.mark.parametrize("role", ["client", "freelancer"])
@pytest.mark.parametrize("partial", [False, True])
def test_rejection_is_terminal(role, partial):
    async def scenario():
        service, initial = await initialized()
        other = "freelancer" if role == "client" else "client"
        if partial:
            await service.submit_decision(decision(initial, key="other"), "synthetic-" + other)
        result = await service.submit_decision(decision(initial, choice="REJECT", key="reject", reason="Synthetic concern"), "synthetic-" + role)
        assert result.state == "REJECTED" and not result.remaining_approvals
        with pytest.raises(InvalidTransition):
            await service.submit_decision(decision(initial, key="late"), "synthetic-" + other)
    run(scenario())


@pytest.mark.parametrize("choice", ["APPROVE", "REJECT"])
def test_both_approved_terminal_except_new_version(choice):
    async def scenario():
        service, initial = await initialized()
        await service.submit_decision(decision(initial, key="c"), "synthetic-client")
        await service.submit_decision(decision(initial, key="f"), "synthetic-freelancer")
        with pytest.raises(InvalidTransition):
            await service.submit_decision(decision(initial, choice=choice, key="new"), "synthetic-client")
        revised = await service.register_amendment(amendment(True), 2, "synthetic-client")
        assert revised.state == "PENDING_REVIEW" and len(revised.remaining_approvals) == 2
    run(scenario())


@pytest.mark.parametrize("context", [None, "unknown", {"role": "CLIENT", "is_authenticated": True},
                                       {"approved_by_client": True}, "synthetic-client-wrong"])
def test_untrusted_context_is_not_authentication(context):
    async def scenario():
        service, initial = await initialized()
        with pytest.raises(AuthorizationError):
            await service.submit_decision(decision(initial), context)
        assert (await service.repository.load(initial.amendment_id)).state == "PENDING_REVIEW"
        with pytest.raises(AuthorizationError):
            await service.get_status(initial.amendment_id, context)
        with pytest.raises(AuthorizationError):
            await service.get_history(initial.amendment_id, context)
    run(scenario())


@pytest.mark.parametrize("field,value", [("role", "FREELANCER"), ("actor_id", "unknown"),
    ("party_id", "unknown"), ("project_id", "wrong"), ("agreement_id", "wrong"),
    ("amendment_id", uuid4()), ("amendment_version", 2), ("content_digest", "0" * 64),
    ("acting_on_own_behalf", False), ("boundary", "wrong")])
def test_even_resolved_actor_must_match_subject(field, value):
    class Forged(SyntheticActorResolver):
        async def resolve(self, context, subject):
            actor = await super().resolve(context, subject)
            return actor.model_copy(update={field: value})
    async def scenario():
        service, initial = await initialized()
        service.actor_resolver = Forged()
        with pytest.raises(AuthorizationError):
            await service.submit_decision(decision(initial), "synthetic-client")
        assert not (await service.repository.load(initial.amendment_id)).decisions
    run(scenario())


@pytest.mark.parametrize("field", ["role", "actor_id", "timestamp", "is_authenticated", "is_owner",
                                  "approved_by_client", "approved_by_freelancer", "effective"])
def test_caller_authority_fields_forbidden(field):
    service, initial = run(initialized())
    data = decision(initial).model_dump(mode="json")
    data[field] = True
    with pytest.raises(ValidationError):
        run(service.submit_decision(data, "synthetic-client"))


@pytest.mark.parametrize("reason", [123, "", "x" * 1001, "private\nheader"])
def test_rejection_reason_type_and_size(reason):
    _, initial = run(initialized())
    with pytest.raises(ValidationError):
        decision(initial, choice="REJECT", reason=reason)


def test_approval_cannot_carry_rejection_reason():
    _, initial = run(initialized())
    with pytest.raises(ValidationError):
        decision(initial, reason="reason")


@pytest.mark.parametrize("kind", ["version", "digest", "unknown"])
def test_stale_or_unknown_subject(kind):
    async def scenario():
        service, initial = await initialized()
        request = decision(initial)
        updates = {"version": {"expected_version": 2}, "digest": {"expected_digest": "0" * 64},
                   "unknown": {"amendment_id": uuid4()}}[kind]
        with pytest.raises(NotFound if kind == "unknown" else StaleVersion):
            await service.submit_decision(request.model_copy(update=updates), "synthetic-client")
        assert not (await service.repository.load(initial.amendment_id)).decisions
    run(scenario())


def test_snapshot_digest_recomputed_and_full_artifact_bound():
    draft = amendment()
    subject = ApprovalSubject.from_draft(draft, 1)
    assert subject.content_digest == canonical_digest(1, draft)
    assert canonical_digest(2, draft) != subject.content_digest
    assert canonical_digest(1, amendment(True)) != subject.content_digest
    assert ApprovalSubject.model_validate_json(subject.model_dump_json()) == subject
    data = subject.model_dump(mode="json")
    data["content_digest"] = "0" * 64
    with pytest.raises(IntegrityError):
        ApprovalSubject.model_validate(data)
    data = subject.model_dump(mode="json")
    data["source_manifest"][0][1] += " fabricated"
    with pytest.raises(IntegrityError):
        ApprovalSubject.model_validate(data)


@pytest.mark.parametrize("field,value", [("rendered_text", "changed"), ("unresolved_terms", ("changed",)),
    ("project_id", "changed"), ("original_agreement_version", 2), ("assessment_version", 2),
    ("human_review_required", False), ("semantic_review_required", False), ("effective", True)])
def test_digest_binds_all_serialized_material_and_review_fields(field, value):
    original = amendment()
    changed = original.model_copy(update={field: value})
    assert canonical_digest(1, original) != canonical_digest(1, changed)
    with pytest.raises((IntegrityError, ValidationError, ValueError)):
        ApprovalSubject.from_draft(changed, 1)


def test_concurrent_approval_and_revision_cannot_reuse_old_approval():
    async def scenario():
        service, initial = await initialized()
        results = await asyncio.gather(
            service.register_amendment(amendment(True), 2, "synthetic-client"),
            service.submit_decision(decision(initial), "synthetic-client"), return_exceptions=True)
        assert any(isinstance(r, StaleVersion) for r in results)
        current = await service.repository.load(initial.amendment_id)
        assert current.subject.amendment_version == 2 and not current.decisions
        assert current.state == "PENDING_REVIEW"
    run(scenario())


@pytest.mark.parametrize("field,value", [("effective", True), ("status", "ACTIVE"),
    ("rendered_text", "tampered"), ("human_review_required", False), ("semantic_review_required", False),
    ("parties_approved", True), ("unresolved_terms", ()), ("original_agreement_version", 99)])
def test_invalid_or_active_v4_copy_rejected_before_publication(field, value):
    service = workflow()
    with pytest.raises(IntegrityError):
        run(service.register_amendment(amendment().model_copy(update={field: value}), 1, "synthetic-client"))
    assert not service.repository._records


def test_same_party_identity_cannot_count_twice():
    draft = amendment()
    project = draft.original_facts.model_copy(update={"freelancer": draft.original_facts.client})
    draft = draft.model_copy(update={"original_facts": project})
    service = workflow()
    with pytest.raises(IntegrityError):
        run(service.register_amendment(draft, 1, "synthetic-client"))


def test_current_trusted_review_rechecked():
    class Revoked:
        boundary_reference = "SYNTHETIC-TEST-REVIEW-STORE"
        async def verify_review(self, reference):
            raise RuntimeError("PRIVATE details")
    service = workflow(verifier=Revoked())
    with pytest.raises(IntegrityError) as caught:
        run(service.register_amendment(amendment(), 1, "synthetic-client"))
    assert "PRIVATE" not in str(caught.value)
    assert not service.repository._records


def test_revision_preserves_old_audit_and_resets_approvals():
    async def scenario():
        service, initial = await initialized()
        await service.submit_decision(decision(initial), "synthetic-client")
        old = await service.repository.load(initial.amendment_id)
        revised = await service.register_amendment(amendment(True), 2, "synthetic-freelancer")
        current = await service.repository.load(initial.amendment_id)
        assert not current.decisions and current.state == "PENDING_REVIEW"
        archived = service.repository._records[(initial.amendment_id, 1)]
        assert archived.state == "SUPERSEDED" and archived.decisions == old.decisions
        assert archived.events[:-1] == old.events
        assert revised.content_digest != initial.content_digest
        with pytest.raises(StaleVersion):
            await service.submit_decision(decision(initial), "synthetic-client")
        history = await service.get_history(initial.amendment_id, "synthetic-client")
        assert [e.action for e in history] == ["CREATED", "APPROVE", "SUPERSEDED", "CREATED"]
        assert list(history) == sorted(history, key=lambda e: e.timestamp)
    run(scenario())


@pytest.mark.parametrize("version,revised", [(1, True), (3, True), (2, False)])
def test_revision_requires_next_version_and_changed_artifact(version, revised):
    service, initial = run(initialized())
    with pytest.raises(StaleVersion):
        run(service.register_amendment(amendment(revised), version, "synthetic-client"))
    assert len(service.repository._records) == 1


@pytest.mark.parametrize("choice", ["APPROVE", "REJECT"])
def test_idempotent_replay_same_key_no_duplicate_audit(choice):
    async def scenario():
        service, initial = await initialized()
        request = decision(initial, choice=choice)
        first = await service.submit_decision(request, "synthetic-client")
        before = await service.get_history(initial.amendment_id, "synthetic-client")
        assert await service.submit_decision(request, "synthetic-client") == first
        assert await service.get_history(initial.amendment_id, "synthetic-client") == before
        with pytest.raises(InvalidTransition):
            await service.submit_decision(request.model_copy(update={"idempotency_key": "another"}), "synthetic-client")
    run(scenario())


@pytest.mark.parametrize("kind", ["decision", "reason", "actor"])
def test_idempotency_conflicts(kind):
    async def scenario():
        service, initial = await initialized()
        request = decision(initial, choice="REJECT", reason="first")
        await service.submit_decision(request, "synthetic-client")
        changed = decision(initial) if kind == "decision" else decision(initial, choice="REJECT", reason="second" if kind == "reason" else "first")
        with pytest.raises(IdempotencyConflict):
            await service.submit_decision(changed, "synthetic-freelancer" if kind == "actor" else "synthetic-client")
    run(scenario())


def test_concurrent_distinct_approvals_and_duplicate_requests():
    async def scenario():
        service, initial = await initialized()
        await asyncio.gather(*(service.submit_decision(decision(initial, key=role), "synthetic-" + role)
                               for role in ["client", "freelancer", "client", "freelancer"]))
        record = await service.repository.load(initial.amendment_id)
        assert record.state == "BOTH_APPROVED" and len(record.decisions) == 2
        assert len(record.events) == 3
    run(scenario())


def test_cross_thread_concurrency_no_lost_update():
    service, initial = run(initialized())
    def approve(role):
        return run(service.submit_decision(decision(initial, key=role), "synthetic-" + role))
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(approve, ["client", "freelancer"]))
    assert run(service.get_status(initial.amendment_id, "synthetic-client")).state == "BOTH_APPROVED"


def test_concurrent_conflicting_decisions_first_committed_wins():
    async def scenario():
        service, initial = await initialized()
        results = await asyncio.gather(service.submit_decision(decision(initial, key="a"), "synthetic-client"),
            service.submit_decision(decision(initial, choice="REJECT", key="r"), "synthetic-client"), return_exceptions=True)
        assert sum(isinstance(r, InvalidTransition) for r in results) == 1
        record = await service.repository.load(initial.amendment_id)
        assert len(record.decisions) == 1 and len(record.events) == 2
        assert record.state in {"PARTIALLY_APPROVED", "REJECTED"}
    run(scenario())


@pytest.mark.parametrize("after_assignment", [False, True])
def test_storage_or_audit_commit_failure_rolls_back(after_assignment):
    service, initial = run(initialized())
    before = run(service.repository.load(initial.amendment_id))
    def fail(replacement):
        if after_assignment:
            service.repository._records = replacement
        raise RuntimeError("PRIVATE persistence body")
    service.repository._commit = fail
    with pytest.raises(PersistenceError) as caught:
        run(service.submit_decision(decision(initial), "synthetic-client"))
    assert "PRIVATE" not in str(caught.value)
    assert run(service.repository.load(initial.amendment_id)) == before


def test_revision_commit_failure_rolls_back_supersession_and_creation():
    service, initial = run(initialized())
    before = dict(service.repository._records)
    def fail(replacement):
        raise OSError("synthetic storage failure")
    service.repository._commit = fail
    with pytest.raises(PersistenceError):
        run(service.register_amendment(amendment(True), 2, "synthetic-client"))
    assert service.repository._records == before


def test_repository_load_failure_closed():
    service, initial = run(initialized())
    async def fail(amendment_id):
        raise OSError("PRIVATE")
    service.repository.load = fail
    with pytest.raises(PersistenceError):
        run(service.submit_decision(decision(initial), "synthetic-client"))


def test_audit_metadata_utc_ordered_and_no_contract_or_reason():
    async def scenario():
        service, initial = await initialized()
        await service.submit_decision(decision(initial, choice="REJECT", reason="PRIVATE REASON", key="PRIVATE KEY"), "synthetic-client")
        history = await service.get_history(initial.amendment_id, "synthetic-client")
        assert len(history) == 2 and all(e.timestamp.tzinfo == timezone.utc for e in history)
        wire = json.dumps([e.model_dump(mode="json") for e in history])
        assert all(s not in wire for s in ("PRIVATE REASON", "PRIVATE KEY", "rendered_text", "api_key", "bakery website"))
        assert history[1].previous_state == "PENDING_REVIEW" and history[1].new_state == "REJECTED"
        assert history[1].decision_id is not None
    run(scenario())


def test_tampered_storage_detected_and_history_not_rewritten():
    service, initial = run(initialized())
    key = (initial.amendment_id, 1)
    old = service.repository._records[key]
    service.repository._records[key] = old.model_copy(update={"state": "BOTH_APPROVED"})
    with pytest.raises(IntegrityError):
        run(service.get_status(initial.amendment_id, "synthetic-client"))
    with pytest.raises(IntegrityError):
        validate_record(old.model_copy(update={"events": ()}))


def test_offline_demo_has_no_network(monkeypatch):
    import socket
    import httpx
    def forbidden(*args, **kwargs):
        pytest.fail("Network forbidden")
    async def async_forbidden(*args, **kwargs):
        pytest.fail("Network forbidden")
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "send", async_forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    report = run(run_demo())
    assert report["initial"]["state"] == "PENDING_REVIEW"
    assert report["client"]["state"] == "PARTIALLY_APPROVED"
    assert report["both"]["state"] == "BOTH_APPROVED"
    assert report["decision_event_count"] == 2
    assert report["stale_attempt"] == "REJECTED_STALE_VERSION"
    assert report["rejection_state"] == "REJECTED"
    assert report["original_agreement_unchanged"] and not report["effective"]
