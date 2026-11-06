# ContractFlow backend: isolated contract draft pipeline

## V2: opt-in professional agreement draft

V1 remains unchanged, including its extractive service and live-test command.
V2 uses the same validated `ProjectInput`, provider protocol, Groq adapter and
environment configuration, with no additional dependencies:

```python
from backend.app.modules.contractflow.v2.service import AgreementDraftService
from backend.app.modules.contractflow.v2.render import render_agreement

# Within an async caller; provider can be GroqProvider(settings) or a fake.
async def make_v2_draft(provider, project_data):
    draft = await AgreementDraftService(provider).generate_contract(project_data)
    return draft, render_agreement(draft)
```

For a configured Groq provider, pass `timeout_seconds=settings.timeout_seconds`
to `AgreementDraftService` as well. V2 returns an immutable `AgreementDraft` with
the authoritative snapshot, separate source-linked `ai_wording`, and six
deterministically assembled sections: parties, scope, deliverables, timeline,
compensation and unresolved terms. The plain-text renderer revalidates its input
and includes the original descriptions beside proposed prose. It creates no files.

AI can paraphrase scope, deliverable and milestone descriptions, but cannot
populate identities, budgets, currencies, dates, headings or review status.
The service alone copies these authoritative facts. Every source must occur
exactly once; unknown references, extra fields and omitted/duplicate sources fail.
Numeric tokens must match their own source (including equivalents from zero
through twenty), and common currency values/symbols in prose are rejected.
Conservative lexical checks reject selected legal/commercial terms, obligation
markers, new negation/qualification and control characters. Detected issues fail
generation; there is no automatic retry, silent correction or V1 fallback.

**These checks do not prove semantic equivalence.** Keeping original facts
unchanged in structured fields does not guarantee that proposed prose preserves
them. Changed formats, scope, responsibilities, spelled-out values, implicit
deadlines, invented names, synonyms and obfuscated obligations can escape these
heuristics. Benign references to acceptance or licensing can also be rejected.
Tests explicitly demonstrate a format-changing false negative and a conservative
false positive. Source references are provenance hints, not entailment proofs.
Project instructions are treated as untrusted data in prompts, but prompt
injection cannot be ruled out through prompting or keyword checks.

All V2 results enforce `semantic_review_required=True` and report only
`passed; semantic equivalence not established` for deterministic checks.
The mandatory draft label and human-review requirement cannot be removed through
validated deserialization. A reviewer must compare every proposed paragraph
against its source, especially output format, exclusions, duties and timing.
The renderer does not treat the original text as a cure for contradictory prose.
Unresolved legal/commercial terms are server-controlled; V2 never drafts those
clauses. Source text can itself be unsuitable and also needs human review.

Run all V1 and V2 offline tests with the existing test command below. The new
`tests/fixtures/v2_provider_output.json` contains synthetic paraphrases for the
website project; it is not a live Groq response. The module owner reported a
successful V2 live test with `openai/gpt-oss-120b`, passing deterministic checks
and retaining mandatory human semantic review. The existing `live_test.py`
intentionally continues to exercise V1 only.

For one explicit V2 live request, run from the repository root in your configured
PowerShell session:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v2
```

This reads the existing Groq environment configuration and synthetic website
fixture, calls `AgreementDraftService` once with SDK retries disabled, revalidates
the serialized draft and compares its authoritative snapshot against the input.
It prints the model, deterministic-check status and full rendered agreement,
including unresolved terms and mandatory human semantic review. It suppresses
raw provider errors and SDK logging. Exit codes: 0 for deterministic validation
success, 1 for failure, 130 for interruption. Success is not semantic approval.

Person 2 owns only this backend module and its local tests. Another teammate
owns frontend development and UI integration. There are no shared backend,
database, authentication, WorkBridge or payment dependencies.

## Installation and offline tests

Python 3.11+ is required. From the repository root, in an activated Python environment:

```powershell
python -m pip install "pydantic>=2.10,<3" "groq>=1.7,<2" "pytest>=8,<10"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest backend/app/modules/contractflow/tests -p no:cacheprovider -q
```

No shared dependency manifest is required. Tests clear ambient Groq credentials,
use deterministic fake providers and a mocked SDK, and block HTTPX async sends.
No live calls or real credentials are required. The fake-provider service itself
requires only Pydantic and the standard library; adapter tests also require Groq.
Verified environment: Python 3.12.10, Pydantic 2.13.4, Groq 1.7.0, Pytest 9.1.1.

## Async interface

```python
import json
from pathlib import Path
from backend.app.modules.contractflow.service import ContractGenerationService

async def make_draft(provider):
    path = Path("backend/app/modules/contractflow/tests/fixtures/website_project.json")
    project_data = json.loads(path.read_text(encoding="utf-8"))
    service = ContractGenerationService(provider, timeout_seconds=30)
    draft = await service.generate_contract(project_data)
    return draft.model_dump(mode="json")
```

Providers implement `async generate(*, system_prompt: str, user_prompt: str) -> str`
and return JSON matching `ProviderOutput`. Providers must cooperate with async
cancellation; blocking synchronous work cannot be forcibly stopped by a timeout.
External task cancellation propagates to the caller.

## Optional live Groq configuration

Set `GROQ_API_KEY` securely in the backend process environment; never commit it.
Set `GROQ_MODEL` to an account-accessible model supporting JSON object mode.
There is no hardcoded model default. `CONTRACTFLOW_TIMEOUT_SECONDS` defaults to
30 and must be positive and at most 300 seconds. No environment is read at import
and no `.env` file is automatically loaded.

```python
from backend.app.modules.contractflow.config import GroqSettings
from backend.app.modules.contractflow.providers.groq import GroqProvider
from backend.app.modules.contractflow.service import ContractGenerationService

settings = GroqSettings.from_env()
service = ContractGenerationService(
    GroqProvider(settings), timeout_seconds=settings.timeout_seconds
)
# draft = await service.generate_contract(project_data)
```

The adapter opens and closes an async client per call, disables SDK retries and
sets a request timeout. The service also enforces its deadline. JSON mode does
not ensure schema conformance: local validation remains mandatory. See the
[official Groq SDK](https://github.com/groq/groq-python) and
[API response formats](https://console.groq.com/docs/api-reference).
Live model compatibility and generation quality have not been tested here.

## Facts, wording and review boundaries

- `ProjectInput` validates parties, project scope, positive Decimal budget,
  uppercase three-letter currency syntax, dates, deliverables and milestones.
  Delivery milestones are not payment schedules. IDs must be unique within each
  collection, references valid, and deadlines consistent. Client and freelancer
  IDs must differ. Up to 99 deliverables and 99 milestones are supported.
- Currency membership, currency-specific minor units, identity authenticity and
  authorization need upstream validation. No FX conversion or rounding occurs.
  Dates are not checked against today, allowing historical project snapshots.
- `authoritative_data` is a detached, immutable validated input snapshot, assembled
  by the service rather than the model. Nested collections are tuples. AI output
  cannot replace names, amounts, dates or other authoritative data.
- `ai_wording` is separate and deliberately extractive. AI may order sections,
  but must copy every scope, deliverable and milestone description verbatim,
  exactly once, with indexed source references. Altered text, extra fields,
  unknown sources, omissions and duplicates are rejected. Arbitrary paraphrasing
  is excluded because prompts alone cannot prove semantic grounding.
- Names, IDs, amounts and dates are not sent as separate fields to the provider.
  Scope and descriptions are sent and can themselves contain sensitive content;
  callers own the decision to send them. Project text is treated as untrusted data.
- Every output is labeled `DRAFT — REQUIRES CLIENT AND FREELANCER REVIEW` and
  has `requires_human_review=True`. Governing law, IP ownership, termination,
  penalties, payment schedule, acceptance conditions and other legal/commercial
  terms remain explicitly unresolved. This schema does not accept legal terms;
  supporting agreed terms requires a future explicit validated design.
- Supplied source text can itself contain unsuitable or conflicting obligations.
  Exact matching prevents AI-added wording but does not certify source content,
  legal completeness, enforceability or suitability. Human review is mandatory.

## Errors

Invalid input raises Pydantic `ValidationError` before any provider call.
Configuration errors raise `ConfigurationError`; provider failures raise
`ProviderError`; timeouts raise `GenerationTimeout`; malformed, incomplete or
ungrounded output raises `InvalidProviderOutput`. Provider messages are sanitized.
No secrets, prompts or responses are logged. Pydantic input errors may include
input values, so future API handlers must define their response/logging policy.
There is no persistence or automatic retry.

## Future integration

Core Platform must supply authenticated identities, authorization, shared
configuration and application error mapping. WorkBridge must supply an agreed
project snapshot and consistent identifiers. This service fetches no records and
writes to no tables. Another teammate will integrate frontend UI through future
API routes. Shared stack choices and scaffolding remain subject to confirmation.

Contract management APIs, dual-party acceptance, amendments, version history,
scope-change detection and persistence remain future work. No shared entry
points, authentication, database sessions, migrations, frontend or PayPal logic
are implemented here.
