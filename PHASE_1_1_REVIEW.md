# ContractFlow Integration — Phase 1.1 Review & Corrections

**Date:** November 10, 2026  
**Scope:** Phase 1.1 Corrective Revision (Architecture & Audit Only)  
**Status:** Completed & Ready for Review

---

## 1. Summary of Corrective Actions Taken

In response to the Phase 1 audit review, `CONTRACTFLOW_INTEGRATION_PLAN.md` has been completely updated to Phase 1.1. No application code, database schemas, or commits were altered.

| # | Review Finding / Issue | Corrective Revision in Plan | Plan Reference |
| :--- | :--- | :--- | :--- |
| **1** | **No Invented Terms / Dates** | Removed automatic baseline deliverable and 30-day default deadline. Explicit deliverables and deadlines are strictly required before agreement generation. Added frontend **Incomplete Setup State**. | Section 5, Section 9 |
| **2** | **Correct `cf_audit` RLS Join** | Fixed RLS join to connect through `agreements.project_id`: `cf_audit` -> `cf_approval_versions` -> `agreements.id` -> `agreements.project_id` -> `project_members`. | Section 7 |
| **3** | **Access-Control Policies & Database Privileges** | Defined complete two-layer access control: (a) Explicit application-level JWT verification & membership checks in Python, and (b) Database privileges (`REVOKE ALL FROM anon`, `GRANT SELECT TO authenticated`, explicit hard revoke of `UPDATE/DELETE` on immutable tables). | Section 6, Section 7 |
| **4** | **Missing Relational Constraints** | Added: (a) `cf_approval_heads` FK to `cf_approval_versions(amendment_id, current_revision)` (deferrable), (b) `cf_approval_versions` FK to `cf_artifacts(artifact_id, revision)`, and (c) `cf_reviews` FK to `cf_approval_versions(amendment_id, revision)`. | Section 7 |
| **5** | **Monotonic Project Source Version** | Replaced `updated_at`-derived versioning with an explicit monotonic `source_version INT NOT NULL DEFAULT 1` column on `public.projects`, with explicit increment rules and commit-time freshness validation. | Section 5, Section 7 |
| **6** | **Strengthen Audit Immutability** | Replaced silent `DO INSTEAD NOTHING` with explicit `REVOKE UPDATE, DELETE` and a PostgreSQL trigger `prevent_cf_audit_tampering()` that raises an immediate SQL exception on any update or deletion attempt. | Section 7 |
| **7** | **Amendment Route Project Resolution** | Express routes resolving `/api/contractflow/amendments/:amendmentId/*` now query PostgreSQL to look up the owning project before evaluating project membership, preventing cross-project amendment access. | Section 6, Section 8 |
| **8** | **FastAPI Supabase JWT Verification** | Documented complete independent JWT validation in Python: header format, signature verification (HS256/RS256), claims check (`iss`, `aud`, `exp`, `sub`), clock skew allowance (60s), and `Principal` mapping. | Section 6 |
| **9** | **Atomic Approval Transaction** | Defined the complete SQL transaction sequence: lock approval head (`SELECT ... FOR UPDATE`), verify version & digest, verify review grant, check idempotency, check role/actor conflicts, insert decision, update version state, append audit event, and update head timestamp in one atomic commit. | Section 10 |
| **10** | **Preserve Invariant on `BOTH_APPROVED`** | Explicitly documented that reaching `BOTH_APPROVED` only marks mutual amendment agreement; it does **not** activate agreements in `public.agreements` or trigger PayPal escrow funding. | Section 10 |

---

## 2. Verified vs. Proposed Status

| Component | Status | Notes |
| :--- | :--- | :--- |
| `feature/core-platform` (Express, React, Router, Auth) | **VERIFIED - CODE** | Verified at commit `ce4d277`. 15 tables in Supabase. |
| `origin/feature/contractflow` (V1–V6 domain logic, 902 tests) | **VERIFIED - CODE** | Verified at commit `0608adf` / `f6cd74f`. Isolated in `backend/app/modules/contractflow/`. |
| Relational Schema (`002_contractflow_schema.sql`) | **PROPOSED - DESIGN** | Fully drafted executable SQL. Ready to apply in Phase 2 upon approval. |
| Python PostgreSQL Adapters (`services/contractflow/`) | **PROPOSED - DESIGN** | Designed to implement ContractFlow's V6 protocols (`SharedAuth`, `WorkBridgeSource`, `ArtifactRepository`, `ApprovalRepository`, `ApprovalTransactions`, `AmendmentReviews`). |
| Express Proxy Gateway (`contractflow.route.ts`) | **PROPOSED - DESIGN** | Architecture designed with project resolution and Supabase JWT forwarding. |
| React Workspace ContractFlow Panel | **PROPOSED - DESIGN** | UI components and workflow designed for `ProjectDetailView.tsx`. |

---

## 3. Unresolved Decisions (To Confirm Before Phase 2)

1. **Database Migration Authorization:**
   - Confirm approval to execute `database/migrations/002_contractflow_schema.sql` against the live Supabase project when Phase 2 starts.
2. **Review Grant Authority Model:**
   - ContractFlow V4 and V5 require an unexpired, unrevoked `cf_reviews` grant before registering or approving an amendment.
   - *Option A (Automated Pre-Grant):* System issues an automated review grant once deterministic checks pass, allowing direct peer approvals with an admin revocation option.
   - *Option B (Human Platform Reviewer):* Dedicated reviewer or admin must approve the grant before client/freelancer can approve.
   - *Recommendation:* Option A for standard workflow, preserving Option B for flagged or disputed projects.
3. **Groq API Key:**
   - Live AI contract and amendment drafting requires a `GROQ_API_KEY` in `services/contractflow/.env`. Offline testing works deterministically without external credentials.

