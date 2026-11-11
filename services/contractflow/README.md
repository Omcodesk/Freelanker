# ContractFlow — Overview

ContractFlow is Freelanker's backend module for turning validated project data into
reviewable freelance contract drafts and assessing requested scope changes. It
helps clients and freelancers review proposed amendments and record independent
decisions on the same immutable version without changing the original agreement.

## Implemented Features

| Version | Feature | Description |
|---|---|---|
| V1 | AI Contract Generation | Structures supplied descriptions into extractive, validated draft sections. |
| V2 | AI Agreement Drafting | Produces controlled paraphrases with immutable project facts and mandatory semantic review. |
| V3 | Scope Change Detection | Classifies requests as IN_SCOPE, OUT_OF_SCOPE or NEEDS_CLARIFICATION with source-linked evidence. |
| V4 | Contract Amendments | Generates inactive, cited amendment proposals with professional deterministic rendering. |
| V5 | Dual-Party Approval | Records distinct client/freelancer decisions, idempotency, supersession and atomic audit/state changes in memory. |
| V6 | API Integration Layer | Exports eight FastAPI routes and typed integration boundaries; shared production adapters remain pending. |

Domain services and offline integration tests are implemented. Production auth,
WorkBridge retrieval, PostgreSQL persistence and shared application mounting are not.
`BOTH_APPROVED` is a workflow record, not activation, a signature or payment authority.

## Technology Stack

- Python 3.11+ and asynchronous service interfaces.
- FastAPI for the exported router; Pydantic v2 for immutable schemas and validation.
- Groq SDK behind a provider-independent interface; Pytest and HTTPX for offline tests.
- SHA-256 for canonical artifact and approval-content digests.
- PostgreSQL is a **design/protocol target only**; no operational SQLAlchemy adapter,
  database session factory or Alembic migrations are implemented in this module.

## Project Structure

```text
contractflow/
├── service.py, schemas.py       # V1 generation and validated project facts
├── config.py, providers/        # Explicit Groq settings and provider protocol/adapter
├── v2/                         # Agreement drafting and deterministic assembly
├── v3/                         # Scope assessment, evidence and quantity safeguards
├── v4/                         # Amendment generation, review boundary and renderers
├── v5/                         # Approval state machine, authorization, repository and audit
├── api/                        # V6 router, HTTP schemas, dependencies and safe errors
├── integrations/               # Auth, WorkBridge, review and transaction contracts/orchestration
├── persistence/                # Artifact storage interface and PostgreSQL design proposal
├── tests/                      # Offline tests, fake adapters and synthetic fixtures
├── demo_v5.py                  # Offline synthetic approval demonstration
├── live_test_v4.py             # Explicit opt-in synthetic Groq test
└── V6_HANDOFF.md               # Detailed integration contracts and team handoff
```

## API Endpoints

Prefix: `/api/v1/contractflow`. All routes use the Bearer authentication dependency
and require authorized project/agreement access through trusted adapters.
**The router is not mounted in a shared application; these are not running APIs.**

| Method | Endpoint | Purpose | Authentication |
|---|---|---|---|
| POST | `/api/v1/contractflow/contracts/generate` | Generate/store V1 draft | Bearer + project authorization |
| POST | `/api/v1/contractflow/agreements/draft` | Generate/store V2 agreement draft | Bearer + project authorization |
| POST | `/api/v1/contractflow/scope/assess` | Assess scope against the original agreement | Bearer + project authorization |
| POST | `/api/v1/contractflow/amendments/generate` | Draft from a reviewed stored assessment | Bearer + project authorization + trusted review |
| POST | `/api/v1/contractflow/amendments/{amendment_id}/register` | Register a verified inactive revision | Bearer + party authorization + trusted review |
| POST | `/api/v1/contractflow/amendments/{amendment_id}/decisions` | Record APPROVE/REJECT | Bearer + party authorization + trusted review |
| GET | `/api/v1/contractflow/amendments/{amendment_id}/status` | Read approval status | Bearer + party authorization + trusted review |
| GET | `/api/v1/contractflow/amendments/{amendment_id}/history` | Read audit history | Bearer + party authorization + trusted review |

Request models are in `api/schemas.py`; amendment path IDs are UUIDs:

- Generation: `project_id`, `expected_source_version`.
- Assessment: generation fields plus `client_request`; optional `supporting_context`
  is an array of `{id, text}` objects treated as untrusted data.
- Amendment generation: generation fields plus `assessment_id` (stored UUID) and
  `review_reference`, which must resolve through trusted assessment review.
- Registration: `expected_version`, `expected_digest` from the stored artifact.
- Decision: `expected_version`, `expected_digest` from ApprovalStatus, `decision`
  (APPROVE/REJECT), `idempotency_key`; optional `rejection_reason` only for REJECT.

Example generation body (replace the project ID with an authorized WorkBridge ID):

```json
{"project_id":"YOUR_PROJECT_ID","expected_source_version":1}
```

Generation returns `StoredArtifact`: ID/version, source snapshot, digest, UTC time,
kind and `payload_json` containing the validated domain draft/assessment. Registration
and decisions return `ApprovalStatus`; history returns an array of `AuditEvent`.
Archive digests and V5 approval digests are **different**; do not interchange them.
Bodies are limited to 131072 bytes. Caller-supplied roles, approval flags and
additional authoritative facts are rejected. Errors use `{"error":{"code":"..."}}`:
401 missing/invalid auth, 403 denied/review failure, 404 hidden/missing resource,
409 stale/conflict, 413 oversized body, 422 schema error, 502 provider failure,
503 timeout or unavailable integration. Raw errors and input values are suppressed.

## Environment Configuration

`GroqSettings.from_env()` reads exactly these variables when explicitly called:

| Variable | Required | Purpose | Safe example |
|---|---|---|---|
| `GROQ_API_KEY` | For live Groq calls only | Provider credential; never log or commit | Enter through the secure prompt below |
| `GROQ_MODEL` | For live Groq calls only | Account-accessible model supporting JSON-object mode | `openai/gpt-oss-120b` |
| `CONTRACTFLOW_TIMEOUT_SECONDS` | No | Finite timeout, greater than 0 and at most 300; default 30 | `60` |

Offline tests/demo need no credentials. The loader does not read `.env` files.
There is no module DATABASE_URL, JWT secret or production enable flag; shared
configuration belongs to the real adapters. Environment settings do not construct
or enable the V6 runtime automatically.

For local live testing, set variables in the same PowerShell session without
placing the key in command history:

```powershell
$groqSecret = Read-Host "Groq API key" -AsSecureString
$env:GROQ_API_KEY = [System.Net.NetworkCredential]::new("", $groqSecret).Password
$groqSecret.Dispose()
Remove-Variable groqSecret
$env:GROQ_MODEL = "openai/gpt-oss-120b"
$env:CONTRACTFLOW_TIMEOUT_SECONDS = "60"
```

The adapter uses JSON-object mode, temperature 0, no explicit token limit and
SDK retries disabled. Live scripts suppress raw provider errors and credential output.

## Local Setup and Testing

Run commands from the repository root. Reuse an existing suitable `.venv`; the
following creates one only if its Python executable is absent:

```powershell
Set-Location "C:\Users\Aanya Aggarwal\Freelanker"
if (-not (Test-Path ".venv\Scripts\python.exe")) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
```

If activation is blocked by local policy, use `.\.venv\Scripts\python.exe` in
place of `python` below. No verified dependency manifest exists in this checkout.
This manual development install lists the inspected local top-level versions;
it is not a complete dependency lockfile. The team must establish a shared lockfile.

```powershell
python -m pip install "fastapi==0.141.1" "pydantic==2.13.4" "groq==1.7.0" "pytest==9.1.1" "httpx==0.28.1"
```

Run the complete offline suite (fake providers and synthetic integration adapters):

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -B -m pytest backend/app/modules/contractflow/tests -p no:cacheprovider -q
```

Run the offline V5 approval demo; it uses fictional identities and never constructs
a Groq or PayPal client:

```powershell
python -B -m backend.app.modules.contractflow.demo_v5
```

**Optional external API call:** after configuring Groq above, this makes exactly
one real request using the pinned synthetic ordering fixture. It requires
`openai/gpt-oss-120b`; there are no automatic retries.

```powershell
python -B -m backend.app.modules.contractflow.live_test_v4 --run-live --scenario ordering
Remove-Item Env:GROQ_API_KEY
```

No shared application entry point exists, so no production server startup command
can be given until Core supplies the actual application and adapters.

## Data Flow

1. Clients/freelancers maintain requirements through the shared project system;
   a trusted WorkBridge adapter supplies immutable, versioned project facts.
2. V1/V2 prepare reviewable contract/agreement drafts from those facts.
3. A client submits untrusted change text; V3 assesses it against the original agreement.
4. A reviewed OUT_OF_SCOPE assessment becomes eligible for an inactive V4 proposal.
5. Trusted human/semantic review precedes V5 registration; distinct parties decide
   on the same revision/digest. BOTH_APPROVED does not activate the amendment.
6. The shared backend can expose records to WorkBridge/frontend through authorized
   adapters. No outbound WorkBridge writeback, payment execution or activation exists.

This is the intended connected workflow. Only fake-provider, in-process integration
and synthetic local demos are currently connected; production systems remain unwired.

## Integration Requirements — IMPORTANT

| Integration | Required From Team | Current Status |
|---|---|---|
| Shared FastAPI application | Core supplies app factory, configures runtime and mounts router once | Exported `api.router.router`; not mounted |
| Real authentication/identity | Implement `SharedAuth.authenticate` and current session/token verification | Typed `Principal` boundary only; no production auth |
| Client/freelancer authorization | Implement `SharedAuth.authorize` with trusted membership and read/write permissions | Module checks exact distinct party IDs; no caller-role trust |
| Real project/contract data | Map complete `ProjectInput` and original `AgreementSnapshot`, with authoritative versions | `SourceSnapshot` validates identity consistency; no caller facts accepted |
| WorkBridge integration | Implement `WorkBridgeSource.load(project_id, principal)` and agree ID/version mappings | Interface only; no assumptions about shared models/database |
| PostgreSQL persistence | Implement `ArtifactRepository`, V5 `ApprovalRepository` and `ApprovalTransactions` using shared sessions | Typed artifact/digest checks; approval memory repository for standalone use only |
| Database migrations | Supply declarative base, Alembic conventions and approved CF-owned schema | Design proposal only; no executed migrations or shared-table changes |
| Trusted review/revocation | Implement V4 `ReviewVerifier` and V6 `AmendmentReviews`; define reviewer authority/expiry | Exact review/version/digest checks exist; real review storage is missing |
| Frontend consumption | Teammate consumes authenticated APIs and safely renders untrusted draft text | No frontend implementation or automatic API exposure |
| Approval/version consistency | Supply one transaction across current artifact/source, permissions, reviews, decisions and audit | V5 idempotency/supersession implemented; real DB concurrency not verified |

`integrations/workflow.py::IntegrationRuntime` requires `auth`, `workbridge`,
`artifacts`, `approval_repository`, `reviews`, `assessment_reviews`, `transactions`
and `provider`; `timeout_seconds` defaults to 30. Core must inject real adapters,
not `tests/v6_support.py`. A missing Bearer credential fails with 401; missing
runtime/dependencies fail closed with 503. There is no synthetic production fallback.

In the **Core-owned** app factory, after constructing the real runtime:

```python
from backend.app.modules.contractflow.api.router import router

app.state.contractflow_runtime = runtime
app.include_router(router)  # exactly once; app and runtime are supplied by Core
```

Storage must recheck source freshness at commit and atomically write decisions,
audit and review-verification metadata. Serialize review/membership revocation and
revision publication with approvals; independent remote lookups or an in-memory
lock do not prove distributed correctness. New material content needs a new
immutable revision, new exact-digest review and fresh approvals. Preserve legacy
V4 text/digests on read; never silently re-render already approved artifacts.

## Current Status

- V1–V6 module implementation and offline integration coverage completed;
  shared **production integration is pending**.
- Last reported full verification: **902 tests passed**, with one installed
  Starlette/HTTPX test-client deprecation warning. This README edit changes no code.
- V4 live Groq generation was previously verified with `openai/gpt-oss-120b`;
  professional rendering and exact notice regressions are implemented.
- Latest implementation commit: `cd3a5d9b933e3a7e13586a1247825a79877e2556`.
- Human and semantic review remain mandatory. Amendments retain `effective=false`
  and `parties_approved=false`; BOTH_APPROVED is a separate V5 workflow state.
- No production PostgreSQL durability, distributed transactions or real auth was
  verified. Deterministic checks do not establish semantic or legal correctness.

## Additional Documentation

- [V6 integration handoff](V6_HANDOFF.md) — adapter contracts, detailed examples and team blockers.
- [PostgreSQL design proposal](persistence/POSTGRESQL_DESIGN.md) — proposed tables, transaction constraints and migration requirements; not an operational adapter.
