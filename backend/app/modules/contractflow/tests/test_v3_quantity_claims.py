import json

import pytest

from ..v3.diagnostics import V3InvalidProviderOutput
from ..v3.prompts import build_prompts
from ..v3.quantities import extract_quantities, grounded_count_spans
from ..v3.schemas import ScopeChangeInput
from .test_v3_confirmed_live import REJECTED_EXPLANATION
from .test_v3_live_regressions import run
from .test_v3_schemas import case_input, case_output

LATEST = (
    "The client asks for an online ordering system with payment integration, which was not part of the agreed "
    "three-page bakery website and is not covered by any listed deliverable."
)


@pytest.mark.parametrize("text", [LATEST, REJECTED_EXPLANATION,
    "Ordering exceeds the agreed 3-page bakery site.",
    "The agreed bakery website with three pages is the baseline; ordering appears additional.",
    "The original bakery site consisting of 3 pages does not describe ordering."])
def test_source_grounded_quantities_in_natural_explanations(text):
    data, output = case_input(), case_output()
    output["explanation"] = text
    result = run(data, output)
    assert result.analysis.explanation == text
    assert result.human_review_required and result.semantic_review_required
    assert "not established" in result.deterministic_validation


def test_quantity_parser_distinguishes_value_unit_and_subject():
    a = extract_quantities("Build a responsive three-page bakery website.")[0]
    b = extract_quantities("The agreed bakery site with 3 pages is the baseline.")[0]
    assert a.key == b.key == (3, "pages", ("bakery", "website"))
    assert extract_quantities("The agreed three-page pottery website.")[0].key != a.key
    assert extract_quantities("Charge three dollars in three days.") == ()


@pytest.mark.parametrize("text", [
    "Ordering exceeds the agreed four-page bakery website.",
    "Ordering exceeds the agreed three-page pottery website.",
    "Ordering exceeds the agreed three-page ordering website.",
    "The original scope adds a three-page bakery website.",
    "Add to the agreed scope a three-page bakery website.",
    "Expand the agreed three-page bakery website.",
    "The agreed website will include three bakery pages.",
    "The original scope estimates three days of work.",
    "Charge three dollars for the agreed website.",
    "The agreed website deadline is 2027-01-29.",
    "Apply three percent to the agreed website.",
    "The original scope includes a three-payment schedule.",
    "The client must accept the agreed three-page bakery website.",
    "The freelancer shall deliver the agreed three-page bakery website.",
])
def test_changed_context_finance_schedule_or_obligation_is_rejected(text):
    data, output = case_input(), case_output()
    output["explanation"] = text
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("suffix", [" Add three more pages.", " Charge USD 3.", " Finish in three days.",
    " Add a 3% deposit.", " Payment is due on delivery.", " The client must pay."])
def test_grounded_span_cannot_mask_a_separate_unsupported_claim(suffix):
    data, output = case_input(), case_output()
    output["explanation"] = LATEST + suffix
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("kind", ["budget", "deadline", "request", "context", "partial", "fabricated"])
def test_unrelated_numbers_and_invalid_evidence_cannot_ground_page_count(kind):
    data, output = case_input(), case_output()
    output["explanation"] = LATEST
    if kind == "budget":
        data["original_project"]["budget"] = "3"
        output["source_references"] = [output["source_references"][1], {"reference": "original.budget", "excerpt": "3"}]
    elif kind == "deadline":
        output["source_references"] = [output["source_references"][1], {"reference": "original.deadline", "excerpt": "2027-01-29"}]
    elif kind == "request":
        output["source_references"][0]["reference"] = "request.client_request"
    elif kind == "context":
        data["supporting_context"] = [{"id": "test", "text": data["original_project"]["scope"]}]
        output["source_references"] = [output["source_references"][1]]
    elif kind == "partial":
        output["source_references"][0]["excerpt"] = "three-page"
    else:
        output["source_references"][0]["excerpt"] = "A fabricated three-page bakery website."
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


def test_cited_original_deliverable_can_support_its_own_quantity():
    data, output = case_input(), case_output()
    data["original_project"]["scope"] = "Build a responsive bakery website."
    data["original_project"]["deliverables"][0]["description"] = "Source files for a three-page bakery website."
    output["source_references"] = [{"reference": "original.deliverables/0/description", "excerpt": data["original_project"]["deliverables"][0]["description"]}]
    output["requested_changes"][0]["source_references"][0]["excerpt"] = data["original_project"]["scope"]
    output["potential_impacts"][0]["source_references"][0]["excerpt"] = data["original_project"]["deliverables"][0]["description"]
    output["explanation"] = "The agreed deliverable is a three-page bakery website; ordering appears additional."
    assert run(data, output).human_review_required


def test_grounded_token_spans_do_not_cover_surrounding_text():
    from ..v3.schemas import Evidence
    scope = "Build a three-page bakery website."
    text = "The agreed three-page bakery website costs 3 dollars."
    spans = grounded_count_spans(text, {"original.scope": scope}, (Evidence(reference="original.scope", excerpt=scope),))
    assert len(spans) == 1
    start, end = spans[0]
    assert text[start:end] == "three"
    assert text[end:].endswith("costs 3 dollars.")


def test_prompt_exposes_typed_facts_without_relying_on_sentence_templates():
    _, user = build_prompts(ScopeChangeInput.model_validate(case_input()))
    facts = json.loads(user)["original_quantity_facts"]
    assert {"reference": "original.scope", "value": 3, "unit": "pages", "subject": ["bakery", "website"]} in facts
