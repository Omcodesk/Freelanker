from ..v2.render import render_agreement
from .test_v2_service import generate


def test_readable_review_copy(project_data):
    draft = generate(project_data)
    text = render_agreement(draft)
    assert text.startswith("DRAFT — REQUIRES CLIENT AND FREELANCER REVIEW")
    for heading in ("PARTIES", "SCOPE OF WORK", "DELIVERABLES", "MILESTONES AND TIMELINE", "COMPENSATION", "UNRESOLVED TERMS"):
        assert heading in text
    for value in ("1200.00 USD", "2027-01-04", "2027-01-22", "2027-01-29",
                  "Example Bakery (Synthetic)", "Example Developer (Synthetic)", "Source [scope]", "Proposed wording:"):
        assert value in text
    assert "semantic equivalence is not established" in text
    for term in draft.unresolved_terms:
        assert term.replace("_", " ").capitalize() in text
    assert render_agreement(draft) == text
