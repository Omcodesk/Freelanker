"""Typed durable-artifact boundary; SQL implementation blocked on shared sessions."""

import hashlib
import json
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import model_validator

from ..schemas import Schema, ContractDraft
from ..v2.schemas import AgreementDraft
from ..v3.schemas import ScopeChangeAssessment
from ..v4.schemas import AmendmentDraft
from ..integrations.contracts import Identifier, Principal, Version, SourceSnapshot
from ..v5.schemas import Digest

Kind = Literal["CONTRACT", "AGREEMENT", "ASSESSMENT", "AMENDMENT"]
MODELS = {"CONTRACT": ContractDraft, "AGREEMENT": AgreementDraft,
          "ASSESSMENT": ScopeChangeAssessment, "AMENDMENT": AmendmentDraft}


def digest(kind, version, source, payload):
    value = {"kind": kind, "version": version, "source": source.model_dump(mode="json"), "payload": payload}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=True, allow_nan=False).encode()).hexdigest()


class StoredArtifact(Schema):
    artifact_id: UUID
    artifact_version: Version
    kind: Kind
    source: SourceSnapshot
    content_digest: Digest
    created_at: datetime
    # JSON string keeps nested provider artifacts immutable at this boundary.
    payload_json: str

    def domain(self):
        return MODELS[self.kind].model_validate_json(self.payload_json)

    @model_validator(mode="after")
    def valid(self):
        value = self.domain()
        if self.created_at.utcoffset() is None or self.created_at.utcoffset().total_seconds() != 0:
            raise ValueError("Artifact timestamp must be UTC")
        if self.content_digest != digest(self.kind, self.artifact_version, self.source, value.model_dump(mode="json")):
            raise ValueError("Artifact digest mismatch")
        if self.kind in {"CONTRACT", "AGREEMENT"}:
            if value.authoritative_data != self.source.project:
                raise ValueError("Artifact/project mismatch")
        else:
            if not self.source.agreement:
                raise ValueError("Original agreement required")
            original = value.input_snapshot.original_project if self.kind == "ASSESSMENT" else value.original_facts
            if original != self.source.agreement.project:
                raise ValueError("Artifact/agreement mismatch")
        if self.kind == "AMENDMENT" and (value.draft_id != self.artifact_id or
                (value.original_agreement_id, value.original_agreement_version) !=
                (self.source.agreement.agreement_id, self.source.agreement.version)):
            raise ValueError("Amendment identifiers differ")
        return self


class ArtifactRepository(Protocol):
    async def save(self, kind: Kind, source: SourceSnapshot, payload, principal: Principal) -> StoredArtifact:
        """Atomically persist detached artifact; verify current source/access.
        Allocate server UUID/version (AMENDMENT uses its server draft_id), enforce
        immutable revisions, source/digest constraints; never log contract text.
        """
        ...

    async def load(self, artifact_id: UUID, principal: Principal) -> StoredArtifact:
        """Load latest immutable revision, authorized; hide others as NOT_FOUND."""
        ...
