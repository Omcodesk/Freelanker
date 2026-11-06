"""Async entry point independent of FastAPI, persistence and identity systems."""

import asyncio
import math
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from .errors import GenerationTimeout, InvalidProviderOutput, ProviderError
from .prompts import build_prompts
from .providers.base import ContractProvider
from .schemas import ContractDraft, ProjectInput, ProviderOutput


class ContractGenerationService:
    def __init__(self, provider: ContractProvider, *, timeout_seconds: float = 30):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 300:
            raise ValueError("Timeout must be finite and between 0 and 300 seconds")
        self.provider = provider
        self.timeout_seconds = timeout_seconds

    async def generate_contract(self, project_data: ProjectInput | Mapping[str, Any]) -> ContractDraft:
        # Revalidate a detached snapshot, including when a model instance is supplied.
        data = project_data.model_dump() if isinstance(project_data, ProjectInput) else project_data
        project = ProjectInput.model_validate(data)
        system, user = build_prompts(project)
        try:
            async with asyncio.timeout(self.timeout_seconds):
                raw = await self.provider.generate(system_prompt=system, user_prompt=user)
        except TimeoutError:
            raise GenerationTimeout("Contract generation timed out") from None
        except InvalidProviderOutput:
            raise InvalidProviderOutput("Provider returned incomplete draft wording") from None
        except Exception:
            raise ProviderError("Contract generation provider failed") from None
        try:
            wording = ProviderOutput.model_validate_json(raw)
            return ContractDraft(authoritative_data=project, ai_wording=wording)
        except (ValidationError, TypeError, ValueError):
            raise InvalidProviderOutput("Provider returned invalid or ungrounded draft wording") from None
