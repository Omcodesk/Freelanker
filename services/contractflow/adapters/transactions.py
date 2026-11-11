"""
PostgreSQL Transaction Scope Adapter for ContractFlow.

Implements ContractFlow's ApprovalTransactions protocol:
- Executes operations inside a single shared transaction scope.
- Propagates the active transactional connection via ContextVar to all adapters.
- Guarantees complete atomic rollback on any failure.
"""

from typing import Awaitable, Callable

from ..integrations.contracts import ApprovalTransactions, IntegrationError
from .db import _current_conn, get_pool


class PostgresApprovalTransactions(ApprovalTransactions):
    async def run(self, operation: Callable[[], Awaitable]):
        """
        Execute operation in shared PostgreSQL transaction scope.
        Rolls back all writes if any exception occurs.
        """
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                token = _current_conn.set(conn)
                try:
                    return await operation()
                finally:
                    _current_conn.reset(token)
