# V6 shared integration handoff

## Inspected baseline

Branch feature/contractflow; starting HEAD 3e93f16c96a0ab37423876c2f888840ec70f94bc.
The working tree was clean. Origin was fetched without merging: feature branch
matches V5; origin/main remains the initial commit. No shared backend exists in
this checkout or origin/main: no app entry point, auth/session dependency,
database/session factory, Alembic setup, shared entities or WorkBridge module.
FastAPI, SQLAlchemy and Alembic happen to be installed locally; that is not shared
infrastructure. No dependency installation was needed or performed.

| Dependency | Available | Implemented ContractFlow boundary | Required owner |
| --- | --- | --- | --- |
| V1–V5 services | Yes, reused unchanged | IntegrationRuntime orchestration | ContractFlow |
| FastAPI app/router conventions | No shared app | Exported api.router.router | Core mounts once |
| Authenticated session/roles | No | SharedAuth + Principal; own-party mapping and checks | Core |
| Versioned WorkBridge project/agreement data | No | WorkBridgeSource + SourceSnapshot | WorkBridge |
| Artifact/review storage | No | ArtifactRepository + typed/digested StoredArtifact | Core/DB + ContractFlow |
| PostgreSQL/session/Alembic | No | Existing V5 repository contract + ApprovalTransactions + storage proposal | Core/DB |
| Assessment-review authority | No | Existing V4 ReviewVerifier injected | Core/review owner |
| Amendment human/semantic reviews/revocation | No | AmendmentReviews + ReviewGrant validation | Team-approved review authority |

## Implemented and verified offline

Eight exported FastAPI routes, strict bounded request schemas, sanitized error
envelope, source/identity checks, immutable artifact validation, current-source
checks before persistence, review checks on registration and decisions/reads,
and orchestration using the existing V1–V5 services. All test adapters are under
tests/; production packages import none of them. There is no production app or
server command in this repository. Routes have NOT been registered in any shared
application. Without a server-selected complete IntegrationRuntime, requests
fail closed (401 missing bearer, otherwise 503 unconfigured).

The fake-provider HTTP workflow covers V1 and V2 generation, V3 OUT_OF_SCOPE
assessment, V4 inactive amendment, V5 registration, distinct-party decisions and
authorized audit history. No Groq/PayPal clients are used. Review denial/revocation,
source mismatch, stale revision, caller facts/roles, schema errors, provider errors,
idempotency, concurrent decisions and rollback are tested. The test transaction
is an asyncio lock with snapshot rollback; V5 storage is single-process memory.
These are NOT PostgreSQL, distributed or production-auth tests.

## Endpoint contract

Prefix `/api/v1/contractflow` (new module-owned versioning; no existing shared
router convention was present):

| Method/path | Request | Response |
| --- | --- | --- |
| POST /contracts/generate | ProjectRequest | StoredArtifact CONTRACT |
| POST /agreements/draft | ProjectRequest | StoredArtifact AGREEMENT |
| POST /scope/assess | AssessmentRequest | StoredArtifact ASSESSMENT |
| POST /amendments/generate | AmendmentRequest | StoredArtifact AMENDMENT |
| POST /amendments/{UUID}/register | RegisterRequest | ApprovalStatus |
| POST /amendments/{UUID}/decisions | DecisionBody | ApprovalStatus |
| GET /amendments/{UUID}/status | Authenticated read | ApprovalStatus |
| GET /amendments/{UUID}/history | Authenticated read | AuditEvent array |

Examples (IDs/versions/digests come from authorized server responses, not invented
caller facts):

```json
{"project_id":"PROJECT-ID-FROM-WORKBRIDGE","expected_source_version":1}
```

Scope assessment adds `client_request` and optional `supporting_context` entries
with id/text. These are explicitly untrusted; original facts are loaded from the
authoritative agreement. Amendment generation adds `assessment_id` (stored UUID)
and `review_reference` (must resolve through trusted assessment review).

Registration uses artifact `artifact_version`/`content_digest` as expected_version/
expected_digest. The resulting ApprovalStatus supplies the DIFFERENT V5 subject
digest used for decisions. Never interchange archive and approval digests:

```json
{"expected_version":1,"expected_digest":"<approval-content-digest>","decision":"APPROVE","idempotency_key":"unique-client-request-reference"}
```

Angle-bracket text is explanatory, not a valid digest. HTTP never accepts trusted
role/party/review flags, authoritative budgets/dates or an entire caller draft.
StoredArtifact contains immutable payload_json (decode to obtain typed domain
artifact), source snapshot, server identity/version/time and recomputed digest.
Payload/digest validation is independent of PostgreSQL's future JSONB storage.

Request body limit: 131072 actual streamed bytes. IDs max128 characters, positive
strict versions, SHA-256 hex digests; client request max8000 chars, supporting
context max10 entries. Existing V1–V5 size/safety rules also apply. No input or
raw exception is echoed. Errors use `{"error":{"code":"FIXED_CODE"}}` because no
shared error envelope exists. Map missing auth to401, hidden source/not found404,
authorization/review denial403, stale/conflict409, schema422, body413, invalid AI/
provider502, timeouts/integration/storage unavailable503. Core must adapt this
envelope if a shared standard arrives. No automatic retries or JSON repair.

## Auth, sources and review policy

Core must implement SharedAuth.authenticate with actual session/token validation,
expiry and revocation, and authorize with current own-behalf project/agreement
membership and read/write permissions. Principal is only created by that trusted
dependency. The module checks the configured boundary and exact client/freelancer
ID from WorkBridge; no role is accepted from HTTP. The default dependency uses
Bearer; Core can override it to adapt its existing session system after review.

WorkBridge must implement load(project_id, principal) with authorized access and
complete versioned ProjectInput plus optional original AgreementSnapshot. No
synthetic fallback. Missing/hidden project -> NOT_FOUND; incomplete data ->
INVALID_SOURCE. An absent agreement blocks scope assessment/amendments. Conflicting
IDs are rejected; edited project data cannot replace the original agreement.
Source version drift fails rather than silently substituting a new snapshot.
Generation rechecks source after AI, and storage must recheck at commit.

Review authority is NOT implemented. The team must authorize a reviewer role in
Core (no party self-attestation flag), record human AND semantic review of the
exact amendment ID/revision/V5 digest, reviewer ID and UTC review/expiry times,
and resolve current revocation on every decision. ReviewGrant forbids revoked or
incomplete reviews; times and exact binding are checked locally. The original V4
assessment-review receipt is also rechecked at decision time. Changed content
requires a new matching review; missing/stale/revoked/wrong-bound review denies
registration and approval. Access to status/history also fails closed when these
checks fail. An admin audit-access policy is a separate future decision.

ApprovalTransactions MUST provide one transaction scope shared by artifact,
auth/source/review and V5 storage adapters, serialize review/membership revocation
and version publication against decisions, and persist review-check metadata
with decision/audit updates. A Python callback wrapper around independent remote
services is not sufficient. No operational implementation exists here. See
[PostgreSQL proposal](persistence/POSTGRESQL_DESIGN.md) for constraints/locks/audit.
Until that exists, approval integration is blocked for production.

## Core-owned mounting change — instruction only, not applied

After implementing and testing the REAL adapters, in the Core-owned application
factory, construct IntegrationRuntime with those adapters and the existing provider
abstraction, set `app.state.contractflow_runtime = runtime`, and call
`app.include_router(router)` exactly once with the exported router. Use the shared
session/UoW throughout; do not import tests.v6_support. No create_all, schema setup,
synthetic identity, automatic registration or provider construction occurs here.
No shared files were modified. Core must supply its actual application entry point
before a truthful server startup command can be given.

The existing GroqSettings/GroqProvider may be injected with Core-managed secrets
and bounded timeout; no env file or new secret configuration was introduced. SDK
retries remain disabled. AI calls occur outside approval DB transactions. Do not
log authorization headers, contract/source bodies or exceptions with raw inputs.
Shared middleware/logging/rate limits/correlation IDs require Core ownership;
none are fabricated in this module. UI must safely render untrusted draft text.

## Verification and production blockers

Local verification: 872 tests passed, 0 failed, 0 skipped (806 existing +66 V6);
104 Python files passed syntax checks; tracked/untracked whitespace, credential-
pattern, configured-key and environment-file checks passed. One installed
Starlette/httpx TestClient deprecation warning was emitted; dependencies were not
changed. No PostgreSQL tests ran. V1–V5 code and documentation remain unchanged.

Run from the repository root using installed FastAPI/Pydantic/Pytest/httpx/Groq
SDK test dependencies (no live credentials needed):

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -B -m pytest backend/app/modules/contractflow/tests -p no:cacheprovider -q
```

No migrations, shared tables, production app, DB durability, multi-session races,
real JWT/session validation or real WorkBridge/review calls were verified. No real
signatures, legal execution, automatic activation or payment integration exists.
V5 terminal/idempotency/supersession rules remain unchanged; BOTH_APPROVED is only
a workflow record, effective=false, human and semantic review still required.

Team approvals needed: router mount/error-envelope compatibility, authoritative
ID/version mapping, reviewer authority/expiry/revocation/access policy, shared
transaction design, ContractFlow table migration and real PostgreSQL test setup.
These are explicit blockers; no teammate-owned files were changed to bypass them.
