"""Synthetic trusted actors ONLY for offline tests and the labeled demo."""

import json
from pathlib import Path
from uuid import UUID

from ..v4.renderer import render_text
from ..v4.schemas import AmendmentDraft, AmendmentWording
from ..v5.errors import AuthorizationError
from ..v5.repository import InMemoryApprovalRepository
from ..v5.schemas import DecisionRequest, TrustedActor
from ..v5.service import ApprovalWorkflowService
from .v4_support import SyntheticReviewVerifier, synthetic_output, synthetic_request


def amendment(revised=False):
    request = synthetic_request()
    data = synthetic_output()
    if revised:
        data["changes"][0]["additional_scope"]["text"] = "The proposed work may include online ordering with payment integration, subject to negotiation."
    wording = AmendmentWording.model_validate(data)
    draft_id = UUID("22222222-2222-4222-8222-222222222222")
    a, r = request.original_agreement, request.reviewed_assessment
    return AmendmentDraft(draft_id=draft_id, original_agreement_id=a.agreement_id,
                          original_agreement_version=a.version, project_id=a.project.project_id,
                          assessment_id=r.assessment_id, assessment_version=r.version,
                          original_facts=a.project, request_snapshot=request,
                          verified_review=SyntheticReviewVerifier().record, proposals=wording,
                          rendered_text=render_text(draft_id, request, wording))


class SyntheticActorResolver:
    boundary_reference = "SYNTHETIC-V5-IDENTITY-ONLY"

    async def resolve(self, context, subject):
        roles = json.loads((Path(__file__).parent / "fixtures/v5/actors.json").read_text(encoding="utf-8"))["contexts"]
        if not isinstance(context, str) or context not in roles:
            raise AuthorizationError("Unknown synthetic context")
        role = roles[context]
        draft = subject.draft
        party = draft.original_facts.client if role == "CLIENT" else draft.original_facts.freelancer
        return TrustedActor(actor_id=party.id, party_id=party.id, role=role, project_id=draft.project_id,
                            agreement_id=draft.original_agreement_id, amendment_id=subject.amendment_id,
                            amendment_version=subject.amendment_version, content_digest=subject.content_digest,
                            acting_on_own_behalf=True, boundary=self.boundary_reference)


def workflow(repository=None, resolver=None, verifier=None):
    return ApprovalWorkflowService(repository or InMemoryApprovalRepository(), resolver or SyntheticActorResolver(),
                                   verifier or SyntheticReviewVerifier())


async def initialized(**kwargs):
    service = workflow(**kwargs)
    initial = await service.register_amendment(amendment(), 1, "synthetic-client")
    return service, initial


def decision(status, *, choice="APPROVE", key="synthetic-decision-1", reason=None):
    return DecisionRequest(amendment_id=status.amendment_id, expected_version=status.amendment_version,
                           expected_digest=status.content_digest, decision=choice, idempotency_key=key,
                           rejection_reason=reason)
