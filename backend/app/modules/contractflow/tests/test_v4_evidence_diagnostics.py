import json
import unicodedata

import pytest

from .. import live_test_v4
from ..v4.errors import AmendmentValidationError
from ..v4.prompts import build_prompts
from ..v4.schemas import AmendmentEvidence, AmendmentRequest, AmendmentWording
from ..v4.sources import citation_contract, source_registry
from ..v4.validation import validate_wording
from .conftest import FakeProvider
from .test_live_test_v4 import configure
from .test_v4_pipeline import generate
from .v4_support import synthetic_output, synthetic_request


def evidence_failure(output):
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    return caught.value


@pytest.mark.parametrize("kind,check,field,category", [
    ("legacy", "UNKNOWN_REFERENCE", "changes.0.additional_scope.citations.0.reference", "LEGACY_V3_REFERENCE"),
    ("unknown", "UNKNOWN_REFERENCE", "changes.0.additional_scope.citations.0.reference", "UNKNOWN"),
    ("alias", "UNKNOWN_REFERENCE", "changes.0.additional_scope.citations.0.reference", "AGREEMENT"),
    ("fabricated", "EXCERPT_NOT_EXACT", "changes.0.additional_scope.citations.0.excerpt", "AGREEMENT"),
    ("duplicate", "DUPLICATE_REFERENCE", "changes.0.additional_scope.citations", "AGREEMENT"),
    ("request_missing", "REQUIRED_REQUEST_CITATION_MISSING", "changes.0.additional_scope.citations", "REQUEST"),
    ("request_partial", "REQUEST_EXCERPT_INCOMPLETE", "changes.0.additional_scope.citations.1.excerpt", "REQUEST"),
    ("assessment_missing", "REVIEWED_ASSESSMENT_CITATION_MISSING", "changes.0.additional_scope.citations", "ASSESSMENT"),
    ("assessment_partial", "ASSESSMENT_EXCERPT_INCOMPLETE", "changes.0.additional_scope.citations.2.excerpt", "ASSESSMENT"),
    ("context_missing", "AGREEMENT_CONTEXT_MISSING", "changes.0.additional_scope.citations", "AGREEMENT"),
    ("deadline_missing", "AUTHORITATIVE_FACT_CITATION_MISSING", "timeline.citations", "AGREEMENT"),
    ("budget_partial", "AUTHORITATIVE_FACT_EXCERPT_INCOMPLETE", "compensation.citations.0.excerpt", "AGREEMENT"),
])
def test_each_evidence_check_has_safe_field_and_category(kind, check, field, category):
    output = synthetic_output()
    registry = source_registry(synthetic_request())
    citations = output["changes"][0]["additional_scope"]["citations"]
    def replace(index, ref):
        citations[index] = {"reference": ref, "excerpt": registry[ref]}
    if kind == "legacy":
        citations[0]["reference"] = "original.scope"
    elif kind == "unknown":
        citations[0]["reference"] = "PRIVATE_REFERENCE_DO_NOT_PRINT"
    elif kind == "alias":
        citations[0]["reference"] = "agreement.deliverables[0].description"
    elif kind == "fabricated":
        citations[0]["excerpt"] = "PRIVATE_QUOTE_DO_NOT_PRINT"
    elif kind == "duplicate":
        citations.append(citations[0].copy())
    elif kind == "request_missing":
        replace(1, "assessment.explanation")
    elif kind == "request_partial":
        citations[1]["excerpt"] = "online ordering"
    elif kind == "assessment_missing":
        replace(2, "assessment.explanation")
    elif kind == "assessment_partial":
        citations[2]["excerpt"] = "online ordering"
    elif kind == "context_missing":
        replace(0, "agreement.budget")
    elif kind == "deadline_missing":
        output["timeline"]["citations"][0] = {"reference": "agreement.scope", "excerpt": registry["agreement.scope"]}
    else:
        output["compensation"]["citations"][0]["excerpt"] = "1200"
    error = evidence_failure(output)
    assert error.rule == "INVALID_EVIDENCE"
    assert error.diagnostics == ({"field": field, "check": check, "source_category": category},)
    assert "PRIVATE" not in str(error) + repr(error.diagnostics)


def test_valid_fixture_and_field_copy_contract_are_consistent():
    request, output = synthetic_request(), synthetic_output()
    contract = citation_contract(request)
    assert len(contract) == 4
    for item in contract:
        if item["field"].startswith("changes."):
            field = item["field"].split(".")[-1]
            proposal = output["changes"][item["change_index"]][field]
        else:
            proposal = output[item["field"]]
        assert item["copy_citations"] == proposal["citations"]
    assert generate(output=output).human_review_required


@pytest.mark.parametrize("target", ["additional_scope", "deliverable_proposal", "timeline", "compensation"])
def test_field_local_citations_cannot_be_borrowed_from_other_fields(target):
    output = synthetic_output()
    proposal = output["changes"][0][target] if target in {"additional_scope", "deliverable_proposal"} else output[target]
    proposal["citations"] = []
    assert evidence_failure(output).diagnostics[0]["check"] == "SCHEMA_INVALID"


def test_legitimate_proposal_paraphrase_keeps_exact_evidence():
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["text"] = "Online ordering with payment integration could be considered as proposed additional work, subject to negotiation."
    assert generate(output=output).proposals.changes[0].additional_scope.text == output["changes"][0]["additional_scope"]["text"]


@pytest.mark.parametrize("edit", ["hyphen", "case", "ellipsis", "whitespace"])
def test_literal_evidence_is_not_paraphrased_or_normalized(edit):
    output = synthetic_output()
    cite = output["changes"][0]["additional_scope"]["citations"][0]
    if edit == "hyphen":
        cite["excerpt"] = cite["excerpt"].replace("three-page", "three\u2011page")
    elif edit == "case":
        cite["excerpt"] = cite["excerpt"].upper()
    elif edit == "ellipsis":
        cite["excerpt"] = "Build a responsive ... bakery website."
    else:
        cite["excerpt"] = " " + cite["excerpt"] + " "
    parsed = AmendmentEvidence.model_validate(cite)
    assert parsed.excerpt == cite["excerpt"]
    assert evidence_failure(output).diagnostics[0]["check"] == "EXCERPT_NOT_EXACT"


def test_unicode_composition_matches_source_exactly_not_visually():
    request_data = synthetic_request().model_dump(mode="json")
    scope = request_data["original_agreement"]["project"]["scope"] + " Café."
    request_data["original_agreement"]["project"]["scope"] = scope
    request_data["reviewed_assessment"]["assessment"]["input_snapshot"]["original_project"]["scope"] = scope
    request = AmendmentRequest.model_validate(request_data)
    output = synthetic_output()
    for field in ("additional_scope", "deliverable_proposal"):
        output["changes"][0][field]["citations"][0]["excerpt"] = scope
    # JSON Unicode escaping preserves characters and is valid, unlike changing NFC to NFD.
    wording = AmendmentWording.model_validate_json(json.dumps(output, ensure_ascii=True))
    validate_wording(request, wording)
    output["changes"][0]["additional_scope"]["citations"][0]["excerpt"] = unicodedata.normalize("NFD", scope)
    with pytest.raises(AmendmentValidationError) as caught:
        validate_wording(request, AmendmentWording.model_validate(output))
    assert caught.value.diagnostics[0]["check"] == "EXCERPT_NOT_EXACT"


def test_required_request_quote_does_not_strip_extra_whitespace():
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["citations"][1]["excerpt"] += " "
    assert evidence_failure(output).diagnostics[0]["check"] == "EXCERPT_NOT_EXACT"


def test_local_schema_and_prompt_use_v4_ids_and_concrete_full_quote_contract():
    request = synthetic_request()
    system, user = build_prompts(request)
    payload = json.loads(user)
    schema = payload["output_schema"]
    assert "AmendmentEvidence" in schema["$defs"]
    description = schema["$defs"]["AmendmentEvidence"]["properties"]["reference"]["description"]
    assert "e.g. agreement.scope" in description
    assert "e.g. original." not in description
    assert "citation reference IDs ARE REQUIRED" in system
    assert payload["valid_source_ids"] == list(source_registry(request))
    assert payload["citation_contract"] == citation_contract(request)
    assert all(not ref.startswith("original.") for ref in payload["valid_source_ids"])


def test_full_request_citation_fits_all_valid_client_request_lengths():
    data = synthetic_request().model_dump(mode="json")
    original = data["reviewed_assessment"]["assessment"]["input_snapshot"]["client_request"]
    extended = original + " " + "context " * 600
    assert 4000 < len(extended) < 8000
    data["reviewed_assessment"]["assessment"]["input_snapshot"]["client_request"] = extended
    request = AmendmentRequest.model_validate(data)
    output = synthetic_output()
    for field in ("timeline", "compensation"):
        output[field]["citations"][1]["excerpt"] = request.reviewed_assessment.assessment.input_snapshot.client_request
    wording = AmendmentWording.model_validate(output)
    validate_wording(request, wording)
    assert wording.timeline.citations[1].excerpt == request.reviewed_assessment.assessment.input_snapshot.client_request


@pytest.mark.parametrize("mutation,check", [("unknown", "UNKNOWN_REFERENCE"), ("quote", "EXCERPT_NOT_EXACT"),
                                           ("schema", "SCHEMA_EXTRA_FIELD")])
def test_live_runner_prints_only_sanitized_diagnostics(monkeypatch, capsys, mutation, check):
    configure(monkeypatch)
    output = synthetic_output()
    if mutation == "unknown":
        output["timeline"]["citations"][0]["reference"] = "synthetic-test-key-PRIVATE"
    elif mutation == "quote":
        output["timeline"]["citations"][0]["excerpt"] = "PRIVATE_RESPONSE_TEXT"
    else:
        output["synthetic-test-key-PRIVATE_FIELD"] = "PRIVATE_VALUE"
    provider = FakeProvider(json.dumps(output))
    monkeypatch.setattr(live_test_v4, "GroqProvider", lambda settings: provider)
    assert live_test_v4.main(["--run-live"]) == 1
    captured = capsys.readouterr()
    assert "Validation diagnostics:" in captured.err
    assert check in captured.err
    assert "PRIVATE" not in captured.out + captured.err
    assert "synthetic-test-key" not in captured.out + captured.err
    assert len(provider.calls) == 1


@pytest.mark.parametrize("text", ["The client must pay USD 500.", "The deadline will be 2027-03-01.",
    "Both parties approved this amendment.", "The proposed work could include unrelated analytics."])
def test_unsupported_claims_remain_rejected_after_evidence_fix(text):
    output = synthetic_output()
    output["changes"][0]["deliverable_proposal"]["text"] = text
    error = evidence_failure(output)
    assert error.rule in {"UNSAFE_PROPOSAL", "UNSUPPORTED_WORDING"}
    assert error.diagnostics[0]["field"] == "changes.0.deliverable_proposal.text"
