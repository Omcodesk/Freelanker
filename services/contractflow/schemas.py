"""Validated snapshots and deliberately extractive AI wording."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, max_length=4000)]
Money = Annotated[Decimal, Field(gt=0, allow_inf_nan=False, max_digits=18, decimal_places=4)]
DRAFT_LABEL = "DRAFT — REQUIRES CLIENT AND FREELANCER REVIEW"
UNRESOLVED_TERMS = (
    "governing_law", "intellectual_property_ownership", "termination_conditions",
    "penalties", "payment_schedule", "acceptance_conditions", "other_legal_or_commercial_terms",
)


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class Party(Schema):
    id: Text
    name: Text


class Deliverable(Schema):
    id: Text
    description: Text
    deadline: date


class Milestone(Schema):
    id: Text
    description: Text
    deadline: date
    deliverable_ids: Annotated[tuple[Text, ...], Field(min_length=1)]


class ProjectInput(Schema):
    project_id: Text
    title: Text
    client: Party
    freelancer: Party
    scope: Text
    budget: Money
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    start_date: date
    deadline: date
    deliverables: Annotated[tuple[Deliverable, ...], Field(min_length=1, max_length=99)]
    milestones: Annotated[tuple[Milestone, ...], Field(min_length=1, max_length=99)]

    @model_validator(mode="after")
    def consistent_project(self):
        if self.client.id == self.freelancer.id:
            raise ValueError("Client and freelancer must be distinct")
        if self.start_date > self.deadline:
            raise ValueError("Start date must precede deadline")
        for items in (self.deliverables, self.milestones):
            if len({item.id for item in items}) != len(items):
                raise ValueError("Duplicate identifiers")
            if any(not self.start_date <= item.deadline <= self.deadline for item in items):
                raise ValueError("Item deadline outside project dates")
        deliverables = {item.id: item for item in self.deliverables}
        for milestone in self.milestones:
            refs = milestone.deliverable_ids
            if len(set(refs)) != len(refs) or not set(refs) <= deliverables.keys():
                raise ValueError("Invalid milestone deliverable references")
            if any(deliverables[ref].deadline > milestone.deadline for ref in refs):
                raise ValueError("Deliverable deadline exceeds milestone deadline")
        return self


class WordingSection(Schema):
    source_ref: Text
    text: Text


class ProviderOutput(Schema):
    sections: Annotated[tuple[WordingSection, ...], Field(min_length=1, max_length=200)]


def wording_sources(project: ProjectInput) -> dict[str, str]:
    """Index references avoid ambiguity when external IDs contain punctuation."""
    return {
        "scope": project.scope,
        **{f"deliverables/{i}": d.description for i, d in enumerate(project.deliverables)},
        **{f"milestones/{i}": m.description for i, m in enumerate(project.milestones)},
    }


class ContractDraft(Schema):
    label: Literal["DRAFT — REQUIRES CLIENT AND FREELANCER REVIEW"] = DRAFT_LABEL
    requires_human_review: Literal[True] = True
    authoritative_data: ProjectInput
    ai_wording: ProviderOutput
    unresolved_terms: tuple[str, ...] = UNRESOLVED_TERMS

    @model_validator(mode="after")
    def grounded_draft(self):
        sources = wording_sources(self.authoritative_data)
        sections = self.ai_wording.sections
        if len(sections) != len(sources) or {s.source_ref for s in sections} != set(sources):
            raise ValueError("Wording must cover every source exactly once")
        if any(s.text != sources[s.source_ref] for s in sections):
            raise ValueError("Only verbatim supplied wording is permitted")
        if self.unresolved_terms != UNRESOLVED_TERMS:
            raise ValueError("All unspecified legal/commercial terms require review")
        return self
