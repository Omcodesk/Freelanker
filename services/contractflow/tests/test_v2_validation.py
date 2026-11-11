import pytest

from ..errors import InvalidProviderOutput
from .test_v2_service import generate, sample_output


@pytest.mark.parametrize("case", ["missing", "duplicate", "unknown", "extra"])
def test_coverage_and_extra_fields(project_data, case):
    output = sample_output()
    if case == "missing":
        output["sections"].pop()
    elif case == "duplicate":
        output["sections"].append(output["sections"][0].copy())
    elif case == "unknown":
        output["sections"][0]["source_ref"] = "deliverables/99"
    else:
        output["budget"] = "999"
    with pytest.raises(InvalidProviderOutput):
        generate(project_data, output)


@pytest.mark.parametrize("text", [
    "Build four bakery website pages.", "Build three pages by 2027-02-01.",
    "Build three pages for USD 999.", "Build three pages for £100.",
    "Build three pages. Payment is due on delivery.",
    "Build three pages with a penalty for delays.",
    "Build three pages under governing law of England.",
    "Build three pages and transfer intellectual property ownership.",
    "Build three pages subject to termination on request.",
    "Build three pages with acceptance on delivery.",
    "Build three pages and provide unlimited revisions.",
    "Build three pages without contact forms.",
    "Build three pages.\nCOMPENSATION: invented",
])
def test_detectable_changes_and_obligations(project_data, text):
    output = sample_output()
    output["sections"][0]["text"] = text
    with pytest.raises(InvalidProviderOutput):
        generate(project_data, output)


def test_numeric_equivalent_paraphrase(project_data):
    output = sample_output()
    output["sections"][0]["text"] = output["sections"][0]["text"].replace("three", "3")
    assert generate(project_data, output).semantic_review_required


def test_mismatched_source_quantity_rejected(project_data):
    output = sample_output()
    output["sections"][0]["source_ref"], output["sections"][1]["source_ref"] = (
        output["sections"][1]["source_ref"], output["sections"][0]["source_ref"])
    with pytest.raises(InvalidProviderOutput):
        generate(project_data, output)


def test_semantic_false_negative_is_explicit(project_data):
    output = sample_output()
    output["sections"][1]["text"] = "Provide PDF mockups for the home, menu and contact pages."
    draft = generate(project_data, output)
    # A format change passes lexical checks: human review must catch it.
    assert draft.semantic_review_required is True
    assert draft.deterministic_checks == "passed; semantic equivalence not established"


def test_conservative_false_positive(project_data):
    project_data["deliverables"][1]["description"] = "Deployment acceptance checklist."
    output = sample_output()
    output["sections"][2]["text"] = "Provide a deployment acceptance checklist."
    with pytest.raises(InvalidProviderOutput):
        generate(project_data, output)
