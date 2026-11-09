# V6 storage proposal — NOT an installed or verified database adapter

No shared sessions, database URL conventions, SQLAlchemy declarative base or
Alembic environment exist in this checkout. No database connection or migration
has been run. These are proposed ContractFlow-owned tables, not operational DDL.
Use the team's existing session/base/migration conventions when they arrive.
The V5 ApprovalRepository protocol and V6 ArtifactRepository/ApprovalTransactions
ports define the behavioral contract; do not swap in the test fakes in production.

| Proposed table | Key/constraints | Stored data |
| --- | --- | --- |
| cf_artifacts | PK artifact_id + revision; unique immutable revision; index project_id | kind, source version/snapshot JSONB, validated payload JSONB, SHA-256, UTC created_at |
| cf_approval_heads | PK amendment_id; FK current revision to cf_artifacts | current revision; CAS sequence or row lock |
| cf_approval_versions | PK amendment_id + revision; FK cf_artifacts | V5 subject digest, status, original agreement/version, party IDs, source and review references |
| cf_decisions | PK server decision UUID; FK cf_approval_versions; unique amendment/revision/role; unique amendment/revision/actor; unique amendment/revision/idempotency key | actor ID/role, decision, normalized request digest, rejection reason with restricted access, UTC server timestamp |
| cf_audit | PK event UUID; FK cf_approval_versions; unique append sequence; optional FK decision UUID | prior/new state, action, actor ID/role, digest, UTC timestamp, hashed idempotency reference |
| cf_review_checks | PK check UUID; FK version and optional audit event | trusted review reference/reviewer ID, reviewed revision/digest, check time/expiry; no text or tokens |

Do not invent foreign keys to non-existent user/project tables. Add those FKs only
after Core/WorkBridge owners confirm authoritative keys, tenancy and lifecycle.
Only opaque IDs are appropriate in audit; contract/reason text needs separately
authorized storage and must never be copied into log/audit metadata.

## Transaction requirements

1. Resolve principal from Core authentication. Begin one shared transaction.
2. Lock the current amendment head, authoritative membership/permission rows,
   original agreement/source version and current review rows in a documented
   consistent order. All integration ports must use the SAME session/unit of work.
3. Revalidate the immutable artifact and recompute its V5 digest. Recheck latest
   artifact revision and trusted assessment + amendment human/semantic reviews.
4. Validate request version/digest and authorization. Unique idempotency lookup
   must compare full normalized request and trusted actor. Same request replays;
   conflicting payload/actor fails. No synthetic identity flags are consulted.
5. Apply V5 transition, insert decision + append-only audit + review-check metadata
   and update approval head/state in the same commit. Revisions supersede the old
   cycle and insert the new cycle atomically. Any failure rolls everything back.
6. Serialize review revocation, membership revocation and source/amendment revision
   publication against these locks. A remote HTTP auth/review lookup outside this
   unit of work does NOT establish atomic authorization correctness. Agree an
   explicit distributed freshness policy before enabling such an adapter.

Use row locks or SERIALIZABLE transactions plus bounded DB-only conflict retries.
Never retry Groq generation or replay external side effects inside a DB retry.
Unique constraints are mandatory even with locks. Use server-generated timezone-
aware UTC timestamps and logical append sequence; account for clock rollback.
Grant no UPDATE/DELETE privilege on audit or published immutable artifacts; use
separate migration/admin credentials and retention controls. Application checks
alone cannot make mutable rows tamper-evident against database administrators.

## Artifact persistence

Store CONTRACT/AGREEMENT/ASSESSMENT/AMENDMENT as independently validated immutable
artifacts. Save must recheck source version and access in its commit transaction
after provider generation. The source version and full original-agreement snapshot
are retained; current edited project facts must not replace agreed scope. Fetch
must authorize and revalidate typed payload/digest. AMENDMENT artifact ID is its
server V4 draft UUID; revision numbers are distinct from V4 pipeline version "4".
No API keys, sessions, bearer tokens, raw provider output or headers belong here.

## Migrations and acceptance gates

Core must first supply the session factory, database/schema naming, Alembic base
and authoritative ID types. Then add only new CF tables via a reviewed migration;
do not rewrite teammate migrations, create duplicate user/project tables, call
create_all at startup or modify shared tables without approval.

Real PostgreSQL tests must use multiple independent sessions/workers for duplicate
keys, conflicting decisions, approve/revoke races, revision races, crash rollback
and audit atomicity. Verify indexes/constraints, isolation and migration upgrade
on a disposable database. None of this has been tested here. Passing in-memory
tests or an installed SQLAlchemy package is NOT evidence of PostgreSQL durability.
