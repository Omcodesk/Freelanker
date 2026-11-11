"""Explicit, pinned synthetic demo. Never use its test verifier in production."""

import argparse
import asyncio
import json
import logging
import sys

from pydantic import ValidationError

from .config import GroqSettings
from .errors import ConfigurationError, GenerationTimeout, ProviderError
from .providers.groq import GroqProvider
from .v4.errors import AmendmentValidationError, ReviewVerificationError
from .v4.review import fingerprint
from .v4.service import AmendmentDraftService
from .v4.provider_errors import AmendmentProviderError

SYNTHETIC_INPUT_PIN = "870a4f13174f9fedc07c2487fe0eadc2d10668aeede591968a1aa01378a22dcb"


def main(argv=()):
    parser = argparse.ArgumentParser(description="Synthetic V4 amendment demo: one request, no retries.")
    parser.add_argument("--run-live", action="store_true", help="Explicitly opt in to one real Groq request.")
    parser.add_argument("--scenario", choices=["ordering"], default="ordering")
    args = parser.parse_args(argv)
    if not args.run_live:
        print("No request made. Explicit --run-live is required for this synthetic-only demo.", file=sys.stderr)
        return 2
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        # The ONLY synthetic verifier implementation lives in test support.
        from .tests.v4_support import SyntheticReviewVerifier, synthetic_request

        request = synthetic_request()
        if fingerprint(request) != SYNTHETIC_INPUT_PIN:
            raise ConfigurationError("Synthetic input pin mismatch")
        settings = GroqSettings.from_env()
        if settings.model != "openai/gpt-oss-120b":
            raise ConfigurationError("V4 live demo requires openai/gpt-oss-120b")
        service = AmendmentDraftService(GroqProvider(settings), SyntheticReviewVerifier(),
                                        timeout_seconds=settings.timeout_seconds)
        result = asyncio.run(service.generate_amendment(request))
        report = {"model": settings.model, "status": "DETERMINISTIC_CHECKS_PASSED",
                  "synthetic_review_notice": "SYNTHETIC TEST RECORD — NOT A REAL REVIEW OR AMENDMENT APPROVAL",
                  "human_review_required": result.human_review_required,
                  "semantic_review_required": result.semantic_review_required,
                  "effective": result.effective, "rendered_amendment": result.rendered_text}
        text = json.dumps(report, ensure_ascii=False, indent=2).replace(settings.api_key.get_secret_value(), "[REDACTED]")
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(text.encode(encoding, "backslashreplace").decode(encoding))
        return 0
    except ConfigurationError:
        message = "V4 configuration failure: check Groq environment, model and unchanged synthetic fixtures."
    except ReviewVerificationError:
        message = "V4 review verification failed; no amendment was generated."
    except AmendmentValidationError as error:
        message = "V4 validation failed: " + error.rule + "\nValidation diagnostics: " + json.dumps(error.diagnostics, ensure_ascii=True)
    except GenerationTimeout:
        message = "V4 timeout. No retry was attempted."
    except ProviderError as error:
        category = getattr(error, "category", "UNKNOWN")
        message = "V4 provider failure: " + category + ". No retry was attempted."
        if isinstance(error, AmendmentProviderError):
            message += "\nProvider diagnostics: " + json.dumps(error.diagnostics(), ensure_ascii=True)
    except (OSError, ValidationError, ValueError):
        message = "V4 fixture or validation failure; raw details suppressed."
    except KeyboardInterrupt:
        print("V4 demo interrupted.", file=sys.stderr)
        return 130
    except Exception:
        message = "V4 demo failed; raw details suppressed to protect secrets."
    finally:
        logging.disable(previous_logging)
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
