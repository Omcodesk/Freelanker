"""Synthetic trusted implementation for tests/explicit pinned live demo only."""

import json
from pathlib import Path

from ..v3.schemas import ScopeChangeAssessment
from ..v4.errors import ReviewVerificationError
from ..v4.schemas import AmendmentRequest, VerifiedReview

FIXTURES = Path(__file__).parent / "fixtures"


def synthetic_request():
    metadata = json.loads((FIXTURES / "v4/ordering.json").read_text(encoding="utf-8"))
    project = json.loads((FIXTURES / "website_project.json").read_text(encoding="utf-8"))
    input_data = json.loads((FIXTURES / "v3/out_of_scope.json").read_text(encoding="utf-8"))
    input_data["original_project"] = project
    analysis = json.loads((FIXTURES / "v3/provider_outputs.json").read_text(encoding="utf-8"))["out_of_scope"]
    assessment = ScopeChangeAssessment(request_id=input_data["request_id"], project_id=project["project_id"],
                                       input_snapshot=input_data, analysis=analysis, recommended_action="PROPOSE_AMENDMENT")
    return AmendmentRequest.model_validate({
        "original_agreement": {"agreement_id": metadata["agreement_id"], "version": metadata["agreement_version"], "project": project},
        "reviewed_assessment": {"assessment_id": metadata["assessment_id"], "version": metadata["assessment_version"],
                                "agreement_id": metadata["agreement_id"], "agreement_version": metadata["agreement_version"],
                                "assessment": assessment.model_dump(mode="json")},
        "review_reference": metadata["review_reference"],
    })


def synthetic_output():
    return json.loads((FIXTURES / "v4/provider_output.json").read_text(encoding="utf-8"))


class SyntheticReviewVerifier:
    boundary_reference = "SYNTHETIC-TEST-REVIEW-STORE"

    def __init__(self):
        self.calls = []
        self.record = VerifiedReview.model_validate_json((FIXTURES / "v4/review_record.json").read_text(encoding="utf-8"))

    async def verify_review(self, review_reference):
        self.calls.append(review_reference)
        if review_reference != self.record.review_reference:
            raise ReviewVerificationError("No synthetic review record")
        return self.record
