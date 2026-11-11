"""Side-effect-free assessment orchestration; no routes, storage or amendments."""

import asyncio
import math
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from ..errors import GenerationTimeout, InvalidProviderOutput
from ..providers.base import ContractProvider
from .prompts import build_prompts
from .schemas import ACTIONS, ScopeAnalysis, ScopeChangeAssessment, ScopeChangeInput
from .diagnostics import RuleViolation, V3InvalidProviderOutput, issue, validation_issues
from .validation import validate_analysis
from .provider_errors import categorize_provider_error


class ScopeChangeService:
    def __init__(self, provider: ContractProvider, *, timeout_seconds: float = 30):
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 300:
            raise ValueError("Timeout must be finite, positive and at most 300 seconds")
        self.provider = provider
        self.timeout_seconds = timeout_seconds

    async def assess_scope_change(self, input_data: ScopeChangeInput | Mapping[str, Any]) -> ScopeChangeAssessment:
        payload = input_data.model_dump() if isinstance(input_data, ScopeChangeInput) else input_data
        # JSON round-trip detaches and revalidates nested Pydantic instances too.
        initial = ScopeChangeInput.model_validate(payload)
        snapshot = ScopeChangeInput.model_validate_json(initial.model_dump_json())
        system, user = build_prompts(snapshot)
        try:
            async with asyncio.timeout(self.timeout_seconds):
                raw = await self.provider.generate(system_prompt=system, user_prompt=user)
        except TimeoutError:
            raise GenerationTimeout("Scope assessment timed out") from None
        except InvalidProviderOutput:
            raise V3InvalidProviderOutput([issue("PROVIDER_INCOMPLETE_OUTPUT", ("response",))]) from None
        except Exception as error:
            raise categorize_provider_error(error) from None
        try:
            if not isinstance(raw, str):
                raise RuleViolation("RESPONSE_TYPE", ("response",))
            if len(raw.encode("utf-8")) > 64000:
                raise RuleViolation("RESPONSE_SIZE", ("response",))
            analysis = ScopeAnalysis.model_validate_json(raw)
            validate_analysis(snapshot, analysis)
            result = ScopeChangeAssessment(
                request_id=snapshot.request_id, project_id=snapshot.project_id,
                input_snapshot=snapshot, analysis=analysis,
                recommended_action=ACTIONS[analysis.classification],
            )
            return ScopeChangeAssessment.model_validate_json(result.model_dump_json())
        except RuleViolation as error:
            raise V3InvalidProviderOutput([error.issue]) from None
        except ValidationError as error:
            raise V3InvalidProviderOutput(validation_issues(error)) from None
        except (ValueError, TypeError):
            raise V3InvalidProviderOutput([issue("SCHEMA_INVALID", ("analysis",))]) from None
