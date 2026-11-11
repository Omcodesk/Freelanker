import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from groq import APITimeoutError

from ..config import GroqSettings
from ..errors import GenerationTimeout, InvalidProviderOutput, ProviderError
from ..providers.groq import GroqProvider
from ..service import ContractGenerationService


def adapter(monkeypatch, response=None, error=None):
    create = AsyncMock(return_value=response, side_effect=error)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    context = AsyncMock()
    context.__aenter__.return_value = client
    factory = Mock(return_value=context)
    monkeypatch.setattr("groq.AsyncGroq", factory)
    settings = GroqSettings.from_env({"GROQ_API_KEY": "synthetic-test-key", "GROQ_MODEL": "test-model"})
    return GroqProvider(settings), factory, create, context


def response(content="{}", reason="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=reason)])


def test_adapter_request_and_cleanup(monkeypatch):
    provider, factory, create, context = adapter(monkeypatch, response())
    assert asyncio.run(provider.generate(system_prompt="system", user_prompt="data")) == "{}"
    assert factory.call_args.kwargs["max_retries"] == 0
    assert create.call_args.kwargs["response_format"] == {"type": "json_object"}
    assert create.call_args.kwargs["model"] == "test-model"
    assert create.call_args.kwargs["messages"][1]["content"] == "data"
    context.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("result", [response(None), response(""), response(reason="length"), SimpleNamespace(choices=[])])
def test_adapter_invalid_response(monkeypatch, project_data, result):
    provider, *_ = adapter(monkeypatch, result)
    with pytest.raises(InvalidProviderOutput):
        asyncio.run(ContractGenerationService(provider).generate_contract(project_data))


def test_adapter_timeout_mapping(monkeypatch, project_data):
    provider, *_ = adapter(monkeypatch, error=APITimeoutError(request=httpx.Request("POST", "https://example.invalid")))
    with pytest.raises(GenerationTimeout):
        asyncio.run(ContractGenerationService(provider).generate_contract(project_data))


def test_adapter_failure(monkeypatch, project_data):
    provider, *_ = adapter(monkeypatch, error=RuntimeError("sensitive provider detail"))
    with pytest.raises(ProviderError, match="provider failed"):
        asyncio.run(ContractGenerationService(provider).generate_contract(project_data))
