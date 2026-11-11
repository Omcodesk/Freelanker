-- ============================================================================
-- Migration: 002_contractflow_schema.sql
-- Module: ContractFlow Integration (Person 2 Domain Persistence)
-- Target Database: Supabase PostgreSQL
-- Status: PROPOSED MIGRATION — DO NOT RUN IN PHASE 1 / STEP 2
--
-- Relational Mapping Notes:
--   1. cf_artifacts stores immutable CONTRACT, AGREEMENT, ASSESSMENT, AMENDMENT payloads.
--   2. cf_approval_heads holds current revision pointers with row locks for concurrency.
--   3. cf_approval_versions stores the dual-party approval state of each amendment revision.
--   4. cf_decisions records audited client and freelancer approval/rejection decisions.
--   5. cf_audit is a tamper-evident, append-only chronological event log.
--   6. cf_reviews stores human & semantic review grants required before approval.
--   7. cf_assessment_reviews stores V4 assessment review verification receipts.
--   8. projects.source_version provides monotonic change detection for immutable snapshots.
-- ============================================================================

-- ============================================================================
-- 1. MONOTONIC PROJECT SOURCE VERSIONING
-- ============================================================================

-- Add monotonic source_version column to public.projects
ALTER TABLE public.projects
ADD COLUMN IF NOT EXISTS source_version INT NOT NULL DEFAULT 1 CHECK (source_version >= 1);

-- Function to automatically increment project source_version upon substantive changes
CREATE OR REPLACE FUNCTION public.increment_project_source_version()
RETURNS TRIGGER AS $$
BEGIN
    -- Substantive edits to project scope, budget, currency, parties, terms, or status increment source_version
    IF (OLD.title IS DISTINCT FROM NEW.title OR
        OLD.description IS DISTINCT FROM NEW.description OR
        OLD.total_budget IS DISTINCT FROM NEW.total_budget OR
        OLD.currency IS DISTINCT FROM NEW.currency OR
        OLD.payment_arrangement IS DISTINCT FROM NEW.payment_arrangement OR
        OLD.client_id IS DISTINCT FROM NEW.client_id OR
        OLD.freelancer_id IS DISTINCT FROM NEW.freelancer_id OR
        OLD.review_period_days IS DISTINCT FROM NEW.review_period_days OR
        OLD.status IS DISTINCT FROM NEW.status) THEN
        NEW.source_version := OLD.source_version + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public, pg_temp;

DROP TRIGGER IF EXISTS trg_increment_project_source_version ON public.projects;
CREATE TRIGGER trg_increment_project_source_version
BEFORE UPDATE ON public.projects
FOR EACH ROW
EXECUTE FUNCTION public.increment_project_source_version();

-- Function to increment project source_version when project milestones change
-- SECURITY DEFINER allows project version bump under row-level security
CREATE OR REPLACE FUNCTION public.increment_project_source_on_milestone_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.project_id IS DISTINCT FROM NEW.project_id THEN
        -- Milestone reassigned between projects: bump both projects transactionally
        IF OLD.project_id IS NOT NULL THEN
            UPDATE public.projects
            SET source_version = source_version + 1,
                updated_at = now()
            WHERE id = OLD.project_id;
        END IF;
        IF NEW.project_id IS NOT NULL THEN
            UPDATE public.projects
            SET source_version = source_version + 1,
                updated_at = now()
            WHERE id = NEW.project_id;
        END IF;
    ELSE
        DECLARE
            target_project_id UUID := COALESCE(NEW.project_id, OLD.project_id);
        BEGIN
            IF target_project_id IS NOT NULL THEN
                UPDATE public.projects
                SET source_version = source_version + 1,
                    updated_at = now()
                WHERE id = target_project_id;
            END IF;
        END;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION public.increment_project_source_on_milestone_change() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.increment_project_source_on_milestone_change() TO authenticated, service_role;

DROP TRIGGER IF EXISTS trg_increment_project_source_on_milestone ON public.milestones;
CREATE TRIGGER trg_increment_project_source_on_milestone
AFTER INSERT OR UPDATE OR DELETE ON public.milestones
FOR EACH ROW
EXECUTE FUNCTION public.increment_project_source_on_milestone_change();

-- Function to increment project source_version when base agreement changes
-- SECURITY DEFINER allows project version bump under row-level security
CREATE OR REPLACE FUNCTION public.increment_project_source_on_agreement_change()
RETURNS TRIGGER AS $$
DECLARE
    target_project_id UUID := COALESCE(NEW.project_id, OLD.project_id);
BEGIN
    IF target_project_id IS NOT NULL THEN
        UPDATE public.projects
        SET source_version = source_version + 1,
            updated_at = now()
        WHERE id = target_project_id;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

REVOKE ALL ON FUNCTION public.increment_project_source_on_agreement_change() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.increment_project_source_on_agreement_change() TO authenticated, service_role;

DROP TRIGGER IF EXISTS trg_increment_project_source_on_agreement ON public.agreements;
CREATE TRIGGER trg_increment_project_source_on_agreement
AFTER INSERT OR UPDATE OR DELETE ON public.agreements
FOR EACH ROW
EXECUTE FUNCTION public.increment_project_source_on_agreement_change();


-- ============================================================================
-- 2. CF ARTIFACTS (Immutable Generated Documents)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cf_artifacts (
    artifact_id UUID NOT NULL,
    revision INT NOT NULL CHECK (revision >= 1),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('CONTRACT', 'AGREEMENT', 'ASSESSMENT', 'AMENDMENT')),
    source_version INT NOT NULL CHECK (source_version >= 1),
    source_snapshot JSONB NOT NULL,
    payload_json JSONB NOT NULL,
    content_digest CHAR(64) NOT NULL CHECK (content_digest ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (artifact_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_cf_artifacts_project_id ON public.cf_artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_cf_artifacts_digest ON public.cf_artifacts(content_digest);
CREATE INDEX IF NOT EXISTS idx_cf_artifacts_kind_created ON public.cf_artifacts(kind, created_at DESC);


-- ============================================================================
-- 3. CF APPROVAL VERSIONS (State of each amendment revision)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cf_approval_versions (
    amendment_id UUID NOT NULL,
    revision INT NOT NULL CHECK (revision >= 1),
    content_digest CHAR(64) NOT NULL CHECK (content_digest ~ '^[0-9a-f]{64}$'),
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
        REFERENCES public.cf_artifacts(artifact_id, revision) ON DELETE RESTRICT,
    CONSTRAINT chk_cf_approval_versions_distinct_parties
        CHECK (client_id != freelancer_id)
);

CREATE INDEX IF NOT EXISTS idx_cf_approval_versions_agreement ON public.cf_approval_versions(original_agreement_id);
CREATE INDEX IF NOT EXISTS idx_cf_approval_versions_state ON public.cf_approval_versions(state);


-- ============================================================================
-- 4. CF APPROVAL HEADS (Pointers to current revision with row-level locks)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cf_approval_heads (
    amendment_id UUID PRIMARY KEY,
    current_revision INT NOT NULL CHECK (current_revision >= 1),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Relational Constraint 2: Approval head must reference an existing approval version.
    -- Deferred initially so amendment version 1 and approval head can be inserted in the same transaction.
    CONSTRAINT fk_cf_approval_heads_version
        FOREIGN KEY (amendment_id, current_revision)
        REFERENCES public.cf_approval_versions(amendment_id, revision) ON DELETE RESTRICT
        DEFERRABLE INITIALLY DEFERRED
);


-- ============================================================================
-- 5. CF DECISIONS (Audited client and freelancer approval or rejection decisions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cf_decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amendment_id UUID NOT NULL,
    revision INT NOT NULL CHECK (revision >= 1),
    actor_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('CLIENT', 'FREELANCER')),
    decision TEXT NOT NULL CHECK (decision IN ('APPROVE', 'REJECT')),
    request_digest CHAR(64) NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    rejection_reason TEXT CHECK (rejection_reason IS NULL OR length(trim(rejection_reason)) > 0),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) >= 1 AND length(idempotency_key) <= 128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Relational Constraint 3: Decision must bind to a valid approval version
    CONSTRAINT fk_cf_decisions_version
        FOREIGN KEY (amendment_id, revision)
        REFERENCES public.cf_approval_versions(amendment_id, revision) ON DELETE RESTRICT,
    -- Unique Invariants:
    CONSTRAINT uq_cf_decisions_role UNIQUE (amendment_id, revision, role),
    CONSTRAINT uq_cf_decisions_actor UNIQUE (amendment_id, revision, actor_id),
    CONSTRAINT uq_cf_decisions_idempotency UNIQUE (amendment_id, revision, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_cf_decisions_amendment_rev ON public.cf_decisions(amendment_id, revision);


-- ============================================================================
-- 6. CF AUDIT (Tamper-evident append-only event log)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cf_audit (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amendment_id UUID NOT NULL,
    revision INT NOT NULL CHECK (revision >= 1),
    append_sequence BIGSERIAL NOT NULL UNIQUE,
    action TEXT NOT NULL CHECK (action IN ('CREATED', 'APPROVE', 'REJECT', 'SUPERSEDED')),
    previous_state TEXT CHECK (previous_state IS NULL OR previous_state IN ('PENDING_REVIEW', 'PARTIALLY_APPROVED', 'BOTH_APPROVED', 'REJECTED', 'SUPERSEDED')),
    new_state TEXT NOT NULL CHECK (new_state IN ('PENDING_REVIEW', 'PARTIALLY_APPROVED', 'BOTH_APPROVED', 'REJECTED', 'SUPERSEDED')),
    actor_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('CLIENT', 'FREELANCER')),
    content_digest CHAR(64) NOT NULL CHECK (content_digest ~ '^[0-9a-f]{64}$'),
    idempotency_reference TEXT,
    decision_id UUID REFERENCES public.cf_decisions(decision_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Relational Constraint 4: Audit event must bind to a valid approval version
    CONSTRAINT fk_cf_audit_version
        FOREIGN KEY (amendment_id, revision)
        REFERENCES public.cf_approval_versions(amendment_id, revision) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_cf_audit_amendment ON public.cf_audit(amendment_id, revision, append_sequence ASC);


-- ============================================================================
-- 7. CF REVIEWS (Human and semantic review grants required before approval)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cf_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amendment_id UUID NOT NULL,
    revision INT NOT NULL CHECK (revision >= 1),
    content_digest CHAR(64) NOT NULL CHECK (content_digest ~ '^[0-9a-f]{64}$'),
    reviewer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    human_review BOOLEAN NOT NULL DEFAULT TRUE,
    semantic_review BOOLEAN NOT NULL DEFAULT TRUE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    revocation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Relational Constraint 5: Review grant must bind to its exact amendment artifact revision
    CONSTRAINT fk_cf_reviews_artifact
        FOREIGN KEY (amendment_id, revision)
        REFERENCES public.cf_artifacts(artifact_id, revision) ON DELETE RESTRICT,
    CONSTRAINT chk_cf_reviews_lifetime CHECK (reviewed_at < expires_at),
    CONSTRAINT chk_cf_reviews_revocation CHECK (
        (revoked = FALSE AND revoked_at IS NULL AND revocation_reason IS NULL) OR
        (revoked = TRUE AND revoked_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_cf_reviews_lookup ON public.cf_reviews(amendment_id, revision, content_digest)
    WHERE (revoked = FALSE);


-- ============================================================================
-- 8. CF ASSESSMENT REVIEWS (V4 Scope Assessment Review Verification Receipts)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.cf_assessment_reviews (
    assessment_review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_reference TEXT NOT NULL UNIQUE,
    assessment_id UUID NOT NULL,
    assessment_revision INT NOT NULL DEFAULT 1 CHECK (assessment_revision >= 1),
    original_agreement_id UUID NOT NULL REFERENCES public.agreements(id) ON DELETE RESTRICT,
    original_agreement_version INT NOT NULL CHECK (original_agreement_version >= 1),
    agreement_digest CHAR(64) NOT NULL CHECK (agreement_digest ~ '^[0-9a-f]{64}$'),
    assessment_digest CHAR(64) NOT NULL CHECK (assessment_digest ~ '^[0-9a-f]{64}$'),
    reviewer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    decision TEXT NOT NULL DEFAULT 'AUTHORIZE_DRAFT_GENERATION' CHECK (decision = 'AUTHORIZE_DRAFT_GENERATION'),
    verification_boundary TEXT NOT NULL DEFAULT 'CONTRACTFLOW-V4-ASSESSMENT-REVIEW',
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    revocation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Relational Constraint 6: Assessment review must bind to its exact assessment artifact
    CONSTRAINT fk_cf_assessment_reviews_artifact
        FOREIGN KEY (assessment_id, assessment_revision)
        REFERENCES public.cf_artifacts(artifact_id, revision) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_cf_assessment_reviews_lookup ON public.cf_assessment_reviews(review_reference)
    WHERE (revoked = FALSE);


-- ============================================================================
-- 9. IMMUTABILITY ENFORCEMENT TRIGGERS (Anti-Tampering)
-- ============================================================================

-- Function to prevent unauthorized modification or deletion of append-only audit records
CREATE OR REPLACE FUNCTION public.prevent_cf_audit_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Integrity violation: cf_audit records are strictly append-only. Updates and deletions are forbidden.'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cf_audit_no_update_delete ON public.cf_audit;
CREATE TRIGGER trg_cf_audit_no_update_delete
BEFORE UPDATE OR DELETE ON public.cf_audit
FOR EACH ROW
EXECUTE FUNCTION public.prevent_cf_audit_tampering();

-- Function to prevent modification or deletion of immutable published artifacts
CREATE OR REPLACE FUNCTION public.prevent_cf_artifacts_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Integrity violation: cf_artifacts records are immutable. Updates and deletions are forbidden.'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cf_artifacts_no_update_delete ON public.cf_artifacts;
CREATE TRIGGER trg_cf_artifacts_no_update_delete
BEFORE UPDATE OR DELETE ON public.cf_artifacts
FOR EACH ROW
EXECUTE FUNCTION public.prevent_cf_artifacts_mutation();

-- Function to prevent modification or deletion of recorded decisions
CREATE OR REPLACE FUNCTION public.prevent_cf_decisions_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Integrity violation: cf_decisions records are final and immutable. Updates and deletions are forbidden.'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cf_decisions_no_update_delete ON public.cf_decisions;
CREATE TRIGGER trg_cf_decisions_no_update_delete
BEFORE UPDATE OR DELETE ON public.cf_decisions
FOR EACH ROW
EXECUTE FUNCTION public.prevent_cf_decisions_mutation();

-- Function to prevent modification of immutable cf_approval_versions fields or deletion
CREATE OR REPLACE FUNCTION public.prevent_cf_approval_versions_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Integrity violation: cf_approval_versions records are permanent and cannot be deleted.'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    -- On UPDATE: only state column is allowed to change during lifecycle transitions
    IF (OLD.amendment_id IS DISTINCT FROM NEW.amendment_id OR
        OLD.revision IS DISTINCT FROM NEW.revision OR
        OLD.content_digest IS DISTINCT FROM NEW.content_digest OR
        OLD.original_agreement_id IS DISTINCT FROM NEW.original_agreement_id OR
        OLD.original_agreement_version IS DISTINCT FROM NEW.original_agreement_version OR
        OLD.client_id IS DISTINCT FROM NEW.client_id OR
        OLD.freelancer_id IS DISTINCT FROM NEW.freelancer_id OR
        OLD.review_reference IS DISTINCT FROM NEW.review_reference OR
        OLD.created_at IS DISTINCT FROM NEW.created_at) THEN
        RAISE EXCEPTION 'Integrity violation: cf_approval_versions identity, revision, and digest are immutable. Only state transitions are permitted.'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cf_approval_versions_no_tampering ON public.cf_approval_versions;
CREATE TRIGGER trg_cf_approval_versions_no_tampering
BEFORE UPDATE OR DELETE ON public.cf_approval_versions
FOR EACH ROW
EXECUTE FUNCTION public.prevent_cf_approval_versions_tampering();


-- ============================================================================
-- 10. DATABASE PRIVILEGES (Least-Privilege Model)
-- ============================================================================

-- Deny all access to anonymous web clients
REVOKE ALL ON public.cf_artifacts, public.cf_approval_heads, public.cf_approval_versions,
               public.cf_decisions, public.cf_audit, public.cf_reviews,
               public.cf_assessment_reviews FROM anon;

-- Authenticated frontend users can SELECT via Supabase RLS (never write directly)
GRANT SELECT ON public.cf_artifacts, public.cf_approval_heads, public.cf_approval_versions,
                public.cf_decisions, public.cf_audit, public.cf_reviews,
                public.cf_assessment_reviews TO authenticated;

-- Hard revoke of UPDATE and DELETE on strictly immutable tables for authenticated and service_role
REVOKE UPDATE, DELETE ON public.cf_artifacts FROM authenticated, service_role;
REVOKE UPDATE, DELETE ON public.cf_decisions FROM authenticated, service_role;
REVOKE UPDATE, DELETE ON public.cf_audit FROM authenticated, service_role;

-- Version record protections: prevent DELETE entirely; table-level revoke of UPDATE
REVOKE DELETE ON public.cf_approval_versions FROM authenticated, service_role;
REVOKE UPDATE ON public.cf_approval_versions FROM authenticated, service_role;

-- Service role permissions for backend operations
GRANT SELECT, INSERT ON public.cf_artifacts, public.cf_approval_versions,
                        public.cf_decisions, public.cf_audit, public.cf_reviews,
                        public.cf_assessment_reviews TO service_role;

-- Grant column-level UPDATE on lifecycle state column ONLY (preserves immutable fields)
GRANT UPDATE (state) ON public.cf_approval_versions TO service_role;

GRANT SELECT, INSERT, UPDATE ON public.cf_approval_heads TO service_role;
GRANT SELECT, UPDATE ON public.cf_reviews TO service_role;
GRANT SELECT, UPDATE ON public.cf_assessment_reviews TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.cf_audit_append_sequence_seq TO service_role;

-- ----------------------------------------------------------------------------
-- Dedicated ContractFlow Application Runtime Role (Non-Superuser Least-Privilege)
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'contractflow_app') THEN
        CREATE ROLE contractflow_app WITH LOGIN NOINHERIT BYPASSRLS;
    ELSE
        ALTER ROLE contractflow_app BYPASSRLS;
    END IF;
END;
$$;

GRANT USAGE ON SCHEMA public TO contractflow_app;

-- Read-only Core table access for party resolution and monotonic source tracking
GRANT SELECT ON public.projects, public.project_members, public.profiles,
                public.agreements, public.milestones TO contractflow_app;

-- Dedicated runtime access to ContractFlow tables
GRANT SELECT, INSERT ON public.cf_artifacts, public.cf_approval_versions,
                        public.cf_decisions, public.cf_audit, public.cf_reviews,
                        public.cf_assessment_reviews TO contractflow_app;

-- Grant column-level UPDATE on lifecycle state column ONLY for application role
GRANT UPDATE (state) ON public.cf_approval_versions TO contractflow_app;

GRANT SELECT, INSERT, UPDATE ON public.cf_approval_heads TO contractflow_app;
GRANT SELECT, UPDATE ON public.cf_reviews TO contractflow_app;
GRANT SELECT, UPDATE ON public.cf_assessment_reviews TO contractflow_app;
GRANT USAGE, SELECT ON SEQUENCE public.cf_audit_append_sequence_seq TO contractflow_app;

-- Strict immutability: deny UPDATE and DELETE on immutable tables for runtime role
REVOKE UPDATE, DELETE ON public.cf_artifacts, public.cf_decisions, public.cf_audit FROM contractflow_app;
REVOKE DELETE ON public.cf_approval_versions FROM contractflow_app;


-- ============================================================================
-- 11. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

ALTER TABLE public.cf_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_approval_heads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_approval_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cf_assessment_reviews ENABLE ROW LEVEL SECURITY;

-- 11.1 cf_artifacts: Read access for project members
DROP POLICY IF EXISTS "Project members can read cf_artifacts" ON public.cf_artifacts;
CREATE POLICY "Project members can read cf_artifacts"
    ON public.cf_artifacts FOR SELECT
    USING (public.is_project_member(project_id, auth.uid()));

-- 11.2 cf_approval_versions: Read access for project members via agreements.project_id
DROP POLICY IF EXISTS "Project members can read cf_approval_versions" ON public.cf_approval_versions;
CREATE POLICY "Project members can read cf_approval_versions"
    ON public.cf_approval_versions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.agreements a
        WHERE a.id = cf_approval_versions.original_agreement_id
        AND public.is_project_member(a.project_id, auth.uid())
    ));

-- 11.3 cf_approval_heads: Read access for project members via version -> agreement
DROP POLICY IF EXISTS "Project members can read cf_approval_heads" ON public.cf_approval_heads;
CREATE POLICY "Project members can read cf_approval_heads"
    ON public.cf_approval_heads FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.cf_approval_versions v
        JOIN public.agreements a ON a.id = v.original_agreement_id
        WHERE v.amendment_id = cf_approval_heads.amendment_id
        AND public.is_project_member(a.project_id, auth.uid())
    ));

-- 11.4 cf_decisions: Read access for project members
DROP POLICY IF EXISTS "Project members can read cf_decisions" ON public.cf_decisions;
CREATE POLICY "Project members can read cf_decisions"
    ON public.cf_decisions FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.cf_approval_versions v
        JOIN public.agreements a ON a.id = v.original_agreement_id
        WHERE v.amendment_id = cf_decisions.amendment_id
        AND v.revision = cf_decisions.revision
        AND public.is_project_member(a.project_id, auth.uid())
    ));

-- 11.5 cf_audit: Read access for project members
DROP POLICY IF EXISTS "Project members can read cf_audit" ON public.cf_audit;
CREATE POLICY "Project members can read cf_audit"
    ON public.cf_audit FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.cf_approval_versions v
        JOIN public.agreements a ON a.id = v.original_agreement_id
        WHERE v.amendment_id = cf_audit.amendment_id
        AND v.revision = cf_audit.revision
        AND public.is_project_member(a.project_id, auth.uid())
    ));

-- 11.6 cf_reviews: Read access for project members and reviewer
DROP POLICY IF EXISTS "Project members and reviewer can read cf_reviews" ON public.cf_reviews;
CREATE POLICY "Project members and reviewer can read cf_reviews"
    ON public.cf_reviews FOR SELECT
    USING (
        reviewer_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.cf_artifacts art
            WHERE art.artifact_id = cf_reviews.amendment_id
            AND art.revision = cf_reviews.revision
            AND public.is_project_member(art.project_id, auth.uid())
        )
    );

-- 11.7 cf_assessment_reviews: Read access for project members and reviewer
DROP POLICY IF EXISTS "Project members and reviewer can read cf_assessment_reviews" ON public.cf_assessment_reviews;
CREATE POLICY "Project members and reviewer can read cf_assessment_reviews"
    ON public.cf_assessment_reviews FOR SELECT
    USING (
        reviewer_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.agreements a
            WHERE a.id = cf_assessment_reviews.original_agreement_id
            AND public.is_project_member(a.project_id, auth.uid())
        )
    );

