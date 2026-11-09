"""Explicit three-scenario live smoke test; no calls occur on import."""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from .config import GroqSettings
from .errors import ConfigurationError, GenerationTimeout, InvalidProviderOutput, ProviderError
from .providers.groq import GroqProvider
from .schemas import ProjectInput
from .v3.schemas import ScopeChangeAssessment, ScopeChangeInput
from .v3.service import ScopeChangeService
from .v3.diagnostics import V3InvalidProviderOutput, issue, validation_issues
from .v3.provider_errors import V3ProviderError
from .v3.synthetic_diagnostics import SyntheticExplanationProbe, require_synthetic_cases

SCENARIOS = (("in_scope", "IN_SCOPE"), ("out_of_scope", "OUT_OF_SCOPE"),
             ("needs_clarification", "NEEDS_CLARIFICATION"))


def _load_scenarios():
    root = Path(__file__).parent / "tests" / "fixtures"
    project = ProjectInput.model_validate_json((root / "website_project.json").read_text(encoding="utf-8"))
    cases = []
    for name, expected in SCENARIOS:
        data = json.loads((root / "v3" / f"{name}.json").read_text(encoding="utf-8"))
        data["original_project"] = project.model_dump(mode="json")
        cases.append((name, expected, ScopeChangeInput.model_validate(data)))
    return cases


async def _run(settings, cases, *, synthetic_diagnostics=False, selected_scenario=None):
    if synthetic_diagnostics:
        require_synthetic_cases(cases, selected_scenario=selected_scenario)  # Before provider construction.
    provider = GroqProvider(settings)
    probe = SyntheticExplanationProbe(provider, settings.api_key.get_secret_value()) if synthetic_diagnostics else None
    service = ScopeChangeService(probe or provider, timeout_seconds=settings.timeout_seconds)
    reports = []
    for name, expected, data in cases:
        report = {"scenario": name, "request_id": data.request_id, "project_id": data.project_id,
                  "expected_classification": expected, "actual_classification": None,
                  "classification_comparison": "NOT_EVALUATED", "deterministic_validation": "FAILED"}
        try:
            # Exactly one invocation per case; GroqProvider disables SDK retries.
            result = await service.assess_scope_change(data)
            assessment = ScopeChangeAssessment.model_validate_json(result.model_dump_json())
            if assessment.input_snapshot != data:
                raise V3InvalidProviderOutput([issue("SNAPSHOT_MISMATCH", ("input_snapshot",))])
            analysis = assessment.analysis.model_dump(mode="json")
            report.update(
                actual_classification=analysis.pop("classification"),
                deterministic_validation="PASSED",
                validation_limits=assessment.deterministic_validation,
                recommended_action=assessment.recommended_action,
                human_review_required=assessment.human_review_required,
                semantic_review_required=assessment.semantic_review_required,
                **analysis,
            )
            report["classification_comparison"] = (
                "MATCH" if assessment.analysis.classification == expected else "MISMATCH"
            )
        except GenerationTimeout:
            report["error"] = "TIMEOUT: configured deadline exceeded; no retry attempted."
            report["provider_error_category"] = "TIMEOUT"
        except V3InvalidProviderOutput as error:
            report["error"] = "VALIDATION: structure, evidence, snapshot or wording safeguards failed."
            report["validation_diagnostics"] = list(error.diagnostics)
            if probe and probe.preview is not None and any(
                d["field"] == "analysis.explanation" for d in error.diagnostics
            ):
                report["synthetic_rejected_explanation"] = probe.preview
            if probe:
                rejected = []
                for diagnostic in error.diagnostics:
                    field = diagnostic["field"]
                    if field in {f"analysis.potential_impacts.{i}.explanation" for i in range(3)}:
                        preview = probe.preview_for(field)
                        if preview is not None and not any(item["field"] == field for item in rejected):
                            rejected.append({"field": field, "text": preview})
                if rejected:
                    report["synthetic_rejected_fields"] = rejected
        except ValidationError as error:
            report["error"] = "VALIDATION: response schema failed."
            report["validation_diagnostics"] = validation_issues(error)
        except InvalidProviderOutput:
            report["error"] = "VALIDATION: structure, evidence, snapshot or wording safeguards failed."
            report["validation_diagnostics"] = [issue("SCHEMA_INVALID", ("analysis",))]
        except ProviderError as error:
            report["error"] = "API/PROVIDER: check credentials, model support, quota and connectivity."
            report["provider_error_category"] = error.category if isinstance(error, V3ProviderError) else "UNKNOWN"
            if isinstance(error, V3ProviderError) and error.http_status is not None:
                report["provider_http_status"] = error.http_status
            if report["provider_error_category"] == "RATE_LIMIT":
                report["retry_advice"] = (
                    "No automatic retry. Wait for your account rate limit to reset, then manually "
                    "rerun only this scenario with --scenario " + name + "."
                )
        except Exception:
            report["error"] = "UNEXPECTED: raw details suppressed to protect secrets."
        reports.append(report)
    return reports


def _redact(value, secret):
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, list):
        return [_redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, secret) for key, item in value.items()}
    return value


def main(argv=()) -> int:
    parser = argparse.ArgumentParser(description="Run three explicit synthetic V3 Groq scenarios.")
    parser.add_argument("--synthetic-diagnostics", action="store_true",
                        help="Opt in to sanitized rejected-explanation previews for pinned synthetic fixtures only.")
    parser.add_argument("--scenario", choices=[name for name, _ in SCENARIOS],
                        help="Run only the selected scenario (one request); default runs all three.")
    args = parser.parse_args(argv)
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        settings = GroqSettings.from_env()
        # Preflight all fixtures before any request. Expected labels are not sent to AI.
        cases = _load_scenarios()
        if args.scenario:
            cases = [case for case in cases if case[0] == args.scenario]
            if len(cases) != 1:
                raise ValueError("Selected scenario missing or duplicated")
        reports = asyncio.run(_run(settings, cases, synthetic_diagnostics=args.synthetic_diagnostics,
                                  selected_scenario=args.scenario))
        matched = all(r["classification_comparison"] == "MATCH" for r in reports)
        report = {
            "model": settings.model,
            "status": "ALL_EXPECTATIONS_MATCHED" if matched else "FAILURE_OR_CLASSIFICATION_MISMATCH",
            "review_notice": "HUMAN SEMANTIC REVIEW REQUIRED; matches do not prove semantic correctness.",
            "retry_policy": "No retries; each scenario is attempted once unless interrupted.",
            "synthetic_diagnostics_enabled": args.synthetic_diagnostics,
            "requested_scenario": args.scenario or "all",
            "scenarios": reports,
        }
        print(json.dumps(_redact(report, settings.api_key.get_secret_value()), ensure_ascii=True, indent=2))
        return 0 if matched else 1
    except ConfigurationError:
        message = (
            "Configuration error: set GROQ_API_KEY and GROQ_MODEL in this PowerShell session. "
            "CONTRACTFLOW_TIMEOUT_SECONDS defaults to 30 and must be positive and <= 300."
        )
    except (OSError, ValidationError, ValueError):
        message = "V3 fixture/setup validation failed; no live requests were made."
    except KeyboardInterrupt:
        print("V3 live test interrupted; remaining scenarios were not attempted.", file=sys.stderr)
        return 130
    except Exception:
        message = "V3 runner failure; raw details suppressed to protect secrets."
    finally:
        logging.disable(previous_logging)
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
