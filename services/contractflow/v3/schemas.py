"""Immutable original evidence and separately validated AI interpretations."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from ..schemas import ProjectInput, Schema
from .diagnostics import RuleViolation

Identifier = Annotated[str, Field(min_length=1, max_length=128)]
Prose = Annotated[str, Field(min_length=1, max_length=2000,
    description="No financial/date/estimate/percentage/obligation claims. Existing website page counts may be paraphrased only with matching cited authoritative value, unit, subject and original/agreed baseline attribution. Other quantities only in excerpts.")]
Classification = Literal["IN_SCOPE", "OUT_OF_SCOPE", "NEEDS_CLARIFICATION"]
Action = Literal["REVIEW_AND_CONFIRM_SCOPE", "PROPOSE_AMENDMENT", "REQUEST_CLARIFICATION"]
ACTIONS = {"IN_SCOPE": "REVIEW_AND_CONFIRM_SCOPE", "OUT_OF_SCOPE": "PROPOSE_AMENDMENT",
           "NEEDS_CLARIFICATION": "REQUEST_CLARIFICATION"}


class SupportingContext(Schema):
    id: Identifier
    text: Annotated[str, Field(min_length=1, max_length=4000)]


class ScopeChangeInput(Schema):
    request_id: Identifier
    project_id: Identifier
    original_project: ProjectInput
    client_request: Annotated[str, Field(min_length=1, max_length=8000)]
    supporting_context: Annotated[tuple[SupportingContext, ...], Field(max_length=10)] = ()

    @model_validator(mode="after")
    def consistent_input(self):
        if self.project_id != self.original_project.project_id:
            raise ValueError("Project identifier does not match original snapshot")
        if len({c.id for c in self.supporting_context}) != len(self.supporting_context):
            raise ValueError("Duplicate context identifiers")
        if len(self.model_dump_json().encode("utf-8")) > 64000:
            raise ValueError("Input exceeds 64000 UTF-8 bytes; evidence must not be truncated")
        return self


class Evidence(Schema):
    reference: Annotated[str, Field(min_length=1, max_length=200,
        description="Exact key copied from the provided registry, e.g. original.deliverables/0/description. No dot/bracket aliases.")]
    excerpt: Annotated[str, Field(min_length=1, max_length=4000,
        description="Exact nonempty contiguous substring of that source value. Do not paraphrase or insert ellipses.")]


EvidenceList = Annotated[tuple[Evidence, ...], Field(min_length=1, max_length=30)]


class RequestedChange(Schema):
    description: Prose
    request_evidence: Evidence
    source_references: EvidenceList


class PotentialImpact(Schema):
    category: Literal["DELIVERABLES", "TIMELINE", "COMPENSATION"]
    explanation: Prose = Field(description="Qualitative possible effects only. For TIMELINE use conditional language and human review before changes; no explicit dates or asserted extensions.")
    source_references: EvidenceList = Field(description="For TIMELINE include an exact full original date/deadline value from an original timeline registry key, in addition to other relevant evidence.")


class ScopeAnalysis(Schema):
    classification: Classification
    explanation: Prose
    source_references: EvidenceList
    requested_changes: Annotated[tuple[RequestedChange, ...], Field(min_length=1, max_length=20)]
    potential_impacts: Annotated[tuple[PotentialImpact, ...], Field(max_length=3)]
    clarification_questions: Annotated[tuple[Prose, ...], Field(max_length=10)] = ()
    context_references: Annotated[tuple[Evidence, ...], Field(max_length=10)] = ()

    @model_validator(mode="after")
    def consistent_analysis(self):
        categories = [i.category for i in self.potential_impacts]
        if len(set(categories)) != len(categories):
            raise RuleViolation("DUPLICATE_IMPACT_CATEGORY", ("analysis", "potential_impacts"))
        if self.classification == "NEEDS_CLARIFICATION" and not self.clarification_questions:
            raise RuleViolation("CLARIFICATION_QUESTIONS_REQUIRED", ("analysis", "clarification_questions"))
        return self


class ScopeChangeAssessment(Schema):
    version: Literal["3"] = "3"
    request_id: Identifier
    project_id: Identifier
    input_snapshot: ScopeChangeInput
    analysis: ScopeAnalysis
    recommended_action: Action
    human_review_required: Literal[True] = True
    semantic_review_required: Literal[True] = True
    deterministic_validation: Literal["passed; semantic correctness not established"] = "passed; semantic correctness not established"

    @model_validator(mode="after")
    def consistent_assessment(self):
        from .validation import validate_analysis

        if (self.request_id, self.project_id) != (self.input_snapshot.request_id, self.input_snapshot.project_id):
            raise RuleViolation("SNAPSHOT_MISMATCH", ("input_snapshot",))
        if self.recommended_action != ACTIONS[self.analysis.classification]:
            raise RuleViolation("ACTION_MISMATCH", ("recommended_action",))
        validate_analysis(self.input_snapshot, self.analysis)
        return self
