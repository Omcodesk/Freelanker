"""
Database connection pool and transactional context management for ContractFlow.

Supports:
- Shared transactional execution via ContextVar for atomic multi-adapter operations.
- Direct row-level locking (SELECT ... FOR UPDATE).
- Graceful fail-closed behavior when DATABASE_URL is not configured.
"""

import os
from contextvars import ContextVar
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlparse
import asyncpg

from ..integrations.contracts import IntegrationError

# ContextVar holding the active transactional connection during ApprovalTransactions.run()
_current_conn: ContextVar[asyncpg.Connection | None] = ContextVar("_current_conn", default=None)

_pool: asyncpg.Pool | None = None


def get_database_url() -> str | None:
    """Read DATABASE_URL from environment; strip quotes if present."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if url:
        return url.strip("\"'")
    return None


def _build_pool_kwargs(db_url: str) -> dict:
    """Derive safe SSL and pooler settings from DATABASE_URL without logging secrets."""
    parsed = urlparse(db_url)
    host = (parsed.hostname or "").lower()
    query = parse_qs(parsed.query)
    kwargs: dict = {
        "dsn": db_url,
        "min_size": 2,
        "max_size": 10,
        "timeout": 30.0,
        "command_timeout": 30.0,
    }
    # Disable asyncpg prepared statement cache when using Supavisor/PgBouncer transaction pooler
    if parsed.port == 6543 or "pooler" in host or "pgbouncer" in query:
        kwargs["statement_cache_size"] = 0
    # Enforce TLS for remote Postgres hosts unless sslmode is explicitly provided in DSN
    if host and host not in {"localhost", "127.0.0.1", "::1"} and "sslmode" not in query and "ssl" not in query:
        kwargs["ssl"] = "require"
    return kwargs


async def init_db_pool() -> asyncpg.Pool | None:
    """Initialize the global connection pool if DATABASE_URL is configured."""
    global _pool
    db_url = get_database_url()
    if not db_url:
        return None
    if _pool is None:
        _pool = await asyncpg.create_pool(**_build_pool_kwargs(db_url))
    return _pool


async def close_db_pool() -> None:
    """Close the global connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the active pool or raise IntegrationError UNAVAILABLE."""
    if _pool is None:
        raise IntegrationError("UNAVAILABLE")
    return _pool


def get_current_connection() -> asyncpg.Connection | None:
    """Return the active transactional connection in the current asyncio context."""
    return _current_conn.get()


async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Yields either the current active transactional connection (if in a transaction)
    or acquires a temporary connection from the pool.
    """
    conn = _current_conn.get()
    if conn is not None:
        yield conn
    else:
        pool = get_pool()
        async with pool.acquire() as acquired:
            yield acquired
