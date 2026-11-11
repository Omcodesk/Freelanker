"""Authoritative facts, proposed wording and deterministic agreement sections."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from ..schemas import DRAFT_LABEL, UNRESOLVED_TERMS, ProjectInput, Schema, Text, WordingSection
from .validation import validate_wording


class AgreementWording(Schema):
    sections: Annotated[tuple[WordingSection, ...], Field(min_length=1, max_length=199)]


class AgreementSection(Schema):
    title: Text
    paragraphs: tuple[Annotated[str, Field(min_length=1, max_length=16000)], ...]


def assemble_sections(project: ProjectInput, wording: AgreementWording) -> tuple[AgreementSection, ...]:
    proposed = {s.source_ref: s.text for s in wording.sections}
    parties = (
        f"Client: {project.client.name} (ID: {project.client.id}).",
        f"Freelancer: {project.freelancer.name} (ID: {project.freelancer.id}).",
        f"Project: {project.title} (ID: {project.project_id}).",
    )
    deliverables = tuple(
        f"{d.id} — Due {d.deadline.isoformat()}. Source [deliverables/{i}]: {d.description}\n"
        f"Proposed wording: {proposed[f'deliverables/{i}']}"
        for i, d in enumerate(project.deliverables)
    )
    timeline = (f"Project start: {project.start_date.isoformat()}; deadline: {project.deadline.isoformat()}.",) + tuple(
        f"{m.id} — Due {m.deadline.isoformat()}; deliverables: {', '.join(m.deliverable_ids)}. "
        f"Source [milestones/{i}]: {m.description}\nProposed wording: {proposed[f'milestones/{i}']}"
        for i, m in enumerate(project.milestones)
    )
    return (
        AgreementSection(title="Parties", paragraphs=parties),
        AgreementSection(title="Scope of work", paragraphs=(
            f"Source [scope]: {project.scope}", f"Proposed wording: {proposed['scope']}",
        )),
        AgreementSection(title="Deliverables", paragraphs=deliverables),
        AgreementSection(title="Milestones and timeline", paragraphs=timeline),
        AgreementSection(title="Compensation", paragraphs=(
            f"Project budget: {project.budget} {project.currency}.",
            "Payment schedule is unresolved; delivery milestones do not establish payment dates.",
        )),
        AgreementSection(title="Unresolved terms", paragraphs=tuple(
            f"{term.replace('_', ' ').capitalize()}: unresolved — requires human review."
            for term in UNRESOLVED_TERMS
        )),
    )


class AgreementDraft(Schema):
    version: Literal["2"] = "2"
    label: Literal["DRAFT — REQUIRES CLIENT AND FREELANCER REVIEW"] = DRAFT_LABEL
    requires_human_review: Literal[True] = True
    semantic_review_required: Literal[True] = True
    deterministic_checks: Literal["passed; semantic equivalence not established"] = "passed; semantic equivalence not established"
    authoritative_data: ProjectInput
    ai_wording: AgreementWording
    sections: tuple[AgreementSection, ...]
    unresolved_terms: tuple[str, ...] = UNRESOLVED_TERMS

    @model_validator(mode="after")
    def validate_agreement(self):
        validate_wording(self.authoritative_data, self.ai_wording.sections)
        if self.unresolved_terms != UNRESOLVED_TERMS:
            raise ValueError("Unresolved terms cannot be removed")
        if self.sections != assemble_sections(self.authoritative_data, self.ai_wording):
            raise ValueError("Agreement sections must match deterministic assembly")
        return self
