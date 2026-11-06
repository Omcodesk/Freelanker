"""Exact final notices: preserve spaces, legal wording and historical bytes."""

import json
from pathlib import Path

import pytest

from .. import live_test_v4
from ..v4.renderer import render_text, render_text_legacy, render_amendment
from ..v4.schemas import AmendmentDraft, NOTICE
from ..v5.schemas import ApprovalSubject
from .conftest import FakeProvider
from .test_live_test_v4 import configure
from .test_v4_pipeline import generate
from .v5_support import amendment
from .v4_support import synthetic_output

EXPECTED_LINES = [
    "REVIEW AND APPROVAL NOTICE",
    NOTICE,
    "Review of an assessment does not approve this amendment. Neither party's approval is recorded here.",
    "The original agreement is not modified by generating this draft. No signatures or effective date are supplied.",
]


@pytest.mark.parametrize("renderer", [render_text, render_text_legacy])
def test_exact_final_notice_lines_and_no_missing_word_boundaries(renderer):
    draft = amendment()
    rendered = renderer(draft.draft_id, draft.request_snapshot, draft.proposals)
    assert rendered.splitlines()[-4:] == EXPECTED_LINES
    assert "notapprove" not in rendered and "oreffective" not in rendered


@pytest.mark.parametrize("old,new", [("not approve", "notapprove"), ("or effective", "oreffective")])
@pytest.mark.parametrize("renderer", [render_text, render_text_legacy])
def test_missing_notice_space_is_integrity_failure_not_silent_repair(renderer, old, new):
    draft = amendment()
    payload = draft.model_dump(mode="json")
    payload["rendered_text"] = renderer(draft.draft_id, draft.request_snapshot, draft.proposals).replace(old, new)
    with pytest.raises(ValueError):
        AmendmentDraft.model_validate(payload)


def test_service_notice_and_authoritative_data_are_preserved():
    result = generate()
    assert result.rendered_text.splitlines()[-4:] == EXPECTED_LINES
    assert result.original_facts == result.request_snapshot.original_agreement.project
    assert result.proposals.model_dump(mode="json") == synthetic_output()
    assert result.human_review_required and result.semantic_review_required
    assert not result.effective and not result.parties_approved
    assert render_amendment(result) == result.rendered_text


def test_live_runner_json_and_encoding_preserve_notice_spaces_offline(monkeypatch, capsys):
    configure(monkeypatch)
    provider = FakeProvider(json.dumps(synthetic_output()))
    monkeypatch.setattr(live_test_v4, "GroqProvider", lambda settings: provider)
    assert live_test_v4.main(["--run-live", "--scenario", "ordering"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["rendered_amendment"].splitlines()[-4:] == EXPECTED_LINES
    assert report["human_review_required"] and report["semantic_review_required"]
    assert report["effective"] is False
    assert "synthetic-test-key" not in captured.out + captured.err
    assert len(provider.calls) == 1  # Fake provider only; no SDK request.


def test_legacy_notice_artifact_and_approval_digest_remain_exact():
    draft = amendment()
    expected = (Path(__file__).parent / "fixtures/v4/legacy_render.txt").read_text(encoding="utf-8")
    payload = draft.model_dump(mode="json")
    payload["rendered_text"] = expected
    historical = AmendmentDraft.model_validate(payload)
    original = ApprovalSubject.from_draft(historical, 1)
    restored = ApprovalSubject.model_validate_json(original.model_dump_json())
    assert restored.content_digest == original.content_digest
    assert restored.draft.rendered_text.encode("utf-8") == expected.encode("utf-8")
    assert restored.draft.rendered_text.splitlines()[-4:] == EXPECTED_LINES
    assert render_amendment(restored.draft) == expected
