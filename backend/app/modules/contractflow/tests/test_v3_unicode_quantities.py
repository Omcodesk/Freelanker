import pytest

from ..v3.diagnostics import V3InvalidProviderOutput
from ..v3.quantities import extract_quantities, grounded_count_spans
from ..v3.schemas import Evidence
from .test_v3_live_regressions import run
from .test_v3_schemas import case_input, case_output

EXACT_REJECTION = (
    "The request asks for an online ordering system with payment integration, which is not mentioned in the agreed scope "
    "that only covers building a three\u2011page bakery website and providing deployment instructions."
)


def test_exact_unicode_rejection_passes_with_actual_fixture_and_local_evidence():
    data, output = case_input(), case_output()
    assert "three-page" in data["original_project"]["scope"]
    assert "three\u2011page" in EXACT_REJECTION
    output["explanation"] = EXACT_REJECTION
    result = run(data, output)
    assert result.analysis.explanation == EXACT_REJECTION
    assert result.input_snapshot.original_project.model_dump(mode="json") == data["original_project"]
    assert result.human_review_required and result.semantic_review_required


@pytest.mark.parametrize("separator", ["-", "\u2010", "\u2011", "\ufe63", "\uff0d"])
def test_supported_hyphens_match_same_fact_and_preserve_raw_spans(separator):
    text = f"The agreed three{separator}page bakery website is the baseline."
    source = "Build a three-page bakery website."
    claims = extract_quantities(text)
    assert len(claims) == 1
    assert claims[0].key == (3, "pages", ("bakery", "website"))
    assert text[claims[0].start:claims[0].end] == "three"
    spans = grounded_count_spans(text, {"original.scope": source}, (Evidence(reference="original.scope", excerpt=source),))
    assert spans == ((claims[0].start, claims[0].end),)
    data, output = case_input(), case_output()
    output["explanation"] = text
    assert run(data, output).analysis.explanation == text


def test_unicode_source_matches_ascii_prose_without_modifying_source_or_evidence():
    data, output = case_input(), case_output()
    scope = data["original_project"]["scope"].replace("three-page", "three\u2011page")
    data["original_project"]["scope"] = scope
    output["source_references"][0]["excerpt"] = scope
    output["requested_changes"][0]["source_references"][0]["excerpt"] = scope
    output["explanation"] = EXACT_REJECTION.replace("\u2011", "-")
    result = run(data, output)
    assert result.input_snapshot.original_project.scope == scope
    assert result.analysis.source_references[0].excerpt == scope


def test_unicode_variant_is_not_tolerated_in_exact_evidence_excerpt():
    data, output = case_input(), case_output()
    output["explanation"] = EXACT_REJECTION
    output["source_references"][0]["excerpt"] = data["original_project"]["scope"].replace("three-page", "three\u2011page")
    with pytest.raises(V3InvalidProviderOutput) as caught:
        run(data, output)
    assert caught.value.diagnostics[0]["rule"] == "FABRICATED_EXCERPT"


@pytest.mark.parametrize("case", ["missing", "partial", "unrelated", "fabricated_reference"])
def test_unicode_claim_still_requires_field_local_authoritative_evidence(case):
    data, output = case_input(), case_output()
    output["explanation"] = EXACT_REJECTION
    if case == "missing":
        output["source_references"] = output["source_references"][1:]
    elif case == "partial":
        output["source_references"][0]["excerpt"] = "bakery website"
    elif case == "unrelated":
        output["source_references"] = [output["source_references"][1], {"reference": "original.budget", "excerpt": "1200.00"}]
    else:
        output["source_references"][0]["reference"] = "original.invented"
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


def test_unicode_impact_claim_cannot_borrow_top_level_evidence():
    data, output = case_input(), case_output()
    output["potential_impacts"][2]["explanation"] = EXACT_REJECTION
    with pytest.raises(V3InvalidProviderOutput) as caught:
        run(data, output)
    assert caught.value.diagnostics[0]["rule"] == "QUANTIFIED_PROSE"
    assert caught.value.diagnostics[0]["field"] == "analysis.potential_impacts.2.explanation"


@pytest.mark.parametrize("text", [
    EXACT_REJECTION.replace("three\u2011page", "four\u2011page"),
    EXACT_REJECTION.replace("bakery website", "pottery website"),
    EXACT_REJECTION + " Charge USD 500.",
    EXACT_REJECTION + " Finish by 2027-03-01.",
    EXACT_REJECTION + " Apply a 10% surcharge.",
    EXACT_REJECTION + " Estimate three days.",
    EXACT_REJECTION + " Payment is due on delivery.",
    EXACT_REJECTION + " The client must pay.",
    EXACT_REJECTION + " The freelancer shall deliver.",
    "Add to the agreed scope a three\u2011page bakery website.",
])
def test_unicode_normalization_does_not_allow_fabrications_or_obligations(text):
    data, output = case_input(), case_output()
    output["explanation"] = text
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


@pytest.mark.parametrize("separator", ["\u2012", "\u2013", "\u2014", "\u2212", "\u00ad", "\u200b"])
def test_ranges_minus_and_invisible_separators_are_not_blanket_normalized(separator):
    data, output = case_input(), case_output()
    output["explanation"] = EXACT_REJECTION.replace("\u2011", separator)
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)
