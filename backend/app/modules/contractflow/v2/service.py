"""Opt-in async V2 orchestration using the existing provider abstraction."""

import asyncio
import math
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from ..errors import GenerationTimeout, InvalidProviderOutput, ProviderError
from ..providers.base import ContractProvider
from ..schemas import ProjectInput
from .prompts import build_prompts
from .schemas import AgreementDraft, AgreementWording, assemble_sections
from .validation import validate_wording


class AgreementDraftService:
    def __init__(self, provider: ContractProvider, *, timeout_seconds: float = 30):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 300:
            raise ValueError("Timeout must be finite and between 0 and 300 seconds")
        self.provider = provider
        self.timeout_seconds = timeout_seconds

    async def generate_contract(self, project_data: ProjectInput | Mapping[str, Any]) -> AgreementDraft:
        data = project_data.model_dump() if isinstance(project_data, ProjectInput) else project_data
        project = ProjectInput.model_validate(data)
        system, user = build_prompts(project)
        try:
            async with asyncio.timeout(self.timeout_seconds):
                raw = await self.provider.generate(system_prompt=system, user_prompt=user)
        except TimeoutError:
            raise GenerationTimeout("Agreement generation timed out") from None
        except InvalidProviderOutput:
            raise InvalidProviderOutput("Provider returned incomplete wording") from None
        except Exception:
            raise ProviderError("Agreement provider failed") from None
        try:
            wording = AgreementWording.model_validate_json(raw)
            validate_wording(project, wording.sections)
            return AgreementDraft(authoritative_data=project, ai_wording=wording,
                                  sections=assemble_sections(project, wording))
        except (ValidationError, ValueError, TypeError):
            raise InvalidProviderOutput("Invalid V2 wording: schema or deterministic safeguards failed") from None
