import asyncio
import json

import httpx
import pytest

from .. import live_test_v3
from ..providers.groq import GroqProvider
from ..v3.provider_errors import categorize_provider_error
from ..v3.synthetic_diagnostics import require_synthetic_cases, sanitize_explanation
from .test_live_test_v3 import setup
from .test_v3_live_regressions import run
from .test_v3_schemas import case_input, case_output


def test_preview_disabled_by_default(monkeypatch, capsys):
    output = case_output("in_scope")
    output["explanation"] = "The agreed three-page website includes this request."
    setup(monkeypatch, [output, case_output("out_of_scope"), case_output("needs_clarification")])
    assert live_test_v3.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report["synthetic_diagnostics_enabled"] is False
    assert "synthetic_rejected_explanation" not in report["scenarios"][0]


def test_preview_enabled_for_pinned_synthetic_fixtures(monkeypatch, capsys):
    outputs = [case_output(name) for name, _ in live_test_v3.SCENARIOS]
    outputs[0]["explanation"] = "The original three-page website is the baseline."
    outputs[1]["explanation"] = "No extra cost: zero dollars."
    provider = setup(monkeypatch, outputs)
    assert live_test_v3.main(["--synthetic-diagnostics"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["synthetic_diagnostics_enabled"] is True
    assert report["scenarios"][0]["synthetic_rejected_explanation"] == outputs[0]["explanation"]
    assert report["scenarios"][1]["synthetic_rejected_explanation"] == outputs[1]["explanation"]
    assert "synthetic_rejected_explanation" not in report["scenarios"][2]
    assert len(provider.calls) == 3


def test_preview_rejects_modified_or_production_input_before_request(monkeypatch, capsys):
    provider = setup(monkeypatch)
    cases = live_test_v3._load_scenarios()
    name, expected, data = cases[0]
    cases[0] = (name, expected, data.model_copy(update={"client_request": "Production customer text"}))
    monkeypatch.setattr(live_test_v3, "_load_scenarios", lambda: cases)
    assert live_test_v3.main(["--synthetic-diagnostics"]) == 1
    assert not provider.calls
    assert "Production customer" not in capsys.readouterr().err


def test_pin_checks_cover_project_context_ids_and_scenarios():
    cases = live_test_v3._load_scenarios()
    require_synthetic_cases(cases)
    with pytest.raises(ValueError):
        require_synthetic_cases(cases[:1])
    name, expected, data = cases[2]
    cases[2] = (name, expected, data.model_copy(update={"supporting_context": ()}))
    with pytest.raises(ValueError):
        require_synthetic_cases(cases)


@pytest.mark.parametrize("text", ["authorization: Bearer REAL-KEY", "API_KEY=REAL-KEY", "gsk_private123",
    "Headers: private", "Email user@example.invalid", "https://private.example", "abc\u202ePRIVATE", "actual-key-value"])
def test_preview_sanitizes_potential_credentials_headers_or_contact_data(text):
    assert sanitize_explanation(text, "actual-key-value").startswith("[Explanation omitted")


def test_preview_bounded_and_controls_removed():
    assert "exceeds preview limit" in sanitize_explanation("x" * 2001, "key")
    assert sanitize_explanation("three\npage\x1bwebsite", "key") == "three page website"


def test_preview_not_attached_to_unrelated_evidence_failure(monkeypatch, capsys):
    output = case_output("in_scope")
    output["source_references"][0]["reference"] = "fabricated"
    setup(monkeypatch, [output, case_output("out_of_scope"), case_output("needs_clarification")])
    assert live_test_v3.main(["--synthetic-diagnostics"]) == 1
    first = json.loads(capsys.readouterr().out)["scenarios"][0]
    assert first["validation_diagnostics"][0]["rule"] == "UNKNOWN_SOURCE_REFERENCE"
    assert "synthetic_rejected_explanation" not in first


@pytest.mark.parametrize("kind,status,category", [
    ("AuthenticationError", 401, "AUTHENTICATION"), ("RateLimitError", 429, "RATE_LIMIT"),
    ("BadRequestError", 400, "PROVIDER_REJECTION"), ("PermissionDeniedError", 403, "PROVIDER_REJECTION"),
    ("InternalServerError", 503, "PROVIDER_REJECTION"), ("APIConnectionError", None, "CONNECTIVITY"),
    ("APITimeoutError", None, "TIMEOUT"),
])
def test_provider_categories_through_unchanged_sdk_adapter(monkeypatch, capsys, kind, status, category):
    import groq
    from .test_groq_adapter import adapter, response

    setup(monkeypatch)
    monkeypatch.setattr(live_test_v3, "GroqProvider", GroqProvider)
    request = httpx.Request("POST", "https://example.invalid", headers={"Authorization": "Bearer private"})
    cls = getattr(groq, kind)
    if status:
        error = cls("RAW-PRIVATE-BODY", response=httpx.Response(status, request=request), body={"private": "BODY"})
    else:
        error = cls(request=request)
    _, factory, create, _ = adapter(monkeypatch)
    create.side_effect = [error, response(json.dumps(case_output("out_of_scope"))),
                          response(json.dumps(case_output("needs_clarification")))]
    assert live_test_v3.main() == 1
    captured = capsys.readouterr()
    first = json.loads(captured.out)["scenarios"][0]
    assert first["provider_error_category"] == category
    if status:
        assert first["provider_http_status"] == status
    assert "RAW-PRIVATE-BODY" not in captured.out + captured.err
    assert "Bearer private" not in captured.out + captured.err
    assert create.await_count == 3
    assert all(call.kwargs["max_retries"] == 0 for call in factory.call_args_list)


def test_unknown_provider_error_does_not_guess_auth_or_rate_limit():
    result = categorize_provider_error(RuntimeError("401 authentication failure, maybe rate limit"))
    assert result.category == "UNKNOWN"
    assert "401" not in str(result)


def test_existing_json_mode_and_no_imposed_token_limit(monkeypatch, capsys):
    from .test_groq_adapter import adapter, response
    setup(monkeypatch)
    monkeypatch.setattr(live_test_v3, "GroqProvider", GroqProvider)
    _, _, create, _ = adapter(monkeypatch)
    create.side_effect = [response(json.dumps(case_output(name))) for name, _ in live_test_v3.SCENARIOS]
    assert live_test_v3.main() == 0
    for call in create.call_args_list:
        assert call.kwargs["response_format"] == {"type": "json_object"}
        assert "max_tokens" not in call.kwargs
        assert "max_completion_tokens" not in call.kwargs
    capsys.readouterr()


@pytest.mark.parametrize("full_scope", [False, True])
def test_exact_cited_original_page_count_quote_is_legitimate(full_scope):
    data, output = case_input(), case_output()
    quote = data["original_project"]["scope"] if full_scope else "three-page bakery website"
    output["explanation"] = f'Original scope excerpt: "{quote}". Ordering appears additional.'
    result = run(data, output)
    assert result.human_review_required and result.semantic_review_required


@pytest.mark.parametrize("quote", ["four-page bakery website", "three-page bakery website costs USD 500",
    "three-page bakery website due 2027-03-01", "three-page bakery website with a 10% deposit",
    "three-page bakery website; the client must pay", "three-page bakery website in five days"])
def test_quoted_fabrications_and_binding_terms_remain_rejected(quote):
    from ..v3.diagnostics import V3InvalidProviderOutput
    data, output = case_input(), case_output()
    output["explanation"] = f'Original scope excerpt: "{quote}".'
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)


def test_nonbinding_does_not_mean_authoritative_financial_statement():
    from ..v3.diagnostics import V3InvalidProviderOutput
    data, output = case_input(), case_output()
    output["explanation"] = "There is zero additional cost, subject to review."
    with pytest.raises(V3InvalidProviderOutput):
        run(data, output)
