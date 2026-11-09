"""Plain-text review copy; never render an unchecked payload."""

from .schemas import AgreementDraft


def render_agreement(draft: AgreementDraft) -> str:
    draft = AgreementDraft.model_validate_json(draft.model_dump_json())
    lines = [draft.label, "", "HUMAN SEMANTIC REVIEW REQUIRED",
             "Deterministic checks passed; semantic equivalence is not established.",
             "Compare every proposed paragraph with its source before use."]
    for section in draft.sections:
        lines.extend(["", section.title.upper(), *section.paragraphs])
    return "\n".join(lines) + "\n"
