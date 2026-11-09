-- ============================================================================
-- Freelanker Database Migration 002: Atomic Invitation Acceptance RPC
-- ============================================================================
-- Implements genuine PostgreSQL transactional atomicity for project invitation
-- acceptance with row-level locks, conflict protection, role checks, and audit logging.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.accept_project_invitation(
    p_invitation_id UUID,
    p_user_id UUID,
    p_user_email TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_invitation RECORD;
    v_project RECORD;
    v_existing_member RECORD;
    v_now TIMESTAMPTZ := now();
BEGIN
    -- 1. Lock and fetch the invitation row to prevent concurrent race conditions
    SELECT * INTO v_invitation
    FROM public.invitations
    WHERE id = p_invitation_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invitation not found' USING ERRCODE = 'P0002';
    END IF;

    -- 2. Verify invitation state
    IF v_invitation.status != 'pending' THEN
        RAISE EXCEPTION 'Invitation is no longer pending (current status: %)', v_invitation.status USING ERRCODE = 'P0001';
    END IF;

    IF v_invitation.expires_at <= v_now THEN
        UPDATE public.invitations
        SET status = 'expired', responded_at = v_now
        WHERE id = p_invitation_id;

        RAISE EXCEPTION 'Invitation has expired' USING ERRCODE = 'P0003';
    END IF;

    -- 3. Verify recipient identity against verified Supabase identity
    IF v_invitation.invited_user_id IS NOT NULL AND v_invitation.invited_user_id != p_user_id THEN
        RAISE EXCEPTION 'This invitation was addressed to a different user' USING ERRCODE = '42501';
    END IF;

    IF lower(v_invitation.invited_email) != lower(p_user_email) AND (v_invitation.invited_user_id IS NULL OR v_invitation.invited_user_id != p_user_id) THEN
        RAISE EXCEPTION 'This invitation was addressed to a different email address' USING ERRCODE = '42501';
    END IF;

    -- 4. Lock and fetch the project
    SELECT * INTO v_project
    FROM public.projects
    WHERE id = v_invitation.project_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Associated project not found' USING ERRCODE = 'P0002';
    END IF;

    IF v_project.status NOT IN ('draft', 'invitation_pending') THEN
        RAISE EXCEPTION 'Project is no longer accepting new members (current status: %)', v_project.status USING ERRCODE = 'P0001';
    END IF;

    -- 5. Role and conflict protection: check if counterpart role is already occupied
    IF v_invitation.role = 'freelancer' AND v_project.freelancer_id IS NOT NULL AND v_project.freelancer_id != p_user_id THEN
        RAISE EXCEPTION 'Project already has an assigned freelancer' USING ERRCODE = 'P0004';
    END IF;

    IF v_invitation.role = 'client' AND v_project.client_id IS NOT NULL AND v_project.client_id != p_user_id THEN
        RAISE EXCEPTION 'Project already has an assigned client' USING ERRCODE = 'P0004';
    END IF;

    -- Check if user is already a member
    SELECT * INTO v_existing_member
    FROM public.project_members
    WHERE project_id = v_invitation.project_id AND user_id = p_user_id;

    IF FOUND THEN
        RAISE EXCEPTION 'User is already a member of this project' USING ERRCODE = '23505';
    END IF;

    -- 6. Atomic mutations (executed within this single ACID transaction):
    -- A. Update invitation to accepted
    UPDATE public.invitations
    SET status = 'accepted',
        invited_user_id = p_user_id,
        responded_at = v_now
    WHERE id = p_invitation_id;

    -- B. Insert project member
    INSERT INTO public.project_members (project_id, user_id, role, joined_at)
    VALUES (v_invitation.project_id, p_user_id, v_invitation.role, v_now);

    -- C. Assign counterpart role and advance project status to awaiting_agreement
    IF v_invitation.role = 'freelancer' THEN
        UPDATE public.projects
        SET freelancer_id = p_user_id,
            status = 'awaiting_agreement',
            updated_at = v_now
        WHERE id = v_invitation.project_id;
    ELSIF v_invitation.role = 'client' THEN
        UPDATE public.projects
        SET client_id = p_user_id,
            status = 'awaiting_agreement',
            updated_at = v_now
        WHERE id = v_invitation.project_id;
    END IF;

    -- D. Cancel any other pending invitations for this role on the project
    UPDATE public.invitations
    SET status = 'cancelled',
        responded_at = v_now
    WHERE project_id = v_invitation.project_id
      AND role = v_invitation.role
      AND status = 'pending'
      AND id != p_invitation_id;

    -- E. Record audit logs
    INSERT INTO public.activity_logs (project_id, actor_id, event_type, entity_type, entity_id, new_data)
    VALUES (
        v_invitation.project_id,
        p_user_id,
        'invitation_accepted',
        'invitation',
        p_invitation_id,
        jsonb_build_object('role', v_invitation.role, 'accepted_at', v_now)
    );

    INSERT INTO public.activity_logs (project_id, actor_id, event_type, entity_type, entity_id, new_data)
    VALUES (
        v_invitation.project_id,
        p_user_id,
        'member_added',
        'project_member',
        p_user_id,
        jsonb_build_object('role', v_invitation.role, 'joined_at', v_now)
    );

    RETURN jsonb_build_object(
        'project_id', v_invitation.project_id,
        'invitation_id', p_invitation_id,
        'role', v_invitation.role,
        'user_id', p_user_id,
        'project_status', 'awaiting_agreement'
    );
END;
$$;

REVOKE ALL ON FUNCTION public.accept_project_invitation(UUID, UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.accept_project_invitation(UUID, UUID, TEXT) TO authenticated, service_role;
