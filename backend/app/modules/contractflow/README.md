# ContractFlow backend: isolated contract draft pipeline

## V4: proposed contract amendments

Final verification: the user-run synthetic ordering live test with
`openai/gpt-oss-120b` returned `DETERMINISTIC_CHECKS_PASSED`, with human and semantic
review required, effective false, and original budget/deadline unchanged. The full
live response is not retained in this repository. Awkward timeline and compensation
wording remains a known semantic-quality limitation; deterministic checks do not
certify professional wording or contractual equivalence. No validation exceptions
or untested wording changes were introduced for finalization.

### Proposal-language failures

`UNSAFE_PROPOSAL / PROPOSAL_LANGUAGE` groups inherited numerical/date,
obligation, schedule-change and control-character failures, V4's forbidden
words, and absence of could/may/might/proposed/unresolved. It does not identify
which trigger occurred. The latest lost deliverable response cannot be
reconstructed from that diagnostic. No validator defect was established.

The prompt now gives an ordering-specific conditional example validated offline:
`A proposed deliverable could cover online ordering with payment integration,
subject to negotiation.` Other requests must retain their own reviewed concepts.
Even negated binding/effective language and subject-to-approval/acceptance clauses
are rejected in AI proposal text; the server renders the approval notice. Amounts
and dates remain outside proposal prose. No rejected output is automatically
rewritten, and proposal markers do not bypass vocabulary, coverage or citations.
These checks are conservative filters, not proof that any permitted sentence is
semantically equivalent to the reviewed request. Human review remains mandatory.

### Provider rejection troubleshooting

Confirmed synthetic live metadata `400 / invalid_request_error /
json_validate_failed` identifies provider-side JSON generation validation failure,
before local amendment parsing. It does not reveal the rejected text, whether
quotes/formatting were malformed, or whether output/context limits contributed.
No raw rejected generation was retained. V4 now explicitly requires one JSON
object without Markdown/commentary, correct JSON escaping, closed structures,
and exactly the schema's response fields. Citation equality concerns decoded
strings, so escaping quotes/backslashes/control characters preserves evidence.
No automatic JSON repair, retry or contractual-content substitution is performed.

[Groq's structured-output documentation](https://console.groq.com/docs/structured-outputs)
lists `openai/gpt-oss-120b` for strict JSON Schema output. The existing adapter
supports JSON-object mode only. This correction retains that mode and the shared
adapter unchanged: documented model support alone does not establish compatibility
of every schema constraint with constrained decoding. No V4 wrapper or guessed
token limit was introduced. The schema uses reusable object definitions and no
recursive models or union alternatives; excessive complexity/truncation has not
been established as the cause. Output must still pass the unchanged Pydantic,
evidence, wording, immutable-snapshot and review validators.

The V4 runner reports sanitized `http_status`, `provider_error_type`,
`provider_error_code` and `retryable` metadata. Only fixed recognized type/code
values are shown; unknown/unavailable values are `null`. Messages, raw response
bodies, failed-generation text, headers and request content are never printed.
Retryability is advisory (408/409/429/5xx or connectivity/timeout); SDK retries
remain disabled and the runner never retries automatically. V4 timeout failures
retain their separate timeout report.

The existing adapter sends model, system/user messages, JSON-object response mode
and temperature zero. It sends no explicit token limit, strict JSON-schema API
parameter, tools or reasoning settings. The output schema is supplied in the
prompt and independently validated after generation. A successful models GET
does not prove that a particular chat-completion request will be accepted.
Without the original rejection metadata, request-format/model/JSON-generation/
context-limit/provider-side causes cannot be distinguished offline. Do not change
request parameters or weaken validation based solely on `PROVIDER_REJECTION`.

One explicitly user-run synthetic retest can capture the sanitized status/code:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v4 --run-live --scenario ordering
```

For example, `json_validate_failed` identifies provider JSON-generation rejection;
`context_length_exceeded` identifies a context-limit rejection. Unknown codes stay
suppressed, so some failures will still require a provider-side investigation
without sharing confidential request/response content.

### Existing deliverables versus proposed additions

Proposed deliverable wording uses the specific reviewed change/request vocabulary,
not the union of agreement words. A narrowly supported existing-work reference is
a standalone `Existing deliverable: "verbatim full description".` followed by a
separate conditional proposal sentence. It requires the exact full description
from an `agreement.deliverables/<index>/description` source in that field's own
citations. Evidence and quoted text are not Unicode-normalized. The quoted span
cannot supply proposed material coverage or authorize agreement terminology
elsewhere. Numerical, obligation and approval safeguards still inspect all prose.
Prefer leaving baseline context to the deterministic renderer.

Missing/changed baseline evidence reports `BASELINE_REFERENCE_NOT_GROUNDED`;
ambiguous inline role wording reports `BASELINE_ROLE_AMBIGUOUS`. Diagnostics contain
fixed rule/category metadata, never quoted content. Vocabulary token positions
continue to refer to the original proposal text. Detectable direct negation of
proposed work is rejected; lexical coverage cannot establish semantic equivalence
or detect every misleading relationship between otherwise permitted words.
Human and semantic review remain mandatory.

The historical deliverable failure's four unsupported words were not retained.
Two agreement-only occurrences establish their vocabulary origin, not their role
or correctness. Offline tests demonstrate a labeled-baseline false positive in the
former flat check; they do not reconstruct that historical response.

### V4 wording vocabulary and safe token diagnostics

Additional-scope vocabulary is lexical, not a semantic grammar classifier. A
harmless unlisted connector can fail just like a new feature; conversely permitted
words can be arranged misleadingly. A focused offline example with `together with`
documents this conservative rejection without adding vocabulary permissions.
The prompt now explicitly restricts even connective words to the supplied closed
list and requests short source-terminology clauses. The latest lost response's
single-token metadata does not identify its word or establish a false positive.
No speculative synonyms or validator exceptions were added for that failure.

CONTENT_VOCABULARY compares proposal words against the SPECIFIC reviewed change
and client-request excerpt plus a closed connective/review vocabulary. Original
agreement words are not general permission to introduce additional features.
For ordering, the source terms are add, an, integration, online, ordering, payment,
system and with. A novel gateway, processor, analytics feature, platform, method
or deliverable remains unsupported even when it sounds related to payment work.

Offline reproduction confirmed the former exact-word gate rejected “payments
integrated” although the request used “payment integration.” This does not prove
the historical live response used those words; that response was not retained.
V4 now permits only two explicit source-conditioned word families:

- integration / integrate / integrates / integrated / integrating
- payment / payments

A family is enabled only when its concept occurs in that field's reviewed source
content. It cannot introduce payment or integration into a request lacking it.
The grammatical connective “including” is also permitted. No embedding score,
unrestricted synonym expansion or generic stemming authorizes scope. Required
material-term coverage uses the same source-conditioned forms, so changing a
word's inflection does not falsely imply the concept was omitted. All monetary,
date, legal/approval/obligation, citation and review checks run unchanged first.

Proposal word comparison uses Unicode letters, case folding and NFC composition.
It does not transliterate accents or normalize quotations. Punctuation/hyphen
variants separate words consistently; exact source evidence remains untouched.
The prompt's `wording_contract` lists preferred source terms, permitted conditional
forms and required material terms for each output field, alongside the unchanged
literal `citation_contract`. It explicitly prefers source terminology and forbids
introducing technical components or payment methods not requested/reviewed.

CONTENT_VOCABULARY diagnostics include `token_metadata`: unsupported unique and
occurrence counts, at most 20 token indexes/code-point offsets and normalized
ASCII/NON_ASCII classes, source-conditioned variant counts, and counts found only
in original-agreement context. They contain no rejected words, source text,
tokens' hashes, confidential identifiers, raw responses or credentials. Offsets
identify positions within the submitted proposal field without reproducing it.
Metadata cannot itself prove that an unknown word was harmless or material.

Lexical grounding remains conservative and incomplete: unlisted synonyms may be
rejected, while known words can be recombined misleadingly. Conditional wording
and token overlap do not prove semantic equivalence. Mandatory human semantic
review, proposed-only status and original facts remain invariant. One explicitly
authorized synthetic live retest can show whether the revised constrained prompt
passes; no live request was made while implementing these corrections.

### V4 evidence troubleshooting

`INVALID_EVIDENCE` is a family of strict checks, not a diagnosis by itself.
V4 now reports sanitized `field`, `check` and `source_category` metadata, for
example `timeline.citations.0.excerpt`, `EXCERPT_NOT_EXACT`, `AGREEMENT`.
No rejected reference value, excerpt, prompt, input value, full provider response,
Pydantic error message or credential is included. Unknown schema-field names are
replaced with `<unrecognized_field>`. Up to 20 schema issues may be reported.

Evidence checks are ordered: duplicate IDs; unknown catalog IDs; exact substring
checks; required request citation and its exact expected full excerpt; required
reviewed-assessment citation/full quote; original scope/deliverable context; and
full original deadline/budget values for their respective consideration fields.
Missing references and incomplete required quotes have distinct codes:

| Check | Meaning |
| --- | --- |
| DUPLICATE_REFERENCE | A field repeated the same source ID |
| UNKNOWN_REFERENCE | ID is absent from the V4 catalog |
| EXCERPT_NOT_EXACT | Characters do not occur literally in the cited source |
| REQUIRED_REQUEST_CITATION_MISSING / REQUEST_EXCERPT_INCOMPLETE | Required request evidence absent or shortened |
| REVIEWED_ASSESSMENT_CITATION_MISSING / ASSESSMENT_EXCERPT_INCOMPLETE | Required reviewed-change/assessment evidence absent or shortened |
| AGREEMENT_CONTEXT_MISSING | Scope/deliverable proposal lacks original work context |
| AUTHORITATIVE_FACT_CITATION_MISSING / AUTHORITATIVE_FACT_EXCERPT_INCOMPLETE | Timeline/budget source missing or its required value incomplete |

The reviewed synthetic ordering response satisfies all these checks. V4 is more
specific than V3 field-local grounding: a valid substring is insufficient where
V4 requires the entire reviewed change, selected request excerpt, assessment
explanation or original scalar fact. Main/other-field citations cannot substitute
for a field's own required citations. These checks remain strict.

Inspection confirmed that the original V4 output schema reused V3 `Evidence`,
whose description suggested an invalid `original.*` example for the V4 catalog.
V4 now has its own `AmendmentEvidence` with correct `agreement.*` examples and
literal, non-stripping strings. This fixes both the namespace instruction mismatch
and silent whitespace normalization. Evidence Unicode composition, hyphen type,
case and whitespace are not fuzzily normalized. JSON escapes decoding to identical
characters are valid; visually similar but different excerpts are not.

The V4 excerpt bound is 8000 characters to accommodate the full allowed client
request; the prior 4000-character bound could not represent some valid inputs.
The 64000-byte provider response cap and exact-source checks still apply.

Prompts now provide `valid_source_ids` and a generated `citation_contract` with
concrete valid reference/excerpt objects for every material output field. Copy
those objects literally while paraphrasing proposal text only. `change_index`
and source IDs are explicitly required; project/party IDs remain server-owned.
No aliases, citation repair or silent coercion are used to accept failed output.

These findings do not establish what the earlier live response contained: it
was not retained. One explicit pinned synthetic rerun using the existing V4
command below will identify the failing field/check/category, or demonstrate
successful deterministic validation. Share only the sanitized diagnostic metadata
if it fails; no raw response or secret is needed. The implementation was verified
offline only and did not perform that live rerun.

V4 is isolated in `v4/`. V1/V2/V3 code, providers, live runners, schemas and tests
remain unchanged. It reuses the immutable `ProjectInput`, V3 assessment, async
`ContractProvider`, `GroqProvider`, configuration and sanitized SDK error mapping.
It adds no auth, database, route, frontend, PayPal, activation or approval workflow.

### Public service and trusted review boundary

```python
from backend.app.modules.contractflow.v4.service import AmendmentDraftService

async def propose_amendment(provider, trusted_review_verifier, request_data):
    service = AmendmentDraftService(
        provider, trusted_review_verifier, timeout_seconds=30
    )
    return await service.generate_amendment(request_data)
```

The verifier is a REQUIRED injected `ReviewVerifier` with a `boundary_reference`
and `async verify_review(review_reference) -> VerifiedReview`. There is no default
or permissive production implementation. Core Platform must eventually implement
it against authenticated, current review records. It must independently check
reviewer authority, revocation and latest agreement/assessment versions in trusted
storage. A lookup reference, boolean or serialized receipt from an API caller is
not review proof. This module cannot discover current stored versions itself.

The trusted receipt attests `AUTHORIZE_DRAFT_GENERATION`, not amendment approval.
It contains reviewer/review references, timezone-aware review timestamp, agreement
and assessment IDs/versions, exact canonical SHA-256 content digests and boundary
identity. The service checks those fields, rejects future timestamps and stops
before the LLM if review verification fails. The only synthetic verifier lives in
`tests/v4_support.py` and loads a pre-recorded fictional test receipt; never inject
it into a production application. Digests bind content; they are not signatures
or authentication. Serialized output receipts must not become authorization tokens.

### Inputs, output and flow

`AmendmentRequest` contains `original_agreement` (agreement ID/version and full
`ProjectInput`), `reviewed_assessment` (assessment ID/version, agreement reference
and V3 assessment), and `review_reference`. Only OUT_OF_SCOPE is accepted. The
original project must exactly match the V3 snapshot. IDs, versions, review
references and attestations must all agree. Inputs are detached, revalidated,
immutable and limited to 128000 UTF-8 bytes.

Flow: validate input -> verify trusted review -> check exact content/version
attestation -> construct source registry and prompt -> one provider call ->
validate proposals and local evidence -> deterministic rendering -> return a
round-trip validated immutable `AmendmentDraft`. Review verification and provider
generation each have the configured cooperative timeout (default 30 seconds,
positive and at most 300). Cancellation propagates. No retries or persistence occur.

Output includes a server-generated UUID, original agreement/project/assessment
references, unchanged `original_facts`, request snapshot, verified review receipt,
proposed scope/deliverables, timeline/compensation considerations, citations,
unresolved terms and canonical `rendered_text`. Status is PROPOSED_DRAFT;
`effective=False`, `parties_approved=False`, human and semantic review are mandatory.
Every rendered draft carries:

**PROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE**

### Grounding, language and limitations

- Each additional-scope and deliverable proposal maps to exactly one reviewed V3
  change index, with complete unique change coverage. It must cite the exact full
  reviewed-change description, that change's exact client-request excerpt and
  original scope/deliverable context. Unknown paths, invented excerpts, duplicate
  local references and unsupported change indexes fail closed.
- Timeline and compensation fields cite the full request, full V3 explanation
  and full original deadline/budget respectively. Those original values appear
  only as evidence or server-rendered facts. Generated wording cannot invent or
  restate numerical amounts, deadlines, estimates or payment schedules.
- Proposed work/deliverable content words must come from the specific reviewed
  change and client request, plus a closed connective/review vocabulary. Material
  words in the reviewed description must be retained. Unrelated features and
  unsupported deliverables are rejected. The prompt supplies this vocabulary.
  This is intentionally conservative: novel synonyms, inflections and quantified
  scope requests may fail validation and require a future explicitly reviewed
  schema/grounding extension rather than automatic repair.
- V3 quantitative/obligation/schedule safeguards are reused without exceptions
  for proposal prose. V4 additionally rejects signatures, approval/activation
  claims, legal terms, free/waived compensation and payment-instruction wording.
  Conditional language is required; it does not itself prove safety.
- Unresolved terms are server-controlled: proposed scope/deliverable details,
  timeline, additional compensation, payment schedule and legal terms remain for
  negotiation/review. There are no signatures, effective dates or approval records.
- Lexical coverage and exact citations do NOT prove semantic entailment. Known
  source words can be recombined misleadingly; a model can change responsibility,
  implication or negation without new words. Original evidence may itself contain
  unsuitable or malicious text. Humans must review complete source context and
  every proposed clause. Source citations are quoted as evidence, not instructions
  or assertions that requests became agreed terms. Future UI consumers must safely
  escape source text. No guarantee of legal completeness/enforceability is made.

The renderer separates existing agreed facts, the unagreed client request, AI
proposals and unresolved terms. Original names, IDs, budget/currency and dates
come from trusted snapshot fields, never model-generated replacements. A rendered
draft is revalidated; tampered IDs, flags or text fail. The service returns data
without logging raw prompts or responses. Input ValidationError objects can contain
submitted values, so future API error/logging handlers must sanitize them.

### Synthetic example and offline verification

`tests/fixtures/v4/ordering.json` provides synthetic versioned references. Test
support combines the unchanged website project and V3 OUT_OF_SCOPE fixtures into
a full request. `review_record.json` is a fictional trusted test record, explicitly
not a real approval. `provider_output.json` is a hand-authored fake response.

Example proposal: “The proposed additional work could include online ordering
with payment integration, subject to negotiation.” The original 1200.00 USD
budget and 2027-01-29 deadline remain original facts; no additional price or new
deadline is set. Output requires human semantic review and remains ineffective.

From the repository root, in an activated Python environment:

```powershell
python -m pip install "pydantic>=2.10,<3" "groq>=1.7,<2" "pytest>=8,<10"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest backend/app/modules/contractflow/tests -p no:cacheprovider -q
```

No new dependency is needed. All V4 unit/live-runner tests are offline, using fake
providers or mocked SDK calls. No credentials are needed. Missing/forged/stale
review, unsafe evidence/prose, malicious outputs, rendering tampering, timeout,
cancellation, rate limits and authentication errors have explicit coverage.

### Explicit synthetic live demo (not executed during implementation)

Configure `GROQ_API_KEY` securely in your existing PowerShell environment and set
`GROQ_MODEL=openai/gpt-oss-120b`. The existing optional timeout variable applies.
Without `--run-live`, the script exits without a request. To explicitly run ONE
synthetic request, from the repository root:

```powershell
python -B -m backend.app.modules.contractflow.live_test_v4 --run-live --scenario ordering
```

The entire synthetic request must match its hardcoded canonical digest before
provider construction. The script uses only the test-support synthetic verifier
and prints a clear fictional-review disclaimer. It never loads a production
review. SDK retries stay disabled, including on HTTP 429. Output is the rendered
draft and mandatory review flags; validation reports contain only fixed rule
codes, and SDK errors only sanitized categories. No secret or raw response/error
logging or diagnostic bypass is available. Exit codes: 0 validated draft, 1
failure, 2 missing opt-in, 130 interruption. The user-run synthetic test passed
deterministic checks; human semantic review remains required. Do not replace the
pin to enable real data in this demo.

### Remaining work before V5

Integrate authenticated, current review verification and immutable version storage;
define persistence/audit retention, authorization, revocation and concurrency
rules; agree API error mapping and safely escaped UI presentation; review the
semantic quality of synthetic live wording. V5 must separately implement dual-party approval,
version/activation transactions and any commercial negotiation. V4 does none of
those and never modifies the original agreement or payment instructions.

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
