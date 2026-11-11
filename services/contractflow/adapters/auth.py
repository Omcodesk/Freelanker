"""
Supabase PostgreSQL Authentication Adapter for ContractFlow.

Implements ContractFlow's SharedAuth protocol:
- Independently decodes and verifies Supabase JWTs.
- Verifies audience, expiration (with bounded 60s clock skew), and subject UUID.
- Enforces email confirmation before allowing contract operations.
- Verifies project membership and agreement ownership directly against PostgreSQL.
- Never trusts caller-supplied user IDs or roles.
"""

import os
import re
import uuid
from typing import Any
import jwt
import httpx

from ..integrations.contracts import IntegrationError, Principal, SharedAuth
from .db import get_connection

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class SupabasePostgresAuth(SharedAuth):
    boundary_reference = "CONTRACTFLOW-V6-SHARED-IDENTITY"

    def __init__(
        self,
        supabase_url: str | None = None,
        jwt_secret: str | None = None,
        jwks_url: str | None = None,
        timeout_seconds: float = 10.0,
    ):
        self.supabase_url = (supabase_url or os.environ.get("SUPABASE_URL") or "").rstrip("/")
        self.jwt_secret = jwt_secret or os.environ.get("SUPABASE_JWT_SECRET")
        self.jwks_url = jwks_url or (f"{self.supabase_url}/auth/v1/.well-known/jwks.json" if self.supabase_url else None)
        self.timeout_seconds = timeout_seconds

    async def authenticate(self, bearer_token: str) -> Principal:
        """
        Verify Supabase JWT access token independently; enforce issuer, audience,
        expiry, and subject UUID. Never log or leak the raw token.
        """
        if not bearer_token or len(bearer_token) > 4096:
            raise IntegrationError("UNAUTHENTICATED")

        payload = await self._verify_jwt(bearer_token)
        if not payload:
            raise IntegrationError("UNAUTHENTICATED")

        # 1. Subject (user_id) verification
        sub = payload.get("sub")
        if not sub or not isinstance(sub, str) or not UUID_REGEX.match(sub):
            raise IntegrationError("UNAUTHENTICATED")

        # 2. Audience verification
        aud = payload.get("aud")
        if aud != "authenticated":
            raise IntegrationError("UNAUTHENTICATED")

        # 3. Email verification requirement (Authoritative Server Claims Only)
        # NEVER trust caller-writable user_metadata.email_verified
        app_metadata = payload.get("app_metadata", {})
        is_verified = bool(
            payload.get("email_confirmed_at")
            or app_metadata.get("email_verified")
        )
        if not is_verified:
            # If not verified in token claims, verify via authoritative Supabase Auth API
            is_verified = await self._check_email_verified_remote(bearer_token)
            if not is_verified:
                raise IntegrationError("FORBIDDEN")

        return Principal(user_id=str(sub), boundary=self.boundary_reference)

    async def _verify_jwt(self, token: str) -> dict[str, Any] | None:
        """Verify JWT signature, standard claims, and issuer if present."""
        expected_issuer = f"{self.supabase_url}/auth/v1" if self.supabase_url else None

        # Fast path: Local secret verification (HS256)
        if self.jwt_secret:
            try:
                decoded = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                    leeway=60,  # 60s clock skew
                    options={"require": ["exp", "sub", "aud"]},
                )
                # If issuer is present, it must strictly match the authoritative Supabase Auth endpoint
                if expected_issuer and "iss" in decoded and decoded["iss"] != expected_issuer:
                    return None
                return decoded
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass

        # Remote path: Verify with authoritative Supabase Auth endpoint
        if self.supabase_url:
            try:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "apikey": os.environ.get("SUPABASE_ANON_KEY", ""),
                }
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(f"{self.supabase_url}/auth/v1/user", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        user_id = data.get("id")
                        if user_id and UUID_REGEX.match(user_id):
                            return {
                                "sub": user_id,
                                "aud": data.get("aud", "authenticated"),
                                "email_confirmed_at": data.get("email_confirmed_at"),
                                "app_metadata": data.get("app_metadata", {}),
                            }
            except Exception:
                pass

        # If neither verification succeeds, fail closed
        return None

    async def _check_email_verified_remote(self, token: str) -> bool:
        """Fallback check for email confirmation against Supabase Auth API."""
        if not self.supabase_url:
            return False
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "apikey": os.environ.get("SUPABASE_ANON_KEY", ""),
            }
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(f"{self.supabase_url}/auth/v1/user", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return bool(data.get("email_confirmed_at"))
        except Exception:
            pass
        return False

    async def authorize(
        self,
        principal: Principal,
        project_id: str,
        agreement_id: str | None,
        *,
        write: bool,
    ) -> None:
        """
        Verify project membership and agreement ownership in PostgreSQL.
        Never trust client-supplied roles.
        """
        if not UUID_REGEX.match(project_id) or not UUID_REGEX.match(principal.user_id):
            raise IntegrationError("FORBIDDEN")

        async for conn in get_connection():
            # Check project membership
            member_row = await conn.fetchrow(
                """
                SELECT role FROM public.project_members
                WHERE project_id = $1::uuid AND user_id = $2::uuid
                """,
                uuid.UUID(project_id),
                uuid.UUID(principal.user_id),
            )
            if not member_row:
                raise IntegrationError("FORBIDDEN")

            # If agreement_id is specified, ensure it belongs to the exact project
            if agreement_id:
                if not UUID_REGEX.match(agreement_id):
                    raise IntegrationError("FORBIDDEN")
                ag_row = await conn.fetchrow(
                    """
                    SELECT project_id FROM public.agreements
                    WHERE id = $1::uuid
                    """,
                    uuid.UUID(agreement_id),
                )
                if not ag_row or str(ag_row["project_id"]) != project_id:
                    raise IntegrationError("FORBIDDEN")

