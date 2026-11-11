"""Phase 2 runtime tests: Groq-disabled behavior, /health readiness, and env loading."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from .. import main as service_main
from ..adapters.db import _build_pool_kwargs
from ..config import is_groq_enabled, load_service_env
from .test_v6_api import HEADERS, PREFIX, block_external_clients, client, project_body
from .v6_support import runtime, seed

FREELANCER = {"Authorization": "Bearer synthetic-freelancer"}


def test_groq_disabled_blocks_ai_generation_but_allows_workflow_endpoints():
    rt = runtime()
    rt.provider = None
    item = asyncio.run(seed(rt))
    c = client(rt)

    # AI generation endpoints fail closed with 503 UNAVAILABLE when Groq is disabled
    ai_calls = [
        ("/contracts/generate", project_body(rt)),
        ("/agreements/draft", project_body(rt)),
        ("/scope/assess", {**project_body(rt), "client_request": "Add analytics export"}),
        ("/amendments/generate", {
            **project_body(rt),
            "assessment_id": str(item.artifact_id),
            "review_reference": "synthetic-review:" + str(item.artifact_id),
        }),
    ]
    for path, body in ai_calls:
        resp = c.post(PREFIX + path, json=body, headers=HEADERS)
        assert resp.status_code == 503, f"Expected 503 for {path}, got {resp.status_code}: {resp.text}"
        assert resp.json() == {"error": {"code": "UNAVAILABLE"}}

    # Unauthenticated and outsider callers still enforce auth/isolation before AI availability
    assert c.post(PREFIX + "/contracts/generate", json=project_body(rt)).status_code == 401
    assert c.post(
        PREFIX + "/contracts/generate",
        json=project_body(rt),
        headers={"Authorization": "Bearer synthetic-outsider"},
    ).status_code == 404

    # Non-AI endpoints remain fully operational without Groq
    reg = c.post(
        PREFIX + f"/amendments/{item.artifact_id}/register",
        json={"expected_version": 1, "expected_digest": item.content_digest},
        headers=HEADERS,
    )
    assert reg.status_code == 200, reg.text
    status_data = reg.json()
    assert status_data["state"] == "PENDING_REVIEW"

    dec1 = c.post(
        PREFIX + f"/amendments/{item.artifact_id}/decisions",
        json={
            "expected_version": status_data["amendment_version"],
            "expected_digest": status_data["content_digest"],
            "decision": "APPROVE",
            "idempotency_key": "client-no-groq-1",
        },
        headers=HEADERS,
    )
    assert dec1.status_code == 200 and dec1.json()["state"] == "PARTIALLY_APPROVED"

    dec2 = c.post(
        PREFIX + f"/amendments/{item.artifact_id}/decisions",
        json={
            "expected_version": status_data["amendment_version"],
            "expected_digest": status_data["content_digest"],
            "decision": "APPROVE",
            "idempotency_key": "freelancer-no-groq-1",
        },
        headers=FREELANCER,
    )
    assert dec2.status_code == 200 and dec2.json()["state"] == "BOTH_APPROVED"

    st = c.get(PREFIX + f"/amendments/{item.artifact_id}/status", headers=HEADERS)
    assert st.status_code == 200 and st.json()["state"] == "BOTH_APPROVED"

    hist = c.get(PREFIX + f"/amendments/{item.artifact_id}/history", headers=HEADERS)
    assert hist.status_code == 200 and [e["action"] for e in hist.json()] == ["CREATED", "APPROVE", "APPROVE"]


def test_health_degraded_when_database_not_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    with patch.object(service_main, "load_service_env", return_value=[]):
        with TestClient(service_main.app) as c:
            resp = c.get("/health")
            assert resp.status_code == 503
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["service_running"] is True
            assert body["database_configured"] is False
            assert body["database_connected"] is False
            assert body["jwt_configured"] is False
            assert body["runtime_configured"] is False
            assert body["groq_enabled"] is False


def test_health_degraded_when_jwt_config_missing(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://contractflow_app:test@127.0.0.1:5432/postgres")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    fake_pool = object()
    with (
        patch.object(service_main, "load_service_env", return_value=[]),
        patch.object(service_main, "init_db_pool", AsyncMock(return_value=fake_pool)),
        patch.object(service_main, "close_db_pool", AsyncMock(return_value=None)),
        patch.object(service_main, "check_database_connectivity", AsyncMock(return_value=True)),
    ):
        with TestClient(service_main.app) as c:
            resp = c.get("/health")
            assert resp.status_code == 503
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["service_running"] is True
            assert body["database_configured"] is True
            assert body["database_connected"] is True
            assert body["jwt_configured"] is False
            assert body["runtime_configured"] is False


def test_health_ok_with_db_and_jwt_even_when_groq_disabled(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://contractflow_app:test@127.0.0.1:5432/postgres")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret-minimum-32-characters-long")
    monkeypatch.setenv("CONTRACTFLOW_ENABLE_GROQ", "false")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    fake_pool = object()
    with (
        patch.object(service_main, "load_service_env", return_value=[]),
        patch.object(service_main, "init_db_pool", AsyncMock(return_value=fake_pool)),
        patch.object(service_main, "close_db_pool", AsyncMock(return_value=None)),
        patch.object(service_main, "check_database_connectivity", AsyncMock(return_value=True)),
    ):
        with TestClient(service_main.app) as c:
            resp = c.get("/health")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"
            assert body["service_running"] is True
            assert body["database_configured"] is True
            assert body["database_connected"] is True
            assert body["jwt_configured"] is True
            assert body["runtime_configured"] is True
            assert body["groq_enabled"] is False


def test_health_degraded_when_database_ping_fails(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://contractflow_app:test@127.0.0.1:5432/postgres")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret-minimum-32-characters-long")

    fake_pool = object()
    with (
        patch.object(service_main, "load_service_env", return_value=[]),
        patch.object(service_main, "init_db_pool", AsyncMock(return_value=fake_pool)),
        patch.object(service_main, "close_db_pool", AsyncMock(return_value=None)),
        patch.object(service_main, "check_database_connectivity", AsyncMock(return_value=False)),
    ):
        with TestClient(service_main.app) as c:
            resp = c.get("/health")
            assert resp.status_code == 503
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["database_connected"] is False
            assert body["runtime_configured"] is True


def test_env_loader_and_groq_feature_flag(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "CF_TEST_A='hello'\n"
        "export CF_TEST_B=\"world\"\n"
        "CF_TEST_PRESET=from_file\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("CF_TEST_A", raising=False)
    monkeypatch.delenv("CF_TEST_B", raising=False)
    monkeypatch.setenv("CF_TEST_PRESET", "already_set")

    loaded = load_service_env((env_file,))
    assert loaded == [env_file]
    assert service_main.os.environ["CF_TEST_A"] == "hello"
    assert service_main.os.environ["CF_TEST_B"] == "world"
    assert service_main.os.environ["CF_TEST_PRESET"] == "already_set"

    # Groq remains disabled unless explicitly enabled AND API key is non-empty
    assert is_groq_enabled({"GROQ_API_KEY": "gsk_test", "CONTRACTFLOW_ENABLE_GROQ": "false"}) is False
    assert is_groq_enabled({"GROQ_API_KEY": "gsk_test"}) is False
    assert is_groq_enabled({"GROQ_API_KEY": "", "CONTRACTFLOW_ENABLE_GROQ": "true"}) is False
    assert is_groq_enabled({"GROQ_API_KEY": "gsk_test", "CONTRACTFLOW_ENABLE_GROQ": "true"}) is True


def test_db_pool_kwargs_for_supavisor_pooler_and_remote_ssl():
    direct_local = _build_pool_kwargs("postgresql://contractflow_app:pw@127.0.0.1:5432/postgres")
    assert "statement_cache_size" not in direct_local
    assert "ssl" not in direct_local

    remote_direct = _build_pool_kwargs("postgresql://contractflow_app:pw@db.example.supabase.co:5432/postgres")
    assert remote_direct["ssl"] == "require"
    assert "statement_cache_size" not in remote_direct

    remote_pooler = _build_pool_kwargs(
        "postgresql://contractflow_app.ref:pw@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )
    assert remote_pooler["statement_cache_size"] == 0
    assert "ssl" not in remote_pooler  # Respects explicit sslmode=require in DSN


