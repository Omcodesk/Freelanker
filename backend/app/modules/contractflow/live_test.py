"""Explicit live smoke test. Run with python -m, never during test discovery."""

import asyncio
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from .config import GroqSettings
from .errors import (
    ConfigurationError,
    GenerationTimeout,
    InvalidProviderOutput,
    ProviderError,
)
from .providers.groq import GroqProvider
from .schemas import ContractDraft, ProjectInput
from .service import ContractGenerationService


async def _generate(settings: GroqSettings, project: ProjectInput) -> ContractDraft:
    service = ContractGenerationService(
        GroqProvider(settings), timeout_seconds=settings.timeout_seconds
    )
    # One service invocation; the existing adapter disables SDK retries.
    draft = await service.generate_contract(project)
    # Revalidate the serialized result, including grounding and review invariants.
    return ContractDraft.model_validate_json(draft.model_dump_json())


def main() -> int:
    # Prevent inherited SDK/HTTP debug logging from exposing request details.
    logging.disable(logging.CRITICAL)
    try:
        settings = GroqSettings.from_env()
        fixture = Path(__file__).parent / "tests" / "fixtures" / "website_project.json"
        project = ProjectInput.model_validate_json(fixture.read_text(encoding="utf-8"))
        draft = asyncio.run(_generate(settings, project))
        report = json.dumps({
            "status": "success",
            "validation": "Schema, grounding and review invariants passed",
            "model": settings.model,
            "label": draft.label,
            "sections": draft.ai_wording.model_dump(mode="json")["sections"],
            "unresolved_terms": list(draft.unresolved_terms),
        }, ensure_ascii=True, indent=2)
        # Defense in depth: never emit a credential even if echoed unexpectedly.
        print(report.replace(settings.api_key.get_secret_value(), "[REDACTED]"))
        return 0
    except ConfigurationError:
        message = (
            "Configuration error: set GROQ_API_KEY and GROQ_MODEL in this session; "
            "CONTRACTFLOW_TIMEOUT_SECONDS must be positive and <= 300 (default 30)."
        )
    except (OSError, ValidationError):
        message = "Validation/setup error: check the synthetic fixture and installed dependencies."
    except InvalidProviderOutput:
        message = "Validation failed: Groq returned malformed, incomplete or ungrounded wording."
    except GenerationTimeout:
        message = "Timeout: generation exceeded the configured deadline. No retry was attempted."
    except ProviderError:
        message = (
            "API/provider error: check credentials, model JSON-mode support, quota and connectivity. "
            "The pipeline suppresses raw provider details to protect secrets."
        )
    except KeyboardInterrupt:
        print("Live test cancelled.", file=sys.stderr)
        return 130
    except Exception:
        message = "Unexpected live-test failure; raw exception details were suppressed to protect secrets."
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
