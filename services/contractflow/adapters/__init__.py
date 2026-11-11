"""Production PostgreSQL and Supabase adapters for ContractFlow."""

from .db import init_db_pool, close_db_pool, get_pool, get_database_url
from .auth import SupabasePostgresAuth
from .source import SupabaseCoreSource
from .artifacts import PostgresArtifactRepository
from .approvals import PostgresApprovalRepository
from .transactions import PostgresApprovalTransactions
from .reviews import PostgresReviewRepository

__all__ = [
    "init_db_pool",
    "close_db_pool",
    "get_pool",
    "get_database_url",
    "SupabasePostgresAuth",
    "SupabaseCoreSource",
    "PostgresArtifactRepository",
    "PostgresApprovalRepository",
    "PostgresApprovalTransactions",
    "PostgresReviewRepository",
]
