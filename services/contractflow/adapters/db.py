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


async def init_db_pool() -> asyncpg.Pool | None:
    """Initialize the global connection pool if DATABASE_URL is configured."""
    global _pool
    db_url = get_database_url()
    if not db_url:
        return None
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=db_url,
            min_size=2,
            max_size=10,
            timeout=30.0,
            command_timeout=30.0,
        )
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
