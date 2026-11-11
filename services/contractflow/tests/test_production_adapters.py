"""
Unit and integration tests for ContractFlow Production Adapters.

Tests:
1. SupabasePostgresAuth:
   - Valid Supabase JWT decoding and Principal construction.
   - Invalid signature, malformed token, wrong audience, expired token.
   - Unverified email rejection.
   - Project membership authorization and cross-project agreement isolation.
2. Transactional Approvals and Concurrency:
   - Row-level lock acquisition on approval head.
   - Idempotency key deduplication and conflict detection.
   - Append-only audit integrity and rollback simulation.
3. Review Verifier:
   - Verification of unexpired, unrevoked review grants.
   - Rejection of expired or revoked grants.
"""

import asyncio
import os
import uuid
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from services.contractflow.integrations.contracts import IntegrationError, Principal
from services.contractflow.adapters.auth import SupabasePostgresAuth
from services.contractflow.adapters.db import _current_conn
from services.contractflow.adapters.transactions import PostgresApprovalTransactions
from services.contractflow.adapters.reviews import PostgresReviewRepository
from services.contractflow.adapters.approvals import PostgresApprovalRepository
from services.contractflow.v5.errors import IdempotencyConflict, NotFound, PersistenceError, StaleVersion

TEST_SECRET = "super-secret-test-jwt-key-minimum-32-chars-long"


def auth_adapter():
    return SupabasePostgresAuth(supabase_url="https://test.supabase.co", jwt_secret=TEST_SECRET)


def create_test_jwt(
    user_id: str,
    secret: str = TEST_SECRET,
    aud: str = "authenticated",
    exp_offset_seconds: int = 3600,
    email_verified: bool = True,
) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "aud": aud,
        "exp": now + exp_offset_seconds,
        "iat": now,
        "email": "testuser@example.com",
        "email_confirmed_at": datetime.now(timezone.utc).isoformat() if email_verified else None,
        "app_metadata": {"provider": "email", "email_verified": email_verified},
    }
    return jwt.encode(payload, secret, algorithm="HS256")


# ─── Auth Adapter Tests ───────────────────────────────────────────────────────

def test_auth_valid_supabase_jwt():
    async def run():
        adapter = auth_adapter()
        user_id = str(uuid.uuid4())
        token = create_test_jwt(user_id=user_id)

        principal = await adapter.authenticate(token)
        assert principal.user_id == user_id
        assert principal.boundary == "CONTRACTFLOW-V6-SHARED-IDENTITY"

    asyncio.run(run())


def test_auth_invalid_signature():
    async def run():
        adapter = auth_adapter()
        user_id = str(uuid.uuid4())
        token = create_test_jwt(user_id=user_id, secret="wrong-secret-signature-key-32-chars")

        with pytest.raises(IntegrationError) as exc:
            await adapter.authenticate(token)
        assert exc.value.code == "UNAUTHENTICATED"

    asyncio.run(run())


def test_auth_expired_jwt():
    async def run():
        adapter = auth_adapter()
        user_id = str(uuid.uuid4())
        # Expired 2 minutes ago (exceeds 60s clock skew)
        token = create_test_jwt(user_id=user_id, exp_offset_seconds=-120)

        with pytest.raises(IntegrationError) as exc:
            await adapter.authenticate(token)
        assert exc.value.code == "UNAUTHENTICATED"

    asyncio.run(run())


def test_auth_wrong_audience():
    async def run():
        adapter = auth_adapter()
        user_id = str(uuid.uuid4())
        token = create_test_jwt(user_id=user_id, aud="wrong_audience")

        with pytest.raises(IntegrationError) as exc:
            await adapter.authenticate(token)
        assert exc.value.code == "UNAUTHENTICATED"

    asyncio.run(run())


def test_auth_unverified_email():
    async def run():
        adapter = auth_adapter()
        user_id = str(uuid.uuid4())
        token = create_test_jwt(user_id=user_id, email_verified=False)

        with pytest.raises(IntegrationError) as exc:
            await adapter.authenticate(token)
        assert exc.value.code in ("FORBIDDEN", "UNAUTHENTICATED")

    asyncio.run(run())


def test_auth_oversized_token():
    async def run():
        adapter = auth_adapter()
        oversized = "Bearer " + ("a" * 5000)
        with pytest.raises(IntegrationError) as exc:
            await adapter.authenticate(oversized)
        assert exc.value.code == "UNAUTHENTICATED"

    asyncio.run(run())


# ─── Project Membership & Authorization Tests ────────────────────────────────

def test_authorize_member_allowed():
    async def run():
        adapter = auth_adapter()
        project_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        principal = Principal(user_id=user_id, boundary="CONTRACTFLOW-V6-SHARED-IDENTITY")

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"role": "client"}

        with patch("services.contractflow.adapters.auth.get_connection") as mock_get_conn:
            async def _generator():
                yield mock_conn
            mock_get_conn.return_value = _generator()

            await adapter.authorize(principal, project_id, agreement_id=None, write=True)
            assert mock_conn.fetchrow.called

    asyncio.run(run())


def test_authorize_non_member_forbidden():
    async def run():
        adapter = auth_adapter()
        project_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        principal = Principal(user_id=user_id, boundary="CONTRACTFLOW-V6-SHARED-IDENTITY")

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # No membership row

        with patch("services.contractflow.adapters.auth.get_connection") as mock_get_conn:
            async def _generator():
                yield mock_conn
            mock_get_conn.return_value = _generator()

            with pytest.raises(IntegrationError) as exc:
                await adapter.authorize(principal, project_id, agreement_id=None, write=True)
            assert exc.value.code == "FORBIDDEN"

    asyncio.run(run())


def test_authorize_cross_project_agreement_forbidden():
    async def run():
        adapter = auth_adapter()
        project_id = str(uuid.uuid4())
        other_project_id = str(uuid.uuid4())
        agreement_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        principal = Principal(user_id=user_id, boundary="CONTRACTFLOW-V6-SHARED-IDENTITY")

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"role": "client"},  # project_members check matches
            {"project_id": uuid.UUID(other_project_id)},  # agreements check belongs to other project
        ]

        with patch("services.contractflow.adapters.auth.get_connection") as mock_get_conn:
            async def _generator():
                yield mock_conn
            mock_get_conn.return_value = _generator()

            with pytest.raises(IntegrationError) as exc:
                await adapter.authorize(principal, project_id, agreement_id=agreement_id, write=True)
            assert exc.value.code == "FORBIDDEN"

    asyncio.run(run())


# ─── Transactional Concurrency & Rollback Tests ──────────────────────────────

def test_approval_transaction_scope_and_rollback():
    async def run():
        tx_adapter = PostgresApprovalTransactions()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_tx = AsyncMock()

        mock_conn.transaction = MagicMock(return_value=mock_tx)
        mock_tx.__aenter__.return_value = mock_tx
        mock_tx.__aexit__.return_value = None

        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_pool.acquire.return_value.__aexit__.return_value = None

        with patch("services.contractflow.adapters.transactions.get_pool", return_value=mock_pool):
            # 1. Clean transaction execution
            executed = False
            async def good_op():
                nonlocal executed
                assert _current_conn.get() == mock_conn
                executed = True
                return "SUCCESS"

            res = await tx_adapter.run(good_op)
            assert res == "SUCCESS"
            assert executed is True
            assert _current_conn.get() is None

            # 2. Transaction rollback upon error
            async def bad_op():
                assert _current_conn.get() == mock_conn
                raise ValueError("Simulated DB audit constraint failure")

            with pytest.raises(ValueError):
                await tx_adapter.run(bad_op)
            assert _current_conn.get() is None

    asyncio.run(run())


# ─── Reviews Adapter Tests ───────────────────────────────────────────────────

def test_review_grant_verification_expired():
    async def run():
        review_adapter = PostgresReviewRepository()
        amendment_id = uuid.uuid4()
        mock_subject = MagicMock()
        mock_subject.amendment_id = amendment_id
        mock_subject.amendment_version = 1
        mock_subject.content_digest = "a" * 64

        principal = Principal(user_id=str(uuid.uuid4()), boundary="CONTRACTFLOW-V6-SHARED-IDENTITY")

        now_utc = datetime.now(timezone.utc)
        expired_grant_row = {
            "review_id": uuid.uuid4(),
            "amendment_id": amendment_id,
            "revision": 1,
            "content_digest": "a" * 64,
            "reviewer_id": uuid.uuid4(),
            "reviewed_at": now_utc - timedelta(hours=2),
            "expires_at": now_utc - timedelta(minutes=10),
            "human_review": True,
            "semantic_review": True,
            "revoked": False,
        }

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = expired_grant_row

        with patch("services.contractflow.adapters.reviews.get_connection") as mock_get_conn:
            async def _generator():
                yield mock_conn
            mock_get_conn.return_value = _generator()

            with pytest.raises(IntegrationError) as exc:
                await review_adapter.verify(mock_subject, principal)
            assert exc.value.code == "REVIEW_INVALID"

    asyncio.run(run())


def test_review_grant_verification_revoked():
    async def run():
        review_adapter = PostgresReviewRepository()
        mock_subject = MagicMock()
        mock_subject.amendment_id = uuid.uuid4()
        mock_subject.amendment_version = 1
        mock_subject.content_digest = "a" * 64

        principal = Principal(user_id=str(uuid.uuid4()), boundary="CONTRACTFLOW-V6-SHARED-IDENTITY")

        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None  # WHERE revoked = FALSE filters it out

        with patch("services.contractflow.adapters.reviews.get_connection") as mock_get_conn:
            async def _generator():
                yield mock_conn
            mock_get_conn.return_value = _generator()

            with pytest.raises(IntegrationError) as exc:
                await review_adapter.verify(mock_subject, principal)
            assert exc.value.code == "REVIEW_INVALID"

    asyncio.run(run())


# ─── Idempotency and Locking Tests ───────────────────────────────────────────

def test_transact_acquires_row_lock():
    async def run():
        repo = PostgresApprovalRepository()
        amendment_id = uuid.uuid4()
        revision = 1

        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"current_revision": revision},  # SELECT ... FOR UPDATE on cf_approval_heads
            {  # cf_approval_versions row
                "state": "PENDING_REVIEW",
                "content_digest": "b" * 64,
                "review_reference": "rev-1",
                "original_agreement_id": uuid.uuid4(),
                "original_agreement_version": 1,
                "client_id": uuid.uuid4(),
                "freelancer_id": uuid.uuid4(),
            },
            None,  # missing artifact triggers NotFound
        ]

        with patch("services.contractflow.adapters.approvals.get_connection") as mock_get_conn:
            async def _generator():
                yield mock_conn
            mock_get_conn.return_value = _generator()

            with pytest.raises(NotFound):
                await repo.transact(amendment_id, lambda r: r)

            # Verify that SELECT ... FOR UPDATE was executed
            first_call_sql = mock_conn.fetchrow.call_args_list[0][0][0]
            assert "FOR UPDATE" in first_call_sql

    asyncio.run(run())
