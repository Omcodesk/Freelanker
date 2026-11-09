"""Exact labeled baseline quotations, never a global agreement vocabulary grant."""

import re

from .errors import AmendmentValidationError

LABEL = re.compile(r'(?:^|(?<=[.!?])\s+)Existing deliverable:\s*"(?P<quote>[^"\n]+)"', re.I)


def baseline_quote_spans(text, registry, citations, field):
    supported = {
        c.excerpt for c in citations
        if re.fullmatch(r"agreement\.deliverables/\d+/description", c.reference)
        and registry.get(c.reference) == c.excerpt
    }
    spans = []
    for match in LABEL.finditer(text):
        following = text[match.end():]
        remainder = following.lstrip()
        standalone = (not remainder or remainder[0] in ".!?" or
                      (match.group("quote").endswith((".", "!", "?")) and following[:1].isspace()
                       and remainder[0].isupper()))
        if not standalone:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "text"),
                                           check="BASELINE_ROLE_AMBIGUOUS", source_category="AGREEMENT")
        if match.group("quote") not in supported:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "text"),
                                           check="BASELINE_REFERENCE_NOT_GROUNDED", source_category="AGREEMENT")
        spans.append(match.span("quote"))
    return tuple(spans)


def proposed_only_text(text, spans):
    # Preserve offsets. Exact baseline content cannot supply required material
    # words or excuse unsupported vocabulary elsewhere in the proposal.
    for start, end in spans:
        text = text[:start] + " " * (end - start) + text[end:]
    return text
