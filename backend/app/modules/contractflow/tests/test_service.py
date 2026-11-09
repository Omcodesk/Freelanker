import asyncio
import json

import pytest
from pydantic import ValidationError

from ..errors import GenerationTimeout, InvalidProviderOutput, ProviderError
from ..schemas import ContractDraft, DRAFT_LABEL, ProjectInput, UNRESOLVED_TERMS
from ..service import ContractGenerationService
from .conftest import FakeProvider


def test_valid_generation_and_snapshot(project_data):
    provider = FakeProvider()
    draft = asyncio.run(ContractGenerationService(provider).generate_contract(project_data))
    assert draft.authoritative_data == ProjectInput.model_validate(project_data)
    assert draft.label == DRAFT_LABEL
    assert draft.requires_human_review is True
    assert draft.unresolved_terms == UNRESOLVED_TERMS
    assert ContractDraft.model_validate_json(draft.model_dump_json()) == draft
    project_data["client"]["name"] = "Changed after generation"
    assert draft.authoritative_data.client.name != project_data["client"]["name"]
    assert "Example Bakery" not in provider.calls[0]["user_prompt"]
    with pytest.raises(ValidationError):
        draft.authoritative_data.budget = 1


def test_model_input(project_data):
    draft = asyncio.run(ContractGenerationService(FakeProvider()).generate_contract(ProjectInput(**project_data)))
    assert draft.authoritative_data.project_id == project_data["project_id"]


@pytest.mark.parametrize("field,value", [("label", "FINAL"), ("requires_human_review", False),
                                         ("unresolved_terms", [])])
def test_review_invariants(project_data, field, value):
    draft = asyncio.run(ContractGenerationService(FakeProvider()).generate_contract(project_data))
    payload = draft.model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError):
        ContractDraft.model_validate(payload)


@pytest.mark.parametrize("field,value", [("budget", "999999"), ("governing_law", "Invented law"),
                                         ("authoritative_data", {})])
def test_valid_wording_cannot_smuggle_facts(project_data, field, value):
    draft = asyncio.run(ContractGenerationService(FakeProvider()).generate_contract(project_data))
    payload = draft.ai_wording.model_dump(mode="json")
    payload[field] = value
    with pytest.raises(InvalidProviderOutput):
        asyncio.run(ContractGenerationService(FakeProvider(json.dumps(payload))).generate_contract(project_data))


def test_missing_input_never_calls_provider(project_data):
    provider = FakeProvider()
    del project_data["budget"]
    with pytest.raises(ValidationError):
        asyncio.run(ContractGenerationService(provider).generate_contract(project_data))
    assert not provider.calls


@pytest.mark.parametrize("output", ["not JSON", "```json\n{}\n```", "{}", "null", '{"sections": []}',
    '{"sections": [{"source_ref": "scope", "text": "Pay a penalty"}]}',
    '{"sections": [], "budget": "99999"}', '{"sections": [], "client": {"name": "Invented"}}'])
def test_malformed_or_invented_output(project_data, output):
    with pytest.raises(InvalidProviderOutput):
        asyncio.run(ContractGenerationService(FakeProvider(output)).generate_contract(project_data))


@pytest.mark.parametrize("case", ["altered", "duplicate", "unknown", "missing"])
def test_grounding_checks(project_data, case):
    good = asyncio.run(ContractGenerationService(FakeProvider()).generate_contract(project_data))
    output = good.ai_wording.model_dump(mode="json")
    if case == "altered":
        output["sections"][0]["text"] += " All IP transfers to the client."
    elif case == "duplicate":
        output["sections"].append(output["sections"][0])
    elif case == "unknown":
        output["sections"][0]["source_ref"] = "unknown"
    else:
        output["sections"].pop()
    with pytest.raises(InvalidProviderOutput):
        asyncio.run(ContractGenerationService(FakeProvider(json.dumps(output))).generate_contract(project_data))


def test_provider_error_is_sanitized(project_data):
    with pytest.raises(ProviderError, match="provider failed") as error:
        asyncio.run(ContractGenerationService(FakeProvider(error=RuntimeError("secret"))).generate_contract(project_data))
    assert "secret" not in str(error.value)


def test_timeout_cancels_provider(project_data):
    class BlockingProvider:
        cancelled = False

        async def generate(self, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True

    provider = BlockingProvider()
    with pytest.raises(GenerationTimeout):
        asyncio.run(ContractGenerationService(provider, timeout_seconds=0.01).generate_contract(project_data))
    assert provider.cancelled


def test_external_cancellation_propagates(project_data):
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(ContractGenerationService(FakeProvider(error=asyncio.CancelledError())).generate_contract(project_data))


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), 301])
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        ContractGenerationService(FakeProvider(), timeout_seconds=timeout)
