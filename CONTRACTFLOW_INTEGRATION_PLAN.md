# Freelanker — ContractFlow Integration Plan (Phase 1.1 Corrective Revision)

**Revision Date:** November 10, 2026  
**Module:** Person 2 — ContractFlow Integration  
**Status:** Phase 1.1 Corrective Revision Complete (Awaiting Approval Before Implementation)  
**Strict Scope Rule:** Architecture, code audit, and planning only. No database migrations, application edits, or commits.

---

## 1. Verified Current Git State

| Item | Verified Value | Evidence / Verification Method |
| :--- | :--- | :--- |
| **Core Platform Repository** | `Omcodesk/Freelanker` | Verified local git tracking |
| **Active Branch** | `feature/core-platform` | Verified `git branch --show-current` |
| **Core Platform Commit** | `ce4d277` | `ce4d277 feat(frontend): implement project dashboard, creation modal, workspace details, and invitation acceptance flow` |
| **Core Working Tree** | Clean working tree | 7 commits ahead of origin. Trailing newline diffs only. |
| **ContractFlow Remote Branch** | `origin/feature/contractflow` | Verified `git fetch origin` |
| **ContractFlow Commit** | `0608adf` / `f6cd74f` | Tip is `f6cd74f docs: add report`. Codebase verified at `0608adf`. 107 Python files, 902 passing tests in offline execution. |
| **ContractFlow Module Path** | `backend/app/modules/contractflow/` | Verified via `git ls-tree origin/feature/contractflow` |
| **WorkBridge Remote Branch** | `origin/workbridge` (`d5e7af5`) | Standalone FastAPI + SQLite. **Strictly isolated.** |
| **Main Branch** | `origin/main` (`a873399`) | Protected initial baseline. Unmodified. |

> [!NOTE]
> **Verification Status Indicator:**  
> - **[VERIFIED - CODE]**: Confirmed by inspecting existing repository source code.  
> - **[PROPOSED - DESIGN]**: New architectural component or schema proposed for Phase 2 implementation.

---

## 2. Exact Files to Reuse

### From ContractFlow (`origin/feature/contractflow`) [VERIFIED - CODE]:
ContractFlow's Python domain logic will be reused as an isolated microservice **without rewriting it in TypeScript**:
1. **V1 Contract Generation:**
   - `schemas.py`: Extractive models (`ProjectInput`, `Party`, `Deliverable`, `Milestone`, `ContractDraft`, `WordingSection`, `ProviderOutput`, `DRAFT_LABEL`, `UNRESOLVED_TERMS`).
   - `service.py`: `ContractGenerationService` (verbatim extraction).
   - `prompts.py`: V1 LLM extraction prompts.
2. **V2 Agreement Drafting:**
   - `v2/schemas.py`, `v2/service.py`, `v2/validation.py`, `v2/prompts.py`, `v2/render.py`: Controlled paraphrasing, citation references, and agreement draft assembly.
3. **V3 Scope Change Detection:**
   - `v3/schemas.py`, `v3/service.py`, `v3/validation.py`, `v3/prompts.py`, `v3/quantities.py`, `v3/sources.py`, `v3/diagnostics.py`: AI classification into `IN_SCOPE`, `OUT_OF_SCOPE`, `NEEDS_CLARIFICATION` with cited evidence.
4. **V4 Amendment Generation:**
   - `v4/schemas.py`, `v4/service.py`, `v4/validation.py`, `v4/renderer.py`, `v4/review.py`, `v4/prompts.py`, `v4/wording_quality.py`: Inactive proposed amendment drafts, professional rendering, citation validation, and `ReviewVerifier`.
5. **V5 Dual-Party Approval Workflow:**
   - `v5/schemas.py`: `ApprovalSubject`, `DecisionRequest`, `TrustedActor`, `DecisionRecord`, `AuditEvent`, `ApprovalRecord`, `ApprovalStatus`, `canonical_digest`.
   - `v5/service.py`: `ApprovalWorkflowService`.
   - `v5/states.py`: Transition state machine (`PENDING_REVIEW` -> `PARTIALLY_APPROVED` -> `BOTH_APPROVED` / `REJECTED` / `SUPERSEDED`).
   - `v5/audit.py`, `v5/validation.py`, `v5/errors.py`: Canonical audit events and domain error definitions.
6. **V6 Integration Boundaries & Router:**
   - `integrations/contracts.py`: Integration protocols (`SharedAuth`, `WorkBridgeSource`, `ReviewGrant`, `AmendmentReviews`, `ApprovalTransactions`, `Principal`, `SourceSnapshot`).
   - `integrations/workflow.py`: `IntegrationRuntime` and `IntegrationActorResolver`.
   - `persistence/artifacts.py`: `StoredArtifact`, `ArtifactRepository` protocol, SHA-256 digest.
   - `api/router.py`: FastAPI `APIRouter` with prefix `/api/v1/contractflow` (8 exported endpoints).
   - `api/schemas.py`, `api/dependencies.py`, `api/errors.py`: Request schemas and `SafeRoute` envelope.
   - `providers/base.py` & `providers/groq.py`: LLM provider protocol and live Groq implementation.
   - `config.py` & `errors.py`: Configuration and base exceptions.

### From Core Platform (`feature/core-platform`) [VERIFIED - CODE]:
1. **Backend Infrastructure:**
   - `backend/src/app.ts`, `backend/src/index.ts`: Express application entry and routing.
   - `backend/src/middleware/auth.ts`: Supabase JWT verification (`requireAuth`).
   - `backend/src/middleware/rateLimiter.ts`: Sliding-window rate limiter.
   - `backend/src/lib/supabase.ts`, `backend/src/config/env.ts`: Supabase client and environment variables.
   - `backend/src/routes/project.route.ts`, `invitation.route.ts`, `auth.route.ts`: Existing project and invitation APIs.
2. **Frontend UI & Infrastructure:**
   - `frontend/src/App.tsx`, `AppShell.tsx`, `router.tsx`: History-based client routing.
   - `frontend/src/features/projects/ProjectDetailView.tsx`: Workspace view for project details and collaboration.
   - `frontend/src/features/projects/ProjectDashboard.tsx`, `CreateProjectModal.tsx`: Project listing and creation.
   - `frontend/src/features/auth/AuthContext.tsx`, `AuthModal.tsx`: Supabase session management.
3. **Database Schema:**
   - `database/migrations/001_initial_schema.sql`: 15 tables, RLS policies, and database triggers.

---

## 3. Exact Files to Create or Modify

### A. Python ContractFlow Service (`services/contractflow/`) [PROPOSED - DESIGN]
*To create by porting Person 2's module and adding real PostgreSQL adapters:*
- **Copy:** `backend/app/modules/contractflow/` -> `services/contractflow/src/contractflow/` (unmodified domain logic).
- **Create:** `services/contractflow/src/main.py`: Production FastAPI server entry point.
- **Create:** `services/contractflow/src/adapters/auth.py`: `SupabasePostgresAuth` implementing `SharedAuth` (verifying Supabase JWT + PostgreSQL project membership).
- **Create:** `services/contractflow/src/adapters/source.py`: `SupabaseCoreSource` implementing `WorkBridgeSource` (loading authoritative projects, members, deliverables, milestones, and agreements from PostgreSQL).
- **Create:** `services/contractflow/src/adapters/artifacts.py`: `PostgresArtifactRepository` implementing `ArtifactRepository` (`cf_artifacts` table).
- **Create:** `services/contractflow/src/adapters/approvals.py`: `PostgresApprovalRepository` implementing `ApprovalRepository` (`cf_approval_heads`, `cf_approval_versions`, `cf_decisions`, and `cf_audit` tables).
- **Create:** `services/contractflow/src/adapters/transactions.py`: `PostgresApprovalTransactions` implementing `ApprovalTransactions` (atomic PostgreSQL transaction with row-level locks).
- **Create:** `services/contractflow/src/adapters/reviews.py`: `PostgresReviewRepository` implementing `AmendmentReviews` and `ReviewVerifier` (`cf_reviews` table).
- **Create:** `services/contractflow/requirements.txt`: Python dependencies (`fastapi`, `uvicorn`, `pydantic`, `asyncpg`, `pyjwt`, `cryptography`, `groq`, `pytest`, `httpx`).

### B. Core Express Backend (`backend/`) [PROPOSED - DESIGN]
*To modify and create proxy and authorization routes:*
- **Modify:** `backend/src/app.ts`: Mount ContractFlow proxy router at `/api/contractflow`.
- **Modify:** `backend/src/config/env.ts`: Add `CONTRACTFLOW_SERVICE_URL` (default `http://127.0.0.1:8000`).
- **Create:** `backend/src/routes/contractflow.route.ts`: Express routes with `requireAuth` and explicit owning project resolution.
- **Create:** `backend/src/controllers/contractflow.controller.ts`: Handling project lookup, membership authorization, and proxy forwarding.
- **Create:** `backend/src/services/contractflowProxy.service.ts`: HTTP client talking to FastAPI with correlation IDs and timeouts.
- **Modify:** `backend/src/types/index.ts`: Add ContractFlow response and request DTO interfaces.

### C. Database Migrations (`database/migrations/`) [PROPOSED - DESIGN]
*To prepare for future migration (NOT executed in Phase 1):*
- **Create:** `database/migrations/002_contractflow_schema.sql`: Executable PostgreSQL DDL adding `source_version` to `public.projects`, creating `cf_artifacts`, `cf_approval_heads`, `cf_approval_versions`, `cf_decisions`, `cf_audit`, `cf_reviews`, composite FKs, explicit privileges, append-only triggers, and RLS policies.

### D. Frontend (`frontend/src/`) [PROPOSED - DESIGN]
*To enhance the project workspace with ContractFlow tabs and modals:*
- **Create:** `frontend/src/features/contractflow/AgreementDraftCard.tsx`: AI contract/agreement viewer, clauses, unresolved terms banner, and **Incomplete Setup State**.
- **Create:** `frontend/src/features/contractflow/ScopeAssessmentModal.tsx`: Scope change request form with AI evidence citations display.
- **Create:** `frontend/src/features/contractflow/AmendmentApprovalCard.tsx`: Dual-party approval checklist, decision modal (Approve / Reject with reason), and audit history drawer.
- **Create:** `frontend/src/services/contractflowService.ts`: API client talking to Express `/api/contractflow` endpoints.
- **Modify:** `frontend/src/features/projects/ProjectDetailView.tsx`: Integrate ContractFlow tabs into the project workspace.
- **Modify:** `frontend/src/types/index.ts`: Add TypeScript types for ContractFlow models.

---

## 4. Proposed Final Folder Structure

```text
Freelanker/
├── backend/                              # Express application API & Auth gateway (Port 4000)
│   ├── src/
│   │   ├── config/                       # env.ts, supabase.ts
│   │   ├── controllers/                  # auth, project, invitation, contractflow.controller.ts
│   │   ├── middleware/                   # auth.ts, rateLimiter.ts, errorHandler.ts
│   │   ├── routes/                       # health, auth, project, invitation, contractflow.route.ts
│   │   ├── services/                     # project, invitation, contractflowProxy.service.ts
│   │   ├── types/                        # shared TypeScript contracts
│   │   ├── app.ts                        # Express app setup
│   │   └── index.ts                      # Express HTTP listener
│   └── package.json
│
├── services/
│   └── contractflow/                     # ContractFlow Python FastAPI Service (Port 8000)
│       ├── requirements.txt
│       └── src/
│           ├── main.py                   # FastAPI server entry point & runtime initialization
│           ├── adapters/                 # Real PostgreSQL and Supabase production adapters
│           │   ├── auth.py               # SupabasePostgresAuth (implements SharedAuth)
│           │   ├── source.py             # SupabaseCoreSource (implements WorkBridgeSource)
│           │   ├── artifacts.py          # PostgresArtifactRepository (implements ArtifactRepository)
│           │   ├── approvals.py          # PostgresApprovalRepository (implements ApprovalRepository)
│           │   ├── transactions.py       # PostgresApprovalTransactions (implements ApprovalTransactions)
│           │   └── reviews.py            # PostgresReviewRepository (implements AmendmentReviews & ReviewVerifier)
│           └── contractflow/             # Person 2's unmodified Python module
│               ├── api/                  # router.py, schemas.py, dependencies.py, errors.py
│               ├── integrations/         # contracts.py, workflow.py
│               ├── persistence/          # artifacts.py, POSTGRESQL_DESIGN.md
│               ├── providers/            # base.py, groq.py
│               ├── v2/                   # Agreement draft service & validation
│               ├── v3/                   # Scope change detection service
│               ├── v4/                   # Amendment generation service & renderer
│               ├── v5/                   # Dual-party approval workflow & audit
│               ├── service.py            # V1 contract generation service
│               ├── schemas.py            # ProjectInput, Deliverable, Milestone
│               ├── config.py
│               └── tests/                # 900+ offline unit/integration tests
│
├── frontend/                             # React + Vite + Tailwind Single-Page App (Port 5173)
│   ├── src/
│   │   ├── components/                   # AppShell, Button, Input, Modal
│   │   ├── features/
│   │   │   ├── auth/                     # AuthContext, AuthModal
│   │   │   ├── projects/                 # ProjectDashboard, ProjectDetailView, CreateProjectModal
│   │   │   └── contractflow/             # AgreementDraftCard, ScopeAssessmentModal, AmendmentApprovalCard
│   │   ├── lib/                          # router.tsx, supabase.ts
│   │   ├── services/                     # authService, projectService, contractflowService.ts
│   │   └── types/                        # TypeScript DTOs
│   └── package.json
│
├── database/
│   └── migrations/
│       ├── 001_initial_schema.sql        # Core Platform 15 tables (applied)
│       └── 002_contractflow_schema.sql   # ContractFlow tables & constraints (prepared)
│
└── docs/
    ├── PRD.md
    ├── DATABASE_SCHEMA.md
    ├── DATABASE_SECURITY.md
    ├── API_CONTRACTS.md
    ├── CONTRACTFLOW_INTEGRATION_PLAN.md
    └── PHASE_1_1_REVIEW.md
```

---

## 5. Core-to-ContractFlow Data Mapping

ContractFlow's `ProjectInput` enforces strict extractive domain invariants. In accordance with corrective issue 1, **we do NOT invent default terms, dummy deliverables, or 30-day deadlines**.

### Field-by-Field Mapping Matrix

| ContractFlow `ProjectInput` Field | Type & Validation Rules [VERIFIED - CODE] | Core Platform Source [VERIFIED - CODE] | Mapping & Validation Rule [PROPOSED - DESIGN] |
| :--- | :--- | :--- | :--- |
| `project_id` | `str`, min 1, max 128 | `public.projects.id` | String representation of project UUID. |
| `title` | `str`, min 1, max 4000 | `public.projects.title` | Direct 1:1 copy. |
| `client` | `Party(id, name)` | `public.projects.client_id` + `public.profiles` | `client.id = profiles.id::text`, `client.name = profiles.display_name`. |
| `freelancer` | `Party(id, name)` | `public.projects.freelancer_id` + `public.profiles` | `freelancer.id = profiles.id::text`, `freelancer.name = profiles.display_name`. |
| `scope` | `str`, min 1, max 4000 | `public.projects.description` | Direct copy from project description (or `agreements.scope_of_work`). |
| `budget` | `Decimal`, gt 0, max 18 digits, 4 dec | `public.projects.total_budget` | Decimal value from `NUMERIC(12,2)`. Required `> 0`. |
| `currency` | `str`, pattern `^[A-Z]{3}$` | `public.projects.currency` | 3-letter currency code (e.g. `'USD'`). |
| `start_date` | `date` | `public.agreements.start_date` or milestone earliest | **Explicit date required.** If missing, contract generation is rejected. |
| `deadline` | `date`, must be `>= start_date` | `public.agreements.end_date` or milestone max | **Explicit date required.** If missing, contract generation is rejected. |
| `deliverables` | `tuple[Deliverable, ...]`, length 1–99 | `public.milestones` & planned deliverables | **Explicit planned items required.** Each must have `id`, `description`, and `deadline` within project dates. |
| `milestones` | `tuple[Milestone, ...]`, length 1–99 | `public.milestones` | **Explicit planned items required.** Each has `id`, `description`, `deadline`, and valid `deliverable_ids`. |

### Handling Incomplete Project Terms (Frontend Setup State)
1. **No Synthetic Fallback:** If `public.projects` lacks explicit deliverables, milestones, start date, or deadline, backend adapter `SupabaseCoreSource.load()` raises `IntegrationError("INVALID_SOURCE")`.
2. **Frontend Incomplete Setup State:**
   - In `ProjectDetailView.tsx`, if the project status is `awaiting_agreement` but deliverables/milestones have not been configured, the UI displays an **"Agreement Setup Required"** banner.
   - It prompts the client and freelancer: *"Please define the project deliverables, milestones, and target deadlines before generating the legal agreement draft."*
   - The "Generate Agreement Draft" button remains disabled until valid terms are recorded.

### Explicit Monotonic Source Versioning
Instead of deriving versions from timestamps, `public.projects` will have an explicit monotonic integer column:
```sql
ALTER TABLE public.projects 
ADD COLUMN IF NOT EXISTS source_version INT NOT NULL DEFAULT 1 CHECK (source_version >= 1);
```
- **Increment Rules:** A database trigger or service transaction increments `source_version = source_version + 1` whenever:
  - Project scope (`description`), budget (`total_budget`), currency, start date, or deadline changes.
  - A milestone or planned deliverable is added, updated, or removed.
- **Snapshot Validation:**
  - Client requests specify `expected_source_version`.
  - `SupabaseCoreSource.load()` verifies that the database `source_version` matches `expected_source_version`. If mismatched, it fails closed with `STALE_SOURCE` (409 Conflict).
  - During AI generation (which takes several seconds), the service checks the current database `source_version` at commit time. If the source version incremented concurrently, the save is aborted with `STALE_SOURCE`.

---

## 6. Complete Authentication and Authorization Architecture

### A. FastAPI Supabase JWT Verification Requirements [PROPOSED - DESIGN]
The ContractFlow service independently validates Supabase JWTs without calling Express:
1. **Header Inspection:** Reads `Authorization: Bearer <jwt>` (rejects if missing, not Bearer, or length > 4096 bytes).
2. **Cryptographic Signature Verification:**
   - Validates signature using `SUPABASE_JWT_SECRET` (via HMAC-SHA256) or Supabase JWKS public keys (RS256).
   - Python library: `PyJWT` with explicit algorithm selection (`algorithms=["HS256"]` or `["RS256"]`).
3. **Claims Validation:**
   - `iss`: Must match Supabase project auth issuer `https://<project-ref>.supabase.co/auth/v1`.
   - `aud`: Must equal `'authenticated'`.
   - `exp`: Must be in the future (rejects expired tokens; maximum clock skew allowance: 60 seconds).
   - `nbf` / `iat`: Must be in the past (clock skew allowance: 60 seconds).
   - `sub`: Must be a valid UUID string representing the Supabase user ID.
4. **Principal Construction:**
   - Creates `Principal(user_id=sub, boundary="CONTRACTFLOW-V6-SHARED-IDENTITY")`.

### B. Two-Layer Access Control Model
Do **NOT** assume direct PostgreSQL connections automatically enforce Supabase user-level RLS:
1. **Application-Level Authorization (Python Service):**
   - Python connects to Supabase PostgreSQL using dedicated application credentials.
   - For every operation, `SharedAuth.authorize(principal, project_id, agreement_id, write=...)` queries `public.project_members` to verify that `principal.user_id` belongs to `project_id`.
   - If the user is not a member -> `IntegrationError("FORBIDDEN")` (HTTP 403).
   - In `IntegrationActorResolver`, the actor's role (`CLIENT` vs `FREELANCER`) is derived strictly by matching `principal.user_id` against `source.project.client.id` and `source.project.freelancer.id`.
2. **Database-Level Privileges & RLS (Direct DB Security):**
   - Tables carry explicit PostgreSQL `GRANT` and `REVOKE` statements (see Section 7).
   - Supabase PostgREST client queries are bound by RLS policies using `auth.uid()`.

### C. Amendment Route Project Resolution [PROPOSED - DESIGN]
When requests target `/api/contractflow/amendments/:amendmentId/*`:
1. The route does not receive `:projectId` directly.
2. The controller **must resolve the owning project before evaluating membership**:
   ```sql
   SELECT a.project_id 
   FROM public.cf_approval_versions v
   JOIN public.agreements a ON a.id = v.original_agreement_id
   WHERE v.amendment_id = $1
   LIMIT 1;
   ```
3. If no row matches -> return 404 Not Found (`AMENDMENT_NOT_FOUND`).
4. Once `project_id` is resolved, verify whether `req.user.id` is in `public.project_members` for that `project_id`.
5. If not a member -> return 403 Forbidden (`FORBIDDEN_PROJECT_ACCESS`).
6. Cross-project amendment access is blocked immediately at the gateway.

---

## 7. Database Tables, Relational Constraints, and Migration Plan

### Executable PostgreSQL Migration: `002_contractflow_schema.sql`

```sql
-- ============================================================================
-- 002_contractflow_schema.sql
-- ContractFlow Relational Storage, Integrity Constraints & Access Controls
-- ============================================================================

-- 0. MONOTONIC SOURCE VERSION ON PROJECTS
ALTER TABLE public.projects 
ADD COLUMN IF NOT EXISTS source_version INT NOT NULL DEFAULT 1 CHECK (source_version >= 1);

-- 1. CF ARTIFACTS (Immutable versioned contract, agreement, assessment, amendment artifacts)
CREATE TABLE IF NOT EXISTS public.cf_artifacts (
    artifact_id UUID NOT NULL,
    revision INT NOT NULL CHECK (revision >= 1),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('CONTRACT', 'AGREEMENT', 'ASSESSMENT', 'AMENDMENT')),
    source_version INT NOT NULL CHECK (source_version >= 1),
    source_snapshot JSONB NOT NULL,
    payload_json JSONB NOT NULL,
    content_digest CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (artifact_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_cf_artifacts_project_id ON public.cf_artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_cf_artifacts_digest ON public.cf_artifacts(content_digest);

-- 2. CF APPROVAL VERSIONS (State of each amendment revision)
-- Created before cf_approval_heads to allow clean relational foreign keys.
CREATE TABLE IF NOT EXISTS public.cf_approval_versions (
    amendment_id UUID NOT NULL,
    revision INT NOT NULL CHECK (revision >= 1),
    content_digest CHAR(64) NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('PENDING_REVIEW', 'PARTIALLY_APPROVED', 'BOTH_APPROVED', 'REJECTED', 'SUPERSEDED')),
    original_agreement_id UUID NOT NULL REFERENCES public.agreements(id) ON DELETE RESTRICT,
    original_agreement_version INT NOT NULL CHECK (original_agreement_version >= 1),
    client_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    freelancer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    review_reference TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (amendment_id, revision),
    -- Relational Constraint 1: Approval revision must bind to its exact underlying immutable artifact
    CONSTRAINT fk_cf_approval_versions_artifact 
        FOREIGN KEY (amendment_id, revision) 
        REFERENCES public.cf_artifacts(artifact_id, revision) ON DELETE RESTRICT
);

-- 3. CF APPROVAL HEADS (Pointers to current revision with row-level locking)
CREATE TABLE IF NOT EXISTS public.cf_approval_heads (
    amendment_id UUID PRIMARY KEY,
    current_revision INT NOT NULL CHECK (current_revision >= 1),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Relational Constraint 2: Approval head must reference a valid existing approval version (deferred for initial insert)
    CONSTRAINT fk_cf_approval_heads_version 
        FOREIGN KEY (amendment_id, current_revision) 
        REFERENCES public.cf_approval_versions(amendment_id, revision) ON DELETE RESTRICT 
        DEFERRABLE INITIALLY DEFERRED
);

-- 4. CF DECISIONS (Audited client and freelancer approval or rejection decisions)
CREATE TABLE IF NOT EXISTS public.cf_decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amendment_id UUID NOT NULL,
    revision INT NOT NULL,
    actor_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('CLIENT', 'FREELANCER')),
    decision TEXT NOT NULL CHECK (decision IN ('APPROVE', 'REJECT')),
    request_digest CHAR(64) NOT NULL,
    rejection_reason TEXT,
    idempotency_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (amendment_id, revision) REFERENCES public.cf_approval_versions(amendment_id, revision) ON DELETE RESTRICT,
    CONSTRAINT uq_cf_decisions_role UNIQUE (amendment_id, revision, role),
    CONSTRAINT uq_cf_decisions_actor UNIQUE (amendment_id, revision, actor_id),
    CONSTRAINT uq_cf_decisions_idempotency UNIQUE (amendment_id, revision, idempotency_key)
);

-- 5. CF AUDIT (Tamper-evident append-only event log)
CREATE TABLE IF NOT EXISTS public.cf_audit (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amendment_id UUID NOT NULL,
    revision INT NOT NULL,
    append_sequence BIGSERIAL NOT NULL UNIQUE,
    action TEXT NOT NULL CHECK (action IN ('CREATED', 'APPROVE', 'REJECT', 'SUPERSEDED')),
    previous_state TEXT,
    new_state TEXT NOT NULL,
    actor_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('CLIENT', 'FREELANCER')),
    content_digest CHAR(64) NOT NULL,
    idempotency_reference TEXT,
    decision_id UUID REFERENCES public.cf_decisions(decision_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (amendment_id, revision) REFERENCES public.cf_approval_versions(amendment_id, revision) ON DELETE RESTRICT
);

-- 6. CF REVIEWS (Human and semantic review grants required before approval)
CREATE TABLE IF NOT EXISTS public.cf_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amendment_id UUID NOT NULL,
    revision INT NOT NULL,
    content_digest CHAR(64) NOT NULL,
    reviewer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    human_review BOOLEAN NOT NULL DEFAULT TRUE,
    semantic_review BOOLEAN NOT NULL DEFAULT TRUE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Relational Constraint 3: Review grant must bind to its exact amendment revision
    CONSTRAINT fk_cf_reviews_version 
        FOREIGN KEY (amendment_id, revision) 
        REFERENCES public.cf_approval_versions(amendment_id, revision) ON DELETE RESTRICT,
    CONSTRAINT chk_cf_reviews_lifetime CHECK (reviewed_at < expires_at)
);

-- 7. AUDIT IMMUTABILITY ENFORCEMENT (Exception-raising trigger)
CREATE OR REPLACE FUNCTION public.prevent_cf_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log violation: cf_audit records are strictly append-only. Updates and deletions are forbidden.'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cf_audit_no_update_delete ON public.cf_audit;
CREATE TRIGGER trg_cf_audit_no_update_delete
BEFORE UPDATE OR DELETE ON public.cf_audit
FOR EACH ROW
EXECUTE FUNCTION public.prevent_cf_audit_tampering();

-- 8. DATABASE PRIVILEGES (Least privilege model)
REVOKE ALL ON public.cf_artifacts, public.cf_approval_heads, public.cf_approval_versions, 
               public.cf_decisions, public.cf_audit, public.cf_reviews FROM anon;

GRANT SELECT ON public.cf_artifacts, public.cf_approval_heads, public.cf_approval_versions, 
                public.cf_decisions, public.cf_audit, public.cf_reviews TO authenticated;

-- Hard revoke of UPDATE/DELETE on immutable tables for all roles
REVOKE UPDATE, DELETE ON public.cf_artifacts FROM authenticated, service_role;
REVOKE UPDATE, DELETE ON public.cf_decisions FROM authenticated, service_role;
REVOKE UPDATE, DELETE ON public.cf_audit FROM authenticated, service_role;

GRANT SELECT, INSERT ON public.cf_artifacts, public.cf_approval_versions, 
                        public.cf_decisions, public.cf_audit, public.cf_reviews TO service_role;
GRANT SELECT, INSERT, UPDATE ON public.cf_approval_heads TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.cf_audit_append_sequence_seq TO service_role;

-- 9. ROW LEVEL SECURITY (RLS)
ALTER TABLE public.cf_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_approval_heads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_approval_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_reviews ENABLE ROW LEVEL SECURITY;

-- Correct RLS Policies (Joining through agreements.project_id)
CREATE POLICY "Project members can read cf_artifacts"
    ON public.cf_artifacts FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.project_members
        WHERE project_members.project_id = cf_artifacts.project_id
        AND project_members.user_id = auth.uid()
    ));

CREATE POLICY "Project members can read cf_approval_versions"
    ON public.cf_approval_versions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.agreements a
        JOIN public.project_members pm ON pm.project_id = a.project_id
        WHERE a.id = cf_approval_versions.original_agreement_id
        AND pm.user_id = auth.uid()
    ));

CREATE POLICY "Project members can read cf_approval_heads"
    ON public.cf_approval_heads FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.cf_approval_versions v
        JOIN public.agreements a ON a.id = v.original_agreement_id
        JOIN public.project_members pm ON pm.project_id = a.project_id
        WHERE v.amendment_id = cf_approval_heads.amendment_id
        AND pm.user_id = auth.uid()
    ));

CREATE POLICY "Project members can read cf_decisions"
    ON public.cf_decisions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.cf_approval_versions v
        JOIN public.agreements a ON a.id = v.original_agreement_id
        JOIN public.project_members pm ON pm.project_id = a.project_id
        WHERE v.amendment_id = cf_decisions.amendment_id
        AND v.revision = cf_decisions.revision
        AND pm.user_id = auth.uid()
    ));

CREATE POLICY "Project members can read cf_audit"
    ON public.cf_audit FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.cf_approval_versions v
        JOIN public.agreements a ON a.id = v.original_agreement_id
        JOIN public.project_members pm ON pm.project_id = a.project_id
        WHERE v.amendment_id = cf_audit.amendment_id
        AND v.revision = cf_audit.revision
        AND pm.user_id = auth.uid()
    ));

CREATE POLICY "Project members can read cf_reviews"
    ON public.cf_reviews FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.cf_approval_versions v
        JOIN public.agreements a ON a.id = v.original_agreement_id
        JOIN public.project_members pm ON pm.project_id = a.project_id
        WHERE v.amendment_id = cf_reviews.amendment_id
        AND v.revision = cf_reviews.revision
        AND pm.user_id = auth.uid()
    ));
```

---

## 8. API Gateway & Proxy Architecture

### Endpoints Mounted in Express:

| Express Gateway Route | Method | Authorization & Gateway Logic | FastAPI Upstream Route |
| :--- | :--- | :--- | :--- |
| `/api/projects/:id/contractflow/contracts/generate` | POST | `requireAuth`, Project Member | `/api/v1/contractflow/contracts/generate` |
| `/api/projects/:id/contractflow/agreements/draft` | POST | `requireAuth`, Project Member | `/api/v1/contractflow/agreements/draft` |
| `/api/projects/:id/contractflow/scope/assess` | POST | `requireAuth`, Project Member | `/api/v1/contractflow/scope/assess` |
| `/api/projects/:id/contractflow/amendments/generate` | POST | `requireAuth`, Project Member | `/api/v1/contractflow/amendments/generate` |
| `/api/contractflow/amendments/:amendmentId/register` | POST | `requireAuth`, **Resolves owning project first** | `/api/v1/contractflow/amendments/{id}/register` |
| `/api/contractflow/amendments/:amendmentId/decisions` | POST | `requireAuth`, **Resolves owning project first** | `/api/v1/contractflow/amendments/{id}/decisions` |
| `/api/contractflow/amendments/:amendmentId/status` | GET | `requireAuth`, **Resolves owning project first** | `/api/v1/contractflow/amendments/{id}/status` |
| `/api/contractflow/amendments/:amendmentId/history` | GET | `requireAuth`, **Resolves owning project first** | `/api/v1/contractflow/amendments/{id}/history` |

### Security Boundaries in Proxy:
- Body limit strictly capped at 128 KB.
- Header forwarding preserves `Authorization: Bearer <jwt>`.
- Client requests never supply `role` or `user_id`.
- Upstream error translation maps ContractFlow errors into standard Freelanker `{ success: false, error: { code, message } }`.

---

## 9. Frontend Integration Plan

1. **Agreement Setup & Generation (`AgreementDraftCard.tsx`):**
   - If planned milestones/deliverables are missing, shows **"Incomplete Project Setup"** warning state.
   - When terms are valid, enables "Generate Agreement Draft".
   - Renders extractive agreement text, deliverables table, and unresolved legal terms warning pill.
2. **Scope Change Detection (`ScopeAssessmentModal.tsx`):**
   - Form to submit proposed change.
   - Renders AI classification (`IN_SCOPE`, `NEEDS_CLARIFICATION`, `OUT_OF_SCOPE`) with verbatim citations.
   - If `OUT_OF_SCOPE`, enables "Draft Proposed Amendment".
3. **Amendment Approval Card (`AmendmentApprovalCard.tsx`):**
   - Displays proposed wording with prominent notice: `PROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE`.
   - Dual-party approval status pills (Client [Pending/Approved], Freelancer [Pending/Approved]).
   - **Approve Button** (generates unique client idempotency key).
   - **Reject Button** (opens required modal for rejection reason).
   - Collapsible **Audit History Drawer** displaying append-only chronological log.

---

## 10. Security Risks, Concurrency Safeguards & Atomic Approval Transaction

### Complete Atomic Approval Transaction Specification [PROPOSED - DESIGN]
Implemented in `services/contractflow/src/adapters/transactions.py` using PostgreSQL:

```text
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

1. LOCK APPROVAL HEAD:
   SELECT current_revision FROM public.cf_approval_heads 
   WHERE amendment_id = $amendment_id FOR UPDATE;
   -- If not found -> RAISE NotFound("Unknown amendment")

2. FETCH CURRENT VERSION ROW:
   SELECT * FROM public.cf_approval_versions 
   WHERE amendment_id = $amendment_id AND revision = $current_revision;

3. VERIFY DIGEST & STATE:
   -- Assert request.expected_version == current_revision
   -- Assert request.expected_digest == version.content_digest
   -- Assert version.state IN ('PENDING_REVIEW', 'PARTIALLY_APPROVED')

4. VERIFY REVIEW GRANT:
   SELECT * FROM public.cf_reviews 
   WHERE amendment_id = $amendment_id 
     AND revision = $current_revision 
     AND content_digest = $expected_digest 
     AND human_review = TRUE 
     AND semantic_review = TRUE 
     AND revoked = FALSE 
     AND now() >= reviewed_at 
     AND now() < expires_at;
   -- If no matching unexpired grant -> RAISE IntegrationError("REVIEW_INVALID")

5. IDEMPOTENCY CHECK:
   SELECT actor_id, request_digest FROM public.cf_decisions 
   WHERE amendment_id = $amendment_id 
     AND revision = $current_revision 
     AND idempotency_key = $idempotency_key;
   -- If match found:
   --   If actor_id == $actor_id AND request_digest == $request_digest:
   --     COMMIT and return current status (safe idempotent replay)
   --   Else:
   --     RAISE ConflictError("Conflicting parameters for existing idempotency key")

6. CONFLICT CHECK:
   -- Check if a decision already exists for (amendment_id, revision, role):
   --   If role already decided -> RAISE ConflictError("Role already decided")
   -- Check if actor already decided:
   --   If actor_id already decided -> RAISE ConflictError("Actor already decided")

7. INSERT DECISION:
   INSERT INTO public.cf_decisions (
       decision_id, amendment_id, revision, actor_id, role, 
       decision, request_digest, rejection_reason, idempotency_key, created_at
   ) VALUES (
       $decision_id, $amendment_id, $current_revision, $actor_id, $role,
       $decision, $request_digest, $rejection_reason, $idempotency_key, now()
   );

8. TRANSITION STATE:
   -- If decision == 'REJECT': new_state = 'REJECTED'
   -- If decision == 'APPROVE':
   --   If counterpart role already approved: new_state = 'BOTH_APPROVED'
   --   Else: new_state = 'PARTIALLY_APPROVED'

9. UPDATE APPROVAL VERSION:
   UPDATE public.cf_approval_versions 
   SET state = $new_state 
   WHERE amendment_id = $amendment_id AND revision = $current_revision;

10. APPEND AUDIT EVENT:
   INSERT INTO public.cf_audit (
       event_id, amendment_id, revision, action, previous_state, new_state,
       actor_id, role, content_digest, idempotency_reference, decision_id, created_at
   ) VALUES (
       $event_id, $amendment_id, $current_revision, $decision, $old_state, $new_state,
       $actor_id, $role, $content_digest, $idempotency_key, $decision_id, now()
   );

11. UPDATE HEAD TIMESTAMP:
   UPDATE public.cf_approval_heads 
   SET updated_at = now() 
   WHERE amendment_id = $amendment_id;

COMMIT;
```

### Invariant: `BOTH_APPROVED` Does Not Trigger Contract Activation or Payments
- In `ApprovalStatus`, `effective` remains `Literal[False] = False`.
- In ContractFlow's domain logic: reaching `BOTH_APPROVED` marks that both parties have agreed to the wording of the amendment proposal.
- It does **not** update `public.agreements.status` to `'active'`.
- It does **not** capture escrow payments or execute PayPal transactions.
- Formal legal activation and financial escrow release remain independent Core Platform lifecycle events.

---

## 11. Ordered Implementation Tasks

### Phase 2: Service Setup & Relational Adapters
1. Initialize `services/contractflow/` and copy Person 2's `contractflow` package.
2. Prepare `database/migrations/002_contractflow_schema.sql` (review without applying).
3. Implement production PostgreSQL adapters:
   - `SupabasePostgresAuth` (Supabase JWT verification + membership check).
   - `SupabaseCoreSource` (Project, deliverables, milestones, and agreements source loader).
   - `PostgresArtifactRepository` (`cf_artifacts`).
   - `PostgresApprovalRepository` (`cf_approval_heads`, `cf_approval_versions`, `cf_decisions`).
   - `PostgresApprovalTransactions` (atomic approval transaction with row-level locks).
   - `PostgresReviewRepository` (`cf_reviews`).
4. Build `services/contractflow/src/main.py` assembling `IntegrationRuntime` with production adapters.

### Phase 3: Express Proxy Gateway
5. Implement `backend/src/routes/contractflow.route.ts` with owning project lookup.
6. Implement `backend/src/controllers/contractflow.controller.ts`.
7. Implement `backend/src/services/contractflowProxy.service.ts`.
8. Mount `/api/contractflow` in `backend/src/app.ts`.

### Phase 4: Frontend UI Integration
9. Implement `frontend/src/services/contractflowService.ts`.
10. Build `AgreementDraftCard.tsx`, `ScopeAssessmentModal.tsx`, and `AmendmentApprovalCard.tsx`.
11. Integrate into `frontend/src/features/projects/ProjectDetailView.tsx`.

### Phase 5: Verification & End-to-End Testing
12. Run automated test suite against live PostgreSQL.
13. Execute full dual-party browser walk-through.

---

## 12. Required Comprehensive Test Suite

| Test Category | Target Scenario | Verification Criteria |
| :--- | :--- | :--- |
| **Missing Deliverables** | Initial project has no deliverables or dates | `POST /contracts/generate` fails with 422 `INVALID_SOURCE`. Frontend renders incomplete setup state. |
| **Cross-Project Access** | User A calls `/api/contractflow/amendments/:id/status` for a project they do not belong to | Express and FastAPI resolve owning project, detect missing membership, and return 403 Forbidden. |
| **Wrong-Project Amendment ID** | Caller requests decision using non-existent or wrong amendment UUID | Route fails to resolve owning project and returns 404 Not Found (`AMENDMENT_NOT_FOUND`). |
| **Stale Source Version** | Project description is edited concurrently while AI is generating draft | Commit point re-reads `projects.source_version`; detects drift and aborts with 409 Conflict (`STALE_SOURCE`). |
| **Expired / Revoked Review Grant** | Decision submitted when `cf_reviews.expires_at < now()` or `revoked = TRUE` | Atomic transaction check detects invalid grant and aborts with 403 `REVIEW_INVALID`. |
| **Duplicate Decisions** | Actor submits approval; then submits another approval for the same revision | Database constraint `uq_cf_decisions_actor` or service logic rejects with 409 Conflict. |
| **Idempotency Replay** | Identical request re-sent with exact same `idempotency_key` and actor | Transaction returns current status cleanly; no duplicate rows in `cf_decisions` or `cf_audit`. |
| **Concurrent Approvals** | Client and Freelancer submit approvals at the exact same millisecond | `SELECT ... FOR UPDATE` serializes executions. First transitions to `PARTIALLY_APPROVED`, second to `BOTH_APPROVED`. |
| **Audit Tampering** | Malicious actor or DBA attempts `UPDATE` or `DELETE` on `cf_audit` | Hard SQL exception is raised: `Audit log violation: cf_audit records are strictly append-only.` |
| **Premature Activation** | State reaches `BOTH_APPROVED` | Verify `public.agreements.status` remains unchanged; no PayPal API call is triggered. |

---

## 13. Estimated Complexity & Unresolved Decisions

### Complexity Breakdown
- **PostgreSQL Relational Adapters & Locking:** Medium
- **FastAPI JWT & Gateway Proxy:** Low-Medium
- **Frontend Workspace UI:** Medium
- **Total Integration Complexity:** Medium

### Unresolved Decisions Before Phase 2 Implementation:
1. **Database Migration Application:** Confirm authorization to apply `database/migrations/002_contractflow_schema.sql` to live Supabase once Phase 2 begins.
2. **Review Grant Issuance Model:** In production, who inserts the initial `cf_reviews` grant?
   - Option A: Automated platform verification trigger checking deterministic validation.
   - Option B: Admin/Moderator approval grant.
   *(Recommendation: Platform automated semantic pre-grant with admin revocation capability).*
3. **Groq API Key Configuration:** Confirm the live `GROQ_API_KEY` for live AI generations during testing.
