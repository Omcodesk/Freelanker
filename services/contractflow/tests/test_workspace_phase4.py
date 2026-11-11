"""Phase 4 unit tests: workspace router, active-only agreement filtering, and V4/V5 review endpoints."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..adapters import source as source_mod
from ..adapters.source import SupabaseCoreSource
from ..api.workspace_router import workspace_router
from ..integrations.contracts import Principal
from .test_v6_api import PREFIX, block_external_clients
from .v6_support import runtime


def test_supabase_core_source_ignores_unapproved_draft_agreement():
    project_id = uuid4()
    client_id = uuid4()
    freelancer_id = uuid4()
    milestone_id = uuid4()
    created_at = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    due_date = date(2026, 11, 20)

    executed_queries = []

    class FakeConn:
        async def fetchrow(self, query, *args):
            executed_queries.append(query)
            if "FROM public.projects" in query:
                return {
                    "id": project_id,
                    "title": "Demo Project",
                    "description": "Build app",
                    "status": "awaiting_agreement",
                    "client_id": client_id,
                    "freelancer_id": freelancer_id,
                    "currency": "USD",
                    "total_budget": Decimal("1500.00"),
                    "source_version": 2,
                    "created_at": created_at,
                }
            if "FROM public.profiles" in query:
                uid = args[0]
                return {"id": uid, "display_name": "Client" if uid == client_id else "Freelancer"}
            if "FROM public.agreements" in query:
                # Verify query explicitly restricts to approved/active agreements
                assert "status IN ('approved', 'active')" in query
                return None
            return None

        async def fetch(self, query, *args):
            executed_queries.append(query)
            if "FROM public.milestones" in query:
                return [
                    {
                        "id": milestone_id,
                        "title": "M1",
                        "description": "Core delivery",
                        "due_date": due_date,
                        "order_index": 1,
                    }
                ]
            return []

    async def fake_get_conn():
        yield FakeConn()

    async def run():
        src = SupabaseCoreSource()
        with patch.object(source_mod, "get_connection", fake_get_conn):
            snap = await src.load(str(project_id), Principal(user_id=str(client_id), boundary="CONTRACTFLOW-V6-SHARED-IDENTITY"))
            assert snap.agreement is None
            assert snap.source_version == 2

    asyncio.run(run())


def test_workspace_amendment_review_requires_explicit_human_and_semantic_flags():
    rt = runtime()
    app = FastAPI()
    app.state.contractflow_runtime = rt
    app.include_router(workspace_router)
    c = TestClient(app)

    amendment_id = str(uuid4())
    # Missing semantic_review=True must fail 422 validation
    resp = c.post(
        f"/api/v1/contractflow/workspace/amendments/{amendment_id}/reviews",
        json={
            "expected_version": 1,
            "expected_digest": "a" * 64,
            "human_review": True,
            "semantic_review": False,
        },
        headers={"Authorization": "Bearer synthetic-client"},
    )
    assert resp.status_code == 422
    assert not any(
        "review" in str(resp.json()) and "PRIVATE" in str(resp.json()) for _ in [1]
    )


def test_workspace_assessment_review_requires_confirm_human_review_true():
    rt = runtime()
    app = FastAPI()
    app.state.contractflow_runtime = rt
    app.include_router(workspace_router)
    c = TestClient(app)

    project_id = rt.workbridge.snapshot.project.project_id
    assessment_id = str(uuid4())
    resp = c.post(
        f"/api/v1/contractflow/workspace/projects/{project_id}/assessments/{assessment_id}/reviews",
        json={
            "expected_version": 1,
            "expected_digest": "b" * 64,
            "confirm_human_review": False,
        },
        headers={"Authorization": "Bearer synthetic-client"},
    )
    assert resp.status_code == 422
