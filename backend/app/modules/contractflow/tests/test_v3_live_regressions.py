import asyncio
import json

import pytest

from ..v3.diagnostics import V3InvalidProviderOutput
from ..v3.prompts import build_prompts
from ..v3.schemas import Evidence, ScopeChangeInput
from ..v3.service import ScopeChangeService
from ..v3.sources import original_sources, page_count_notices
from .conftest import FakeProvider
from .test_v3_schemas import case_input, case_output


def run(data, output):
    return asyncio.run(ScopeChangeService(FakeProvider(json.dumps(output))).assess_scope_change(data))


@pytest.mark.parametrize("count", ["three", "3"])
def test_cited_original_page_count_notice_allowed(count):
    data, output = case_input(), case_output()
    data["original_project"]["scope"] = data["original_project"]["scope"].replace("three", count)
    # Refresh the exact citation along with its original source; no alias conversion.
    output["source_references"][0]["excerpt"] = data["original_project"]["scope"]
    output["requested_changes"][0]["source_references"][0]["excerpt"] = data["original_project"]["scope"]
    notice, phrase = page_count_notices(data["original_project"]["scope"])[0]
    output["explanation"] = notice + " Online ordering appears additional."
    result = run(data, output)
    assert phrase in result.analysis.explanation
    assert result.human_review_required and result.semantic_review_required
    assert str(result.input_snapshot.original_project.budget) == "1200.00"


@pytest.mark.parametrize("suffix", [" Add four pages.", " Charge USD 500.", " Finish by 2027-03-01.",
    " Estimate five days.", " Add a 10% fee.", " The client must pay.",
    " The freelancer shall deliver.", " Charge three hundred dollars."])
def test_page_count_exception_cannot_hide_other_values_or_obligations(suffix):
    data, output = case_input(), case_output()
    notice = page_count_notices(data["original_project"]["scope"])[0][0]
    output["explanation"] = notice + suffix
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("case", ["wrong_count", "no_citation", "wrong_excerpt", "unattributed", "new_work"])
def test_page_count_requires_exact_attributed_original_evidence(case):
    data, output = case_input(), case_output()
    notice = page_count_notices(data["original_project"]["scope"])[0][0]
    output["explanation"] = notice
    if case == "wrong_count":
        output["explanation"] = notice.replace("three", "four")
    elif case == "no_citation":
        output["source_references"] = output["source_references"][1:]
    elif case == "wrong_excerpt":
        output["source_references"][0]["excerpt"] = "bakery website"
    elif case == "unattributed":
        output["explanation"] = "The agreed three-page website includes this request."
    else:
        output["explanation"] = "Add a three-page bakery website."
    with pytest.raises(V3InvalidProviderOutput) as caught:
        run(data, output)
    assert caught.value.diagnostics[0]["rule"] == "QUANTIFIED_PROSE"


def test_request_or_context_page_count_does_not_become_authoritative():
    data, output = case_input(), case_output()
    data["client_request"] += " The original scope describes a four-page bakery website."
    data["supporting_context"] = [{"id": "test", "text": "The original scope describes a four-page bakery website."}]
    output["explanation"] = "The original scope describes a four-page bakery website."
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


def test_amount_in_source_phrase_cannot_be_hidden_by_page_notice():
    data, output = case_input(), case_output()
    data["original_project"]["scope"] = "Build a three-page USD website."
    output["source_references"][0]["excerpt"] = data["original_project"]["scope"]
    output["requested_changes"][0]["source_references"][0]["excerpt"] = data["original_project"]["scope"]
    output["explanation"] = "The original scope describes a three-page USD website."
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("bad_ref", ["original.timeline", "original.deliverables", "original.deliverables[0].description",
    "request.client_request", "context/0", "COMPENSATION", "original.milestones/99/description"])
def test_ambiguous_impact_second_reference_stays_strict(bad_ref):
    data = case_input("needs_clarification")
    output = case_output("needs_clarification")
    output["potential_impacts"] = [{
        "category": "DELIVERABLES", "explanation": "Interactive behaviour could affect the deliverable scope.",
        "source_references": [output["source_references"][0].copy(), {"reference": bad_ref, "excerpt": "Untrusted text"}],
    }]
    with pytest.raises(V3InvalidProviderOutput) as caught:
        run(data, output)
    assert caught.value.diagnostics[0] == {
        "rule": "UNKNOWN_SOURCE_REFERENCE", "field": "analysis.potential_impacts.0.source_references.1.reference",
    }


def test_ambiguous_impact_with_single_real_reference_is_valid():
    data, output = case_input("needs_clarification"), case_output("needs_clarification")
    output["potential_impacts"] = [{
        "category": "DELIVERABLES", "explanation": "Interactive behaviour could affect the deliverable scope.",
        "source_references": [output["source_references"][0].copy()],
    }]
    result = run(data, output)
    assert result.analysis.classification == "NEEDS_CLARIFICATION"
    assert result.semantic_review_required


def test_prompt_lists_exact_field_registries_and_valid_impact_examples():
    data = ScopeChangeInput.model_validate(case_input("needs_clarification"))
    system, user = build_prompts(data)
    payload = json.loads(user)
    originals = original_sources(data)
    rules = payload["allowed_references_by_field"]
    assert rules["potential_impacts[*].source_references"] == list(originals)
    assert "request.client_request" not in rules["potential_impacts[*].source_references"]
    assert rules["requested_changes[*].request_evidence"] == ["request.client_request"]
    assert rules["context_references"] == ["context/0"]
    for example in payload["potential_impact_evidence_examples"]:
        assert len(example["source_references"]) == 1
        e = Evidence.model_validate(example["source_references"][0])
        assert e.excerpt == originals[e.reference]
    assert "do not invent a second citation" in system
    assert "original.timeline" not in rules["potential_impacts[*].source_references"]
    assert payload["allowed_page_count_notices"] == [{
        "sentence": "The original scope describes a three-page bakery website.",
        "reference": "original.scope", "source_phrase": "three-page bakery website",
    }]
