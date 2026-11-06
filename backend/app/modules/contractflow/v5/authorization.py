"""Required server-trusted identity boundary; no built-in synthetic resolver."""

from typing import Protocol

from .errors import AuthorizationError
from .schemas import ApprovalSubject, TrustedActor


class TrustedActorResolver(Protocol):
    boundary_reference: str

    async def resolve(self, authentication_context: object, subject: ApprovalSubject) -> TrustedActor:
        """Authenticate current credentials, ownership, decision permission and own behalf.

        Context is opaque to the service. Implementations must NOT interpret caller
        role/ownership/approval flags as authority. Recheck revocation in V6.
        """
        ...


def verify_actor(subject, actor, boundary):
    actor = TrustedActor.model_validate_json(actor.model_dump_json())
    draft = subject.draft
    project = draft.original_facts
    expected_party = project.client.id if actor.role == "CLIENT" else project.freelancer.id
    if (not boundary or actor.boundary != boundary or actor.actor_id != actor.party_id
            or project.client.id == project.freelancer.id or actor.party_id != expected_party
            or actor.project_id != draft.project_id or actor.agreement_id != draft.original_agreement_id
            or actor.amendment_id != subject.amendment_id
            or actor.amendment_version != subject.amendment_version
            or actor.content_digest != subject.content_digest):
        raise AuthorizationError("Actor is not authorized for this exact amendment")
    return actor
