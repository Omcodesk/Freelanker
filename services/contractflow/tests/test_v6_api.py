import asyncio
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ..api.router import router
from ..errors import ProviderError, GenerationTimeout, InvalidProviderOutput
from .v6_support import app, runtime, seed

PREFIX = "/api/v1/contractflow"
HEADERS = {"Authorization": "Bearer synthetic-client"}


@pytest.fixture(autouse=True)
def block_external_clients(monkeypatch):
    import groq
    import socket
    import httpx
    original = httpx.Client.send
    def forbidden(*args, **kwargs):
        pytest.fail("External clients are forbidden in V6 offline tests")
    def asgi_only(self, *args, **kwargs):
        assert type(self._transport).__module__ == "starlette.testclient"
        return original(self, *args, **kwargs)
    monkeypatch.setattr(groq, "AsyncGroq", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(httpx.Client, "send", asgi_only)


def project_body(rt):
    return {"project_id": rt.workbridge.snapshot.project.project_id, "expected_source_version": 1}


def client(rt=None):
    return TestClient(app(rt), raise_server_exceptions=True)


def test_default_missing_auth_and_unwired_runtime_fail_closed():
    c = client()
    response = c.post(PREFIX + "/contracts/generate", json={})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    response = c.post(PREFIX + "/contracts/generate", json={}, headers=HEADERS)
    assert response.status_code == 503


@pytest.mark.parametrize("token,status", [("synthetic-outsider", 404), ("wrong", 401)])
def test_authentication_and_cross_project_isolation(token, status):
    rt = runtime()
    response = client(rt).post(PREFIX + "/contracts/generate", json=project_body(rt),
                                headers={"Authorization": "Bearer " + token})
    assert response.status_code == status and not rt.provider.calls


@pytest.mark.parametrize("field", ["budget", "scope", "client", "role", "reviewed", "approved", "is_authenticated"])
def test_caller_facts_and_authority_rejected(field):
    rt = runtime()
    body = {**project_body(rt), field: "PRIVATE"}
    response = client(rt).post(PREFIX + "/contracts/generate", json=body, headers=HEADERS)
    assert response.status_code == 422 and "PRIVATE" not in response.text
    assert not rt.provider.calls


@pytest.mark.parametrize("field,value", [("expected_source_version", 0), ("expected_source_version", True),
                                        ("project_id", ""), ("project_id", 123)])
def test_invalid_schema(field, value):
    rt = runtime()
    response = client(rt).post(PREFIX + "/contracts/generate", json={**project_body(rt), field: value}, headers=HEADERS)
    assert response.status_code == 422 and not rt.provider.calls


@pytest.mark.parametrize("kind,path", [("CONTRACT", "/contracts/generate"), ("AGREEMENT", "/agreements/draft")])
def test_trusted_project_generation(kind, path):
    rt = runtime()
    response = client(rt).post(PREFIX + path, json=project_body(rt), headers=HEADERS)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["kind"] == kind
    assert json.loads(data["payload_json"])["authoritative_data"]["budget"] == "1200.00"
    assert len(rt.provider.calls) == 1 and len(rt.artifacts.records) == 1


@pytest.mark.parametrize("error,status", [(ProviderError("PRIVATE"), 502),
    (TimeoutError("PRIVATE"), 503), (InvalidProviderOutput("PRIVATE"), 502)])
def test_provider_error_mapping_no_raw_details(error, status):
    rt = runtime()
    rt.provider.error = error
    response = client(rt).post(PREFIX + "/contracts/generate", json=project_body(rt), headers=HEADERS)
    assert response.status_code == status
    assert "PRIVATE" not in response.text and not rt.artifacts.records


def test_body_size_and_malformed_json_are_sanitized():
    rt = runtime()
    c = client(rt)
    result = c.post(PREFIX + "/contracts/generate", content=b"x" * 131073, headers=HEADERS)
    assert result.status_code == 413
    result = c.post(PREFIX + "/contracts/generate", content=b'{"PRIVATE":', headers={**HEADERS, "Content-Type": "application/json"})
    assert result.status_code == 422 and "PRIVATE" not in result.text


def test_route_registration_and_openapi_are_unique():
    application = app(runtime())
    routes = [(r.path, tuple(sorted(r.methods))) for r in application.routes if hasattr(r, "methods")]
    assert len(routes) == len(set(routes))
    assert len(router.routes) == 8
    assert len(application.openapi()["paths"]) == 8


def test_unknown_and_forbidden_approval_reads():
    rt = runtime()
    c = client(rt)
    result = c.get(PREFIX + f"/amendments/{uuid4()}/status", headers=HEADERS)
    assert result.status_code == 404
    item = asyncio.run(seed(rt))
    registered = c.post(PREFIX + f"/amendments/{item.artifact_id}/register", json={
        "expected_version": 1, "expected_digest": item.content_digest}, headers=HEADERS)
    assert registered.status_code == 200, registered.text
    for suffix in ("status", "history"):
        result = c.get(PREFIX + f"/amendments/{item.artifact_id}/{suffix}",
                        headers={"Authorization": "Bearer synthetic-outsider"})
        assert result.status_code == 403
