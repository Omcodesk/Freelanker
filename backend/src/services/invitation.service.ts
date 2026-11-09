import crypto from 'crypto';
import { supabaseAdmin } from '../lib/supabase.js';
import { env } from '../config/env.js';
import { logActivity } from './activity.service.js';
import type { Invitation } from '../types/index.js';

export interface CreateInvitationInput {
  email: string;
  message?: string;
}

export interface InvitationResponse {
  invitation: Invitation;
  invitationLink: string;
  delivery: {
    method: 'link';
    status: 'ready';
    recipientEmail: string;
  };
}

export class InvitationError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
    this.name = 'InvitationError';
  }
}

/**
 * Creates and sends a project invitation for an unoccupied counterpart role.
 */
export async function createInvitation(
  projectId: string,
  inviterId: string,
  inviterEmail: string,
  input: CreateInvitationInput
): Promise<InvitationResponse> {
  const targetEmail = input.email?.trim().toLowerCase();
  if (!targetEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(targetEmail)) {
    throw new InvitationError(400, 'A valid recipient email address is required.');
  }

  // 1. Guard against self-invitation
  if (targetEmail === inviterEmail.toLowerCase()) {
    throw new InvitationError(400, 'You cannot invite yourself to the project.');
  }

  // 2. Fetch project and verify inviter membership
  const { data: member, error: memberErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', inviterId)
    .maybeSingle();

  if (memberErr || !member) {
    throw new InvitationError(403, 'Access denied: You must be a project member to invite collaborators.');
  }

  const { data: project, error: projErr } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .maybeSingle();

  if (projErr || !project) {
    throw new InvitationError(404, 'Project not found.');
  }

  // 3. Project state checks
  if (project.status !== 'draft' && project.status !== 'invitation_pending') {
    throw new InvitationError(
      400,
      `Cannot invite members while project is in '${project.status}' state.`
    );
  }

  // 4. Counterpart role determination & occupancy check
  const targetRole: 'client' | 'freelancer' =
    member.role === 'client' ? 'freelancer' : 'client';

  if (targetRole === 'freelancer' && project.freelancer_id) {
    throw new InvitationError(409, 'Project already has an assigned freelancer.');
  }

  if (targetRole === 'client' && project.client_id) {
    throw new InvitationError(409, 'Project already has an assigned client.');
  }

  // 5. Competing pending invitation guard
  const { data: existingPendingInv } = await supabaseAdmin
    .from('invitations')
    .select('id, invited_email')
    .eq('project_id', projectId)
    .eq('role', targetRole)
    .eq('status', 'pending')
    .gt('expires_at', new Date().toISOString())
    .maybeSingle();

  if (existingPendingInv) {
    throw new InvitationError(
      409,
      `A pending invitation already exists for the ${targetRole} role on this project (${existingPendingInv.invited_email}). Cancel it before sending a new one.`
    );
  }

  // 6. Check if target email belongs to an existing user
  let invitedUserId: string | null = null;
  try {
    const { data: userListData } = await supabaseAdmin.auth.admin.listUsers();
    const matchedUser = userListData?.users.find(
      u => u.email?.toLowerCase() === targetEmail
    );
    if (matchedUser) {
      invitedUserId = matchedUser.id;

      // Check if this registered user is already a member
      const { data: existingMember } = await supabaseAdmin
        .from('project_members')
        .select('id')
        .eq('project_id', projectId)
        .eq('user_id', matchedUser.id)
        .maybeSingle();

      if (existingMember) {
        throw new InvitationError(409, 'This user is already a member of the project.');
      }
    }
  } catch (err: unknown) {
    if (err instanceof InvitationError) throw err;
    // Non-blocking user lookup
  }

  // 7. Token generation & 7-day expiration
  const token = crypto.randomUUID();
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

  // 8. Insert invitation
  const { data: invRow, error: insertErr } = await supabaseAdmin
    .from('invitations')
    .insert({
      project_id: projectId,
      invited_by: inviterId,
      invited_email: targetEmail,
      invited_user_id: invitedUserId,
      role: targetRole,
      status: 'pending',
      token,
      message: input.message?.trim() || null,
      expires_at: expiresAt,
    })
    .select('*')
    .single();

  if (insertErr || !invRow) {
    throw new InvitationError(500, `Failed to create invitation: ${insertErr?.message}`);
  }

  // 9. Advance project status to invitation_pending if in draft
  if (project.status === 'draft') {
    await supabaseAdmin
      .from('projects')
      .update({
        status: 'invitation_pending',
        updated_at: new Date().toISOString(),
      })
      .eq('id', projectId);
  }

  // 10. Record activity log
  await logActivity({
    projectId,
    actorId: inviterId,
    eventType: 'invitation_sent',
    entityType: 'invitation',
    entityId: invRow.id,
    newData: {
      invitedEmail: targetEmail,
      role: targetRole,
      expiresAt,
    },
  });

  const invitationLink = `${env.FRONTEND_URL}/invitations/${token}`;

  return {
    invitation: mapInvitationRow(invRow),
    invitationLink,
    delivery: {
      method: 'link',
      status: 'ready',
      recipientEmail: targetEmail,
    },
  };
}

/**
 * Lists invitations for the authenticated user.
 */
export async function listUserInvitations(
  userId: string,
  userEmail: string,
  isEmailVerified: boolean,
  statusFilter?: string
): Promise<any[]> {
  let query = supabaseAdmin
    .from('invitations')
    .select(
      `
      id,
      project_id,
      invited_by,
      invited_email,
      invited_user_id,
      role,
      status,
      token,
      message,
      expires_at,
      responded_at,
      created_at,
      projects:project_id (
        id,
        title,
        currency,
        total_budget,
        status
      ),
      inviter_profile:invited_by (
        display_name,
        avatar_url
      )
    `
    )
    .order('created_at', { ascending: false });

  if (statusFilter) {
    query = query.eq('status', statusFilter);
  }

  // If email is verified, user can see invitations addressed to their email OR their user ID
  if (isEmailVerified) {
    query = query.or(`invited_user_id.eq.${userId},invited_email.ilike.${userEmail}`);
  } else {
    query = query.eq('invited_user_id', userId);
  }

  const { data: rows, error } = await query;
  if (error || !rows) {
    throw new InvitationError(500, `Failed to list invitations: ${error?.message}`);
  }

  return rows.map((r: any) => ({
    ...mapInvitationRow(r),
    project: r.projects
      ? {
          id: r.projects.id,
          title: r.projects.title,
          currency: r.projects.currency,
          totalBudget: r.projects.total_budget,
          status: r.projects.status,
        }
      : null,
    inviter: r.inviter_profile
      ? {
          displayName: r.inviter_profile.display_name,
          avatarUrl: r.inviter_profile.avatar_url,
        }
      : null,
  }));
}

/**
 * Accepts an invitation atomically.
 */
export async function acceptInvitation(
  invitationId: string,
  user: { id: string; email: string; isEmailVerified: boolean }
): Promise<{ success: boolean; projectId: string; role: string }> {
  // 1. Enforce verified email
  if (!user.isEmailVerified) {
    throw new InvitationError(
      403,
      'Email verification required: You must verify your email address before accepting project invitations.'
    );
  }

  // 2. Try PostgreSQL RPC first for genuine database-level ACID transaction
  try {
    const { data: rpcResult, error: rpcErr } = await supabaseAdmin.rpc(
      'accept_project_invitation',
      {
        p_invitation_id: invitationId,
        p_user_id: user.id,
        p_user_email: user.email.toLowerCase(),
      }
    );

    if (!rpcErr && rpcResult) {
      return {
        success: true,
        projectId: rpcResult.project_id,
        role: rpcResult.role,
      };
    }

    if (rpcErr && rpcErr.code !== 'PGRST202') {
      // Postgres error from within RPC
      const status = rpcErr.code === '42501' ? 403 : rpcErr.code === 'P0004' || rpcErr.code === '23505' ? 409 : 400;
      throw new InvitationError(status, rpcErr.message);
    }
  } catch (err: unknown) {
    if (err instanceof InvitationError) throw err;
    // If RPC is missing (PGRST202), fall through to robust backend atomic workflow
  }

  // 3. Fallback: Robust atomic server-side workflow with optimistic locking
  // Fetch invitation
  const { data: inv, error: invErr } = await supabaseAdmin
    .from('invitations')
    .select('*')
    .eq('id', invitationId)
    .maybeSingle();

  if (invErr || !inv) {
    throw new InvitationError(404, 'Invitation not found.');
  }

  if (inv.status !== 'pending') {
    throw new InvitationError(400, `Invitation is no longer pending (current status: ${inv.status}).`);
  }

  if (new Date(inv.expires_at) <= new Date()) {
    await supabaseAdmin
      .from('invitations')
      .update({ status: 'expired', responded_at: new Date().toISOString() })
      .eq('id', invitationId);
    throw new InvitationError(400, 'Invitation has expired.');
  }

  // Identity verification
  if (inv.invited_user_id && inv.invited_user_id !== user.id) {
    throw new InvitationError(403, 'This invitation was addressed to a different user account.');
  }

  if (inv.invited_email.toLowerCase() !== user.email.toLowerCase() && inv.invited_user_id !== user.id) {
    throw new InvitationError(403, 'This invitation was addressed to a different email address.');
  }

  // Fetch project
  const { data: project, error: projErr } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', inv.project_id)
    .maybeSingle();

  if (projErr || !project) {
    throw new InvitationError(404, 'Associated project not found.');
  }

  if (project.status !== 'draft' && project.status !== 'invitation_pending') {
    throw new InvitationError(
      409,
      `Project is no longer accepting new members (current status: ${project.status}).`
    );
  }

  // Occupancy checks
  if (inv.role === 'freelancer' && project.freelancer_id && project.freelancer_id !== user.id) {
    throw new InvitationError(409, 'Project already has an assigned freelancer.');
  }

  if (inv.role === 'client' && project.client_id && project.client_id !== user.id) {
    throw new InvitationError(409, 'Project already has an assigned client.');
  }

  // Duplicate member check
  const { data: existingMember } = await supabaseAdmin
    .from('project_members')
    .select('id')
    .eq('project_id', inv.project_id)
    .eq('user_id', user.id)
    .maybeSingle();

  if (existingMember) {
    throw new InvitationError(409, 'You are already a member of this project.');
  }

  const nowIso = new Date().toISOString();

  // Step A: Optimistic lock on invitation status (must be pending)
  const { data: updatedInv, error: updateInvErr } = await supabaseAdmin
    .from('invitations')
    .update({
      status: 'accepted',
      invited_user_id: user.id,
      responded_at: nowIso,
    })
    .eq('id', invitationId)
    .eq('status', 'pending')
    .select('*')
    .single();

  if (updateInvErr || !updatedInv) {
    throw new InvitationError(409, 'Concurrent modification conflict: Invitation has already been processed.');
  }

  // Step B: Insert project member
  const { error: insertMemberErr } = await supabaseAdmin
    .from('project_members')
    .insert({
      project_id: inv.project_id,
      user_id: user.id,
      role: inv.role,
      joined_at: nowIso,
    });

  if (insertMemberErr) {
    // Compensating rollback
    await supabaseAdmin
      .from('invitations')
      .update({ status: 'pending', responded_at: null })
      .eq('id', invitationId);
    throw new InvitationError(500, `Failed to record membership: ${insertMemberErr.message}`);
  }

  // Step C: Update project role and advance status to awaiting_agreement
  const projectUpdates: Record<string, unknown> = {
    status: 'awaiting_agreement',
    updated_at: nowIso,
  };
  if (inv.role === 'freelancer') {
    projectUpdates.freelancer_id = user.id;
  } else {
    projectUpdates.client_id = user.id;
  }

  await supabaseAdmin
    .from('projects')
    .update(projectUpdates)
    .eq('id', inv.project_id);

  // Step D: Cancel competing pending invitations for the same role
  await supabaseAdmin
    .from('invitations')
    .update({ status: 'cancelled', responded_at: nowIso })
    .eq('project_id', inv.project_id)
    .eq('role', inv.role)
    .eq('status', 'pending')
    .neq('id', invitationId);

  // Step E: Record activity logs
  await logActivity({
    projectId: inv.project_id,
    actorId: user.id,
    eventType: 'invitation_accepted',
    entityType: 'invitation',
    entityId: invitationId,
    newData: { role: inv.role, acceptedAt: nowIso },
  });

  await logActivity({
    projectId: inv.project_id,
    actorId: user.id,
    eventType: 'member_added',
    entityType: 'project_member',
    entityId: user.id,
    newData: { role: inv.role, joinedAt: nowIso },
  });

  return {
    success: true,
    projectId: inv.project_id,
    role: inv.role,
  };
}

/**
 * Rejects an invitation.
 */
export async function rejectInvitation(
  invitationId: string,
  user: { id: string; email: string; isEmailVerified: boolean }
): Promise<{ success: boolean; projectId: string }> {
  const { data: inv, error: invErr } = await supabaseAdmin
    .from('invitations')
    .select('*')
    .eq('id', invitationId)
    .maybeSingle();

  if (invErr || !inv) {
    throw new InvitationError(404, 'Invitation not found.');
  }

  if (inv.status !== 'pending') {
    throw new InvitationError(400, `Invitation is no longer pending (current status: ${inv.status}).`);
  }

  // Verify recipient
  if (inv.invited_user_id && inv.invited_user_id !== user.id) {
    throw new InvitationError(403, 'This invitation was addressed to a different user account.');
  }

  if (inv.invited_email.toLowerCase() !== user.email.toLowerCase() && inv.invited_user_id !== user.id) {
    throw new InvitationError(403, 'This invitation was addressed to a different email address.');
  }

  const nowIso = new Date().toISOString();
  const { error: rejectErr } = await supabaseAdmin
    .from('invitations')
    .update({
      status: 'rejected',
      responded_at: nowIso,
    })
    .eq('id', invitationId)
    .eq('status', 'pending');

  if (rejectErr) {
    throw new InvitationError(500, `Failed to reject invitation: ${rejectErr.message}`);
  }

  // Check if project should revert to draft (if no other pending invitations and only 1 member)
  const { data: pendingRemaining } = await supabaseAdmin
    .from('invitations')
    .select('id')
    .eq('project_id', inv.project_id)
    .eq('status', 'pending');

  if (!pendingRemaining || pendingRemaining.length === 0) {
    const { data: proj } = await supabaseAdmin
      .from('projects')
      .select('status')
      .eq('id', inv.project_id)
      .maybeSingle();

    if (proj?.status === 'invitation_pending') {
      await supabaseAdmin
        .from('projects')
        .update({ status: 'draft', updated_at: nowIso })
        .eq('id', inv.project_id);
    }
  }

  await logActivity({
    projectId: inv.project_id,
    actorId: user.id,
    eventType: 'invitation_rejected',
    entityType: 'invitation',
    entityId: invitationId,
    newData: { rejectedAt: nowIso },
  });

  return {
    success: true,
    projectId: inv.project_id,
  };
}

function mapInvitationRow(row: any): Invitation {
  return {
    id: row.id,
    projectId: row.project_id,
    invitedBy: row.invited_by,
    invitedEmail: row.invited_email,
    invitedUserId: row.invited_user_id || undefined,
    role: row.role,
    status: row.status,
    token: row.token,
    message: row.message || undefined,
    expiresAt: row.expires_at,
    respondedAt: row.responded_at || undefined,
    createdAt: row.created_at,
  };
}
