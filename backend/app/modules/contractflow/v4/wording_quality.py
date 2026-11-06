"""Narrow quality rejections, never source rewriting or a grammar guarantee."""

import re

from .errors import AmendmentValidationError
from .baseline import baseline_quote_spans, proposed_only_text
from .sources import source_registry

FRAGMENTS = re.compile(r",\s*require\s+negotiation\b|\ba\s+proposed\s+(?:timeline|compensation)\b", re.I)


def validate_quality(request, proposals):
    registry = source_registry(request)
    fields = [(('changes', i, name), proposal) for i, c in enumerate(proposals.changes)
              for name, proposal in (("additional_scope", c.additional_scope), ("deliverable_proposal", c.deliverable_proposal))]
    fields += [(("timeline",), proposals.timeline), (("compensation",), proposals.compensation)]
    for field, proposal in fields:
        # Exact baseline quotes are authoritative source text, not generated
        # wording; do not normalize them or apply formatting fixes inside them.
        spans = baseline_quote_spans(proposal.text, registry, proposal.citations, field) if field[-1] == 'deliverable_proposal' else ()
        text = proposed_only_text(proposal.text, spans)
        if (FRAGMENTS.search(text) or re.search(r":(?=\w)", text)
                or re.search(r"\bproposed(?:addition|scope|deliverable|work)\b", text, re.I)):
            raise AmendmentValidationError("UNSUPPORTED_WORDING", field=(*field, "text"), check="WORDING_QUALITY")
