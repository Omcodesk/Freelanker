import asyncio
import json

import pytest

from ..v3.diagnostics import V3InvalidProviderOutput
from ..v3.service import ScopeChangeService
from ..v3.validation import validate_prose
from .conftest import FakeProvider
from .test_v3_schemas import case_input, case_output


def failure(output):
    raw = output if isinstance(output, str) else json.dumps(output)
    with pytest.raises(V3InvalidProviderOutput) as caught:
        asyncio.run(ScopeChangeService(FakeProvider(raw)).assess_scope_change(case_input()))
    return caught.value


@pytest.mark.parametrize("text", ["No revised price is proposed.", "Compensation is not estimated.",
    "Adding a pay button could expand implementation effort."])
def test_legitimate_review_and_technical_wording(text):
    validate_prose(text)
    output = case_output()
    output["explanation"] = text
    result = asyncio.run(ScopeChangeService(FakeProvider(json.dumps(output))).assess_scope_change(case_input()))
    assert result.human_review_required and result.semantic_review_required


@pytest.mark.parametrize("text", ["No revised price is proposed. Charge USD 500.",
    "Compensation is not estimated. The client must pay.",
    "The client will pay for a pay button.", "Payment is due on delivery.",
    "No revised price is proposed. The budget increases."])
def test_narrow_exceptions_do_not_hide_obligations(text):
    with pytest.raises(ValueError):
        validate_prose(text)


def test_numeric_description_reports_field_without_echo():
    output = case_output()
    output["requested_changes"][0]["description"] = "Add ordering for USD 900 SECRET-CONTENT."
    error = failure(output)
    assert error.diagnostics == ({"rule": "QUANTIFIED_PROSE", "field": "analysis.requested_changes.0.description"},)
    assert "SECRET-CONTENT" not in repr(error.diagnostics) + str(error)


def test_binding_term_field_diagnostic():
    output = case_output()
    output["potential_impacts"][1]["explanation"] = "The freelancer shall deliver."
    error = failure(output)
    assert error.diagnostics[0] == {"rule": "POTENTIAL_BINDING_TERM", "field": "analysis.potential_impacts.1.explanation"}


def test_unknown_reference_is_not_echoed():
    output = case_output()
    output["source_references"][0]["reference"] = "SECRET-PROJECT-ID"
    error = failure(output)
    assert error.diagnostics[0] == {"rule": "UNKNOWN_SOURCE_REFERENCE", "field": "analysis.source_references.0.reference"}
    assert "SECRET-PROJECT-ID" not in repr(error.diagnostics)


def test_wrong_excerpt_reports_known_reference_not_content():
    output = case_output()
    output["source_references"][0]["excerpt"] = "SECRET-CONTENT incorrect excerpt"
    error = failure(output)
    assert error.diagnostics[0] == {"rule": "FABRICATED_EXCERPT", "field": "analysis.source_references.0.excerpt", "reference": "original.scope"}
    assert "SECRET-CONTENT" not in repr(error.diagnostics)


def test_path_alias_is_rejected_with_diagnostic():
    output = case_output()
    output["source_references"][0]["reference"] = "original.deliverables[0].description"
    assert failure(output).diagnostics[0]["rule"] == "UNKNOWN_SOURCE_REFERENCE"


def test_schema_missing_required_field():
    output = case_output()
    del output["requested_changes"]
    assert failure(output).diagnostics[0] == {"rule": "SCHEMA_MISSING", "field": "requested_changes"}


def test_unknown_schema_key_sanitized():
    output = case_output()
    output["SECRET-API-KEY-FIELD"] = "SECRET-CONTENT"
    diagnostics = failure(output).diagnostics
    assert diagnostics[0] == {"rule": "SCHEMA_EXTRA_FIELD", "field": "<unrecognized_field>"}
    assert "SECRET" not in repr(diagnostics)


def test_wrong_schema_type_no_input_or_message():
    output = case_output()
    output["source_references"] = ["SECRET-CONTENT"]
    diagnostic = failure(output).diagnostics[0]
    assert diagnostic == {"rule": "SCHEMA_INVALID", "field": "source_references.0"}


def test_json_error_no_parse_fragment_exposed():
    error = failure('{"classification": SECRET-CONTENT}')
    assert error.diagnostics[0]["rule"] == "INVALID_JSON"
    assert "SECRET" not in str(error) + repr(error.diagnostics)


@pytest.mark.parametrize("case,rule", [("duplicate", "DUPLICATE_REFERENCE"),
    ("clarification", "CLARIFICATION_QUESTIONS_REQUIRED"), ("impact", "DUPLICATE_IMPACT_CATEGORY")])
def test_deterministic_and_schema_rules_diagnosed(case, rule):
    output = case_output()
    if case == "duplicate":
        output["source_references"].append(output["source_references"][0].copy())
    elif case == "clarification":
        output["classification"] = "NEEDS_CLARIFICATION"
    else:
        output["potential_impacts"][1]["category"] = output["potential_impacts"][0]["category"]
    assert failure(output).diagnostics[0]["rule"] == rule
