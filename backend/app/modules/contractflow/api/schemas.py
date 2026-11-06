from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from ..schemas import Schema
from ..v3.schemas import SupportingContext
from ..v5.schemas import Digest
from ..integrations.contracts import Identifier, Version


class ProjectRequest(Schema):
    project_id: Identifier
    expected_source_version: Version


class AssessmentRequest(ProjectRequest):
    client_request: Annotated[str, Field(strict=True, min_length=1, max_length=8000)]
    supporting_context: Annotated[tuple[SupportingContext, ...], Field(max_length=10)] = ()


class AmendmentRequest(ProjectRequest):
    assessment_id: UUID
    review_reference: Identifier


class RegisterRequest(Schema):
    expected_version: Version
    expected_digest: Digest


class DecisionBody(RegisterRequest):
    decision: Literal["APPROVE", "REJECT"]
    rejection_reason: Annotated[str, Field(strict=True, min_length=1, max_length=1000)] | None = None
    idempotency_key: Identifier

    @model_validator(mode="after")
    def reason(self):
        if self.rejection_reason is not None and (self.decision != "REJECT" or
                any(ord(c) < 32 or ord(c) == 127 for c in self.rejection_reason)):
            raise ValueError("Invalid rejection reason")
        return self
