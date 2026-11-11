# ContractFlow Integration Plan — Freelanker

Date: 10 November 2026 (Asia/Calcutta). Scope: architecture/documentation only.

**Evidence convention:** Every paragraph, list, table and code block inherits the
nearest preceding evidence label, until another label appears. Mixed tables label
each row. Labels are exactly **VERIFIED IN CODE**, **VERIFIED BY TEST**,
**PROPOSED DESIGN**, **NOT IMPLEMENTED**, or **REQUIRES DECISION**. Proposed paths,
interfaces and columns are not statements that those objects already exist.

## 1. Executive summary and release decision

**VERIFIED IN CODE:** ContractFlow V1–V5 domain logic, V6 router, typed integration
ports, synthetic tests and single-process memory repository exist on the inspected
branch. No production auth, PostgreSQL adapter, migrations, shared app mount or
frontend integration is present there. The eight Python endpoints are exported,
not operational production URLs.

**PROPOSED DESIGN:** Preserve the requested architecture: one React/Vite frontend,
Express/TypeScript as primary API/auth gateway, a separate Python/FastAPI
ContractFlow service reusing V1–V5, and shared Supabase PostgreSQL persistence.
Express forwards the original Supabase bearer token; Python independently verifies
it, loads authoritative project/membership data and enforces its own authorization.
No TypeScript rewrite of the Python domain logic is proposed.

**REQUIRES DECISION:** This is a complete ContractFlow-owned target design with
explicit integration gates, **not an executable migration or production-ready
integration**. The actual Core implementation is unavailable. Exact Core table
names, column types, middleware, invitation services, error envelope and frontend
paths cannot be verified. No Core foreign keys or edits may be approved from this
document until Person 1 supplies the actual local/pushed code and DDL.

**NOT IMPLEMENTED:** The hybrid review policy, independent JWT verification,
Express proxy, Supabase persistence and React workspace changes described below
do not exist yet. This task creates only this plan; no source behavior, environment,
database, Supabase configuration, Git branch, commit or deployment is changed.

## 2. Verified repositories, commits and unavailable evidence

**VERIFIED IN CODE:** One provided repository is
`C:\Users\Aanya Aggarwal\Freelanker`, URL https://github.com/Omcodesk/Freelanker.
`git branch -vva`, `git worktree list --porcelain`, `git ls-remote --heads origin`
and the explicitly requested `git fetch origin --no-tags` were inspected/executed
without checkout or merge. The sole registered local worktree remains ContractFlow.

| Evidence | Component | Exact tip inspected | Source of inspection |
|---|---|---|---|
| VERIFIED IN CODE | ContractFlow | `f6cd74f63c412b2d29135bbcdb176b40fc39eb76` | Local HEAD and remote origin/feature/contractflow match |
| VERIFIED IN CODE | Previous CF baseline | `0608adf2fce1f10d42c62141f38f1a4348e4e7ca` | Committed README baseline; not current HEAD |
| VERIFIED IN CODE | Core Platform | `a87339908a55da4435d2368d8bc9b25ea83491e3` | Fresh origin/feature/core-platform; tree contains LICENSE only |
| VERIFIED IN CODE | WorkBridge | `d5e7af5f1038f5da782f4377cf1dfc446baedee8` | Read-only origin/workbridge tree/source |
| VERIFIED IN CODE | main | `a87339908a55da4435d2368d8bc9b25ea83491e3` | Remote branch tip |
| REQUIRES DECISION | Person 1's latest local Core checkout | Unavailable | User has no checkout path or confirmation of pushed implementation |

**VERIFIED IN CODE:** No local `feature/core-platform` branch exists in this
checkout. A targeted filename search in Desktop/Documents/Downloads did not find
`ProjectDetailView.tsx`. This does not establish that Person 1 has no local work;
it establishes only that such work was not available for inspection here. Core's
actual Express middleware, Supabase migrations, project/invitation services and
React component cannot be invented from the requested architecture.

**VERIFIED IN CODE:** Current tracked tree was clean before this task. Existing
untracked `.venv/`, module caches, the technical PDF and prior output/ PDF are
outside the intended change and remain untouched. The implementation report is
committed at current HEAD; its internal older Git/test snapshot is historical.

## 3. Existing implementation versus proposed integration

**VERIFIED IN CODE:** Local paths below are relative to
`backend/app/modules/contractflow/`, unless explicitly marked Core/remote.

| Evidence | Existing interface/file | Actual behavior / gap |
|---|---|---|
| VERIFIED IN CODE | `service.py::ContractGenerationService` | Async extractive V1 draft from validated ProjectInput |
| VERIFIED IN CODE | `v2/service.py::AgreementDraftService` | Controlled paraphrases; immutable authoritative facts |
| VERIFIED IN CODE | `v3/service.py::ScopeChangeService` | Three classifications, exact field-local evidence, deterministic actions |
| VERIFIED IN CODE | `v4/service.py::AmendmentDraftService` | Inactive amendment with trusted assessment review; professional/legacy canonical rendering |
| VERIFIED IN CODE | `v5/service.py::ApprovalWorkflowService` | Register/decide/read; exact version/digest, actor boundary, idempotency, terminal states |
| VERIFIED IN CODE | `v5/repository.py::ApprovalRepository` | Transactional protocol; only built-in implementation is volatile memory with RLock |
| VERIFIED IN CODE | `integrations/contracts.py::SharedAuth` | authenticate/authorize protocol; no real JWT implementation |
| VERIFIED IN CODE | `WorkBridgeSource`, `SourceSnapshot` | Versioned source contract, not a connected WorkBridge client |
| VERIFIED IN CODE | `ReviewGrant`, `AmendmentReviews` | Grant requires human_review=True and semantic_review=True, revoked=False, exact digest and valid UTC times |
| VERIFIED IN CODE | `v4/review.py::ReviewVerifier` | Trusted original-assessment receipt; distinct from review of the generated amendment |
| VERIFIED IN CODE | `integrations/workflow.py::IntegrationRuntime` | Requires eight injected dependencies; rechecks artifact/source/review authority |
| VERIFIED IN CODE | `persistence/artifacts.py::ArtifactRepository` | Typed save/load protocol; no durable implementation |
| VERIFIED IN CODE | `api/dependencies.py` | Fail closed: 401 without bearer, 503 without configured runtime |
| NOT IMPLEMENTED | Production integration | No Express proxy, real Supabase auth/source/review/UoW, SQL models/migrations or CF React UI |

**VERIFIED BY TEST:** Prior executed full verification at this unchanged code
baseline: 902 passed, 0 failed, 0 skipped; one Starlette/httpx deprecation warning.
The last PDF-task run was 45.49s. Those tests use fake providers/synthetic adapters;
they are not JWT, Supabase, real database or browser E2E verification. No fresh test
suite is claimed for this documentation-only plan.

## 4. Final architecture, flows and deployment assumptions

**PROPOSED DESIGN:**

```text
React + Vite (single frontend; Supabase user access token)
    -> Express + TypeScript (existing primary API; verify auth and membership)
        -> Python FastAPI ContractFlow (verify SAME token independently)
            -> Core-authoritative source/membership adapter
            -> existing V1-V5 services and Groq provider abstraction
            -> same Supabase PostgreSQL: immutable CF artifacts and review/approval UoW
```

- Browser cannot set trusted identity/role headers or send authoritative terms to
  generation routes. Facts come from authorized persistent rows.
- Express resolves project ownership, checks permission and proxies a bounded
  allowlisted request. Python repeats authority checks; gateway success is not proof.
- Python remains a separate process/container, not a Python library imported into
  Express. Its owned app factory mounts the exported router once. Preserve the
  primary Express API and frontend; do not merge WorkBridge's standalone app into it.
- Prefer private service networking/TLS or mTLS gateway-to-Python. Restrict ingress
  to the gateway; that transport control does not replace user JWT verification.
- Use one shared Supabase project/database after Core confirms it. The actual
  project URL, JWT settings, DB schema and deployment environment are unverified.
- AI generation runs outside long-lived DB locks. Snapshot facts/version, call
  provider once under a bounded timeout, then revalidate current source/access
  before the storage commit. Drift returns409, not silent regeneration.
- Approval and review issuance/revocation run inside one DB transaction, with no
  Groq call or remote UI request while locks are held.
- Provider timeout ->503; invalid/provider output ->502; missing adapters/database
  unavailable ->503. Do not fabricate success, substitute fixtures or auto-retry
  generation/decision requests after an uncertain upstream outcome.

**VERIFIED IN CODE:** Existing environment loader reads only GROQ_API_KEY,
GROQ_MODEL and optional CONTRACTFLOW_TIMEOUT_SECONDS (default30, finite >0, <=300).
It reads no .env. Groq adapter uses JSON-object mode, temperature0, retries0.

**PROPOSED DESIGN:** Additional server-only configuration names are proposals, not
existing settings: CONTRACTFLOW_SERVICE_URL (Express), SUPABASE_URL,
SUPABASE_JWT_ISSUER, SUPABASE_JWT_AUDIENCE, SUPABASE_JWT_ALGORITHM,
SUPABASE_JWKS_URL, CF_DATABASE_DSN, CF_DB_ROLE, CF_ALLOWED_GATEWAY,
CF_REVIEW_POLICY_VERSION and bounded CF_JWKS_CACHE_SECONDS. Use Core's actual names
if already defined when its code arrives. DSNs/service secrets never enter Vite
VITE_* variables. Browser gets only the public Supabase configuration allowed by
Core, never a service-role key or direct database credential.

## 5. Core-to-ContractFlow data mapping and incomplete setup

**VERIFIED IN CODE:** `schemas.py::ProjectInput` requires complete nonempty scope,
distinct client/freelancer IDs, positive Decimal budget, uppercase three-letter
currency, dates and 1–99 deliverables/milestones. Dates/links/IDs are cross-validated.
SourceSnapshot additionally requires positive source_version and optionally an
AgreementSnapshot. V3/V4 require the original agreement, not edited project prose.

**REQUIRES DECISION:** Actual Core columns/types are UNVERIFIED for every row below.
Proposed mapping is semantic, not a claim that `projects.client_id`, memberships
or any similarly named columns exist. Person 1 must fill the physical schema
mapping and invitation-to-membership rules from their actual migrations/services.

| CF target | Verified CF type/rule | Actual Core column | Required authoritative mapping / missing-data behavior |
|---|---|---|---|
| project_id | string; API max128 | UNVERIFIED | Stable Core PK canonical string; no generated replacement or WB integer assumption |
| title | nonempty string | UNVERIFIED | Stored project title, not caller override |
| client.id/name | Party; distinct ID | UNVERIFIED | Exact designated client Supabase subject + trusted profile name; name alone is not identity |
| freelancer.id/name | Party; distinct ID | UNVERIFIED | Exact designated freelancer subject + trusted profile name; accepted assignment, not pending invitation |
| scope | nonempty string | UNVERIFIED | Authorized requirements; agreed snapshot for V3/V4, never latest edited description substituted |
| budget | Decimal >0, max18 digits/4 decimals | UNVERIFIED | Prefer numeric(18,4); no float roundtrip or inferred zero |
| currency | uppercase 3-letter syntax | UNVERIFIED | Stored explicit currency; validate allowed currency/business precision; never assume USD/INR |
| start_date/deadline | date; ordered | UNVERIFIED | Explicit project dates; no today/default or inferred milestone maximum |
| deliverables[].id/description/deadline | unique IDs, description, bounded date | UNVERIFIED | Planned deliverables with explicit dates; uploaded file names are not a substitute |
| milestones[].id/description/deadline | unique IDs, bounded date | UNVERIFIED | Delivery milestones; payment amount does not create a payment schedule |
| milestones[].deliverable_ids | nonempty valid links | UNVERIFIED | Explicit membership of deliverables in delivery milestones |
| agreement_id/version | string / strict positive integer | UNVERIFIED | Immutable authoritative original agreement registry; a mutable contract_ref is insufficient |
| source_version | strict positive integer | UNVERIFIED | Monotonic counter over all relevant source facts, not updated_at |
| membership/permissions | outside ProjectInput | UNVERIFIED | Current active Core memberships, designated parties and operation permissions; invitation alone grants none |

**PROPOSED DESIGN:** Return a derived `INCOMPLETE_SETUP` state with a list of missing
field codes and current source_version from an authorized setup endpoint. Generation
is blocked with409 `PROJECT_SETUP_INCOMPLETE` until an authorized party supplies
all required fields through Core's normal audited mutation workflow. Empty lists,
missing dates/currency/party IDs or an unaccepted freelancer assignment must not
be patched with dummy values. Missing original agreement blocks scope/amendment
operations even when V1/V2 project setup is complete. Inconsistent data returns
`SOURCE_CONFLICT`; never silently choose one party/budget/version.

**PROPOSED DESIGN:** Separate current requirements from immutable original agreed
facts. Project edits increment source_version but never rewrite an original
AgreementSnapshot. Original agreement publication requires Core-authorized authority;
V1/V2 generation or V5 BOTH_APPROVED is not that publication/activation authority.

## 6. Authentication and project authorization

### 6.1 End-to-end flow

**PROPOSED DESIGN:**

1. Browser obtains a Supabase user access token using Core's actual auth flow.
2. Express verifies the token using its existing middleware once inspected; do
   not replace the primary authentication gateway or assume decoding is verification.
3. For project routes, resolve the Core project and current membership/permission.
   For amendment routes, first resolve amendment -> exact artifact -> owning project
   via trusted storage, then check membership. Do not accept a project ID in an
   extra body/header to choose ownership.
4. Proxy the original `Authorization: Bearer ...` token over TLS; strip browser
   X-User-ID/X-Role/X-Reviewed and similar headers. Regenerate request/correlation IDs.
5. FastAPI independently verifies token signature/claims, resolves Principal and
   reloads current Core membership through the trusted adapter.
6. Derive CLIENT/FREELANCER from designated authoritative party IDs. JWT role is
   not a project role; user_metadata is not permission authority. Verify own-behalf,
   distinct parties and amendment agreement/project association.
7. Before writes, recheck session/membership/review/source under the shared UoW.
   Neither Express forwarding nor matching a digest authorizes a decision.

### 6.2 Supabase JWT signing and rotation

**VERIFIED IN CODE:** Real JWT verification does not yet exist in SharedAuth.
The Supabase project's actual signing mode/issuer/audience are not available here.

**PROPOSED DESIGN:** Pin one trusted Supabase issuer/project and its JWKS endpoint
in server config. Prefer confirmed ES256 or RS256 asymmetric signing; allow only
the configured algorithm and compatible JWK kty/use/alg. Ignore token jku/x5u and
never derive issuer/JWKS URLs from a token. Cache bounded JWKS, refresh once for an
unknown kid with rate limits, and fail closed if no trusted key is available.
Do not accept none or mix RSA public keys and HMAC secrets in one verifier.

**REQUIRES DECISION:** Confirm the real project signing configuration. Legacy
HS256 must be a separate explicitly approved mode with Auth-server validation or
a server-only correctly scoped HMAC verifier; never silently fall back from
asymmetric verification. The Supabase docs describe asymmetric discovery/rotation
and the legacy shared-secret distinction; these are provider facts, not proof of
this project's configuration. [Official signing-key documentation](https://supabase.com/docs/guides/auth/signing-keys).

**PROPOSED DESIGN:** Validate exact issuer, configured audience, exp, required
nonempty UUID sub, nbf when present, iat not in the future, and expected authenticated
user token purpose. Reject anonymous/API/service-role keys as user access tokens.
Proposed clock skew: at most30s, never extending a DB review grant's expiry. Confirm
audience with Core; do not assume authenticated without checking its actual tokens.
No raw token or claim dump in logs. Bounded key cache does not guarantee instantaneous
key revocation; disable writes on key compromise until trusted configuration refresh.

### 6.3 Session, membership and role semantics

**PROPOSED DESIGN:** Signature validity alone is insufficient for sensitive writes.
Check session_id against an authoritative active-session/revocation mechanism,
including user disablement and configured maximum/idle-session rules. Lock the
relevant session/membership rows or a common revocation gate in the approval UoW.
Auth-service outage fails503; absent/revoked/expired authentication fails401.
No refresh token is forwarded to Python; token refresh is Core/browser responsibility.

**REQUIRES DECISION:** Core must provide the actual session lookup and permissions
without broad CF access to auth internals. Supabase documents that JWTs can remain
valid until expiry after sign-out and sensitive actions can check session existence;
cleanup/timeout behavior also matters. Offline JWT validation alone is not session
revocation. [Official session documentation](https://supabase.com/docs/guides/auth/sessions).

**PROPOSED DESIGN:** Only designated active CLIENT/FREELANCER parties can generate,
register or decide by default. Either party may read their artifacts/status/audit
with read permission. A collaborator or pending invite is not a party. Platform
reviewers use separate scoped review permissions; they cannot act as a party or
satisfy both approvals. Apply 404 for invisible resources, 403 for a visible but
forbidden operation; keep cross-project ownership lookup server-side. A removed
member cannot replay a previously authorized write. Do not reuse WorkBridge role
strings or an email invitation as membership evidence.

## 7. Hybrid review-grant authority — explicit versioned policy

### 7.1 Existing safeguards and incompatibility

**VERIFIED IN CODE:** Current V6 ReviewGrant has human_review Literal[True],
semantic_review Literal[True] and revoked Literal[False]. validate_grant checks exact
amendment/version/digest and UTC validity. The runtime checks grants on registration,
decisions and reads. V4's ReviewVerifier attests a prior scope assessment/agreement,
not the generated amendment. V5 requires a current matching assessment receipt at
registration. These are different reviews and must not share an invented receipt.

**NOT IMPLEMENTED:** There is no machine semantic issuer, risk classifier, human
reviewer authorization store or hybrid policy. Passing deterministic/LLM checks
does not establish that any human reviewed the generated amendment.

### 7.2 Required policy

**PROPOSED DESIGN:**

| Revision class | Gate before party decisions | Who issues it | Human truth |
|---|---|---|---|
| STANDARD | Valid machine semantic grant after all existing deterministic guards and bounded semantic evaluation | Dedicated authorized review-worker principal | human_review_performed=false; never represented as platform human review |
| FLAGGED or DISPUTED | Valid semantic evidence PLUS platform human-review grant | Core-authorized reviewer/admin with contractflow.review.flagged permission | Only the actual authenticated reviewer action sets human_review_performed=true |
| Unknown, low-confidence, evaluator failure or unclassified risk | No standard grant; flag/escalate or hold | No implicit issuer | Decisions remain blocked |

- Risk classification is server-owned and versioned, derived from trusted facts,
  rule results, disputes and semantic findings, not caller-provided risk=standard.
  An unresolved detector failure cannot be downgraded to standard.
- Suggested flag triggers: detected ambiguity/conflict, source-review mismatch,
  safety finding, disputed content, or inability to establish the standard gate.
  Binding legal/financial/obligation violations still FAIL generation; human review
  is not permission to bypass V4 validation or legal/commercial missing-term rules.
- On the standard path, BOTH parties must explicitly inspect/approve the exact
  amendment after identity verification. Generation/review workers never insert
  decisions. An approve action is recorded as that party's attestation; a click or
  fetch cannot prove actual understanding. Do not claim such proof in status flags.
- For flagged/disputed content, no party approval is accepted before the human
  grant. Reviewer must have current scoped Core permission, not merely a JWT claim
  or party role. Record reviewer identity, review record/evidence digests, UTC times,
  policy version and rationale reference; exclude raw prompts/tokens from audit.
- If no reviewer is available, keep REVIEW_PENDING/ESCALATED and return403/409 gate
  status. No timeout-to-approval, synthetic admin or ordinary-party override.
- Every grant binds amendment UUID/revision/approval digest, project binding,
  source version, original agreement/version, risk class and policy version. Expiry
  is explicit; proposed maximum15min machine and24h human, subject to team policy.
  Re-evaluation creates a new grant, not an in-place evidence/expiry edit.
- Revocation locks the same project/head/review rows as decisions, records who/why
  via safe metadata and blocks later decisions. Prior committed decisions remain
  historical; they do not authorize a changed subject or retroactively disappear.

### 7.3 Exact proposed interface changes and compatibility

**PROPOSED DESIGN:** New names below are interface proposals, not existing classes.

| Existing interface | Proposed change | Compatibility rule |
|---|---|---|
| ReviewGrant | Add separate ReviewGrantV2 discriminated union: MACHINE_SEMANTIC vs PLATFORM_HUMAN, issuer_type/ref, policy/risk, evidence digest, exact source/agreement bindings and times | Do not loosen old Literal[True] or construct fake human=True for a machine |
| AmendmentReviews.verify | Add AmendmentReviewPolicy.verify_gate(subject, principal, operation, tx) -> ReviewGateV2 with typed grant set and eligibility | Runtime explicitly dispatches by immutable policy version; old human-only validator remains unchanged for legacy subjects |
| SharedAuth | Implement independent JWT auth; proposed PrincipalV2 adds session binding and token claims needed for revalidation; reviewer/service authority is separate from party context | Never add trust for caller identity headers or body booleans |
| ReviewVerifier | Retain actual V4 assessment-review semantics and current receipt authority | Amendment machine grant does not replace assessment review; automating that earlier review would require a separate approved policy |
| ApprovalTransactions | Implement PostgreSQL UoW; add scoped review issuance/revocation and verified session/membership recheck inside it | No independent remote lookups masquerading as atomic DB authority |
| ApprovalStatus HTTP output | Proposed wrapper adds policy_version, risk_class, eligibility, machine_semantic_status and platform_human_review_status | Keep domain human_review_required=true/semantic_review_required=true; never turn required into proof performed |
| Audit HTTP history | Preserve existing V5 decision-event representation; store operational review/service audit separately or expose a versioned admin response | Do not fabricate CLIENT/FREELANCER actors for workers/admins |

**PROPOSED DESIGN:** Preserve V1–V5 generation/state/digest algorithms. Implement
the new gate at the V6 orchestration boundary; no TypeScript rewrite and no
automatic decision generation. The old V4 assessment receipt remains genuinely
trusted; both amendment parties still supply their human decisions.

**REQUIRES DECISION:** Migration is opt-in for NEW subjects under a versioned
hybrid policy. Existing artifacts, receipts, approvals and digest serialization
stay human-only and byte-identical; do not reinterpret an old approval as new
policy consent. Freeze late-disputed/risk-escalated subjects against further
decisions and revoke grants. Resume only on a new materially changed revision or
a new draft UUID linked as its replacement, with fresh review and both decisions.
V5 publish rejects an unchanged-content next revision: do not bypass that rule
just to create a policy cycle. A new draft UUID is an explicit new subject, not
silent supersession of old audit. If the product requires same-ID/same-content
review cycles, it needs a separately versioned V5 model change and migration.

## 8. PostgreSQL schema and migration design

### 8.1 Boundaries and blocking physical-schema decision

**VERIFIED IN CODE:** `persistence/POSTGRESQL_DESIGN.md` is a proposal only. No
ContractFlow SQL models, shared session factory, migration or PostgreSQL repository
exists. WorkBridge's SQLite `projects.id` and mutable `contract_ref` are not Core
Supabase project/agreement keys.

**REQUIRES DECISION:** A deployable migration cannot name correct Core FKs before
the actual Core DDL is supplied. The following fully specified CF-owned relational
design uses a minimal **identity binding**, not duplicate user/project business
tables. External Core project/user/agreement FKs remain an explicit release gate.
Do not invent `public.projects(id)` or `profiles(id)`, or guess that an agreement
ID is a project ID. A future migration must replace/augment the opaque binding
with verified Core relationships and backfill/validate them before enabling traffic.

**PROPOSED DESIGN:** All proposed tables/functions live in non-Data-API-exposed
`contractflow_private`. UUIDs are server-generated; timestamps are UTC timestamptz.
Use `bigint` counters with CHECK 1 <= value <= 9007199254740991 to retain safe
integer JSON round trips to TypeScript. Digest columns are text CHECK matching
`^[0-9a-f]{64}$`; they never grant authorization. All cross-project FKs below use
the explicit `project_binding_id`, not an assumed agreement/project equivalence.
All FK deletes are RESTRICT/NO ACTION, never cascading away audit/history.
Columns are NOT NULL unless explicitly marked nullable. Creation/event timestamps
default to the database clock; expiry and revocation timestamps have no implicit
future value. Composite-key shorthand such as binding, revision and digest below
means the named table's project_binding_id, amendment_version/artifact_revision
and specified digest column respectively; approval links always bind
approval_digest, never archive_digest. This is a relational design, not executable
DDL; final migration review must expand every shorthand into exact column names.

### 8.2 Supporting authoritative bindings and snapshots

**PROPOSED DESIGN:** These additional tables are needed to avoid fake Core FKs,
capture immutable facts and make the required approval/review FKs non-circular.

| Table | Columns/types | Keys, checks and indexes |
|---|---|---|
| cf_project_bindings | project_binding_id uuid; core_namespace text; core_project_key text; source_version bigint; frozen boolean default false; created_at timestamptz | PK project_binding_id; UQ(core_namespace,core_project_key); namespace/key nonempty; positive version; lookup UQ index. Mapping is one authoritative Core project, not project facts. Core physical FK/type unverified and deployment-blocking. |
| cf_project_sources | project_binding_id uuid; source_version bigint; source_digest text; snapshot_json jsonb; created_at timestamptz | PK(binding,source_version); FK binding -> cf_project_bindings; UQ(binding,version,source_digest); object JSON and digest/version checks; insert only a complete validated SourceSnapshot. Entire row immutable. |
| cf_agreement_versions | agreement_id uuid; agreement_version bigint; project_binding_id uuid; origin_reference text; source_version bigint; agreement_digest text; project_snapshot jsonb; created_at timestamptz | PK(agreement_id,agreement_version); UQ(id,version,binding); FK(binding,source_version) -> cf_project_sources; positive versions/nonempty origin/object JSON; index(binding,id,version). Immutable imported/published original facts, not a draft activated by V5. Actual external Core agreement FK remains gated. |
| cf_review_authorities | authority_id uuid; issuer_type text; user_subject uuid nullable; service_identity_ref text nullable; enabled boolean; capabilities text[]; created_at timestamptz | PK authority_id; issuer HUMAN or SERVICE; exactly one user_subject/service_identity_ref; unique nonnull user_subject and service_identity_ref; index enabled/type. Authority is Core-provisioned, never self-enrolled by body fields. External user FK unverified. |

**PROPOSED DESIGN:** A binding is a CF-internal UUID mapped to a verified Core
primary key; it is not necessarily the value in ProjectInput.project_id. The
adapter resolves that distinction once and checks every read/write. Supabase JWT
sub values identify users; no unverified FK to a guessed Core profile table is
declared. Core must confirm the user/party mapping and session lookup schema.

**PROPOSED DESIGN:** AgreementSnapshot.agreement_id can encode the CF registry
UUID as a string while origin_reference preserves the confirmed Core agreement
identity. Core may instead mandate its own UUID registry after inspection; do not
mix the two namespaces. This mapping is an approval gate, not permission to create
an authoritative agreement from a generated draft. V1/V2 can precede an original
agreement; V3/V4 remain blocked until authorized original facts/version exist.

### 8.3 Required ContractFlow tables

**PROPOSED DESIGN:** Every row below inherits the RLS, privileges, immutability,
retention and insertion rules in Sections 8.5–8.7. Those rules are mandatory per
table, not optional implementation details.

#### cf_artifacts — immutable generation artifact

- Columns: artifact_id uuid; artifact_revision bigint; project_binding_id uuid;
  kind text; source_version bigint; agreement_id uuid nullable; agreement_version
  bigint nullable; archive_digest text; approval_digest text nullable;
  source_snapshot jsonb; payload jsonb; canonical_archive text;
  canonical_approval text nullable; created_by_subject uuid; created_at timestamptz.
- PK(artifact_id,artifact_revision). FK(binding,source_version) -> cf_project_sources.
  FK(agreement_id,agreement_version,binding) -> cf_agreement_versions, with both
  nullable agreement fields either absent or present together.
- kind CHECK CONTRACT/AGREEMENT/ASSESSMENT/AMENDMENT. ASSESSMENT/AMENDMENT require
  agreement fields; AMENDMENT additionally requires approval_digest and canonical
  approval bytes. JSON fields must be objects. All digests/version/time checked.
- UQ(artifact_id,revision,binding,kind,archive_digest,approval_digest) supports an
  exact amendment-artifact FK, not just an ID match. Index(binding,kind,created_at),
  index(binding,source_version). Archive/approval hashes are independently recomputed
  from validated canonical representations; JSONB key reordering is not canonical
  serialization. Read paths revalidate domain models and digests.
- No UPDATE/DELETE of any field. A material change creates a new artifact revision
  or new draft UUID. Preserve legacy renderings and format tags; never rehash old
  artifacts through a changed serializer. No raw provider output/token is stored.

#### cf_approval_versions — immutable subject plus transactional workflow state

- Columns: amendment_id uuid; revision bigint; project_binding_id uuid; artifact_kind
  text default AMENDMENT; archive_digest text; approval_digest text; source_version
  bigint; agreement_id uuid; agreement_version bigint; policy_version text;
  risk_class text; client_subject uuid; freelancer_subject uuid; subject_json jsonb;
  registration_state text; workflow_state text nullable; record_json jsonb nullable;
  created_at timestamptz; registered_at timestamptz nullable.
- PK(amendment_id,revision); UQ(amendment_id,revision,binding);
  FK(amendment_id,revision,binding,artifact_kind,archive_digest,approval_digest)
  -> exact cf_artifacts tuple. artifact_kind CHECK AMENDMENT, so a contract draft
  cannot accidentally serve as an amendment. FK(agreement_id,version,binding) ->
  cf_agreement_versions; FK(binding,source_version) -> cf_project_sources.
- UQ(amendment_id,revision,binding,approval_digest,source_version,agreement_id,
  agreement_version,policy_version,risk_class) is the target of exact review FKs.
  Also UQ(amendment_id,revision,binding,approval_digest) for decision/audit links.
- CHECK distinct client_subject/freelancer_subject; risk STANDARD/FLAGGED/DISPUTED;
  registration UNREGISTERED/REGISTERED. workflow_state NULL and record_json NULL
  before registration; afterward one of V5's five states with validated record.
  Versions/digests/nonempty policy/JSON shape constrained. Index(binding,registration_state),
  index(amendment_id,workflow_state).
- Material/party/source/policy fields are immutable. Only validated workflow state,
  record_json and first registered_at may change through the approval transaction
  function; a trigger forbids mutation of the immutable subject columns.

#### cf_approval_heads — current real revision, never an orphan pointer

- Columns: amendment_id uuid; project_binding_id uuid; current_revision bigint;
  row_version bigint; eligibility text; last_audit_sequence bigint; created_at
  timestamptz; updated_at timestamptz.
- PK(amendment_id). Composite FK(amendment_id,current_revision,binding) ->
  cf_approval_versions, DEFERRABLE for atomic publication. FK binding -> cf_project_bindings.
  Positive revision/row_version; nonnegative sequence. eligibility
  READY/REVIEW_PENDING/SOURCE_STALE/FROZEN is a gate, never effective/activation.
  Index(binding,eligibility), index(binding,amendment_id).
- Update only via publication/registration/decision/revocation functions; do not
  roll current_revision backward. A frozen/stale head never counts old approvals
  for a replacement subject. CAS row_version increments with committed changes.

#### cf_approval_parties — exact distinct role/actor mapping

- Columns: amendment_id uuid; revision bigint; project_binding_id uuid;
  approval_digest text; party_role text; actor_subject uuid.
- PK(amendment_id,revision,party_role); UQ(amendment_id,revision,actor_subject);
  UQ(amendment_id,revision,binding,approval_digest,party_role,actor_subject).
  Composite FK(amendment_id,revision,binding,digest) -> cf_approval_versions.
- CHECK role CLIENT/FREELANCER. Registration/publication inserts exactly the two
  authoritative designated parties under lock; a deferred constraint trigger
  checks count=2 and agreement/subject equality. This prevents one user occupying
  both roles or an approval using another project's party.
- Entire rows immutable; role reassignment needs a new subject/cycle, not an edit.

#### cf_reviews — immutable grant body, controlled revocation metadata

- Columns: review_id uuid; amendment_id uuid; revision bigint; project_binding_id
  uuid; approval_digest text; source_version bigint; agreement_id uuid;
  agreement_version bigint; policy_version text; risk_class text; grant_kind text;
  issuer_authority_id uuid; evidence_digest text; human_review_performed boolean;
  issued_at timestamptz; expires_at timestamptz; revoked_at timestamptz nullable;
  revoked_by_authority_id uuid nullable; revocation_reason_code text nullable.
- PK(review_id). Composite FK of amendment/revision/binding/digest/source/agreement/
  policy/risk -> exact cf_approval_versions tuple. Authority and revoking authority
  FKs -> cf_review_authorities. UQ(review_id,amendment_id,revision,binding,approval_digest)
  supports exact decision links.
- CHECK grant_kind MACHINE_SEMANTIC/PLATFORM_HUMAN; machine implies
  human_review_performed=false; human implies true. Require issued_at<expires_at
  and paired revocation metadata. Expiry/current time cannot be a stable CHECK;
  verify with DB clock inside the decision function, not a stale cached boolean.
  A constraint trigger enforces issuer type/capability and grant-kind matching.
- Index(amendment_id,revision,grant_kind,expires_at) WHERE revoked_at IS NULL;
  index(issuer_authority_id). No UQ that permits only one grant forever: renewal
  inserts a new row; older grants remain audit evidence.
- Grant evidence/body/expiry cannot be edited. Only a scoped revocation function
  may set revocation metadata once, with locked audit insertion. No delete.

#### cf_decisions — one authorized decision per exact party/revision

- Columns: decision_id uuid; amendment_id uuid; revision bigint; project_binding_id
  uuid; approval_digest text; actor_subject uuid; party_role text; decision text;
  rejection_reason text nullable; idempotency_key text; request_digest text;
  semantic_review_id uuid; human_review_id uuid nullable; decided_at timestamptz.
- PK(decision_id); UQ(amendment_id,revision,actor_subject);
  UQ(amendment_id,revision,party_role); UQ(amendment_id,revision,idempotency_key).
  UQ(decision_id,amendment_id,revision,binding,approval_digest) supports audit FK.
- Composite party FK(amendment,revision,binding,digest,role,actor) ->
  cf_approval_parties. Exact semantic/human review FKs(review_id,amendment,revision,
  binding,digest) -> cf_reviews. Thus a valid grant for another project/revision
  cannot satisfy this row. A transaction guard checks grant kinds/authority/current
  policy and mandatory human grant for flagged/disputed subjects.
- CHECK APPROVE/REJECT; reason NULL for APPROVE, bounded nonblank max1000 for REJECT
  when supplied; key nonblank max128; request_digest/digest regex, UTC server time.
  Index(binding,decided_at). Idempotency compares normalized payload AND trusted
  actor, not hash alone or a client identity field. Stored reason is restricted
  untrusted content and never copied into audit/logs. Entire decision immutable.

#### cf_audit — append-only revision-owned evidence

- Columns: event_id uuid; project_binding_id uuid; amendment_id uuid; revision
  bigint; approval_digest text; event_sequence bigint; event_kind text; action text;
  actor_kind text; actor_subject uuid nullable; actor_authority_id uuid nullable;
  party_role text nullable; decision_id uuid nullable; review_id uuid nullable;
  previous_state text nullable; new_state text nullable; idempotency_reference
  text nullable; correlation_id uuid; occurred_at timestamptz; metadata jsonb.
- PK(event_id); UQ(amendment_id,event_sequence). Exact owning version FK
  (amendment,revision,binding,digest) -> cf_approval_versions. Optional composite
  decision/review FKs include the SAME version/project/digest. No FK directly from
  agreement_id to projects is introduced. Index(binding,occurred_at),
  index(amendment_id,revision,event_sequence), index(correlation_id).
- event_kind APPROVAL/REVIEW/SOURCE_GATE; actor_kind USER/SERVICE with exactly the
  corresponding subject/authority reference; scoped actions allowlisted. V5
  party decisions retain their CLIENT/FREELANCER role; service/admin review events
  are not falsely serialized as V5 party events.
- Positive sequence allocated under head lock; server time; metadata is an
  allowlisted object of safe codes/digests/references, never contract text, raw
  rejection reasons, bearer tokens, provider responses or user-supplied headers.
  Full table is INSERT-only through the trusted transaction insertion path.

### 8.4 Publication order and source-version rules

**PROPOSED DESIGN:** Persist the immutable artifact, approval-version material
registry and two designated party rows **at draft publication**, then create/update
the real head. These rows have registration_state UNREGISTERED and no V5 approval
record. Review grants can now reference a real revision BEFORE V5 registration,
avoiding a review-FK/registration circular dependency. Registration validates the
grant and creates PENDING_REVIEW + V5 CREATED audit atomically; no implicit party
approval occurs. New revisions retain immutable prior artifacts/decisions/audit.

**PROPOSED DESIGN:** `cf_project_bindings.source_version` is monotonic, independent
of timestamps. Relevant changes increment it in the SAME transaction: scope/title,
budget/currency, project/line-item dates, planned deliverable content, milestone
content/links, designated party/profile identity values included in the snapshot,
and original agreement/version/facts. Invitations/membership/reviewer permissions
also trigger access/review revalidation; party changes additionally change source
version. Never use updated_at as a counter or reuse a version after rollback/restart.

**PROPOSED DESIGN:** Core must identify EVERY source mutation path: Express
project/invitation/assignment endpoints, WorkBridge adapter writes, imports, jobs,
admin/SQL changes and child-table changes. Install reviewed database triggers on
the ACTUAL participating Core tables after their relationships are known. Triggers
resolve the real owning Core project, lock the common project coordination row,
and increment its counter. Child relations must map through their actual project
FKs, not compare milestone/agreement IDs to project IDs. Direct DB writes must
not bypass these triggers. CF onboarding creates a binding/counter atomically
while locking the Core project, so concurrent edits cannot evade the first snapshot.

**PROPOSED DESIGN:** Counter gaps are permitted; every increment need not publish
a snapshot. Under the project lock, the adapter creates immutable cf_project_sources
only for a complete validated snapshot of the exact current version. Missing
facts yield INCOMPLETE_SETUP, no fake snapshot. Source changes invalidate relevant
grants/eligibility without rewriting old agreements or historical approvals.
Provider jobs capture version N and compare it again before publishing; N+1 is409.

**REQUIRES DECISION:** Trigger DDL, Core FK targets and exact child-table ownership
paths cannot be written truthfully until Person 1 supplies actual migrations.
Production remains disabled if any mutation path can escape versioning/revocation.

### 8.5 Direct PostgreSQL access, RLS and privileges

**PROPOSED DESIGN:** Python connects over TLS using a dedicated least-privilege
`cf_app` login (NOINHERIT, NOBYPASSRLS, not table owner/superuser), not the browser's
token as a DB password. Use a bounded pool and one request-scoped transaction.
`cf_owner` is a separate NOLOGIN migration owner; `cf_writer` is a tightly scoped
NOLOGIN function-owner role, also NOBYPASSRLS. Secrets stay server-side. No generic
postgres/service_role credential is supplied to CF as the default runtime solution.

**PROPOSED DESIGN:** Revoke schema/table/function privileges from PUBLIC, anon and
authenticated on contractflow_private. Enable and FORCE RLS on EVERY CF table,
including sources/bindings/authorities, not only decisions. CF app receives only
required SELECT and EXECUTE on audited write functions; no unrestricted DML or
TRUNCATE. cf_writer receives narrow DML required by functions, not ownership or
BYPASSRLS. Harden SECURITY DEFINER functions with fixed safe search_path, qualified
identifiers, no caller-controlled dynamic SQL, and EXECUTE only to approved service
roles. Keep schema outside the exposed Supabase Data API unless separately reviewed.

**PROPOSED DESIGN:** Policy families apply by row.project_binding_id and current
verified subject/operation: member-read for authorized designated parties; source
write only through Core authority; approval writes only through decision functions;
review writes only authorized issuer/revoker; audit INSERT only trusted commit
path. Child policies join through exact version/binding FKs, never arbitrary user
body project IDs. Authorities have admin-only management. Core membership lookup
must be an audited nonrecursive function against verified actual relationships;
until it exists, policies deny all. Table grants and policies are both required.

**REQUIRES DECISION:** A direct DB connection does NOT automatically inherit the
browser's Supabase RLS identity. A verified transaction-local subject/session may
be set for defense-in-depth policies, but a custom GUC is not authentication and
is forgeable by a compromised trusted DB credential. Python independently verifies
JWT/session and membership before DB access; reset/SET LOCAL context for each pooled
transaction. Supabase's privileged service_role bypasses RLS, so do not claim
per-user RLS when using such a key. If Core mandates a bypass role, require explicit
security approval, restricted CF functions/data scope, independent Python checks
and credential-compromise acceptance; it is not the preferred plan.
[Official role behavior](https://supabase.com/docs/guides/database/postgres/roles),
[RLS and grants](https://supabase.com/docs/guides/database/postgres/row-level-security).

### 8.6 Audit immutability and retention, per-table policy

**PROPOSED DESIGN:** Revoke UPDATE/DELETE/TRUNCATE on cf_audit from cf_app,
cf_writer and ordinary admin API roles. BEFORE UPDATE/DELETE row triggers and a
BEFORE TRUNCATE statement trigger must RAISE EXCEPTION with an authorization error;
do not use silent DO INSTEAD NOTHING rules. Only a reviewed append function can
INSERT, binding the transaction's exact project/revision/digest, server actor and
sequence. It commits with the corresponding state/review change or not at all.
Add equivalent immutable-material guards for artifacts/sources/agreements/parties/
decisions; only the explicitly mutable state/revocation/counter columns may change
through narrow functions. Database owners can bypass administration controls;
restrict migration credentials and use external backup/audit monitoring, not a
claim of tamper-proofness against superusers.

| Table class | Allowed normal changes | Retention/deletion rule |
|---|---|---|
| bindings / review_authorities | Scoped counters/freeze/authority enablement through trusted functions | No deleting referenced mappings/issuers; retire/tombstone |
| sources / agreement versions / artifacts / approval parties | Insert-only | Keep exact bytes/digests for referenced cycles; no cascade deletion |
| approval_versions / heads | State, registration and CAS/gate changes only; material immutable | Preserve superseded/rejected/both-approved history |
| reviews | New grants; one-way authorized revocation metadata | Retain grant/evidence references used by decisions; expiry is not deletion |
| decisions | Insert-only | Restrict sensitive reason access; never erase audit linkage |
| audit | Trusted INSERT only; modification raises | Append-only, no runtime deletion or raw secrets/text |

**REQUIRES DECISION:** Product/legal/privacy owners must set retention periods,
account-deletion and erasure policy before production. Until approved, no automated
purge job. Separate sensitive reason/profile content from minimal audit references;
any redaction or retention exception requires a privileged reviewed process and
new audit evidence, not silent rewriting. This document makes no legal-retention claim.

### 8.7 Migration and backfill acceptance gates

**PROPOSED DESIGN:** Sequence: verify Core physical schema/role policy; approve
binding/FKs and migration owner; create CF tables/constraints/indexes/roles;
add audited functions/RLS/immutability triggers; add source-mutation hooks; validate
constraints on a disposable database; import only verified artifacts preserving
legacy hashes; enable new policy for new subjects; then mount/roll out. Review
existing data for incomplete setup, invalid identities or legacy review semantics;
quarantine rather than invent missing facts or rehash already-approved records.

**NOT IMPLEMENTED:** No SQL migration, role/policy/function, Supabase change,
database connection, backfill or production PostgreSQL test has been executed.

## 9. Atomic registration, approval and concurrency

**PROPOSED DESIGN:** JWT cryptographic verification/key retrieval happens before
opening the transaction; all decisive DB authority checks occur inside it. Use a
single AsyncSession/UoW shared by source/auth/review/repository adapters. Load
locked data asynchronously, apply the existing synchronous V5 transition callback
to detached immutable records, then persist its result asynchronously. Do not open
a second session inside ReviewVerifier, resolver or repository methods.

**PROPOSED DESIGN:** A common project-binding coordination lock precedes the
numbered steps below to avoid head/project lock inversion. Every related Core
membership/source mutation, review issuance/revocation and CF publication must use
the same coordination order. For multiple heads lock UUIDs in sorted order.

1. Lock cf_approval_heads FOR UPDATE; registration must reference an already
   published real approval-version material row, never create a phantom head.
2. Verify current artifact revision, recompute archive/V5 digests and compare the
   request's correct digest type. A client hash does not replace this computation.
3. Check authoritative Core session/user activity, project membership, source
   counter, original agreement/version and immutable snapshot equality under locks.
   Map the amendment to its binding/Core project through FKs before permission checks.
4. Lock selected review rows and issuer authority. Check exact version/digest/
   source/agreement/policy/risk, current permission, expiry, revocation and required
   machine/human grant combination. Unknown or disputed eligibility fails closed.
5. Look up the request key under the version's unique constraint; compare normalized
   payload, actor and role. Same request returns current state with no new decision
   or audit. Revoked/stale authority is checked BEFORE allowing an old key replay.
6. Resolve CLIENT/FREELANCER from authoritative party rows and current Core access,
   not request role or a name. The party FK additionally enforces exact binding.
7. Apply existing V5 prior-decision/terminal-state rules. REJECTED/BOTH_APPROVED/
   SUPERSEDED cannot accept a new decision; one actor cannot decide twice.
8. Insert one server-ID/UTC decision with exact review references and bound digest.
9. Update only the allowed workflow fields using the existing V5 transition result.
10. Append trusted audit/review-check metadata with the owning revision/project FK
    and next sequence; no sensitive reason/body text is copied into audit.
11. Advance head CAS sequence/gates/current pointer as applicable. For material
    revision registration, supersede the previous cycle and register the new one
    atomically; archive approvals and never carry them into the new cycle.
12. Commit together. Recheck expiry using DB clock_timestamp after lock waits;
    a deferred constraint guard can reject an expired/revoked grant before commit.
    Do not use transaction-start now() as proof that a grant remained valid during
    a long lock wait. No external AI or notification effect occurs inside the UoW.

**PROPOSED DESIGN:** Registration performs the same authority/source/review checks
but creates the initial V5 PENDING_REVIEW/CREATED record rather than a party decision.
Publication of an unregistered draft is not approval. Review rows can exist because
their material revision registry was created at publication, not at registration.
Emit any external event only after commit via a transactional outbox if the team
later authorizes that integration; there is no payment/activation event in scope.

| Race/failure | Proposed deterministic result |
|---|---|
| Concurrent client/freelancer approval | Head lock serializes; second reads first's committed decision, reaches BOTH_APPROVED without lost update |
| Same key + same actor/payload concurrently | One insertion; other returns current status after validation, no duplicate event |
| Same key + different payload/actor | Unique constraint plus payload comparison ->409, never last-write-wins |
| Same party APPROVE vs REJECT | First committed decision wins; other returns409 under V5 rules |
| New revision/source update vs decision | Common project/head locks serialize; stale old digest/version/source fails409; old approvals never count for new subject |
| Review revoke vs decision | Same locks; revoke first blocks decision; decision first is historically valid before revoke. Later actions blocked; no silent deletion |
| Membership/session revoke vs decision | Same Core coordination gate; revoke first denies401/403/404 as appropriate, decision first linearizes before revoke |
| Grant expires while waiting | Re-evaluate actual DB clock after locks; expired grant blocks, no cached valid flag |
| Audit/DB failure or cancellation | Entire transaction rolls back; no success status, partial approval or missing audit |
| Response lost after commit | Caller may replay SAME key; do not invent new key or auto-submit a different approval |
| Serialization/deadlock | Bounded DB-only retry of pure transaction after rechecking all authority/expiry; exhausted ->503; never retry Groq automatically |

**REQUIRES DECISION:** If Core authority lives in an external service that cannot
join/serialize with the Supabase transaction, the claimed revocation guarantee
cannot be implemented merely with HTTP calls. Agree a shared authoritative gate,
revocation epoch or weaker explicitly approved policy; keep approvals disabled
until that decision and race tests exist. A memory/asyncio lock is not a substitute.

## 10. Express proxy and FastAPI API contract

### 10.1 Existing exported Python endpoints

**VERIFIED IN CODE:** Prefix is `/api/v1/contractflow`. All routes depend on
`api/dependencies.py::get_principal/get_runtime`, use strict Pydantic bodies and
safe fixed-code errors. No shared app mount exists. Project/amendment ownership
comes from trusted adapters; the table lists intended own-party permissions, not
a claim that production memberships are connected.

| Method/path after prefix | Request schema and exact fields | Response | Required party permission |
|---|---|---|---|
| POST /contracts/generate | ProjectRequest: project_id, expected_source_version | StoredArtifact CONTRACT | Own authorized project/write |
| POST /agreements/draft | Same ProjectRequest | StoredArtifact AGREEMENT | Own authorized project/write |
| POST /scope/assess | AssessmentRequest: project fields + client_request; optional supporting_context[{id,text}] | StoredArtifact ASSESSMENT | Own project/write; original agreement |
| POST /amendments/generate | AmendmentRequest: project fields + assessment_id UUID, review_reference | StoredArtifact AMENDMENT | Own project/write; reviewed stored OUT_OF_SCOPE assessment |
| POST /amendments/{amendment_id}/register | RegisterRequest: expected_version, expected_digest (archive digest) | ApprovalStatus | Exact amendment owning project/party/write and current reviews |
| POST /amendments/{amendment_id}/decisions | DecisionBody: expected_version, expected_digest (V5 digest), decision APPROVE/REJECT, idempotency_key; optional rejection_reason only for REJECT | ApprovalStatus | Exact own party/write and current reviews |
| GET /amendments/{amendment_id}/status | No body | ApprovalStatus | Own party/read; current code also gates on current reviews |
| GET /amendments/{amendment_id}/history | No body | AuditEvent array | Own party/read; current code also gates on current reviews |

**VERIFIED IN CODE:** API ID strings max128; amendment path IDs UUIDs; versions
positive strict integers; digest64 lowercase hex; client_request max8000 characters;
supporting_context max10; reasons max1000 and no control characters. SafeRoute bounds
actual streamed body bytes at131072. StoredArtifact includes server ID/version,
source, content_digest, UTC time and payload_json (a validated artifact JSON string).
ApprovalStatus includes state, remaining_approvals, digest, review-required flags,
effective=false. Archive and approval digests differ and must not be interchanged.

### 10.2 Proposed gateway contract and error behavior

**PROPOSED DESIGN:** Expose these SAME eight paths at Express unless Person 1's
actual routing convention requires a reviewed mapping. For each path, Express
validates the same request shape, verifies token/current owning project/role,
forwards the original token and allowlisted body/query, and returns the validated
upstream response through an explicit error adapter. Never accept an arbitrary
upstream URL, forward cookies/service keys, or copy browser identity headers.
Python still verifies token, owner, source and policy independently.

**PROPOSED DESIGN:** Ownership lookup for register uses artifact->binding; for
decisions/status/history use head/version->binding->Core project. Express can
perform a minimal authorized join against shared durable metadata; no unauthenticated
Python metadata endpoint or caller-provided project override is introduced.
Unauthorized/nonexistent resources are indistinguishable404 where appropriate.

| Category | Existing FastAPI behavior | Proposed Express behavior |
|---|---|---|
| Missing/invalid bearer | 401 UNAUTHENTICATED, WWW-Authenticate | Preserve401; do not leak token/verification details |
| Visible forbidden/review denial | 403 FORBIDDEN/REVIEW_INVALID | Preserve403 and safe typed action state |
| Hidden/missing resource | 404 NOT_FOUND | Preserve404, no owning-project information leak |
| Stale/source/state/idempotency | 409 STALE_SOURCE/MISSING_AGREEMENT/WORKFLOW_CONFLICT | Preserve409; refresh current snapshot/status, no silent retry |
| Schema/body size | 422 INVALID_REQUEST /413 REQUEST_TOO_LARGE | Same semantic validation/limit before proxying |
| AI invalid/provider failure | 502 PROVIDER_FAILED | Preserve502; no raw provider body |
| Timeout/integration unavailable | 503 PROVIDER_TIMEOUT/UNAVAILABLE/INTEGRATION_UNAVAILABLE | Preserve503; gateway transport failure also503 with generated correlation ID |
| Rate limiting | No module limiter implemented | Proposed429 with bounded Retry-After; never auto-submit approval/AI on behalf of user |
| Incomplete setup/hybrid eligibility | Not implemented as distinct codes | Proposed409 PROJECT_SETUP_INCOMPLETE or REVIEW_PENDING;403 flagged denial; schema/allowlist updates required |

**REQUIRES DECISION:** Actual Core response envelope and auth middleware are not
available; do not claim a guessed `{success,data,error}` contract is existing.
Propose a `ContractFlowErrorAdapter` translating fixed codes into the inspected
Core envelope once supplied. Current CF envelope is `{"error":{"code":"..."}}`.
Unknown/HTML upstream bodies become sanitized503, never parsed as trusted errors.
Keep query/path encoding, status semantics and correlation logs consistent.

**PROPOSED DESIGN:** Initial rate budget: AI5 requests/minute/user and at most2
concurrent per project; decisions/register20/minute/user/project; reads60/minute/
user/project. Enforce gateway plus Python/distributed limiter, with a common
131072-byte body limit on all eight endpoints. These numbers are proposed operational
limits, not current configuration. Preserve individual domain constraints. Configure
route-local parser limits after inspecting Core; do not override all Express APIs.
Use bounded connect/read timeouts consistent with Python's <=300s provider bound;
the gateway must not time out earlier than an intentionally supported generation
window without a documented job/status design. No transparent POST retries.

### 10.3 New read/setup/review interfaces needed by the target UI

**PROPOSED DESIGN:** These routes do NOT exist yet and require Core/API approval:

| Candidate route | Typed purpose / auth | Safety requirement |
|---|---|---|
| GET /api/v1/contractflow/projects/{project_id}/setup | Current source_version, READY/INCOMPLETE_SETUP, missing field codes; authorized project member/party | No caller facts or role claims; read-only |
| GET /api/v1/contractflow/artifacts/{artifact_id} | Authorized immutable revision/digest/facts/proposals/citations | Exact owner lookup; historical integrity and access checks, no silent latest replacement |
| GET /api/v1/contractflow/amendments/{id}/review-status | Typed policy/risk, semantic vs human review, expiry/revocation and eligibility | Membership/read authority independent of approval eligibility; no mutation |
| Internal review issuance/revocation operations | Service or platform reviewer authority only, exact version/digest | Private workload/admin authorization and transaction locking; not a browser grant flag |

**PROPOSED DESIGN:** Current V6 reads deny when reviews are invalid; that cannot
alone support an expired-review UI. Introduce operation-specific READ authorization
and a versioned HTTP status wrapper or the review-status route. Authorized users
may inspect their stale/ineligible artifacts and audit without being allowed to
approve them. Never relax the decision/registration gate. Historical reads must
preserve bytes/digests, enforce CURRENT access and explicitly show staleness.
Removed members/new unrelated project collaborators do not inherit past-party
access; an admin audit-access policy requires separate permission design.

## 11. React/Vite workspace integration

**NOT IMPLEMENTED:** `ProjectDetailView.tsx`, the Express app and the Core frontend
workspace were not found in available Core source. Their paths, state-management
library, routes, existing request helper and design system are unverified. The
requested component name is a user-provided target, not a verified file.

**PROPOSED DESIGN:** Add a ContractFlow panel to the actual Core ProjectDetailView
only with Person 1/frontend owner approval; reuse the single Vite frontend and
existing authenticated Express request layer. No second CF React app or direct
browser access to Python/DB credentials.

| Panel state/action | Backend source/operation | Required UI behavior |
|---|---|---|
| Incomplete setup | Proposed setup DTO | Show exact missing fields and current source version; authorized Core edit form; generation disabled |
| Contract/agreement drafting | Existing generation POSTs | Explicit click, pending/timeout/error; no automatic regeneration loop |
| Immutable facts | Verified StoredArtifact/source snapshot | Read-only parties/budget/currency/dates; editing uses Core setup workflow, not CF body overrides |
| Unresolved terms | Validated domain artifact | Render separately as unresolved, never fill with legal boilerplate |
| Scope request/assessment | Existing scope POST | Label request/context untrusted; show classification, action and exact citations |
| Amendment preview | Artifact/read response | Display exact revision/digest and canonical stored text; no browser formatting change that masquerades as approved content |
| Review status | Proposed typed policy/review DTO | Distinguish machine semantic check, actual human platform review, pending/escalated/expired/revoked states |
| Client/freelancer approval | Existing decision fields | Own-party button only; fetch current immutable content/status, explicit user action and expected digest; other party independent |
| Rejection | REJECT with bounded reason | Explicit decision, safe reason rendering; no later approval in same terminal cycle |
| Audit | Authorized history | Chronological metadata, exact revision, no credentials/raw reasons; show superseded cycles |
| Stale/conflict | 409 typed codes | Refresh context, preserve user explanation text locally as untrusted, require new explicit action; never auto-approve new digest |
| Auth/loading/errors | 401/403/404/429/502/503 | Distinct retry/login/escalation UI; no synthetic success or spinning approval retry |

**PROPOSED DESIGN:** Use escaped text/code rendering for source and AI prose; no
dangerouslySetInnerHTML of model output. UI may display a digest but must not
invent an authority hash from an edited browser copy. Idempotency keys remain
stable for the SAME submitted action across uncertain network retries; changed
decision/version uses a new explicit action. Client visibility hints never replace
server authorization. No UI action calls PayPal or marks effective=true.

**REQUIRES DECISION:** A manual authenticated approve click records that party's
attestation on the digest, not scientific proof they inspected/understood it.
Agree any stronger confirmation/MFA/view-receipt requirement with Core; such a
receipt is access evidence, never a machine-created human review grant.

## 12. WorkBridge compatibility and minimum trusted source contract

**VERIFIED IN CODE:** Inspected WorkBridge `backend/database.py` uses
`sqlite:///./workbridge.db`, sync SessionLocal/get_db. `backend/main.py` creates
tables at import and routes with DB dependencies; no real auth dependency is
present in the inspected routes. Models use integer project IDs, names and role
strings, Float budgets, mutable contract_ref, uploaded deliverable file versions,
and due_date/payment-amount milestones. ContractFlow calls none of its hooks.

| Evidence | Compatibility gap | Consequence |
|---|---|---|
| VERIFIED IN CODE | WB integer project IDs versus CF strings/UUID artifacts and future Core IDs | Namespace mapping required; no equality assumption |
| VERIFIED IN CODE | Member names/role fields instead of authenticated subject relationships | Cannot authorize parties from WB data |
| VERIFIED IN CODE | Float budget; missing currency/project dates/planned links | Cannot construct complete ProjectInput by defaults |
| VERIFIED IN CODE | Mutable contract_ref/file revision | Not an immutable agreement/source/amendment revision |
| VERIFIED IN CODE | SQLite, separate sessions, import-time create_all | Not Supabase persistence or common approval UoW |
| VERIFIED IN CODE | POST /api/contracts/approved auto-creates a project | Bootstrap mismatch: CF needs trusted pre-contract requirements first |
| VERIFIED IN CODE | GET /api/milestones/approved advertises payout handoff | Not legal effect or CF approval/payment authority |
| PROPOSED DESIGN | Core-authoritative source adapter, no SQLite reuse | WB compatibility through approved Core mapping, not direct unauthenticated API trust |

**PROPOSED DESIGN:** Minimum adapter: `WorkBridgeSource.load(project_id, principal)`
returns a complete authorized immutable SourceSnapshot with explicit monotonic
source_version, exact designated party IDs, validated ProjectInput and optional
original AgreementSnapshot. It must resolve actual owning Core project and current
permissions; missing/hidden project fails404, incomplete setup blocks generation,
source mismatch fails409. Names, payout amounts, created_at and file upload versions
must not be promoted into trusted identity/contract terms/version values.

**REQUIRES DECISION:** The existing port name WorkBridgeSource does not require
that WB be the authoritative DB owner. Under the target architecture, implement
it over trusted Core/Supabase records and agree a later neutral name alias if
needed. Core/WorkBridge must settle pre-contract project creation and planned-
deliverable lifecycle. Do not connect WB's SQLite DB or unauthenticated hooks,
and do not call POST /api/contracts/approved automatically after BOTH_APPROVED.

## 13. Phased implementation, file ownership and rollback

**VERIFIED IN CODE:** Current phase is audit/planning only. The filenames below
are proposed changes for a later approved implementation, not files created here.

**REQUIRES DECISION:** `<CORE_API_ROOT>`, `<CORE_FRONTEND_ROOT>`,
`<CORE_MIGRATION_ROOT>` and the existing Core app/middleware/project/invitation
paths are UNRESOLVED placeholders. Do not present them as discovered paths or
modify them before Person 1 supplies/reviews the actual checkout.

| Phase | Proposed files / owner | Dependencies | Acceptance and tests | Risks / rollback |
|---|---|---|---|---|
| Phase 1 gate: interface alignment | This plan; Core actual auth/DDL/project/invitation/frontend review; joint owners | Person 1 local/pushed implementation and schema | Fill physical mapping, signing config and Core paths; approve hybrid/DB policy | No implementation while mappings unresolved |
| Phase 2: Python service + PostgreSQL | CF: deployment/app.py, integrations/supabase_auth.py, integrations/core_source.py, integrations/review_policy.py, persistence/models.py, persistence/postgres_repository.py, persistence/postgres_uow.py, persistence/review_repository.py; update api/dependencies.py, api/errors.py, integrations/workflow.py, integrations/contracts.py; versioned HTTP schemas as approved | Verified Core DDL/roles/source hooks, actual Supabase config, authoritative review policy | JWT/security tests; immutable/durable artifacts; real review/revocation; DB rollback/races; keep all existing tests | New service isolated and unmounted; feature disabled on failure; additive reviewed migrations, no dropping old data |
| Phase 2 shared migration work | Core/DB owner: <CORE_MIGRATION_ROOT>/<approved-sequence>_contractflow.sql plus actual Core source/membership mutation hooks | Physical FK/ID/version mapping and privilege review | All proposed constraints/RLS/guards/roles and transaction functions exercised on disposable PostgreSQL | Requires explicit Core approval; restore compatible schema/code, never destructive rollback of audit |
| Phase 3: Express proxy/auth | Core-owned actual app/router registration and auth/project/invitation services; candidates <CORE_API_ROOT>/routes/contractflow.ts, services/contractflowProxy.ts, services/contractflowErrorAdapter.ts | Stable Python service and agreed Core request/error convention | Original token forwarded, both layers verify auth, ownership resolved by stored FK, body/rate/timeout tests | Register behind explicit rollout flag; disable proxy without changing other routes; do not auto-retry POST |
| Phase 4: React workspace | Frontend owner: actual ProjectDetailView.tsx plus proposed <CORE_FRONTEND_ROOT>/src/features/contractflow/{ContractFlowPanel.tsx,api.ts,types.ts}; actual shared request helper | Core API/error schema and permissions; proposed setup/artifact/review reads | Incomplete setup, preview/citations, machine vs human review, distinct approval/rejection, audit, stale/expired errors | Guarded panel rollout; preserve source data, no browser secrets; revert UI access independently |
| Phase 5: automated/DB/security/E2E | CF tests/test_supabase_auth.py, test_postgres_approval.py, test_hybrid_reviews.py; Core proxy tests; frontend E2E files under actual test conventions | Real disposable PG + approved Supabase test config, no production data | Verification matrix below; service restart, unique-key/race/RLS/audit attacks; full CF regression suite | Block release on failures; no passing-memory substitute for PostgreSQL evidence |
| Phase 6: deployment/ops | CF deployment files and Core-owned infra/secret/runtime config; paths decided by platform owner | Completed gates, pool/TLS policy, monitoring, backups and app ownership | Real JWT/key rotation, controlled integration smoke test, rollback drill, immutable audit and no payment/activation | Stage/canary; disable proxy and revoke CF service credentials on incident; preserve database evidence |

**PROPOSED DESIGN:** V1–V5 domain services are reused rather than rewritten. Any
necessary versioned policy/DTO adapter change must preserve old literal flags,
canonical hash algorithms and snapshot bytes. Never add default model fields that
silently alter old serialized V5 approval digests. New representation/policy is
versioned server-side; legacy cycles retain their stricter original policy.

**REQUIRES DECISION:** Shared edits requiring Person 1/DB owner approval include
Express app/router/auth middleware, project/invitation mutations, Supabase migrations,
RLS/grants/functions, source-version triggers, frontend ProjectDetailView and shared
API helper, deployment secrets and gateway networking. This plan assigns no work
to a teammate branch without that agreement.

## 14. Verification matrix — existing evidence versus future acceptance

**VERIFIED BY TEST:** Existing evidence refers to previously executed offline
tests at unchanged source, not a new run in this task. None of the proposed
JWT/PostgreSQL/Express/frontend/hybrid checks below has been executed here.

| Scenario | Existing evidence | Required proposed production test |
|---|---|---|
| Valid/invalid JWTs, bad alg/issuer/audience/kid/signature/sub | NOT IMPLEMENTED: no real JWT verifier | Independent Express + Python tests; reject algorithm confusion, unknown key, identity headers and service keys |
| Expired/revoked session/user, clock skew, rotated keys | NOT IMPLEMENTED | Actual trusted session policy; key refresh/outage; revoke racing approval; DB clock after lock waits |
| Nonmember/cross-project access | VERIFIED BY TEST: test_v6_api.py synthetic-outsider/unknown-resource tests | Real memberships and amendment->version->binding->Core relation; hidden404, no body project override |
| Missing deliverables/dates/currency and unaccepted party | VERIFIED BY TEST: test_v6_boundaries.py incomplete trusted source tests | INCOMPLETE_SETUP through Core UI/API; no generation/provider call until complete |
| Stale source versions | VERIFIED BY TEST: test_v6_boundaries.py stale source/change-during-generation | DB-trigger increments on every actual mutation path, including direct SQL/import and child edits |
| Changed amendment digest / legacy reads | VERIFIED BY TEST: test_v5_workflow.py and test_v4_professional_rendering.py | Durable immutable rows; preserve old canonical hashes after restart/backfill |
| Missing/stale/revoked/wrong-bound human grants | VERIFIED BY TEST: test_v6_integration.py fake reviews | Real review authority, exact composite FKs and transaction revocation races |
| Standard machine semantic path | NOT IMPLEMENTED | Human=false machine grant, correct issuer/evidence, no auto decision, both parties independently approve |
| Flagged/disputed human path | NOT IMPLEMENTED | Machine-only denied; unauthorized reviewer denied; human grant required; reviewer unavailable stays blocked |
| Duplicate/conflicting idempotency keys | VERIFIED BY TEST: V5/V6 fake repositories | Independent DB sessions; same key replay no extra row/event; payload/actor conflict409 |
| Simultaneous client/freelancer or conflicting decisions | VERIFIED BY TEST: V5 threads/V6 asyncio fake | Multi-worker PG row locks and unique constraints; one valid decision per party, no lost update |
| Superseded/rejected revision | VERIFIED BY TEST: V5 state/revision and V6 tests | Durable stale/terminal denial and no old approvals reused under new review policy |
| Audit UPDATE/DELETE/TRUNCATE attempts | NOT IMPLEMENTED: immutable Python models are not DB triggers | Every runtime/ordinary role receives exception, not silent success; no audit rewrite/cascade |
| PostgreSQL rollback/audit atomicity | VERIFIED BY TEST only for fake memory failure injection | Real DB failure after decision insert and before audit/head write; total rollback |
| Service restart and durable persistence | NOT IMPLEMENTED | Restart workers; facts/decisions/reviews/history/digests remain exact |
| Review/membership/source revoke races | NOT IMPLEMENTED in real DB | Two sessions contend on same common gate; deterministic before/after commit outcome |
| RLS/DB privilege isolation | NOT IMPLEMENTED | Direct cf_app cannot bypass subject/membership path or use raw DML; browser/Data API cannot access private schema |
| Express/FastAPI errors/body/rate limits | VERIFIED BY TEST only for Python SafeRoute | Real Core envelope mapping; byte limits, timeouts, malformed upstream,429; no secret echo or automatic POST retry |
| Frontend dual-party workflow | NOT IMPLEMENTED | Real two sessions/users, exact preview digest, independent decisions, stale/expired/revoked states and no automatic payment |
| Source invitation/member lifecycle | NOT IMPLEMENTED | Pending invite grants none, accepted authoritative assignment reflected, removal blocks writes/reads per policy |

**PROPOSED DESIGN:** Maintain all existing offline regressions; add isolated real
PostgreSQL and gateway/browser suites with separate evidence reports. Synthetic
tests may not assert live Supabase/JWT/DB readiness. Do not call Groq/PayPal in
automated regression tests; any controlled live test needs explicit authorization
and remains separate from semantic/legal correctness claims.

## 15. Decisions, blockers, rollback and approval boundary

| Evidence | Decision/blocker | Required resolution |
|---|---|---|
| REQUIRES DECISION | Person 1 local Core not available | Supply actual commit/checkout or push implementation; inspect migrations/auth/project/invitation/UI before assigning paths/FKs |
| REQUIRES DECISION | Supabase configuration not inspected | Confirm exact project, asymmetric/legacy JWT mode, issuer/audience, session policy and access roles |
| REQUIRES DECISION | Project/user/agreement physical key mapping | Approve binding strategy or replace with verified actual FKs; never ship guessed relationships |
| REQUIRES DECISION | Hybrid review authority and risk policy | Approve machine/human distinction, reviewer permission, grant TTLs, escalation and late-dispute freeze/replacement policy |
| REQUIRES DECISION | Read/approval permission separation | Agree authorized stale-history/review-status access without relaxing decision guards |
| REQUIRES DECISION | DB source/membership mutation coverage | Provide actual trigger targets, transaction coordination and reviewed session/authority gates |
| REQUIRES DECISION | Retention/account deletion | Approve protected append-only history versus private content erasure; no automatic cascade/purge |
| REQUIRES DECISION | Express/UI file paths and envelope | Inspect real workspace conventions; approve rate limits, body/timeouts and new read endpoints |
| NOT IMPLEMENTED | Production mounting/persistence/hybrid/JWT/React | Requires later approved implementation and real integration tests, not this plan |

**PROPOSED DESIGN:** Rollout gates remain OFF until all blockers pass. Deploy
additive schema/compatible readers first; import only verified snapshots and retain
legacy policy. Then isolated Python, reviewed proxy, guarded UI and staged traffic.
Rollback disables the proxy/new policy, revokes affected service authority and
stops new writes while preserving artifacts/audit. Restore compatible binaries,
not old database contents that would erase committed decisions. Never fabricate
success after partial outages or reassign old approvals to another digest.

**VERIFIED IN CODE:** Files read as authority include `README.md`,
`CONTRACTFLOW_IMPLEMENTATION_REPORT.md`, `V6_HANDOFF.md`,
`persistence/POSTGRESQL_DESIGN.md`, `schemas.py`, `api/{router,schemas,dependencies,errors}.py`,
`integrations/{contracts,workflow}.py`, `persistence/artifacts.py`,
`v4/{schemas,review,service,renderer,validation}.py`,
`v5/{schemas,authorization,service,repository,states}.py` and the V5/V6 tests.
Remote WorkBridge `backend/{database,models,schemas,main}.py` and branch trees were
inspected read-only; Core's fetched tree contains no implementation files.

**VERIFIED IN CODE:** Public Supabase documentation was read for provider facts,
not as proof of this project's settings. No live Supabase project, environment
secret, database or deployed API was queried or modified. No code, schema, test,
migration or frontend file was created/changed in this task.

**PROPOSED DESIGN:** This plan is the approval deliverable. Stop here: no Git
commit/push, merge/rebase, branch switch, application implementation or Supabase
change is authorized by producing it. After Core supplies the missing evidence,
review and amend the blocked mappings before approving Phase 2 implementation.
