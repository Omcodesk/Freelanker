"""Explicit allowlisted source registries; never resolve arbitrary object paths."""

import re

from .schemas import ScopeChangeInput
from .quantities import extract_quantities


def original_sources(data: ScopeChangeInput) -> dict[str, str]:
    p = data.original_project
    result = {"original.scope": p.scope, "original.title": p.title,
              "original.start_date": p.start_date.isoformat(), "original.deadline": p.deadline.isoformat(),
              "original.budget": str(p.budget), "original.currency": p.currency}
    for kind in ("deliverables", "milestones"):
        for i, item in enumerate(getattr(p, kind)):
            for field in ("id", "description", "deadline"):
                value = getattr(item, field)
                result[f"original.{kind}/{i}/{field}"] = str(value)
            if kind == "milestones":
                for j, ref in enumerate(item.deliverable_ids):
                    result[f"original.milestones/{i}/deliverable_ids/{j}"] = ref
    return result


def untrusted_sources(data: ScopeChangeInput) -> dict[str, str]:
    return {"request.client_request": data.client_request,
            **{f"context/{i}": c.text for i, c in enumerate(data.supporting_context)}}


def original_quantity_facts(data: ScopeChangeInput) -> list[dict]:
    """Typed context for prompting; validation independently checks cited excerpts."""
    facts = []
    for reference, value in original_sources(data).items():
        if reference == "original.scope" or re.fullmatch(r"original\.deliverables/\d+/description", reference):
            for claim in extract_quantities(value):
                facts.append({"reference": reference, "value": claim.value, "unit": claim.unit,
                              "subject": list(claim.subject)})
    return facts


def is_timeline_reference(reference: str) -> bool:
    return reference in {"original.start_date", "original.deadline"} or bool(re.fullmatch(
        r"original\.(?:deliverables|milestones)/\d+/deadline", reference
    ))


def page_count_notices(scope: str) -> tuple[tuple[str, str], ...]:
    """Narrow attributed restatements of page counts, never estimates or new work."""
    counts = "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
    pattern = rf"\b(?:[1-9]\d{{0,2}}|{counts})[- ]page (?:[A-Za-z]+ ){{0,3}}website\b"
    phrases = dict.fromkeys(m.group() for m in re.finditer(pattern, scope, re.I))
    return tuple((f"The original scope describes a {phrase}.", phrase) for phrase in phrases)


def page_count_quotations(scope: str) -> tuple[tuple[str, str, str], ...]:
    """Exact source quotations with a page count; no unrestricted numeric whitelist."""
    result = []
    for _, phrase in page_count_notices(scope):
        result.append((f'Original scope excerpt: "{phrase}".', phrase, phrase))
        if len(scope) < 1800:
            result.append((f'Original scope excerpt: "{scope}".', scope, phrase))
    return tuple(result)
