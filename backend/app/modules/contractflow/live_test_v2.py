"""One-request V2 smoke test; run as a module from the repository root."""

import asyncio
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from .config import GroqSettings
from .errors import ConfigurationError, GenerationTimeout, InvalidProviderOutput, ProviderError
from .providers.groq import GroqProvider
from .schemas import ProjectInput
from .v2.render import render_agreement
from .v2.schemas import AgreementDraft
from .v2.service import AgreementDraftService


async def _generate(settings: GroqSettings, project: ProjectInput) -> AgreementDraft:
    service = AgreementDraftService(GroqProvider(settings), timeout_seconds=settings.timeout_seconds)
    # One service call; the existing adapter sets max_retries=0.
    result = await service.generate_contract(project)
    draft = AgreementDraft.model_validate_json(result.model_dump_json())
    if draft.authoritative_data != project:
        raise InvalidProviderOutput("Authoritative snapshot changed")
    return draft


def main() -> int:
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        settings = GroqSettings.from_env()
        path = Path(__file__).parent / "tests" / "fixtures" / "website_project.json"
        project = ProjectInput.model_validate_json(path.read_text(encoding="utf-8"))
        draft = asyncio.run(_generate(settings, project))
        report = (
            f"V2 live test succeeded. Model: {settings.model}\n"
            "Deterministic validation PASSED: structure, project snapshot, source references, "
            "wording safeguards and draft/review labels.\n"
            "HUMAN SEMANTIC REVIEW REQUIRED — semantic equivalence is not established.\n\n"
            + render_agreement(draft)
        )
        report = report.replace(settings.api_key.get_secret_value(), "[REDACTED]")
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(report.encode(encoding, errors="backslashreplace").decode(encoding))
        return 0
    except ConfigurationError:
        message = (
            "Configuration error: set GROQ_API_KEY and GROQ_MODEL in this PowerShell session. "
            "CONTRACTFLOW_TIMEOUT_SECONDS defaults to 30 and must be positive and <= 300."
        )
    except InvalidProviderOutput:
        message = (
            "V2 validation FAILED: response is malformed, incomplete, changes project facts, "
            "or fails source/wording safeguards. No retry or validation bypass was used."
        )
    except GenerationTimeout:
        message = "V2 timeout: configured deadline exceeded. No retry was attempted."
    except ProviderError:
        message = (
            "V2 API/provider failure: check credentials, model JSON-mode support, quota and connectivity. "
            "Raw provider errors are suppressed. No retry was attempted."
        )
    except (OSError, ValidationError):
        message = "V2 setup/validation failure: check the synthetic fixture and installed dependencies."
    except KeyboardInterrupt:
        print("V2 live test cancelled.", file=sys.stderr)
        return 130
    except Exception:
        message = "Unexpected V2 live-test failure; raw details suppressed to protect secrets."
    finally:
        logging.disable(previous_logging)
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
