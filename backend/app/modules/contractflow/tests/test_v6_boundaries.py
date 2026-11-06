import asyncio

import pytest
from pydantic import ValidationError

from ..integrations.contracts import SourceSnapshot
from ..persistence.artifacts import StoredArtifact
from .test_v6_api import client, project_body, PREFIX, HEADERS, block_external_clients
from .v6_support import runtime, seed


@pytest.mark.parametrize("code,status", [("NOT_FOUND", 404), ("FORBIDDEN", 403), ("UNAVAILABLE", 503),
                                       ("INVALID_SOURCE", 503), ("STALE_SOURCE", 409)])
def test_workbridge_failure_mapping(code, status):
    rt = runtime()
    rt.workbridge.error = code
    response = client(rt).post(PREFIX + "/contracts/generate", json=project_body(rt), headers=HEADERS)
    assert response.status_code == status and not rt.provider.calls and not rt.artifacts.records


def test_expected_source_version_not_silently_replaced():
    rt = runtime()
    response = client(rt).post(PREFIX + "/contracts/generate",
                                json={**project_body(rt), "expected_source_version": 2}, headers=HEADERS)
    assert response.status_code == 409 and not rt.provider.calls


def test_missing_original_agreement_blocks_scope_assessment():
    rt = runtime()
    rt.workbridge.snapshot = rt.workbridge.snapshot.model_copy(update={"agreement": None})
    response = client(rt).post(PREFIX + "/scope/assess", json={**project_body(rt), "client_request": "Untrusted request"}, headers=HEADERS)
    assert response.status_code == 409 and not rt.provider.calls


@pytest.mark.parametrize("field", ["milestones", "client", "budget", "deadline", "scope"])
def test_incomplete_authoritative_source_rejected(field):
    rt = runtime()
    data = rt.workbridge.snapshot.model_dump(mode="json")
    del data["project"][field]
    class InvalidSource:
        def model_dump_json(self):
            import json
            return json.dumps(data)
    rt.workbridge.snapshot = InvalidSource()
    response = client(rt).post(PREFIX + "/contracts/generate", json={
        "project_id": data["agreement"]["project"]["project_id"], "expected_source_version": 1}, headers=HEADERS)
    assert response.status_code == 503 and not rt.provider.calls


def test_wrong_source_project_identifier_fails_closed():
    rt = runtime()
    response = client(rt).post(PREFIX + "/contracts/generate", json={
        **project_body(rt), "project_id": "OTHER-PROJECT"}, headers=HEADERS)
    assert response.status_code == 404 and not rt.provider.calls


def test_conflicting_agreement_source_identity_rejected():
    rt = runtime()
    data = rt.workbridge.snapshot.model_dump(mode="json")
    data["agreement"]["project"]["client"]["id"] = "OTHER-CLIENT"
    with pytest.raises(ValidationError):
        SourceSnapshot.model_validate(data)


def test_artifact_persistence_failure_not_reported_as_success():
    rt = runtime()
    rt.artifacts.fail_write = True
    response = client(rt).post(PREFIX + "/contracts/generate", json=project_body(rt), headers=HEADERS)
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert not rt.artifacts.records and len(rt.provider.calls) == 1


@pytest.mark.parametrize("field,value", [("content_digest", "0" * 64), ("payload_json", "{}"),
                                      ("artifact_version", 2), ("kind", "ASSESSMENT")])
def test_tampered_stored_artifact_rejected(field, value):
    rt = runtime()
    item = asyncio.run(seed(rt))
    forged = item.model_copy(update={field: value})
    with pytest.raises((ValueError, ValidationError)):
        StoredArtifact.model_validate_json(forged.model_dump_json())


def test_stale_source_prevents_registration_and_no_decisions_created():
    rt = runtime()
    item = asyncio.run(seed(rt))
    rt.workbridge.snapshot = rt.workbridge.snapshot.model_copy(update={"source_version": 2})
    response = client(rt).post(PREFIX + f"/amendments/{item.artifact_id}/register", json={
        "expected_version": 1, "expected_digest": item.content_digest}, headers=HEADERS)
    assert response.status_code == 409 and not rt.approval_repository._records


def test_archive_digest_not_trusted_on_registration():
    rt = runtime()
    item = asyncio.run(seed(rt))
    response = client(rt).post(PREFIX + f"/amendments/{item.artifact_id}/register", json={
        "expected_version": 1, "expected_digest": "0" * 64}, headers=HEADERS)
    assert response.status_code == 409 and not rt.approval_repository._records


def test_fail_closed_if_runtime_transaction_dependency_missing():
    rt = runtime()
    rt.transactions = None
    response = client(rt).post(PREFIX + "/contracts/generate", json=project_body(rt), headers=HEADERS)
    assert response.status_code == 503 and not rt.provider.calls


def test_source_change_during_generation_is_not_saved_as_current():
    rt = runtime()
    original = rt.provider.generate
    async def changed(**kwargs):
        output = await original(**kwargs)
        rt.workbridge.snapshot = rt.workbridge.snapshot.model_copy(update={"source_version": 2})
        return output
    rt.provider.generate = changed
    response = client(rt).post(PREFIX + "/contracts/generate", json=project_body(rt), headers=HEADERS)
    assert response.status_code == 409 and not rt.artifacts.records
