import asyncio
import json

import pytest

from .. import live_test_v3
from ..v3.diagnostics import V3InvalidProviderOutput
from ..v3.synthetic_diagnostics import SyntheticExplanationProbe
from .conftest import FakeProvider
from .test_live_test_v3 import setup
from .test_v3_live_regressions import run
from .test_v3_schemas import case_input, case_output

GROUNDED = "The agreed three-page bakery website is the baseline; ordering could affect implementation effort."


@pytest.mark.parametrize("index", range(3))
def test_all_nested_impacts_use_quantity_grounding(index):
    data, output = case_input(), case_output()
    output["potential_impacts"][index]["explanation"] = GROUNDED
    output["potential_impacts"][index]["source_references"] = [output["source_references"][0].copy()]
    if index == 1:
        # TIMELINE now requires its own actual scheduling evidence as well.
        output["potential_impacts"][index]["source_references"].append({"reference": "original.deadline", "excerpt": "2027-01-29"})
    result = run(data, output)
    assert result.analysis.potential_impacts[index].explanation == GROUNDED
    assert result.human_review_required and result.semantic_review_required
    assert result.input_snapshot.original_project.model_dump(mode="json") == data["original_project"]


def test_impact_cannot_borrow_grounding_from_top_level_citations():
    data, output = case_input(), case_output()
    # Top-level scope evidence supports the count; this impact cites only budget.
    output["potential_impacts"][2]["explanation"] = GROUNDED
    with pytest.raises(V3InvalidProviderOutput) as error:
        run(data, output)
    assert error.value.diagnostics[0] == {
        "rule": "QUANTIFIED_PROSE", "field": "analysis.potential_impacts.2.explanation",
    }


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("text", [
    "The agreed four-page bakery website is the baseline.",
    "The agreed three-page pottery website is the baseline.",
    "Additional cost is USD 500.", "Finish by 2027-03-01.",
    "Apply a 10% surcharge.", "Estimate three days of work.",
    "Payment is due on delivery.", "The client must pay.",
])
def test_ungrounded_or_binding_impact_explanations_rejected(index, text):
    data, output = case_input(), case_output()
    output["potential_impacts"][index]["explanation"] = text
    output["potential_impacts"][index]["source_references"] = [output["source_references"][0].copy()]
    with pytest.raises(V3InvalidProviderOutput) as error:
        run(data, output)
    assert error.value.diagnostics[0]["field"] == f"analysis.potential_impacts.{index}.explanation"


@pytest.mark.parametrize("index", range(3))
def test_opt_in_nested_preview_targets_exact_rejected_field(monkeypatch, capsys, index):
    output = case_output()
    text = "A cost increase of USD 500 is proposed."
    output["potential_impacts"][index]["explanation"] = text
    setup(monkeypatch, [output])
    assert live_test_v3.main(["--scenario", "out_of_scope", "--synthetic-diagnostics"]) == 1
    report = json.loads(capsys.readouterr().out)["scenarios"][0]
    assert report["synthetic_rejected_fields"] == [{
        "field": f"analysis.potential_impacts.{index}.explanation", "text": text,
    }]
    assert "synthetic_rejected_explanation" not in report
    assert report["actual_classification"] is None
    assert report["classification_comparison"] == "NOT_EVALUATED"


def test_default_mode_never_displays_rejected_nested_text(monkeypatch, capsys):
    output = case_output()
    output["potential_impacts"][2]["explanation"] = "A cost increase of USD 500 is proposed."
    setup(monkeypatch, [output])
    assert live_test_v3.main(["--scenario", "out_of_scope"]) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)["scenarios"][0]
    assert "synthetic_rejected_fields" not in report
    assert output["potential_impacts"][2]["explanation"] not in captured.out


@pytest.mark.parametrize("text", ["USD 500; authorization: Bearer private", "USD 500; synthetic-test-key",
    "USD 500; user@example.invalid", "USD 500; headers: private"])
def test_nested_preview_reuses_secret_and_privacy_filter(monkeypatch, capsys, text):
    output = case_output()
    output["potential_impacts"][2]["explanation"] = text
    setup(monkeypatch, [output])
    assert live_test_v3.main(["--scenario", "out_of_scope", "--synthetic-diagnostics"]) == 1
    captured = capsys.readouterr()
    assert text not in captured.out
    assert "Bearer private" not in captured.out
    assert "synthetic-test-key" not in captured.out
    assert "user@example.invalid" not in captured.out
    preview = json.loads(captured.out)["scenarios"][0]["synthetic_rejected_fields"][0]["text"]
    assert preview == "[Explanation omitted: potentially sensitive content]"


def test_nested_preview_not_emitted_for_reference_failure(monkeypatch, capsys):
    output = case_output()
    output["potential_impacts"][2]["source_references"][0]["reference"] = "fabricated"
    setup(monkeypatch, [output])
    assert live_test_v3.main(["--scenario", "out_of_scope", "--synthetic-diagnostics"]) == 1
    report = json.loads(capsys.readouterr().out)["scenarios"][0]
    assert report["validation_diagnostics"][0]["rule"] == "UNKNOWN_SOURCE_REFERENCE"
    assert "synthetic_rejected_fields" not in report


def test_probe_bounds_allowed_fields_and_clears_between_requests():
    output = case_output()
    output["potential_impacts"].append({"explanation": "Out-of-schema fourth impact"})
    provider = FakeProvider(json.dumps(output))
    probe = SyntheticExplanationProbe(provider, "synthetic-test-key")

    async def exercise():
        await probe.generate(system_prompt="", user_prompt="")
        assert probe.preview_for("analysis.potential_impacts.2.explanation") is not None
        assert probe.preview_for("analysis.potential_impacts.3.explanation") is None
        assert probe.preview_for("analysis.potential_impacts.2.source_references") is None
        provider.output = "not JSON"
        await probe.generate(system_prompt="", user_prompt="")
        assert probe.field_previews == {}
        assert probe.preview is None

    asyncio.run(exercise())
