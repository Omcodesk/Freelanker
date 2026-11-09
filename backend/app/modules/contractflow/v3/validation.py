"""Deterministic provenance checks and conservative prose filters, not entailment."""

import re

from .schemas import ScopeAnalysis, ScopeChangeInput
from .sources import original_sources, untrusted_sources, is_timeline_reference
from .diagnostics import RuleViolation
from .quantities import ungrounded_numeric_text

# Quantified facts belong in exact attributed evidence, not generated prose.
VALUES = re.compile(
    r"\d|[$€£₹%]|\b(?:USD|EUR|GBP|INR|dollars?|euros?|pounds?|rupees?|"
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|"
    r"january|february|april|june|july|august|september|october|november|december)\b",
    re.I,
)
OBLIGATIONS = re.compile(
    r"\b(?:must|shall|guarantee\w*|warrant\w*|indemn\w*|penalt\w*|"
    r"governing\s+law|jurisdiction|copyright|intellectual\s+property|pay|owes?|owed|"
    r"(?:price|budget|fee|compensation)\s+(?:is|will|increases?|decreases?|becomes?)|"
    r"ownership\s+(?:transfers?|belongs?)|terminat\w*|refund\w*|"
    r"(?:payment|payments)\s+(?:is|are|will|must|shall|due)|"
    r"(?:client|freelancer)\s+(?:agrees|owes|will\s+(?:pay|deliver|provide))|"
    r"acceptance\s+(?:is|will|occurs)|automatically\s+accepted)\b", re.I,
)


def validate_schedule_language(text: str, field) -> None:
    for clause in re.split(r"[.!?;\n]", text):
        if not re.search(r"\b(?:deadline|schedule|timeline|completion)\b", clause, re.I):
            continue
        definite = re.search(
            r"\b(?:will|would|shall|must)\b.{0,100}\b(?:extend\w*|delay\w*|postpon\w*|reschedul\w*|move\w*|chang\w*)\b|"
            r"\b(?:deadline|schedule|timeline|completion)\b.{0,30}\b(?:is|are|has been|have been)\s+(?:now\s+)?(?:extended|delayed|postponed|rescheduled|moved|changed)\b|"
            r"\b(?:automatic|automatically|guaranteed)\b.{0,60}\b(?:extend\w*|extension\w*|delay\w*|postpon\w*|reschedul\w*|mov\w*|chang\w*)\b",
            clause, re.I,
        )
        asserted_extension = re.search(r"\b(?:extends|delays|postpones|reschedules)\b", clause, re.I)
        tentative = re.search(r"\b(?:may|might|could|possible|potential|potentially|possibly)\b", clause, re.I)
        if definite or (asserted_extension and not tentative):
            raise RuleViolation("UNSUPPORTED_SCHEDULE_CHANGE", field)


def validate_prose(text: str, field=("analysis", "explanation"), *, original_scope=None, evidence=(), source_registry=None) -> None:
    registry = source_registry if source_registry is not None else {"original.scope": original_scope or ""}
    numeric_text = ungrounded_numeric_text(text, registry, evidence)
    if VALUES.search(numeric_text):
        raise RuleViolation("QUANTIFIED_PROSE", field)
    # Exact non-binding review notices and technical UI terminology are not duties.
    # Do not generalize this into skipping arbitrary negated sentences.
    checked = text
    for notice in ("No revised price is proposed.", "Compensation is not estimated."):
        checked = checked.replace(notice, "Review notice.")
    checked = re.sub(r"\bpay button\b", "checkout button", checked, flags=re.I)
    if OBLIGATIONS.search(checked):
        raise RuleViolation("POTENTIAL_BINDING_TERM", field)
    if any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise RuleViolation("CONTROL_CHARACTER", field)
    validate_schedule_language(text, field)


def validate_evidence(evidence, registry: dict[str, str], field=("analysis", "source_references")) -> None:
    refs = [e.reference for e in evidence]
    if len(set(refs)) != len(refs):
        raise RuleViolation("DUPLICATE_REFERENCE", field)
    for index, item in enumerate(evidence):
        source = registry.get(item.reference)
        if source is None:
            raise RuleViolation("UNKNOWN_SOURCE_REFERENCE", (*field, index, "reference"))
        if item.excerpt not in source:
            raise RuleViolation("FABRICATED_EXCERPT", (*field, index, "excerpt"), item.reference)


def validate_analysis(data: ScopeChangeInput, analysis: ScopeAnalysis) -> None:
    original, untrusted = original_sources(data), untrusted_sources(data)
    validate_evidence(analysis.source_references, original)
    if not any(e.reference == "original.scope" or re.fullmatch(
        r"original\.deliverables/\d+/description", e.reference
    ) for e in analysis.source_references):
        raise RuleViolation("MISSING_SCOPE_EVIDENCE", ("analysis", "source_references"))
    validate_prose(analysis.explanation, source_registry=original, evidence=analysis.source_references)
    seen_requests = set()
    for index, change in enumerate(analysis.requested_changes):
        field = ("analysis", "requested_changes", index)
        validate_evidence(change.source_references, original, (*field, "source_references"))
        validate_prose(change.description, (*field, "description"), source_registry=original,
                       evidence=change.source_references)
        validate_evidence((change.request_evidence,), {"request.client_request": data.client_request}, (*field, "request_evidence"))
        key = change.request_evidence.excerpt
        if key in seen_requests:
            raise RuleViolation("DUPLICATE_CHANGE", (*field, "request_evidence"))
        seen_requests.add(key)
    for index, impact in enumerate(analysis.potential_impacts):
        field = ("analysis", "potential_impacts", index)
        validate_evidence(impact.source_references, original, (*field, "source_references"))
        validate_prose(impact.explanation, (*field, "explanation"), source_registry=original,
                       evidence=impact.source_references)
        if impact.category == "TIMELINE" and not any(
            is_timeline_reference(e.reference) and e.excerpt == original[e.reference]
            for e in impact.source_references
        ):
            raise RuleViolation("MISSING_TIMELINE_EVIDENCE", (*field, "source_references"))
    for index, question in enumerate(analysis.clarification_questions):
        validate_prose(question, ("analysis", "clarification_questions", index),
                       source_registry=original, evidence=analysis.source_references)
    validate_evidence(analysis.context_references, {k: v for k, v in untrusted.items() if k.startswith("context/")},
                      ("analysis", "context_references"))
