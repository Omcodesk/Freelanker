from ..v3.sources import original_sources
from .schemas import AmendmentRequest


def source_registry(request: AmendmentRequest) -> dict[str, str]:
    a, r = request.original_agreement, request.reviewed_assessment
    assessment = r.assessment
    result = {key.replace("original.", "agreement.", 1): value
              for key, value in original_sources(assessment.input_snapshot).items()}
    result.update({"agreement.id": a.agreement_id, "agreement.version": str(a.version),
                   "request.client_request": assessment.input_snapshot.client_request,
                   "assessment.explanation": assessment.analysis.explanation})
    for i, change in enumerate(assessment.analysis.requested_changes):
        result[f"assessment.requested_changes/{i}/description"] = change.description
    for i, impact in enumerate(assessment.analysis.potential_impacts):
        result[f"assessment.potential_impacts/{i}/explanation"] = impact.explanation
    return result


def citation_contract(request: AmendmentRequest) -> list[dict]:
    """Concrete, valid copy targets for each output field; never guessed aliases."""
    registry = source_registry(request)
    contract = []

    def citation(reference, excerpt=None):
        return {"reference": reference, "excerpt": registry[reference] if excerpt is None else excerpt}

    changes = request.reviewed_assessment.assessment.analysis.requested_changes
    for index, change in enumerate(changes):
        for name in ("additional_scope", "deliverable_proposal"):
            contract.append({"field": f"changes.{index}.{name}", "change_index": index,
                             "copy_citations": [citation("agreement.scope"),
                                                citation("request.client_request", change.request_evidence.excerpt),
                                                citation(f"assessment.requested_changes/{index}/description")]})
    for field, reference in (("timeline", "agreement.deadline"), ("compensation", "agreement.budget")):
        contract.append({"field": field, "copy_citations": [citation(reference),
                         citation("request.client_request"), citation("assessment.explanation")]})
    return contract
