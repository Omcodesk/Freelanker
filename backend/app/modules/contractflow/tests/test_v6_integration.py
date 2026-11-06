import asyncio
import json

import pytest

from ..api.schemas import DecisionBody
from ..v5.schemas import DecisionRequest
from ..v5.errors import AuthorizationError, InvalidTransition, PersistenceError
from .test_v6_api import client, project_body, PREFIX, HEADERS, block_external_clients
from .v6_support import runtime, seed
from .v5_support import amendment

FREELANCER = {"Authorization": "Bearer synthetic-freelancer"}


def registered():
    rt = runtime()
    artifact = asyncio.run(seed(rt))
    c = client(rt)
    result = c.post(PREFIX + f"/amendments/{artifact.artifact_id}/register", json={
        "expected_version": 1, "expected_digest": artifact.content_digest}, headers=HEADERS)
    assert result.status_code == 200, result.text
    return rt, c, artifact, result.json()


def decision_body(status, key="synthetic-client-decision", choice="APPROVE"):
    return {"expected_version": status["amendment_version"], "expected_digest": status["content_digest"],
            "decision": choice, "idempotency_key": key}


def test_all_pipelines_through_http_fake_provider_and_authoritative_snapshots():
    rt = runtime()
    c = client(rt)
    project = project_body(rt)
    for path in ("/contracts/generate", "/agreements/draft"):
        result = c.post(PREFIX + path, json=project, headers=HEADERS)
        assert result.status_code == 200, result.text
    result = c.post(PREFIX + "/scope/assess", json={**project,
        "client_request": "Add an online ordering system with payment integration."}, headers=HEADERS)
    assert result.status_code == 200, result.text
    assessment = result.json()
    result = c.post(PREFIX + "/amendments/generate", json={**project,
        "assessment_id": assessment["artifact_id"], "review_reference": "synthetic-review:" + assessment["artifact_id"]}, headers=HEADERS)
    assert result.status_code == 200, result.text
    artifact = result.json()
    draft = json.loads(artifact["payload_json"])
    before = draft["original_facts"]
    path = PREFIX + f'/amendments/{artifact["artifact_id"]}'
    result = c.post(path + "/register", json={"expected_version": 1, "expected_digest": artifact["content_digest"]}, headers=HEADERS)
    assert result.status_code == 200, result.text
    status = result.json()
    result = c.post(path + "/decisions", json=decision_body(status), headers=HEADERS)
    assert result.status_code == 200 and result.json()["state"] == "PARTIALLY_APPROVED"
    result = c.post(path + "/decisions", json=decision_body(status, "synthetic-freelancer-decision"), headers=FREELANCER)
    assert result.status_code == 200 and result.json()["state"] == "BOTH_APPROVED"
    assert not result.json()["effective"] and result.json()["human_review_required"]
    assert result.json()["semantic_review_required"]
    history = c.get(path + "/history", headers=HEADERS)
    assert history.status_code == 200
    assert [e["action"] for e in history.json()] == ["CREATED", "APPROVE", "APPROVE"]
    assert c.get(path + "/status", headers=HEADERS).json()["state"] == "BOTH_APPROVED"
    assert len(rt.provider.calls) == 4 and len(rt.artifacts.records) == 4
    assert json.loads(rt.artifacts.records[next(key for key in rt.artifacts.records if str(key) == artifact["artifact_id"])].payload_json)["original_facts"] == before


@pytest.mark.parametrize("mode", ["missing", "revoked", "stale", "digest", "version"])
def test_amendment_review_rechecked_at_each_decision(mode):
    rt, c, artifact, status = registered()
    rt.reviews.mode = mode
    response = c.post(PREFIX + f"/amendments/{artifact.artifact_id}/decisions", json=decision_body(status), headers=HEADERS)
    assert response.status_code == 403
    record = asyncio.run(rt.approval_repository.load(artifact.artifact_id))
    assert record.state == "PENDING_REVIEW" and len(record.events) == 1


@pytest.mark.parametrize("mode", ["missing", "revoked", "stale", "digest", "version"])
def test_invalid_review_prevents_registration(mode):
    rt = runtime()
    artifact = asyncio.run(seed(rt))
    rt.reviews.mode = mode
    response = client(rt).post(PREFIX + f"/amendments/{artifact.artifact_id}/register", json={
        "expected_version": 1, "expected_digest": artifact.content_digest}, headers=HEADERS)
    assert response.status_code == 403 and not rt.approval_repository._records


def test_assessment_review_revocation_blocks_later_decision():
    rt, c, artifact, status = registered()
    rt.assessment_reviews.records.clear()
    result = c.post(PREFIX + f"/amendments/{artifact.artifact_id}/decisions", json=decision_body(status), headers=HEADERS)
    assert result.status_code == 403
    assert not asyncio.run(rt.approval_repository.load(artifact.artifact_id)).decisions


def test_rejection_replay_and_conflict_http_mapping():
    rt, c, artifact, status = registered()
    path = PREFIX + f"/amendments/{artifact.artifact_id}/decisions"
    body = decision_body(status, choice="REJECT")
    assert c.post(path, json=body, headers=HEADERS).json()["state"] == "REJECTED"
    assert c.post(path, json=body, headers=HEADERS).status_code == 200
    assert len(asyncio.run(rt.approval_repository.load(artifact.artifact_id)).events) == 2
    assert c.post(path, json={**body, "decision": "APPROVE"}, headers=HEADERS).status_code == 409
    assert c.post(path, json=decision_body(status, "other"), headers=FREELANCER).status_code == 409


@pytest.mark.parametrize("update", [{"role": "CLIENT"}, {"approved": True}, {"timestamp": "now"},
                                  {"rejection_reason": "PRIVATE"}, {"expected_version": 0}])
def test_decision_schema_rejects_authority_and_invalid_reason(update):
    rt, c, artifact, status = registered()
    response = c.post(PREFIX + f"/amendments/{artifact.artifact_id}/decisions",
                        json={**decision_body(status), **update}, headers=HEADERS)
    assert response.status_code == 422 and "PRIVATE" not in response.text


def test_revision_invalidates_old_decisions_and_requires_fresh_review():
    rt, c, artifact, status = registered()
    principal = asyncio.run(rt.auth.authenticate("synthetic-client"))
    revised = asyncio.run(rt.artifacts.save("AMENDMENT", rt.workbridge.snapshot, amendment(True), principal))
    path = PREFIX + f"/amendments/{artifact.artifact_id}"
    assert c.post(path + "/decisions", json=decision_body(status), headers=HEADERS).status_code == 403
    new = c.post(path + "/register", json={"expected_version": 2, "expected_digest": revised.content_digest}, headers=HEADERS)
    assert new.status_code == 200 and new.json()["state"] == "PENDING_REVIEW"
    assert c.post(path + "/decisions", json=decision_body(status), headers=HEADERS).status_code == 409
    assert rt.approval_repository._records[(artifact.artifact_id, 1)].state == "SUPERSEDED"


def test_concurrent_decisions_serialized_by_test_transaction_fake():
    async def scenario():
        rt = runtime()
        item = await seed(rt)
        client_principal = await rt.auth.authenticate("synthetic-client")
        freelancer = await rt.auth.authenticate("synthetic-freelancer")
        from ..api.schemas import RegisterRequest
        status = await rt.register(item.artifact_id, RegisterRequest(expected_version=1, expected_digest=item.content_digest), client_principal)
        def body(key):
            return DecisionRequest(amendment_id=item.artifact_id, expected_version=1,
                expected_digest=status.content_digest, decision="APPROVE", idempotency_key=key)
        await asyncio.gather(rt.decision(body("c"), client_principal), rt.decision(body("f"), freelancer), rt.decision(body("c"), client_principal))
        record = await rt.approval_repository.load(item.artifact_id)
        assert record.state == "BOTH_APPROVED" and len(record.decisions) == 2 and len(record.events) == 3
    asyncio.run(scenario())


def test_approval_failure_rolls_back_audit_and_state():
    rt, c, artifact, status = registered()
    before = dict(rt.approval_repository._records)
    def fail(replacement):
        raise OSError("PRIVATE database failure")
    rt.approval_repository._commit = fail
    result = c.post(PREFIX + f"/amendments/{artifact.artifact_id}/decisions", json=decision_body(status), headers=HEADERS)
    assert result.status_code == 503 and "PRIVATE" not in result.text
    assert rt.approval_repository._records == before
