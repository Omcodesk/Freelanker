"""Orchestration over existing services; authority comes only from injected ports."""

from dataclasses import dataclass
from uuid import uuid4

from ..service import ContractGenerationService
from ..v2.service import AgreementDraftService
from ..v3.service import ScopeChangeService
from ..v3.schemas import ScopeChangeInput
from ..v4.service import AmendmentDraftService
from ..v4.schemas import AmendmentRequest, ReviewedAssessment
from ..v4.review import ReviewVerifier, validate_receipt
from ..providers.base import ContractProvider
from ..v5.repository import ApprovalRepository
from ..v5.service import ApprovalWorkflowService
from ..v5.schemas import ApprovalSubject, TrustedActor
from ..persistence.artifacts import StoredArtifact, ArtifactRepository
from .contracts import (IntegrationError, SourceSnapshot, Principal, validate_grant,
                        SharedAuth, WorkBridgeSource, AmendmentReviews, ApprovalTransactions)


@dataclass(frozen=True)
class ActorContext:
    principal: Principal
    write: bool


class IntegrationActorResolver:
    boundary_reference = "CONTRACTFLOW-V6-SHARED-IDENTITY"

    def __init__(self, runtime):
        self.runtime = runtime

    async def resolve(self, context, subject):
        if not isinstance(context, ActorContext):
            raise IntegrationError("UNAUTHENTICATED")
        principal = self.runtime.principal(context.principal)
        source = await self.runtime.source(subject.draft.project_id, principal, write=context.write)
        if not source.agreement or source.agreement != subject.draft.request_snapshot.original_agreement:
            raise IntegrationError("STALE_SOURCE")
        artifact = await self.runtime.artifact(subject.amendment_id, principal, "AMENDMENT")
        if artifact.artifact_version != subject.amendment_version or artifact.domain() != subject.draft:
            raise IntegrationError("STALE_SOURCE")
        receipt = await self.runtime.assessment_reviews.verify_review(subject.draft.request_snapshot.review_reference)
        validate_receipt(subject.draft.request_snapshot, receipt, self.runtime.assessment_reviews.boundary_reference)
        if receipt != subject.draft.verified_review:
            raise IntegrationError("REVIEW_INVALID")
        validate_grant(await self.runtime.reviews.verify(subject, principal), subject)
        role = "CLIENT" if principal.user_id == source.project.client.id else "FREELANCER"
        return TrustedActor(actor_id=principal.user_id, party_id=principal.user_id, role=role,
                            project_id=source.project.project_id, agreement_id=source.agreement.agreement_id,
                            amendment_id=subject.amendment_id, amendment_version=subject.amendment_version,
                            content_digest=subject.content_digest, acting_on_own_behalf=True,
                            boundary=self.boundary_reference)


@dataclass
class IntegrationRuntime:
    # All are required server-selected dependencies, never auto-filled from env.
    auth: SharedAuth
    workbridge: WorkBridgeSource
    artifacts: ArtifactRepository
    approval_repository: ApprovalRepository
    reviews: AmendmentReviews
    assessment_reviews: ReviewVerifier
    transactions: ApprovalTransactions
    provider: ContractProvider | None = None
    timeout_seconds: float = 30

    def principal(self, context):
        if not isinstance(context, Principal) or context.boundary != self.auth.boundary_reference:
            raise IntegrationError("UNAUTHENTICATED")
        return Principal.model_validate_json(context.model_dump_json())

    async def source(self, project_id, principal, expected=None, *, write=True):
        self.principal(principal)
        source = await self.workbridge.load(project_id, principal)
        try:
            source = SourceSnapshot.model_validate_json(source.model_dump_json())
        except Exception:
            raise IntegrationError("INVALID_SOURCE") from None
        if source.project.project_id != project_id:
            raise IntegrationError("INVALID_SOURCE")
        if principal.user_id not in {source.project.client.id, source.project.freelancer.id}:
            raise IntegrationError("NOT_FOUND")
        await self.auth.authorize(principal, project_id, source.agreement.agreement_id if source.agreement else None, write=write)
        if expected is not None and source.source_version != expected:
            raise IntegrationError("STALE_SOURCE")
        return source

    def approvals(self):
        return ApprovalWorkflowService(self.approval_repository, IntegrationActorResolver(self), self.assessment_reviews)

    async def artifact(self, artifact_id, principal, kind=None):
        item = await self.artifacts.load(artifact_id, principal)
        item = StoredArtifact.model_validate_json(item.model_dump_json())
        if item.artifact_id != artifact_id or (kind and item.kind != kind):
            raise IntegrationError("NOT_FOUND")
        source = await self.source(item.source.project.project_id, principal, item.source.source_version, write=False)
        if source != item.source:
            raise IntegrationError("STALE_SOURCE")
        return item

    async def generate(self, kind, request, principal):
        source = await self.source(request.project_id, principal, request.expected_source_version)
        if self.provider is None:
            raise IntegrationError("UNAVAILABLE")
        if kind == "CONTRACT":
            result = await ContractGenerationService(self.provider, timeout_seconds=self.timeout_seconds).generate_contract(source.project)
        elif kind == "AGREEMENT":
            result = await AgreementDraftService(self.provider, timeout_seconds=self.timeout_seconds).generate_contract(source.project)
        elif kind == "ASSESSMENT":
            if not source.agreement:
                raise IntegrationError("MISSING_AGREEMENT")
            data = ScopeChangeInput(request_id=str(uuid4()), project_id=source.project.project_id,
                                    original_project=source.agreement.project, client_request=request.client_request,
                                    supporting_context=request.supporting_context)
            result = await ScopeChangeService(self.provider, timeout_seconds=self.timeout_seconds).assess_scope_change(data)
        else:
            assessment = await self.artifact(request.assessment_id, principal, "ASSESSMENT")
            if assessment.source != source or not source.agreement:
                raise IntegrationError("STALE_SOURCE")
            reviewed = ReviewedAssessment(assessment_id=str(assessment.artifact_id), version=assessment.artifact_version,
                agreement_id=source.agreement.agreement_id, agreement_version=source.agreement.version,
                assessment=assessment.domain())
            data = AmendmentRequest(original_agreement=source.agreement, reviewed_assessment=reviewed,
                                    review_reference=request.review_reference)
            result = await AmendmentDraftService(self.provider, self.assessment_reviews,
                                                timeout_seconds=self.timeout_seconds).generate_amendment(data)
        # No response is returned as persisted until the adapter confirms storage.
        current = await self.source(source.project.project_id, principal, source.source_version)
        if current != source:
            raise IntegrationError("STALE_SOURCE")
        # The repository must repeat this freshness check at its commit point;
        # a preflight read alone cannot remove a cross-service race.
        stored = await self.artifacts.save(kind, source, result, principal)
        stored = StoredArtifact.model_validate_json(stored.model_dump_json())
        if stored.kind != kind or stored.source != source or stored.domain() != result:
            raise IntegrationError("INVALID_SOURCE")
        return stored

    async def register(self, amendment_id, request, principal):
        async def operation():
            artifact = await self.artifact(amendment_id, principal, "AMENDMENT")
            if artifact.artifact_version != request.expected_version or artifact.content_digest != request.expected_digest:
                raise IntegrationError("STALE_SOURCE")
            subject = ApprovalSubject.from_draft(artifact.domain(), artifact.artifact_version)
            validate_grant(await self.reviews.verify(subject, principal), subject)
            return await self.approvals().register_amendment(artifact.domain(), artifact.artifact_version, ActorContext(principal, True))
        return await self.transactions.run(operation)

    async def decision(self, request, principal):
        # The identity resolver rechecks current amendment review INSIDE this
        # shared transaction. Production adapter must serialize revocation too.
        return await self.transactions.run(lambda: self.approvals().submit_decision(request, ActorContext(principal, True)))

    async def read(self, amendment_id, principal, history=False):
        async def operation():
            service = self.approvals()
            context = ActorContext(principal, False)
            return await (service.get_history(amendment_id, context) if history else service.get_status(amendment_id, context))
        return await self.transactions.run(operation)
