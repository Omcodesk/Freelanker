# ContractFlow backend: isolated contract draft pipeline

## V3: advisory AI scope change detection

### Timeline impacts: conditional assessment, never a revised schedule

A TIMELINE impact must cite an authoritative original scheduling key:
`original.start_date`, `original.deadline`, an original deliverable deadline, or
an original milestone deadline. Its evidence excerpt must be the full exact date
value. Scope-only, budget-only, partial-date, fabricated or borrowed top-level
evidence does not satisfy this field-local requirement.

Keep dates out of generated impact explanations, even when the original date is
accurately cited. Dates remain in evidence and the immutable project snapshot.
For example: “The additional functionality may affect the existing project
timeline and requires human review before any deadline change.”

The confirmed rejected statement “The additional functionality would extend the
project beyond the existing deadline of 2027-01-29.” reproduced QUANTIFIED_PROSE
with valid synthetic timeline citations because of the explicit date. Removing
only the date previously passed, exposing a separate unsupported schedule-outcome
assertion. V3 now rejects detected definite/future/automatic extensions under
UNSUPPORTED_SCHEDULE_CHANGE, independently of quantified-prose validation.
MISSING_TIMELINE_EVIDENCE identifies an otherwise valid TIMELINE impact lacking
its own complete scheduling citation. Exact reference/excerpt checks remain.

Use may/might/could to discuss possible effects, without claiming a deadline
will or would change. A cited deadline does not establish that new work exceeds
it. No dates are invented or revised, and no schedule or commercial commitment
is created. Human review flags remain mandatory. Schedule-language checks are
conservative lexical safeguards, not semantic proof; unusual wording or implicit
commitments can escape them and benign text can still be rejected.

### Explicit V3 live smoke test

#### Single-scenario verification and the confirmed page-count correction

Run only the scenario you want to verify, from your configured PowerShell at
the repository root:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v3 --scenario in_scope
python -B -m backend.app.modules.contractflow.live_test_v3 --scenario out_of_scope
python -B -m backend.app.modules.contractflow.live_test_v3 --scenario needs_clarification
```

Each individual command makes one request. Choose a command rather than running
all three back-to-back when troubleshooting a rate limit. Omitting `--scenario`
retains the existing three-scenario run. You can combine selection with the
opt-in pinned-fixture diagnostic mode:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v3 --scenario out_of_scope --synthetic-diagnostics
```

Selected diagnostic inputs still require the exact canonical hash of that
bundled synthetic scenario. Unselected cases are not sent to the provider. An
invalid scenario is rejected by the CLI before any request. Expected/actual
classification reporting and nonzero exits for failures/mismatches are unchanged.
HTTP 429 is reported as RATE_LIMIT; no automatic retry, sleep or extra request
is performed. Wait for the account rate limit to reset, then manually rerun the
selected scenario. The error report supplies the appropriate `--scenario` option.

Both confirmed live explanations are regression tests, including “the agreed
three-page bakery website” and “the agreed website scope, which only includes
building a responsive three-page bakery website.” The former exposed the old
regex's ordering assumption: it expected a subject noun before the counted phrase.

V3 now uses `v3/quantities.py`, independently of sentence examples. It extracts
typed claims with a normalized value, unit, subject and text span. For example,
`three-page bakery website` and `bakery site with 3 pages` both identify
`(3, pages, bakery website)`. Subject descriptors such as bakery remain required.
Digits/number words and site/website are supported lexical variants; arbitrary
subject or unit substitutions are not. The conservative grammar currently handles
website page counts; other numerical claim types are unsupported in prose.

Quantity matching uses a temporary, length-preserving view in which Unicode
hyphen U+2010, non-breaking hyphen U+2011, small hyphen-minus U+FE63 and fullwidth
hyphen-minus U+FF0D match ASCII hyphens. This corrects the confirmed live false
positive for `three‑page`. It does not normalize snapshots, returned prose,
source references or evidence excerpts. Excerpts must still be exact substrings
of the original source, including its actual separator. Range/em dashes, minus
signs, soft hyphens and invisible separators are not blanket-normalized. All
value/unit/subject, baseline-role, local-citation and obligation checks still run.

Each accepted quantity must occur in both an authoritative source description and
the same field's exact cited excerpt, under `original.scope` or an original
deliverable description. Budget, dates, IDs, requests and context cannot ground
page counts. The generated claim also needs local original/agreed/existing
baseline attribution, with checks against nearby proposals, new work and estimates.
Only the accepted number token is masked for the existing quantitative-prose
filter. Every other numeric/currency/date token and all original obligation text
remain checked. Exact citation validation and immutable snapshots are unchanged.
`original_quantity_facts` in the prompt explains this context to the model; runtime
validation independently reconstructs facts from actual cited evidence.

This is deterministic value/unit/subject/provenance checking, not semantic proof.
Limited grammar, attribution distance, negation, coreference, conflicting source
statements and implicit commitments can cause false positives or false negatives.
The original source may itself be misleading or unsuitable. A supported page
count does not prove that ordering is excluded, that a classification is correct,
or that no new obligation was implied. Mandatory human semantic review remains.
The legacy notice/quote fields are examples retained for compatibility; they are
not used by the validator as whole-sentence exceptions.

#### Focused local diagnostics (off by default)

The synthetic diagnostic probe also supports the three schema-permitted
`analysis.potential_impacts.N.explanation` fields. When one fails, the report
includes only the matching field in `synthetic_rejected_fields`, for example:

```json
{
  "synthetic_rejected_fields": [
    {"field": "analysis.potential_impacts.2.explanation", "text": "sanitized rejected text"}
  ]
}
```

This uses the same 2000-character bound, secret/contact/header filtering,
hash-pinned synthetic input gate and opt-in flag as the main explanation preview.
No whole impact object, response, source excerpt or arbitrary path is dumped.
Unrelated fields are not displayed. Cached previews are cleared before every
request. Default mode never captures or displays these rejected fields.

Nested impact explanations use exactly the same quantity validator as the main
explanation, with that impact's own citations. A count mentioned in the main
explanation cannot ground an impact which cites only budget or deadline evidence.
This is intentional. A QUANTIFIED_PROSE failure at an impact path may represent
an unsupported amount/date/count or a conservative false positive; without its
text and relevant impact citations, the actual cause cannot be established.
Use a single-scenario diagnostic rerun to collect the sanitized text before
changing quantitative validation rules.

Normal run, with no rejected-text preview:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v3
```

Explicitly enable the synthetic-only preview for an investigation run:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v3 --synthetic-diagnostics
```

Each command attempts three live requests, once per scenario, without retries.
Choose one command for a run. The preview is restricted to the exact bundled
website snapshot and three requests, checked using hardcoded canonical SHA-256
pins before provider construction. Modified project facts, IDs, request text,
context or scenario selection fail preflight; labeling real data “synthetic” does
not enable the preview. Do not repin fixtures without explicit synthetic-data review.

When an explanation fails validation, the opt-in JSON report can include
`synthetic_rejected_explanation` for the root field, or `synthetic_rejected_fields`
for a matching nested impact explanation. Only these known fields are inspected,
bounded to 2000 characters each, and shown locally; prompts, full provider responses, headers,
reasoning and raw error bodies are never printed or saved by the runner. The
whole preview is omitted if it resembles credentials, authorization/header text,
URLs/contact details or hidden formatting, or contains the configured key.
Terminal control characters are removed. Do not redirect this optional preview
to shared logging. Default mode never captures or reports rejected explanations.
The preview does not approve a response or change `NOT_EVALUATED` outcomes.

Numeric investigation confirmed that page-count paraphrases and scope quotations
were rejected outside narrow syntax patterns. They are now checked as quantitative
claims using the approach above. Unsupported quantities, estimates, percentages
and financial statements (even “zero additional cost, subject to review”) still
fail. Calling a statement nonbinding does not establish financial grounding.
Original financial/date facts belong in attributed evidence, not new prose.

V3 provider failures now include a safe `provider_error_category`:
`AUTHENTICATION`, `RATE_LIMIT`, `PROVIDER_REJECTION`, `CONNECTIVITY`, `TIMEOUT`,
or `UNKNOWN`, plus a numeric HTTP status when supported. Categorization uses SDK
exception types, not guessed meanings of raw messages. The shared adapter stays
unchanged; V3 inspects typed exception context without printing it. A generic
failure with no recognized SDK type remains UNKNOWN. Request cancellation and
one-attempt semantics remain unchanged.

The Groq adapter uses `response_format={"type":"json_object"}` with explicit
JSON instructions. Groq documents JSON-object mode as syntax validation, not
schema enforcement; the model supports both JSON-object and JSON-schema modes.
See [Groq structured output documentation](https://console.groq.com/docs/structured-outputs)
and [GPT-OSS 120B limits](https://console.groq.com/docs/model/openai/gpt-oss-120b).
No incompatible mode or client-imposed token cap was found. The current adapter
does not set `max_tokens` or `max_completion_tokens`; provider/model limits still
apply. The documented model window is 131072 tokens, with up to 65536 output
tokens. V3's 64000-byte response check is not a token budget. SDK retries remain
disabled and incomplete completions remain rejected. Strict provider-side JSON
schema could improve shape compliance, but cannot establish citation truth or
semantic correctness; it was not enabled speculatively or applied to V1/V2.

Historical rejected wording and the earlier API exception type were not retained.
The next explicit local diagnostic run can distinguish the actual failing wording
and provider category. Authentication, rate limits and connectivity remain possible
causes, not confirmed explanations of the historical provider failure.

The prompt continues to provide legacy page-count notice/quotation examples,
but no prescribed sentence is required. The validator accepts only supported
quantitative claims as described above, and otherwise retains QUANTIFIED_PROSE.

The prompt also includes `allowed_references_by_field` and valid citation-only
examples for deliverable, timeline and compensation impacts. Impact evidence must
use original registry keys; request/context references are not original evidence.
Use the supplied exact keys (for example `original.deadline`), not inferred
aggregate names. A single relevant citation is sufficient; uncertain impacts can
be omitted instead of inventing another reference. Excerpts remain exact substrings.
Unknown references are still rejected, never normalized or silently discarded.

The reported live diagnostics identify the rejecting rules but not the rejected
number or unknown reference value. Therefore these regressions reproduce the
failure classes rather than claim the unseen responses have been reconstructed.
No live call was made to verify the fixes; rerun the command below to confirm.

V3 troubleshooting: failed scenarios now include `validation_diagnostics`, with
allowlisted rule codes, schema-field paths and, where safe, a known registry
reference. No rejected text, excerpt content, arbitrary provider field names,
unknown reference values, raw Pydantic messages, prompts or responses are included
in these diagnostics. A maximum of 20 schema issues is reported.

Example diagnostic metadata:

```json
{
  "validation_diagnostics": [
    {"rule": "FABRICATED_EXCERPT", "field": "analysis.source_references.0.excerpt", "reference": "original.scope"}
  ]
}
```

Interpretation:

| Rule | Meaning |
| --- | --- |
| SCHEMA_MISSING / SCHEMA_INVALID / SCHEMA_EXTRA_FIELD | Required field missing, wrong shape/value, or unexpected field |
| INVALID_JSON | Response is not parseable JSON |
| UNKNOWN_SOURCE_REFERENCE | Reference is not a literal key in the permitted registry |
| FABRICATED_EXCERPT | Excerpt is not a contiguous exact substring of its source |
| DUPLICATE_REFERENCE / MISSING_SCOPE_EVIDENCE | Citation-list consistency failed |
| QUANTIFIED_PROSE | Generated interpretation contains forbidden quantities, currency or date tokens |
| POTENTIAL_BINDING_TERM | Generated interpretation contains a detectable potential obligation |
| PROVIDER_INCOMPLETE_OUTPUT | Existing adapter rejected incomplete/empty output before V3 parsing |
| SNAPSHOT_MISMATCH | Returned input facts differ from the original validated input |

Unknown field names are replaced with `<unrecognized_field>`. A valid citation
path may be displayed, but fabricated/unknown paths are never echoed. Invalid
results remain rejected and `NOT_EVALUATED`; diagnostics do not approve them.

The initial live report collapsed all these failures into a generic error, so
the precise rejection from that run cannot be reconstructed without its response
or a diagnostic rerun. Offline investigation reproduced false positives for
`No revised price is proposed.`, `Compensation is not estimated.` and technical
`pay button` wording. These exact nonbinding notices/technical terms are now
handled narrowly; quantities, remaining obligation wording and source checks
remain enforced. Other benign formulations can still be rejected conservatively.
The prompt/schema now explicitly require a ScopeAnalysis root (no `analysis`
wrapper), object-shaped evidence arrays, exact slash-indexed registry keys,
literal excerpts, qualitative prose and required clarification questions.
Realistic valid citation examples are provided without expected classifications.
No malformed fields or reference aliases are automatically repaired or accepted.

From the repository root in your configured PowerShell session:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v3
```

This reads `GROQ_API_KEY`, `GROQ_MODEL` and optional
`CONTRACTFLOW_TIMEOUT_SECONDS` through the existing loader. It prevalidates the
synthetic website project and the three V3 request fixtures, then attempts each
scenario sequentially exactly once through `ScopeChangeService` and the existing
Groq adapter (`max_retries=0`). A complete run attempts three API requests. It
does not load `provider_outputs.json`, which is reserved for offline tests.

The JSON report includes expected and actual classifications separately, an
explicit `MATCH`, `MISMATCH` or `NOT_EVALUATED` comparison, explanation, source
excerpts, requested changes, qualitative impacts, clarification questions,
recommended action and review flags. Expected labels are not sent to the model.
Validated results are round-trip revalidated and their full input snapshots are
compared with the original inputs before reporting deterministic success.

A mismatch remains a mismatch even if schema/evidence checks passed. A failed
scenario has no accepted actual classification; sanitized errors are reported
and remaining scenarios continue without retry. Cancellation stops remaining
work. Credentials and raw provider errors are not printed; SDK logging is
disabled during the runner and restored on exit.

Exit codes: 0 only when all scenarios validate and match expected labels; 1 for
any failure or mismatch; 130 for keyboard interruption. **HUMAN SEMANTIC REVIEW
REQUIRED** applies even when all expectations match. This runner is explicit
live verification and is never executed by the offline suite. The implementation
was tested with mocks only; no live V3 calls were made here.

V3 is isolated in `v3/`; V1, V2, their tests and live scripts are unchanged.
It compares a new request with the original project snapshot, returning an
explainable assessment rather than changing a contract or generating an amendment.
It reuses `ProjectInput`, `ContractProvider`, `GroqProvider`, `GroqSettings` and
the existing error types. No new dependency or shared infrastructure is added.

```python
import json
from pathlib import Path
from backend.app.modules.contractflow.v3.service import ScopeChangeService

async def assess_request(provider, case="out_of_scope"):
    fixtures = Path("backend/app/modules/contractflow/tests/fixtures")
    data = json.loads((fixtures / "v3" / f"{case}.json").read_text(encoding="utf-8"))
    data["original_project"] = json.loads(
        (fixtures / "website_project.json").read_text(encoding="utf-8")
    )
    return await ScopeChangeService(provider, timeout_seconds=30).assess_scope_change(data)
```

Use an injected fake provider for offline tests. For future explicit live usage,
inject `GroqProvider(settings)` and pass `settings.timeout_seconds` to the service.
No V3 live request has been made during implementation. Importing the module
does not read environment variables or create clients.

Input example (attach the existing website fixture as `original_project`):

```json
{
  "request_id": "SYNTHETIC-REQUEST-OUT",
  "project_id": "SYNTHETIC-WEB-001",
  "client_request": "Add an online ordering system with payment integration.",
  "supporting_context": []
}
```

`original_project` is required and must be the applicable agreed `ProjectInput`
snapshot. This input example references a separate fixture to avoid duplicating
project records. The caller is responsible for authenticating the snapshot and
selecting the correct agreement version. Request and context are untrusted claims,
not amendments or new authoritative facts.

The synthetic response produces this summary (the actual response also contains
the complete immutable `input_snapshot`, change evidence and impact evidence):

```json
{
  "request_id": "SYNTHETIC-REQUEST-OUT",
  "project_id": "SYNTHETIC-WEB-001",
  "classification": "OUT_OF_SCOPE",
  "explanation": "Online ordering and payment integration appear to add functionality beyond the described website and page source deliverables.",
  "source_references": ["original.scope", "original.deliverables/0/description"],
  "requested_changes": ["Add online ordering with payment integration."],
  "potential_impacts": ["DELIVERABLES", "TIMELINE", "COMPENSATION"],
  "recommended_action": "PROPOSE_AMENDMENT",
  "human_review_required": true,
  "semantic_review_required": true,
  "deterministic_validation": "passed; semantic correctness not established"
}
```

This is a flattened documentation summary, not the wire schema: interpretation
fields live under `analysis`. Exact citations contain `reference` and `excerpt`.

| Synthetic request | Classification | Deterministic recommendation |
| --- | --- | --- |
| Provide the source files for the home, menu and contact pages. | IN_SCOPE | REVIEW_AND_CONFIRM_SCOPE |
| Add an online ordering system with payment integration. | OUT_OF_SCOPE | PROPOSE_AMENDMENT |
| Make the menu interactive. | NEEDS_CLARIFICATION | REQUEST_CLARIFICATION |

Recommendations never authorize work, create binding amendments, update project
records or adjust payments. Even an `IN_SCOPE` assessment requires human review.
Ambiguity is a substantive model decision, not a fallback for invalid output.

### V3 deterministic safeguards

- `ScopeChangeInput` and `ScopeChangeAssessment` are frozen Pydantic models with
  forbidden extra fields and immutable nested collections. The service detaches
  and revalidates nested inputs, preserves the original snapshot and IDs, and
  revalidates the assembled assessment. The provider cannot set IDs, snapshots,
  action or review flags. Actions are derived from classification server-side.
- Source registries are allowlisted, never arbitrary object-path traversal.
  Original scope, deliverables, milestones, dates, budget and currency have
  `original.*` keys. Identity names are omitted from the provider payload.
  Requests use `request.client_request`; context uses indexed `context/N` keys.
  These namespaces cannot substitute for original-agreement evidence.
- Every assessment needs original scope/deliverable evidence. Each requested
  change and potential impact needs original evidence; every requested change
  additionally needs an exact client-request excerpt. Nonempty excerpts must be
  literal substrings of their referenced sources. Unknown paths, fabricated
  excerpts and duplicate references within a citation list fail validation.
  Reusing evidence across distinct findings is allowed. Duplicate change excerpts
  and impact categories are rejected. Ambiguous assessments require questions.
- Generated explanations, descriptions, impact prose and questions must remain
  qualitative: numeric values, common spelled-out quantities, currency markers
  and common explicit date forms are rejected. Exact evidence can quote original
  figures or client-proposed figures, but the latter remain unagreed requests.
  No pricing, scheduling or arithmetic is performed. Currency/amount tokens alone
  are never accepted as proof of a valid commercial assertion.
- Conservative lexical checks reject selected binding/financial terms and control
  characters in generated prose. They allow technical **payment integration** and
  qualitative discussions of potential compensation and timeline effects.
  V2's wording validator is intentionally not reused.
- Limits: IDs 128 characters, request 8000 characters, up to 10 context entries
  of 4000 characters each, total input 64000 UTF-8 bytes; response text 64000
  UTF-8 bytes. Interpretation fields are at most 2000 characters, with at most
  20 changes, 30 references per original citation list, 3 impact categories and
  10 clarification questions. Inputs exceeding limits fail, without truncation.
  The response limit is checked after receipt; it is not a provider token limit.
- The service invokes the provider once with a cooperative async timeout and no
  retry. Invalid input raises Pydantic `ValidationError` before any request.
  Malformed/unsafe output raises `InvalidProviderOutput`; provider failures raise
  sanitized `ProviderError`; timeouts raise `GenerationTimeout`. External task
  cancellation propagates. No prompts, raw errors or credentials are logged.

### V3 limitations and integration

**Deterministic validation is not semantic correctness.** A valid citation proves
an excerpt exists, not that it supports the decision or proves absence of work.
The system cannot verify classification, completeness of requested-change analysis,
relevance of citations or whether context improperly influenced the interpretation.
Keyword/numeric filters miss synonyms, implicit dates, obfuscated commitments and
some spelled-out amounts; they can also reject benign text (for example “one at
a time”). Tests explicitly document both a semantic false negative and a false
positive. Prompt injection is mitigated by data separation and output checks,
not eliminated. Exact request/context quotations can still contain malicious or
sensitive text and must be safely presented by future consumers.

Reviewers must compare the entire applicable agreement, request and evidence,
especially exclusions, formats, responsibilities and existing legal terms.
The existing `ProjectInput` schema does not model arbitrary legal clauses; V3
cannot evaluate undisclosed or omitted agreement terms. Supporting context cannot
make such terms authoritative. Missing detail does not automatically establish
an exclusion. V3 never claims an agreement is legally complete or enforceable.

Core Platform will later supply authentication, authorization, configuration,
rate limits and API error mapping. WorkBridge will supply validated snapshots and
request IDs. Storage, provenance/version verification, audit trails, approval
workflows and amendments remain future integrations. Provider context limits,
cost controls and observability need deployment decisions. Async cancellation
cannot guarantee remote processing or billing stops. No shared routes, tables,
auth, frontend, payment or WorkBridge implementation is included here.

Run all offline tests with the existing installation/test commands below. V3
fixtures and responses are synthetic, deterministic test examples, not live AI
results. No Groq credential or network access is needed for the tests.

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
