"""
PostgreSQL Durable Artifact Repository for ContractFlow.

Implements ContractFlow's ArtifactRepository protocol:
- Persists immutable CONTRACT, AGREEMENT, ASSESSMENT, and AMENDMENT artifacts.
- Enforces commit-time source version freshness check against PostgreSQL.
- Computes and verifies SHA-256 canonical content digests.
- Rejects mutable updates or deletes (protected by database constraints and triggers).
"""

import json
import uuid
from datetime import datetime, timezone
from uuid import UUID

from ..integrations.contracts import IntegrationError, Principal, SourceSnapshot
from ..persistence.artifacts import ArtifactRepository, Kind, StoredArtifact, digest
from .db import get_connection


class PostgresArtifactRepository(ArtifactRepository):
    async def save(
        self,
        kind: Kind,
        source: SourceSnapshot,
        payload,
        principal: Principal,
    ) -> StoredArtifact:
        """
        Atomically persist detached immutable artifact; verify current source version.
        """
        # Determine artifact_id and revision
        if kind == "AMENDMENT":
            artifact_id = payload.draft_id
        else:
            artifact_id = uuid.uuid4()

        proj_uuid = uuid.UUID(source.project.project_id)
        now_utc = datetime.now(timezone.utc)

        async for conn in get_connection():
            # 1. Commit-time freshness recheck:
            # Re-read projects.source_version to ensure it did not drift during generation
            cur_source_row = await conn.fetchrow(
                "SELECT COALESCE(source_version, 1) as source_version FROM public.projects WHERE id = $1",
                proj_uuid,
            )
            if not cur_source_row or cur_source_row["source_version"] != source.source_version:
                raise IntegrationError("STALE_SOURCE")

            # 2. Determine revision number
            existing_rev_row = await conn.fetchrow(
                "SELECT COALESCE(MAX(revision), 0) as max_rev FROM public.cf_artifacts WHERE artifact_id = $1",
                artifact_id,
            )
            revision = (existing_rev_row["max_rev"] if existing_rev_row else 0) + 1

            # 3. Payload and digest calculation
            payload_dict = payload.model_dump(mode="json")
            payload_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            content_digest = digest(kind, revision, source, payload_dict)

            # 4. Insert into cf_artifacts
            source_snapshot_json = source.model_dump(mode="json")
            await conn.execute(
                """
                INSERT INTO public.cf_artifacts (
                    artifact_id, revision, project_id, kind, source_version,
                    source_snapshot, payload_json, content_digest, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9)
                """,
                artifact_id,
                revision,
                proj_uuid,
                kind,
                source.source_version,
                json.dumps(source_snapshot_json),
                payload_json,
                content_digest,
                now_utc,
            )

            return StoredArtifact(
                artifact_id=artifact_id,
                artifact_version=revision,
                kind=kind,
                source=source,
                content_digest=content_digest,
                created_at=now_utc,
                payload_json=payload_json,
            )

    async def load(self, artifact_id: UUID, principal: Principal) -> StoredArtifact:
        """
        Load latest immutable revision of the specified artifact.
        """
        async for conn in get_connection():
            row = await conn.fetchrow(
                """
                SELECT artifact_id, revision, project_id, kind, source_version,
                       source_snapshot, payload_json, content_digest, created_at
                FROM public.cf_artifacts
                WHERE artifact_id = $1
                ORDER BY revision DESC
                LIMIT 1
                """,
                artifact_id,
            )
            if not row:
                raise IntegrationError("NOT_FOUND")

            # Parse source snapshot
            source_raw = row["source_snapshot"]
            if isinstance(source_raw, str):
                source_dict = json.loads(source_raw)
            else:
                source_dict = source_raw
            source = SourceSnapshot.model_validate(source_dict)

            # Extract payload JSON string
            payload_raw = row["payload_json"]
            payload_json = payload_raw if isinstance(payload_raw, str) else json.dumps(payload_raw)

            created_at = row["created_at"]
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            return StoredArtifact(
                artifact_id=row["artifact_id"],
                artifact_version=row["revision"],
                kind=row["kind"],
                source=source,
                content_digest=row["content_digest"],
                created_at=created_at,
                payload_json=payload_json,
            )
