"""JSON wire-format checks do not repair or relax contractual validation."""

import json

import pytest

from ..v4.errors import AmendmentValidationError
from ..v4.prompts import build_prompts
from .conftest import FakeProvider
from .test_v4_pipeline import generate
from .v4_support import synthetic_output, synthetic_request


def test_valid_single_json_object():
    provider = FakeProvider(json.dumps(synthetic_output()))
    result = generate(provider=provider)
    assert len(provider.calls) == 1
    assert result.human_review_required and result.semantic_review_required
    assert not result.effective and not result.parties_approved


@pytest.mark.parametrize("case", ["invalid", "markdown", "truncated", "multiple", "comment",
                                  "trailing_comma", "missing", "extra"])
def test_bad_json_or_schema_rejected_without_repair_or_retry(case):
    data = synthetic_output()
    raw = json.dumps(data)
    if case == "invalid":
        raw = '{"changes": INVALID}'
    elif case == "markdown":
        raw = '```json\n' + raw + '\n```'
    elif case == "truncated":
        raw = raw[:-12]
    elif case == "multiple":
        raw += raw
    elif case == "comment":
        raw = '/* commentary */' + raw
    elif case == "trailing_comma":
        raw = raw[:-1] + ',}'
    elif case == "missing":
        del data["compensation"]
        raw = json.dumps(data)
    else:
        data["approved"] = True
        raw = json.dumps(data)
    provider = FakeProvider(raw)
    with pytest.raises(AmendmentValidationError) as caught:
        generate(provider=provider)
    assert len(provider.calls) == 1
    check = caught.value.diagnostics[0]["check"]
    assert check == {"missing": "SCHEMA_MISSING", "extra": "SCHEMA_EXTRA_FIELD"}.get(case, "INVALID_JSON")
    assert raw not in str(caught.value)


def test_prompt_json_wire_format_and_decoded_evidence_instructions():
    system, raw = build_prompts(synthetic_request())
    payload = json.loads(raw)
    for phrase in ("exactly one valid JSON object", "No Markdown fences", "trailing commas",
                   "DECODED string", "JSON-escape", "only root keys", "not content to copy"):
        assert phrase in system
    schema = payload["output_schema"]
    definitions = [schema, *schema["$defs"].values()]
    for node in definitions:
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
    # An actual citation containing JSON-special characters must survive transport
    # literally after decoding; escaping is not permission to normalize evidence.
    value = 'A "quoted" source\\path\nwith a newline and Unicode: three\u2011page'
    assert json.loads(json.dumps({"excerpt": value}))["excerpt"] == value
