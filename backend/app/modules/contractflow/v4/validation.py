"""Field-local provenance and conservative proposal language checks."""

import re

from ..v3.validation import validate_prose
from .errors import AmendmentValidationError
from .schemas import AmendmentRequest, AmendmentWording
from .sources import source_registry
from .diagnostics import category
from .vocabulary import normalized_words, assess_vocabulary, content_terms
from .baseline import baseline_quote_spans, proposed_only_text

# Closed connective/review vocabulary. Content words must occur in the specific
# reviewed change and its client request; original scope alone cannot add features.
CONNECTIVES = frozenset("a an the and or of for to with in on as by from this that these those it its be is are remain remains add additional addition work scope proposed proposal propose deliverable deliverables could may might include includes including cover covers consider considered subject negotiation parties review human semantic before any change changes deadline timeline compensation existing project requires require implications unresolved details discussion confirmation effort affect possible potential only no revised price not estimated".split())
UNSAFE = re.compile(r"\b(?:will|sign|signed|signatures?|approv\w*|accept\w*|active|effective|binding|executed|governing|jurisdiction|copyright|intellectual|ownership|licen[cs]\w*|termination|penalties|refund\w*|warrant\w*|indemn\w*|paypal|free|waiv\w*|paid|payment\s+(?:schedule|terms|instructions|plan))\b", re.I)


def words(text):
    return normalized_words(text)


def check_proposal(proposal, registry, *, assessment_ref, request_excerpt, agreement_ref=None, content=None, field=(), allow_baseline=False):
    refs = [c.reference for c in proposal.citations]
    if len(set(refs)) != len(refs):
        duplicate = next(ref for index, ref in enumerate(refs) if ref in refs[:index])
        raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations"), check="DUPLICATE_REFERENCE",
                                       source_category=category(duplicate))
    for index, c in enumerate(proposal.citations):
        if c.reference not in registry:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations", index, "reference"),
                                           check="UNKNOWN_REFERENCE", source_category=category(c.reference))
        if c.excerpt not in registry[c.reference]:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations", index, "excerpt"),
                                           check="EXCERPT_NOT_EXACT", source_category=category(c.reference))
    by_ref = {c.reference: c.excerpt for c in proposal.citations}
    for required, expected, missing, incomplete in (
        ("request.client_request", request_excerpt, "REQUIRED_REQUEST_CITATION_MISSING", "REQUEST_EXCERPT_INCOMPLETE"),
        (assessment_ref, registry[assessment_ref], "REVIEWED_ASSESSMENT_CITATION_MISSING", "ASSESSMENT_EXCERPT_INCOMPLETE"),
    ):
        if required not in by_ref:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations"),
                                           check=missing, source_category=category(required))
        if by_ref[required] != expected:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations", refs.index(required), "excerpt"),
                                           check=incomplete, source_category=category(required))
    if agreement_ref is None and not any(ref == "agreement.scope" or re.fullmatch(
        r"agreement\.deliverables/\d+/description", ref
    ) for ref in refs):
        raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations"),
                                       check="AGREEMENT_CONTEXT_MISSING", source_category="AGREEMENT")
    if agreement_ref:
        if agreement_ref not in by_ref:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations"),
                                           check="AUTHORITATIVE_FACT_CITATION_MISSING", source_category="AGREEMENT")
        if by_ref[agreement_ref] != registry[agreement_ref]:
            raise AmendmentValidationError("INVALID_EVIDENCE", field=(*field, "citations", refs.index(agreement_ref), "excerpt"),
                                           check="AUTHORITATIVE_FACT_EXCERPT_INCOMPLETE", source_category="AGREEMENT")
    text = proposal.text
    try:
        validate_prose(text)  # No numerical or original-value exceptions in proposals.
    except ValueError:
        raise AmendmentValidationError("UNSAFE_PROPOSAL", field=(*field, "text"), check="PROPOSAL_LANGUAGE") from None
    if UNSAFE.search(text) or not re.search(r"\b(?:could|may|might|proposed|unresolved)\b", text, re.I):
        raise AmendmentValidationError("UNSAFE_PROPOSAL", field=(*field, "text"), check="PROPOSAL_LANGUAGE")
    spans = baseline_quote_spans(text, registry, proposal.citations, field) if allow_baseline else ()
    if content is not None:
        agreement_content = " ".join(value for ref, value in registry.items() if ref.startswith("agreement."))
        permitted, metadata = assess_vocabulary(text, content, CONNECTIVES, agreement_content, ignored_spans=spans)
        if not permitted:
            raise AmendmentValidationError("UNSUPPORTED_WORDING", field=(*field, "text"),
                                           check="CONTENT_VOCABULARY", token_metadata=metadata)
    return proposed_only_text(text, spans)


def validate_wording(request: AmendmentRequest, wording: AmendmentWording):
    registry = source_registry(request)
    changes = request.reviewed_assessment.assessment.analysis.requested_changes
    if len(wording.changes) != len(changes) or {c.change_index for c in wording.changes} != set(range(len(changes))):
        raise AmendmentValidationError("INCOMPLETE_COVERAGE", field=("changes",), check="CHANGE_COVERAGE")
    for index, change in enumerate(wording.changes):
        source = changes[change.change_index]
        content = source.description + " " + source.request_evidence.excerpt
        for name, proposal in (("additional_scope", change.additional_scope), ("deliverable_proposal", change.deliverable_proposal)):
            proposed_text = check_proposal(proposal, registry,
                           assessment_ref=f"assessment.requested_changes/{change.change_index}/description",
                           request_excerpt=source.request_evidence.excerpt, content=content,
                           field=("changes", index, name), allow_baseline=name == "deliverable_proposal")
            if re.search(r"\b(?:not|never)\s+(?:include|cover|integrate|provide|deliver)\b", proposed_text, re.I):
                raise AmendmentValidationError("UNSUPPORTED_CHANGE", field=("changes", index, name, "text"), check="MATERIAL_CONTENT_CONTRADICTION")
            if not content_terms(source.description, content) - CONNECTIVES <= content_terms(proposed_text, content):
                raise AmendmentValidationError("UNSUPPORTED_CHANGE", field=("changes", index, name, "text"), check="MATERIAL_CONTENT")
    request_text = request.reviewed_assessment.assessment.input_snapshot.client_request
    for field, agreement_ref in (("timeline", "agreement.deadline"), ("compensation", "agreement.budget")):
        check_proposal(getattr(wording, field), registry, assessment_ref="assessment.explanation",
                       request_excerpt=request_text, agreement_ref=agreement_ref,
                       content=request_text + " " + request.reviewed_assessment.assessment.analysis.explanation,
                       field=(field,))
