-- =============================================================================
-- Freelanker — Initial Database Migration
-- Version: 1.0 (Corresponds to Schema Design v2.0)
-- Target: Supabase PostgreSQL (Postgres 15+)
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 1. ENUM TYPES
-- =============================================================================

DO $$ BEGIN
    CREATE TYPE project_member_role AS ENUM ('client', 'freelancer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE project_status AS ENUM (
      'draft', 'invitation_pending', 'awaiting_agreement',
      'active', 'in_progress', 'under_review',
      'completed', 'cancelled', 'disputed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE agreement_status AS ENUM (
      'draft', 'sent_for_review', 'changes_requested',
      'approved', 'active', 'completed', 'cancelled'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE milestone_status AS ENUM (
      'not_started', 'awaiting_prepayment', 'in_progress',
      'submitted', 'under_review', 'revision_requested',
      'approved', 'payment_pending', 'paid', 'disputed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'rejected', 'expired', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE deliverable_status AS ENUM (
      'submitted', 'under_review', 'revision_requested', 'approved', 'rejected'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE payment_arrangement AS ENUM (
      'upfront', 'milestone_prepayment', 'payment_after_approval'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE payment_status AS ENUM (
      'pending', 'completed', 'failed', 'cancelled', 'refunded'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE dispute_status AS ENUM (
      'open', 'under_review', 'awaiting_response',
      'resolution_proposed', 'resolved', 'closed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE activity_event_type AS ENUM (
      'project_created', 'project_status_changed',
      'agreement_created', 'agreement_version_created', 'agreement_approved', 'agreement_activated',
      'milestone_created', 'milestone_status_changed',
      'deliverable_submitted', 'deliverable_approved', 'deliverable_revision_requested',
      'payment_initiated', 'payment_completed', 'payment_failed',
      'dispute_opened', 'dispute_resolved',
      'invitation_sent', 'invitation_accepted', 'invitation_rejected',
      'message_sent', 'member_added'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================================
-- 2. TABLES
-- =============================================================================

-- 2.1 PROFILES (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    headline TEXT,
    bio TEXT,
    avatar_url TEXT,
    skills TEXT[] NOT NULL DEFAULT '{}',
    portfolio_links TEXT[] NOT NULL DEFAULT '{}',
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.2 PROJECTS
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    status project_status NOT NULL DEFAULT 'draft',
    initiator_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    client_id UUID REFERENCES public.profiles(id) ON DELETE RESTRICT,
    freelancer_id UUID REFERENCES public.profiles(id) ON DELETE RESTRICT,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    total_budget NUMERIC(12,2) CHECK (total_budget IS NULL OR total_budget > 0),
    payment_arrangement payment_arrangement,
    ai_scope_data JSONB,
    review_period_days INT NOT NULL DEFAULT 3 CHECK (review_period_days > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.3 PROJECT MEMBERS
CREATE TABLE IF NOT EXISTS public.project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role project_member_role NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_project_member UNIQUE (project_id, user_id)
);

-- 2.4 INVITATIONS
CREATE TABLE IF NOT EXISTS public.invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    invited_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    invited_email TEXT NOT NULL,
    invited_user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    role project_member_role NOT NULL,
    status invitation_status NOT NULL DEFAULT 'pending',
    token UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    message TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.5 AGREEMENTS (with versioning)
CREATE TABLE IF NOT EXISTS public.agreements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    version_number INT NOT NULL DEFAULT 1 CHECK (version_number >= 1),
    previous_version_id UUID REFERENCES public.agreements(id) ON DELETE RESTRICT,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    status agreement_status NOT NULL DEFAULT 'draft',
    title TEXT NOT NULL,
    scope_of_work TEXT,
    deliverables_text TEXT,
    acceptance_criteria TEXT,
    payment_arrangement payment_arrangement NOT NULL,
    total_amount NUMERIC(12,2) NOT NULL CHECK (total_amount > 0),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    revision_limit INT CHECK (revision_limit IS NULL OR revision_limit >= 0),
    review_period_days INT NOT NULL DEFAULT 3 CHECK (review_period_days > 0),
    start_date DATE,
    end_date DATE,
    additional_terms TEXT,
    is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
    pdf_url TEXT,
    ai_summary TEXT,
    content_snapshot JSONB,
    client_approved_at TIMESTAMPTZ,
    freelancer_approved_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    superseded_at TIMESTAMPTZ,
    created_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_project_agreement_version UNIQUE (project_id, version_number)
);

-- Partial unique index: only one agreement per project can be is_current = TRUE
CREATE UNIQUE INDEX IF NOT EXISTS idx_agreements_only_one_current 
  ON public.agreements (project_id) 
  WHERE (is_current = TRUE);

-- 2.6 AGREEMENT APPROVALS
CREATE TABLE IF NOT EXISTS public.agreement_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agreement_id UUID NOT NULL REFERENCES public.agreements(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    role project_member_role NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('approved', 'changes_requested', 'withdrawn')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.7 MILESTONES
CREATE TABLE IF NOT EXISTS public.milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status milestone_status NOT NULL DEFAULT 'not_started',
    amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (amount >= 0),
    order_index INT NOT NULL DEFAULT 0,
    due_date DATE,
    is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.8 TASKS
CREATE TABLE IF NOT EXISTS public.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES public.milestones(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    status task_status NOT NULL DEFAULT 'todo',
    assigned_to UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    due_date DATE,
    order_index INT NOT NULL DEFAULT 0,
    is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.9 DELIVERABLES
CREATE TABLE IF NOT EXISTS public.deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES public.milestones(id) ON DELETE SET NULL,
    submitted_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    status deliverable_status NOT NULL DEFAULT 'submitted',
    title TEXT NOT NULL,
    description TEXT,
    submission_note TEXT,
    file_urls TEXT[] NOT NULL DEFAULT '{}',
    link_url TEXT,
    version INT NOT NULL DEFAULT 1 CHECK (version >= 1),
    parent_id UUID REFERENCES public.deliverables(id) ON DELETE RESTRICT,
    review_deadline TIMESTAMPTZ,
    client_feedback TEXT,
    ai_analysis JSONB,
    reviewed_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.10 MESSAGES
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    content TEXT NOT NULL,
    file_urls TEXT[] NOT NULL DEFAULT '{}',
    is_ai_summary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.11 PAYMENTS
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE RESTRICT,
    milestone_id UUID REFERENCES public.milestones(id) ON DELETE RESTRICT,
    payer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    payee_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    amount_snapshot NUMERIC(12,2) NOT NULL CHECK (amount_snapshot > 0),
    currency_snapshot CHAR(3) NOT NULL DEFAULT 'USD',
    status payment_status NOT NULL DEFAULT 'pending',
    arrangement payment_arrangement NOT NULL,
    paypal_order_id TEXT UNIQUE,
    paypal_capture_id TEXT UNIQUE,
    paypal_response JSONB,
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_upfront_no_milestone CHECK (
      (arrangement = 'upfront' AND milestone_id IS NULL) OR
      (arrangement != 'upfront' AND milestone_id IS NOT NULL)
    )
);

-- 2.12 PAYMENT EVENTS
CREATE TABLE IF NOT EXISTS public.payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES public.payments(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL CHECK (event_type IN (
      'order_created', 'capture_attempted',
      'capture_success', 'capture_failed',
      'webhook_received', 'refunded', 'idempotency_duplicate'
    )),
    old_status payment_status,
    new_status payment_status,
    paypal_event_id TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_events_paypal_event_id_unique
  ON public.payment_events (paypal_event_id)
  WHERE paypal_event_id IS NOT NULL;

-- 2.13 DISPUTES
CREATE TABLE IF NOT EXISTS public.disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE RESTRICT,
    raised_by UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    against_user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    status dispute_status NOT NULL DEFAULT 'open',
    reason TEXT NOT NULL,
    description TEXT,
    ai_summary TEXT,
    resolution_notes TEXT,
    resolved_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_no_self_dispute CHECK (raised_by != against_user_id)
);

-- 2.14 ACTIVITY LOGS (Append-only audit trail)
CREATE TABLE IF NOT EXISTS public.activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
    actor_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    event_type activity_event_type NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    old_data JSONB,
    new_data JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.15 NOTIFICATIONS
CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN (
      'invitation', 'agreement_review', 'deliverable_submitted',
      'payment_received', 'revision_requested',
      'dispute_opened', 'reminder'
    )),
    title TEXT NOT NULL,
    body TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    entity_type TEXT,
    entity_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at TIMESTAMPTZ
);

-- =============================================================================
-- 3. VIEWS
-- =============================================================================

-- Safe marketplace projection:
-- - Exposes non-sensitive public discovery fields only (is_admin excluded)
-- - security_barrier = true prevents optimizer leakage through user-defined functions
-- - security_invoker is false (definer default) so discovery is not blocked by profiles RLS
CREATE OR REPLACE VIEW public.public_freelancer_profiles
WITH (security_barrier = true) AS
SELECT
    id,
    display_name,
    headline,
    bio,
    avatar_url,
    skills,
    portfolio_links,
    is_available,
    created_at
FROM public.profiles
WHERE is_available = TRUE;

-- =============================================================================
-- 4. SECURITY DEFINER HELPER FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION public.is_project_member(p_project_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.project_members
    WHERE project_id = p_project_id
      AND user_id = p_user_id
  );
$$;

CREATE OR REPLACE FUNCTION public.get_project_member_role(p_project_id UUID, p_user_id UUID)
RETURNS project_member_role
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT role FROM public.project_members
  WHERE project_id = p_project_id
    AND user_id = p_user_id
  LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.is_platform_admin(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT COALESCE(is_admin, FALSE)
  FROM public.profiles
  WHERE id = p_user_id;
$$;

REVOKE ALL ON FUNCTION public.is_project_member(UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_project_member(UUID, UUID) TO authenticated;

REVOKE ALL ON FUNCTION public.get_project_member_role(UUID, UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_project_member_role(UUID, UUID) TO authenticated;

REVOKE ALL ON FUNCTION public.is_platform_admin(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_platform_admin(UUID) TO authenticated;

-- =============================================================================
-- 5. TRIGGERS & INTEGRITY ENFORCEMENT FUNCTIONS
-- =============================================================================

-- Generic updated_at timestamp updater
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Auto-create profile upon auth.users creation
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name, avatar_url)
    VALUES (
        NEW.id,
        COALESCE(
            NULLIF(NEW.raw_user_meta_data->>'full_name', ''),
            NULLIF(NEW.raw_user_meta_data->>'name', ''),
            NULLIF(split_part(NEW.email, '@', 1), ''),
            'Freelanker User'
        ),
        NEW.raw_user_meta_data->>'avatar_url'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_on_auth_user_created ON auth.users;
CREATE TRIGGER trg_on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Cross-project integrity: task milestone check
CREATE OR REPLACE FUNCTION public.validate_task_milestone_project()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_milestone_project_id UUID;
BEGIN
    IF NEW.milestone_id IS NOT NULL THEN
        SELECT project_id INTO v_milestone_project_id
        FROM public.milestones
        WHERE id = NEW.milestone_id;

        IF v_milestone_project_id IS NULL OR v_milestone_project_id != NEW.project_id THEN
            RAISE EXCEPTION 'Milestone does not belong to the same project as this task';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_task_milestone_same_project ON public.tasks;
CREATE TRIGGER trg_task_milestone_same_project
    BEFORE INSERT OR UPDATE ON public.tasks
    FOR EACH ROW EXECUTE FUNCTION public.validate_task_milestone_project();

-- Cross-project integrity: deliverable check (parent & milestone & version)
CREATE OR REPLACE FUNCTION public.validate_deliverable_integrity()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_milestone_project_id UUID;
    v_parent_project_id UUID;
    v_parent_version INT;
BEGIN
    -- Validate milestone belongs to same project
    IF NEW.milestone_id IS NOT NULL THEN
        SELECT project_id INTO v_milestone_project_id
        FROM public.milestones
        WHERE id = NEW.milestone_id;

        IF v_milestone_project_id IS NULL OR v_milestone_project_id != NEW.project_id THEN
            RAISE EXCEPTION 'Milestone does not belong to the same project as this deliverable';
        END IF;
    END IF;

    -- Validate parent deliverable belongs to same project and version increments
    IF NEW.parent_id IS NOT NULL THEN
        SELECT project_id, version INTO v_parent_project_id, v_parent_version
        FROM public.deliverables
        WHERE id = NEW.parent_id;

        IF v_parent_project_id IS NULL OR v_parent_project_id != NEW.project_id THEN
            RAISE EXCEPTION 'Deliverable revision chain cannot cross projects';
        END IF;

        IF NEW.version <= v_parent_version THEN
            NEW.version = v_parent_version + 1;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_deliverable_integrity ON public.deliverables;
CREATE TRIGGER trg_deliverable_integrity
    BEFORE INSERT OR UPDATE ON public.deliverables
    FOR EACH ROW EXECUTE FUNCTION public.validate_deliverable_integrity();

-- Validate agreement approval membership
CREATE OR REPLACE FUNCTION public.validate_agreement_approval_member()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_project_id UUID;
    v_actual_role project_member_role;
BEGIN
    SELECT project_id INTO v_project_id
    FROM public.agreements
    WHERE id = NEW.agreement_id;

    IF v_project_id IS NULL THEN
        RAISE EXCEPTION 'Agreement not found';
    END IF;

    SELECT role INTO v_actual_role
    FROM public.project_members
    WHERE project_id = v_project_id AND user_id = NEW.user_id;

    IF v_actual_role IS NULL THEN
        RAISE EXCEPTION 'Approving user is not a member of the project';
    END IF;

    IF v_actual_role != NEW.role THEN
        RAISE EXCEPTION 'Approving role does not match registered project membership role';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_agreement_approval_member_check ON public.agreement_approvals;
CREATE TRIGGER trg_agreement_approval_member_check
    BEFORE INSERT ON public.agreement_approvals
    FOR EACH ROW EXECUTE FUNCTION public.validate_agreement_approval_member();

-- Validate dispute participants are project members
CREATE OR REPLACE FUNCTION public.validate_dispute_members()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    IF NOT public.is_project_member(NEW.project_id, NEW.raised_by) THEN
        RAISE EXCEPTION 'Dispute raiser is not a project member';
    END IF;

    IF NOT public.is_project_member(NEW.project_id, NEW.against_user_id) THEN
        RAISE EXCEPTION 'Disputed counterparty is not a project member';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_dispute_member_check ON public.disputes;
CREATE TRIGGER trg_dispute_member_check
    BEFORE INSERT ON public.disputes
    FOR EACH ROW EXECUTE FUNCTION public.validate_dispute_members();

-- Immutability of activated agreements (all agreed terms protected)
CREATE OR REPLACE FUNCTION public.prevent_activated_agreement_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    IF OLD.activated_at IS NOT NULL THEN
        IF NEW.content_snapshot IS DISTINCT FROM OLD.content_snapshot OR
           NEW.total_amount IS DISTINCT FROM OLD.total_amount OR
           NEW.currency IS DISTINCT FROM OLD.currency OR
           NEW.version_number IS DISTINCT FROM OLD.version_number OR
           NEW.payment_arrangement IS DISTINCT FROM OLD.payment_arrangement OR
           NEW.title IS DISTINCT FROM OLD.title OR
           NEW.scope_of_work IS DISTINCT FROM OLD.scope_of_work OR
           NEW.deliverables_text IS DISTINCT FROM OLD.deliverables_text OR
           NEW.acceptance_criteria IS DISTINCT FROM OLD.acceptance_criteria OR
           NEW.additional_terms IS DISTINCT FROM OLD.additional_terms OR
           NEW.revision_limit IS DISTINCT FROM OLD.revision_limit OR
           NEW.review_period_days IS DISTINCT FROM OLD.review_period_days OR
           NEW.start_date IS DISTINCT FROM OLD.start_date OR
           NEW.end_date IS DISTINCT FROM OLD.end_date OR
           NEW.client_approved_at IS DISTINCT FROM OLD.client_approved_at OR
           NEW.freelancer_approved_at IS DISTINCT FROM OLD.freelancer_approved_at THEN
            RAISE EXCEPTION 'Activated agreement terms are immutable. Create a new version for amendments.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_agreement_immutable_after_activation ON public.agreements;
CREATE TRIGGER trg_agreement_immutable_after_activation
    BEFORE UPDATE ON public.agreements
    FOR EACH ROW EXECUTE FUNCTION public.prevent_activated_agreement_mutation();

-- Auto-calculate review deadline on deliverable submission
CREATE OR REPLACE FUNCTION public.calculate_deliverable_review_deadline()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
DECLARE
    v_review_days INT;
BEGIN
    IF NEW.review_deadline IS NULL THEN
        SELECT review_period_days INTO v_review_days
        FROM public.projects
        WHERE id = NEW.project_id;

        NEW.review_deadline = now() + (COALESCE(v_review_days, 3) * INTERVAL '1 day');
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_review_deadline ON public.deliverables;
CREATE TRIGGER trg_set_review_deadline
    BEFORE INSERT ON public.deliverables
    FOR EACH ROW EXECUTE FUNCTION public.calculate_deliverable_review_deadline();

-- Register set_updated_at triggers
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN SELECT unnest(ARRAY['profiles', 'projects', 'agreements', 'milestones', 'tasks', 'deliverables', 'disputes'])
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_set_updated_at ON public.%I;', t);
        EXECUTE format('CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();', t);
    END LOOP;
END $$;

-- =============================================================================
-- 6. INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_profiles_skills ON public.profiles USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_projects_client_id ON public.projects (client_id);
CREATE INDEX IF NOT EXISTS idx_projects_freelancer_id ON public.projects (freelancer_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects (status);

CREATE INDEX IF NOT EXISTS idx_project_members_user_id ON public.project_members (user_id);
CREATE INDEX IF NOT EXISTS idx_project_members_project_role ON public.project_members (project_id, role);

CREATE INDEX IF NOT EXISTS idx_invitations_email ON public.invitations (invited_email);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON public.invitations (token);
CREATE INDEX IF NOT EXISTS idx_invitations_proj_status ON public.invitations (project_id, status);

CREATE INDEX IF NOT EXISTS idx_agreements_proj_version ON public.agreements (project_id, version_number);

CREATE INDEX IF NOT EXISTS idx_milestones_proj_order ON public.milestones (project_id, order_index);

CREATE INDEX IF NOT EXISTS idx_tasks_proj_milestone ON public.tasks (project_id, milestone_id);

CREATE INDEX IF NOT EXISTS idx_deliverables_proj_milestone ON public.deliverables (project_id, milestone_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_parent_id ON public.deliverables (parent_id) WHERE parent_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_messages_proj_created ON public.messages (project_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payments_proj_milestone ON public.payments (project_id, milestone_id);
CREATE INDEX IF NOT EXISTS idx_payments_paypal_order ON public.payments (paypal_order_id);

CREATE INDEX IF NOT EXISTS idx_payment_events_payment_created ON public.payment_events (payment_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_disputes_proj_status ON public.disputes (project_id, status);

CREATE INDEX IF NOT EXISTS idx_activity_logs_proj_created ON public.activity_logs (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_entity ON public.activity_logs (entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON public.notifications (user_id, is_read, created_at DESC);

-- =============================================================================
-- 7. COLUMN PERMISSIONS & ROLE GRANTS
-- =============================================================================

-- Profiles column security
REVOKE ALL ON TABLE public.profiles FROM authenticated, anon;

-- Explicitly allow authenticated users to view safe profile columns
GRANT SELECT (id, display_name, headline, bio, avatar_url, skills, portfolio_links, is_available, created_at, updated_at)
  ON TABLE public.profiles TO authenticated;

-- Allow authenticated users to update their own presentation fields (is_admin excluded!)
GRANT UPDATE (display_name, headline, bio, avatar_url, skills, portfolio_links, is_available)
  ON TABLE public.profiles TO authenticated;

-- Allow marketplace view access (discovery permitted for guests and logged-in users)
GRANT SELECT ON public.public_freelancer_profiles TO authenticated, anon;

-- Milestones column security: authenticated users can read, but can only update work descriptors directly (creation and financial fields are backend-only)
GRANT SELECT ON TABLE public.milestones TO authenticated;
GRANT UPDATE (title, description, order_index, due_date) ON TABLE public.milestones TO authenticated;

-- =============================================================================
-- 8. ROW LEVEL SECURITY (RLS)
-- =============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agreements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agreement_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deliverables ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disputes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- 8.1 PROFILES POLICIES
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own" ON public.profiles
    FOR SELECT TO authenticated
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own" ON public.profiles
    FOR UPDATE TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- 8.2 PROJECT MEMBERS POLICIES (Non-recursive!)
DROP POLICY IF EXISTS "project_members_select" ON public.project_members;
CREATE POLICY "project_members_select" ON public.project_members
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

-- 8.3 PROJECTS POLICIES
DROP POLICY IF EXISTS "projects_select_member" ON public.projects;
CREATE POLICY "projects_select_member" ON public.projects
    FOR SELECT TO authenticated
    USING (public.is_project_member(id, auth.uid()));

DROP POLICY IF EXISTS "projects_insert_auth" ON public.projects;
CREATE POLICY "projects_insert_auth" ON public.projects
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = initiator_id);

-- 8.4 INVITATIONS POLICIES
DROP POLICY IF EXISTS "invitations_select" ON public.invitations;
CREATE POLICY "invitations_select" ON public.invitations
    FOR SELECT TO authenticated
    USING (
      auth.uid() = invited_user_id OR
      auth.uid() = invited_by OR
      public.is_project_member(project_id, auth.uid())
    );

-- 8.5 AGREEMENTS POLICIES
DROP POLICY IF EXISTS "agreements_select_member" ON public.agreements;
CREATE POLICY "agreements_select_member" ON public.agreements
    FOR SELECT TO authenticated
    USING (public.is_project_member(project_id, auth.uid()));

-- 8.6 AGREEMENT APPROVALS POLICIES
DROP POLICY IF EXISTS "agreement_approvals_select_member" ON public.agreement_approvals;
CREATE POLICY "agreement_approvals_select_member" ON public.agreement_approvals
    FOR SELECT TO authenticated
    USING (
      EXISTS (
        SELECT 1 FROM public.agreements a
        WHERE a.id = agreement_id AND public.is_project_member(a.project_id, auth.uid())
      )
    );

-- 8.7 MILESTONES POLICIES
DROP POLICY IF EXISTS "milestones_select_member" ON public.milestones;
CREATE POLICY "milestones_select_member" ON public.milestones
    FOR SELECT TO authenticated
    USING (public.is_project_member(project_id, auth.uid()));

DROP POLICY IF EXISTS "milestones_update_member" ON public.milestones;
CREATE POLICY "milestones_update_member" ON public.milestones
    FOR UPDATE TO authenticated
    USING (public.is_project_member(project_id, auth.uid()))
    WITH CHECK (public.is_project_member(project_id, auth.uid()));

-- 8.8 TASKS POLICIES
DROP POLICY IF EXISTS "tasks_select_member" ON public.tasks;
CREATE POLICY "tasks_select_member" ON public.tasks
    FOR SELECT TO authenticated
    USING (public.is_project_member(project_id, auth.uid()));

DROP POLICY IF EXISTS "tasks_insert_member" ON public.tasks;
CREATE POLICY "tasks_insert_member" ON public.tasks
    FOR INSERT TO authenticated
    WITH CHECK (public.is_project_member(project_id, auth.uid()));

DROP POLICY IF EXISTS "tasks_update_member" ON public.tasks;
CREATE POLICY "tasks_update_member" ON public.tasks
    FOR UPDATE TO authenticated
    USING (public.is_project_member(project_id, auth.uid()))
    WITH CHECK (public.is_project_member(project_id, auth.uid()));

-- 8.9 DELIVERABLES POLICIES
DROP POLICY IF EXISTS "deliverables_select_member" ON public.deliverables;
CREATE POLICY "deliverables_select_member" ON public.deliverables
    FOR SELECT TO authenticated
    USING (public.is_project_member(project_id, auth.uid()));

-- 8.10 MESSAGES POLICIES
DROP POLICY IF EXISTS "messages_select_member" ON public.messages;
CREATE POLICY "messages_select_member" ON public.messages
    FOR SELECT TO authenticated
    USING (public.is_project_member(project_id, auth.uid()));

DROP POLICY IF EXISTS "messages_insert_member" ON public.messages;
CREATE POLICY "messages_insert_member" ON public.messages
    FOR INSERT TO authenticated
    WITH CHECK (
      public.is_project_member(project_id, auth.uid()) AND
      auth.uid() = sender_id
    );

-- 8.11 PAYMENTS POLICIES (Read-only for members; writes exclusively via backend)
DROP POLICY IF EXISTS "payments_select_member" ON public.payments;
CREATE POLICY "payments_select_member" ON public.payments
    FOR SELECT TO authenticated
    USING (public.is_project_member(project_id, auth.uid()));

-- 8.12 PAYMENT EVENTS POLICIES (Read-only for project members)
DROP POLICY IF EXISTS "payment_events_select_member" ON public.payment_events;
CREATE POLICY "payment_events_select_member" ON public.payment_events
    FOR SELECT TO authenticated
    USING (
      EXISTS (
        SELECT 1 FROM public.payments p
        WHERE p.id = payment_id AND public.is_project_member(p.project_id, auth.uid())
      )
    );

-- 8.13 DISPUTES POLICIES
DROP POLICY IF EXISTS "disputes_select_member_or_admin" ON public.disputes;
CREATE POLICY "disputes_select_member_or_admin" ON public.disputes
    FOR SELECT TO authenticated
    USING (
      public.is_project_member(project_id, auth.uid()) OR
      public.is_platform_admin(auth.uid())
    );

DROP POLICY IF EXISTS "disputes_insert_member" ON public.disputes;
CREATE POLICY "disputes_insert_member" ON public.disputes
    FOR INSERT TO authenticated
    WITH CHECK (
      public.is_project_member(project_id, auth.uid()) AND
      auth.uid() = raised_by
    );

-- 8.14 ACTIVITY LOGS POLICIES (Append-only; viewable by project members or platform admin)
DROP POLICY IF EXISTS "activity_logs_select" ON public.activity_logs;
CREATE POLICY "activity_logs_select" ON public.activity_logs
    FOR SELECT TO authenticated
    USING (
      (project_id IS NOT NULL AND public.is_project_member(project_id, auth.uid())) OR
      public.is_platform_admin(auth.uid())
    );

-- 8.15 NOTIFICATIONS POLICIES
DROP POLICY IF EXISTS "notifications_select_own" ON public.notifications;
CREATE POLICY "notifications_select_own" ON public.notifications
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "notifications_update_own" ON public.notifications;
CREATE POLICY "notifications_update_own" ON public.notifications
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
