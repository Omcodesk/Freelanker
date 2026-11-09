"""Synthetic adapters only. NO authentication or PostgreSQL production implementation."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI

from ..api.router import router
from ..integrations.contracts import IntegrationError, Principal, SourceSnapshot, ReviewGrant
from ..integrations.workflow import IntegrationRuntime
from ..persistence.artifacts import StoredArtifact, digest
from ..v4.schemas import ReviewedAssessment, VerifiedReview
from ..v4.review import fingerprint
from ..v5.repository import InMemoryApprovalRepository
from .v4_support import synthetic_request, synthetic_output
from .v5_support import amendment
from .test_v2_service import sample_output
from .conftest import FakeProvider


class SyntheticAuth:
    boundary_reference = "SYNTHETIC-V6-AUTH"

    async def authenticate(self, token):
        p = synthetic_request().original_agreement.project
        users = {"synthetic-client": p.client.id, "synthetic-freelancer": p.freelancer.id,
                 "synthetic-outsider": "not-a-party"}
        if token not in users:
            raise IntegrationError("UNAUTHENTICATED")
        return Principal(user_id=users[token], boundary=self.boundary_reference)

    async def authorize(self, principal, project_id, agreement_id, *, write):
        source = synthetic_request().original_agreement
        if (project_id != source.project.project_id or
                principal.user_id not in {source.project.client.id, source.project.freelancer.id}):
            raise IntegrationError("NOT_FOUND")


class SyntheticWorkBridge:
    def __init__(self):
        a = synthetic_request().original_agreement
        self.snapshot = SourceSnapshot(source_version=1, project=a.project, agreement=a)
        self.error = None

    async def load(self, project_id, principal):
        if self.error:
            raise IntegrationError(self.error)
        if project_id != self.snapshot.project.project_id:
            raise IntegrationError("NOT_FOUND")
        return self.snapshot


class SyntheticArtifacts:
    def __init__(self):
        self.records = {}
        self.fail_write = False

    async def save(self, kind, source, payload, principal):
        if self.fail_write:
            raise OSError("PRIVATE storage failure")
        identifier = payload.draft_id if kind == "AMENDMENT" else uuid4()
        version = self.records[identifier].artifact_version + 1 if identifier in self.records else 1
        item = StoredArtifact(artifact_id=identifier, artifact_version=version, kind=kind, source=source,
            content_digest=digest(kind, version, source, payload.model_dump(mode="json")),
            created_at=datetime.now(timezone.utc), payload_json=payload.model_dump_json())
        self.records[identifier] = item
        return item

    async def load(self, identifier, principal):
        if identifier not in self.records:
            raise IntegrationError("NOT_FOUND")
        return self.records[identifier]


class SyntheticReviews:
    def __init__(self):
        self.mode = "valid"

    async def verify(self, subject, principal):
        if self.mode == "missing":
            raise IntegrationError("REVIEW_INVALID")
        now = datetime.now(timezone.utc)
        grant = ReviewGrant(amendment_id=subject.amendment_id, amendment_version=subject.amendment_version,
            content_digest=subject.content_digest, reviewer_reference="SYNTHETIC-REVIEWER",
            reviewed_at=now - timedelta(minutes=1), expires_at=now + timedelta(minutes=5),
            human_review=True, semantic_review=True, revoked=False)
        updates = {"revoked": {"revoked": True}, "stale": {"expires_at": now - timedelta(seconds=1)},
                   "digest": {"content_digest": "0" * 64}, "version": {"amendment_version": 99}}
        return grant.model_copy(update=updates.get(self.mode, {}))


class SyntheticAssessmentReviews:
    boundary_reference = "SYNTHETIC-TEST-REVIEW-STORE"

    def __init__(self, artifacts):
        self.artifacts = artifacts
        self.records = {}

    async def verify_review(self, reference):
        if reference in self.records:
            return self.records[reference]
        if not reference.startswith("synthetic-review:"):
            raise IntegrationError("REVIEW_INVALID")
        from uuid import UUID
        item = self.artifacts.records[UUID(reference.split(":", 1)[1])]
        reviewed = ReviewedAssessment(assessment_id=str(item.artifact_id), version=item.artifact_version,
            agreement_id=item.source.agreement.agreement_id, agreement_version=item.source.agreement.version,
            assessment=item.domain())
        record = VerifiedReview(review_reference=reference, reviewer_reference="SYNTHETIC-REVIEWER",
            assessment_id=reviewed.assessment_id, assessment_version=reviewed.version,
            agreement_id=reviewed.agreement_id, agreement_version=reviewed.agreement_version,
            agreement_digest=fingerprint(item.source.agreement), assessment_digest=fingerprint(reviewed),
            reviewed_at=datetime.now(timezone.utc), decision="AUTHORIZE_DRAFT_GENERATION",
            verification_boundary=self.boundary_reference)
        self.records[reference] = record
        return record


class SyntheticProvider:
    def __init__(self):
        self.calls = []
        self.error = None

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        payload = json.loads(kwargs["user_prompt"])
        if "wording_sources" in payload:
            if "Paraphrase" in kwargs["system_prompt"]:
                return json.dumps(sample_output())
            return await FakeProvider().generate(**kwargs)
        if "citation_contract" in payload:
            return json.dumps(synthetic_output())
        return json.dumps(json.loads((Path(__file__).parent / "fixtures/v3/provider_outputs.json").read_text())["out_of_scope"])


class SyntheticTransactions:
    """Test-only one-loop atomic fake, NOT a multi-worker DB transaction."""
    def __init__(self, repository, artifacts):
        self.lock = asyncio.Lock()
        self.repository, self.artifacts = repository, artifacts

    async def run(self, operation):
        async with self.lock:
            before, artifacts = dict(self.repository._records), dict(self.artifacts.records)
            try:
                return await operation()
            except BaseException:
                self.repository._records = before
                self.artifacts.records = artifacts
                raise


def runtime():
    artifacts, approvals = SyntheticArtifacts(), InMemoryApprovalRepository()
    return IntegrationRuntime(SyntheticAuth(), SyntheticWorkBridge(), artifacts, approvals,
                              SyntheticReviews(), SyntheticAssessmentReviews(artifacts),
                              SyntheticTransactions(approvals, artifacts), SyntheticProvider())


def app(runtime=None):
    result = FastAPI()
    if runtime is not None:
        result.state.contractflow_runtime = runtime
    result.include_router(router)
    return result


async def seed(runtime):
    principal = await runtime.auth.authenticate("synthetic-client")
    draft = amendment()
    runtime.assessment_reviews.records[draft.request_snapshot.review_reference] = draft.verified_review
    return await runtime.artifacts.save("AMENDMENT", runtime.workbridge.snapshot, draft, principal)
