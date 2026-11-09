"""Source-backed presentation, strict rejection, and historical digest compatibility."""

import asyncio
from pathlib import Path
from uuid import UUID

import pytest

from ..v4.errors import AmendmentValidationError
from ..v4.renderer import render_text, render_text_legacy, render_amendment
from ..v4.schemas import AmendmentDraft, AmendmentWording, NOTICE, UNRESOLVED
from ..v4.validation import validate_wording
from ..v5.schemas import ApprovalSubject, canonical_digest
from ..v5.errors import StaleVersion
from ..persistence.artifacts import StoredArtifact, digest
from ..integrations.contracts import SourceSnapshot
from .test_v4_pipeline import generate
from .v4_support import synthetic_request, synthetic_output
from .v5_support import amendment, initialized, decision

IDENTIFIER = UUID("22222222-2222-4222-8222-222222222222")


def change_text(field, text):
    value = synthetic_output()
    if field in {"additional_scope", "deliverable_proposal"}:
        value["changes"][0][field]["text"] = text
    else:
        value[field]["text"] = text
    return value


@pytest.mark.parametrize("field,text", [
    ("deliverable_proposal", "A proposed deliverable could cover an online ordering system with payment integration, require negotiation."),
    ("timeline", "A proposed timeline could affect the project, require negotiation."),
    ("compensation", "A proposed compensation could require negotiation."),
    ("deliverable_proposal", "A proposed deliverable:could cover online ordering with payment integration."),
])
def test_reproduce_previous_lexical_acceptance_but_new_quality_rejection(field, text):
    output = change_text(field, text)
    validate_wording(synthetic_request(), AmendmentWording.model_validate(output))
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "UNSUPPORTED_WORDING"
    assert caught.value.diagnostics[0]["check"] == "WORDING_QUALITY"


@pytest.mark.parametrize("text", [
    "A proposedaddition could include an online ordering system with payment integration, require negotiation.",
    "A proposed deliverable could cover onlineordering with payment integration.",
])
def test_joined_content_words_are_rejected_not_inventively_split(text):
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=change_text("additional_scope", text))
    assert caught.value.diagnostics[0]["check"] == "CONTENT_VOCABULARY"


def test_server_template_grammar_unresolved_spacing_and_exact_sources():
    draft = generate()
    rendered = draft.rendered_text
    for sentence in (
        "Proposed additional scope remains subject to negotiation and human review.",
        "Proposed deliverable specifications remain unresolved and require human review.",
        "Timeline implications require negotiation and human review.",
        "No revised deadline is established by this draft.",
        "Compensation implications require negotiation and human review.",
        "No additional amount or payment schedule is established by this draft.",
    ):
        assert sentence in rendered
    assert "Reviewed requested change (not agreed terms): Add online ordering with payment integration." in rendered
    assert ", require negotiation" not in rendered and "proposedaddition" not in rendered
    for term in UNRESOLVED:
        assert f"{term.replace('_', ' ').capitalize()}: unresolved — requires negotiation and review." in rendered
    assert "Termination conditions: unresolved" in rendered
    assert "Termination conditions:unresolved" not in rendered
    assert rendered.count(NOTICE) == 2
    assert draft.original_facts == synthetic_request().original_agreement.project
    assert draft.human_review_required and draft.semantic_review_required
    assert not draft.effective and not draft.parties_approved
    assert "Neither party's approval is recorded here." in rendered
    assert "1200.00 USD" in rendered and "2027-01-29" in rendered
    for c in draft.proposals.changes[0].additional_scope.citations:
        assert f"[{c.reference}] {c.excerpt}" in rendered
    assert render_amendment(draft) == rendered


def test_legacy_fixture_stays_byte_identical_and_preserves_v5_digest():
    legacy = Path(__file__).parent / "fixtures/v4/legacy_render.txt"
    expected = legacy.read_text(encoding="utf-8")
    wording = AmendmentWording.model_validate(synthetic_output())
    assert render_text_legacy(IDENTIFIER, synthetic_request(), wording) == expected
    data = amendment().model_dump(mode="json")
    data["rendered_text"] = expected
    historical = AmendmentDraft.model_validate(data)
    old_digest = canonical_digest(1, historical)
    decoded = AmendmentDraft.model_validate_json(historical.model_dump_json())
    assert render_amendment(decoded) == expected
    assert canonical_digest(1, decoded) == old_digest
    assert canonical_digest(1, amendment()) != old_digest
    assert ApprovalSubject.from_draft(decoded, 1).content_digest == old_digest


@pytest.mark.parametrize("kind", ["legacy", "professional"])
def test_final_rendering_tampering_is_rejected(kind):
    draft = amendment()
    data = draft.model_dump(mode="json")
    if kind == "legacy":
        data["rendered_text"] = render_text_legacy(draft.draft_id, draft.request_snapshot, draft.proposals)
    data["rendered_text"] += "\nThe client must pay USD 500."
    with pytest.raises(ValueError):
        AmendmentDraft.model_validate(data)


@pytest.mark.parametrize("text", [
    "The proposed deliverable will include online ordering with payment integration.",
    "The proposed deliverable must include online ordering with payment integration.",
    "The proposed deliverable could include online ordering with payment integration for USD 500.",
    "The proposed deliverable could include online ordering with payment integration by 2027-02-01.",
    "The proposed deliverable could include online ordering with payment integration and analytics.",
    "The proposed deliverable could not include online ordering with payment integration.",
])
def test_templates_do_not_rescue_unsupported_ai_content(text):
    value = AmendmentWording.model_validate(change_text("deliverable_proposal", text))
    with pytest.raises(AmendmentValidationError):
        render_text(IDENTIFIER, synthetic_request(), value)


def test_templates_do_not_rescue_inexact_evidence():
    output = synthetic_output()
    output["changes"][0]["additional_scope"]["citations"][0]["excerpt"] += " changed"
    with pytest.raises(AmendmentValidationError) as caught:
        generate(output=output)
    assert caught.value.rule == "INVALID_EVIDENCE"


def test_ai_interpretation_retained_separately_without_claiming_equivalence():
    text = "A proposed deliverable might include online ordering with integrated payments, subject to negotiation."
    draft = generate(output=change_text("deliverable_proposal", text))
    assert draft.proposals.changes[0].deliverable_proposal.text == text
    assert text not in draft.rendered_text
    assert draft.semantic_review_required
    assert "semantic correctness not established" in draft.deterministic_validation


def test_same_professional_view_still_binds_changed_ai_interpretation():
    original = amendment()
    output = synthetic_output()
    output["changes"][0]["deliverable_proposal"]["text"] = "A proposed deliverable might include online ordering with integrated payments, subject to negotiation."
    proposals = AmendmentWording.model_validate(output)
    data = original.model_dump(mode="json")
    data["proposals"] = proposals.model_dump(mode="json")
    data["rendered_text"] = render_text(original.draft_id, original.request_snapshot, proposals)
    revised = AmendmentDraft.model_validate(data)
    assert revised.rendered_text == original.rendered_text
    assert canonical_digest(1, revised) != canonical_digest(1, original)


def test_material_presentation_revision_supersedes_old_approvals():
    async def scenario():
        # Register a historical rendering with the same exact authoritative data.
        service, _ = await initialized()
        service.repository._records.clear()  # isolated test setup only
        draft = amendment()
        data = draft.model_dump(mode="json")
        data["rendered_text"] = render_text_legacy(draft.draft_id, draft.request_snapshot, draft.proposals)
        old = await service.register_amendment(AmendmentDraft.model_validate(data), 1, "synthetic-client")
        await service.submit_decision(decision(old, key="c"), "synthetic-client")
        await service.submit_decision(decision(old, key="f"), "synthetic-freelancer")
        new = await service.register_amendment(draft, 2, "synthetic-client")
        assert new.state == "PENDING_REVIEW" and new.content_digest != old.content_digest
        assert service.repository._records[(draft.draft_id, 1)].state == "SUPERSEDED"
        assert not (await service.repository.load(draft.draft_id)).decisions
        with pytest.raises(StaleVersion):
            await service.submit_decision(decision(old, key="c"), "synthetic-client")
    asyncio.run(scenario())


def test_v6_archive_retains_historical_payload_and_digest():
    from datetime import datetime, timezone
    draft = amendment()
    source = SourceSnapshot(source_version=1, project=draft.original_facts,
                            agreement=draft.request_snapshot.original_agreement)
    data = draft.model_dump(mode="json")
    data["rendered_text"] = render_text_legacy(draft.draft_id, draft.request_snapshot, draft.proposals)
    historical = AmendmentDraft.model_validate(data)
    item = StoredArtifact(artifact_id=draft.draft_id, artifact_version=1, kind="AMENDMENT", source=source,
        created_at=datetime.now(timezone.utc), payload_json=historical.model_dump_json(),
        content_digest=digest("AMENDMENT", 1, source, historical.model_dump(mode="json")))
    assert StoredArtifact.model_validate_json(item.model_dump_json()).domain().rendered_text == historical.rendered_text
    assert digest("AMENDMENT", 1, source, draft.model_dump(mode="json")) != item.content_digest
