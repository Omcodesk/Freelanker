from .schemas import AmendmentDraft, AmendmentRequest, AmendmentWording, NOTICE, UNRESOLVED


def _render_text(draft_id, request: AmendmentRequest, proposals: AmendmentWording, *, professional=False) -> str:
    a, r = request.original_agreement, request.reviewed_assessment
    p = a.project
    lines = ["PROPOSED CONTRACT AMENDMENT", NOTICE, f"Draft reference: {draft_id}",
             "HUMAN AND SEMANTIC REVIEW REQUIRED; deterministic checks do not prove semantic correctness.",
             "", "ORIGINAL AGREEMENT REFERENCE", f"Agreement: {a.agreement_id}; version: {a.version}; project: {p.project_id}.",
             f"Assessment: {r.assessment_id}; version: {r.version}.",
             f"Client: {p.client.name} ({p.client.id}); freelancer: {p.freelancer.name} ({p.freelancer.id}).",
             "", "PURPOSE OF AMENDMENT", "For negotiation of client-requested work identified in the reviewed scope assessment.",
             "", "EXISTING AGREED FACTS — ORIGINAL SCOPE SUMMARY", p.scope,
             f"Original budget: {p.budget} {p.currency}; start: {p.start_date}; deadline: {p.deadline}."]
    for d in p.deliverables:
        lines.append(f"Original deliverable {d.id}: {d.description} — due {d.deadline}.")
    for m in p.milestones:
        lines.append(f"Original milestone {m.id}: {m.description} — due {m.deadline}; deliverables: {', '.join(m.deliverable_ids)}.")
    lines.extend(["", "CLIENT-REQUESTED CHANGES (NOT AGREED TERMS)", r.assessment.input_snapshot.client_request,
                  "", "PROPOSED ADDITIONAL WORK"])
    for c in sorted(proposals.changes, key=lambda c: c.change_index):
        if professional:
            lines.extend(["Proposed additional scope remains subject to negotiation and human review.",
                          "Reviewed requested change (not agreed terms): " + r.assessment.analysis.requested_changes[c.change_index].description])
        else:
            lines.append(c.additional_scope.text)
    lines.extend(["", "PROPOSED DELIVERABLE CHANGES"])
    for c in sorted(proposals.changes, key=lambda c: c.change_index):
        if professional:
            lines.extend(["Proposed deliverable specifications remain unresolved and require human review.",
                          "Reviewed requested change (not agreed terms): " + r.assessment.analysis.requested_changes[c.change_index].description])
        else:
            lines.append(c.deliverable_proposal.text)
    timeline = "Timeline implications require negotiation and human review." if professional else proposals.timeline.text
    compensation = "Compensation implications require negotiation and human review." if professional else proposals.compensation.text
    lines.extend(["", "TIMELINE CONSIDERATIONS", timeline,
                  "No revised deadline is established by this draft.", "", "COMPENSATION CONSIDERATIONS",
                  compensation, "No additional amount or payment schedule is established by this draft.",
                  "", "UNRESOLVED TERMS"])
    lines.extend(f"{term.replace('_', ' ').capitalize()}: unresolved — requires negotiation and review." for term in UNRESOLVED)
    lines.extend(["", "SOURCE CITATIONS"])
    fields = [p for c in proposals.changes for p in (c.additional_scope, c.deliverable_proposal)] + [proposals.timeline, proposals.compensation]
    for proposal in fields:
        for citation in proposal.citations:
            lines.append(f"[{citation.reference}] {citation.excerpt}")
    lines.extend(["", "REVIEW AND APPROVAL NOTICE", NOTICE,
                  "Review of an assessment does not approve this amendment. Neither party's approval is recorded here.",
                  "The original agreement is not modified by generating this draft. No signatures or effective date are supplied."])
    # Base immutable schemas strip outer whitespace; canonical text has no final
    # newline so validation and serialized round trips retain identical content.
    return "\n".join(lines)


def render_text_legacy(draft_id, request: AmendmentRequest, proposals: AmendmentWording) -> str:
    """Historical canonical representation; never auto-upgrade stored artifacts."""
    from .validation import validate_wording

    validate_wording(request, proposals)
    return _render_text(draft_id, request, proposals)


def render_text(draft_id, request: AmendmentRequest, proposals: AmendmentWording) -> str:
    """Professional view of exact reviewed requests, not a repair of AI claims.

    The original validated AI structure remains in draft.proposals for semantic
    comparison. Every input claim is checked BEFORE any server template is used.
    """
    from .validation import validate_wording
    from .wording_quality import validate_quality

    validate_wording(request, proposals)
    validate_quality(request, proposals)
    return _render_text(draft_id, request, proposals, professional=True)


def render_amendment(draft: AmendmentDraft) -> str:
    return AmendmentDraft.model_validate_json(draft.model_dump_json()).rendered_text
