import { supabaseAdmin } from '../lib/supabase.js';
import { logActivity } from './activity.service.js';
import { mapMilestoneRow } from './milestone.service.js';
import type {
  Project,
  ProjectMember,
  Milestone,
  ProjectStatus,
  PaymentArrangement,
} from '../types/index.js';

export interface CreateProjectInput {
  title: string;
  description?: string;
  role: 'client' | 'freelancer';
  currency?: string;
  totalBudget?: number;
  paymentArrangement?: PaymentArrangement;
  reviewPeriodDays?: number;
  aiScopeData?: Record<string, unknown>;
}

export interface UpdateProjectInput {
  title?: string;
  description?: string;
  currency?: string;
  totalBudget?: number;
  paymentArrangement?: PaymentArrangement;
  reviewPeriodDays?: number;
}

export interface ProjectDetailResponse {
  project: Project;
  currentUserRole: 'client' | 'freelancer';
  members: Array<{
    id: string;
    userId: string;
    role: 'client' | 'freelancer';
    joinedAt: string;
    profile: {
      displayName: string;
      avatarUrl?: string;
    };
  }>;
  activeInvitation?: {
    id: string;
    invitedEmail: string;
    role: 'client' | 'freelancer';
    status: string;
    expiresAt: string;
    createdAt: string;
  } | null;
  milestones: Milestone[];
}

export class ProjectError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
    this.name = 'ProjectError';
  }
}

/**
 * Creates a project with the authenticated user as initiator and first member.
 */
export async function createProject(
  initiatorId: string,
  input: CreateProjectInput
): Promise<{ project: Project; membership: ProjectMember }> {
  const title = input.title?.trim();
  if (!title) {
    throw new ProjectError(400, 'Project title is required.');
  }

  if (title.length > 200) {
    throw new ProjectError(400, 'Project title cannot exceed 200 characters.');
  }

  if (input.role !== 'client' && input.role !== 'freelancer') {
    throw new ProjectError(400, "Role must be either 'client' or 'freelancer'.");
  }

  if (input.totalBudget !== undefined && input.totalBudget !== null) {
    if (typeof input.totalBudget !== 'number' || input.totalBudget <= 0) {
      throw new ProjectError(400, 'Total budget must be a positive number.');
    }
  }

  const reviewPeriodDays = input.reviewPeriodDays ?? 3;
  if (!Number.isInteger(reviewPeriodDays) || reviewPeriodDays < 1) {
    throw new ProjectError(400, 'Review period days must be an integer greater than or equal to 1.');
  }

  const currency = (input.currency?.trim() || 'USD').toUpperCase().slice(0, 3);

  // 1. Insert Project
  const clientId = input.role === 'client' ? initiatorId : null;
  const freelancerId = input.role === 'freelancer' ? initiatorId : null;

  const { data: projectRow, error: projectError } = await supabaseAdmin
    .from('projects')
    .insert({
      title,
      description: input.description?.trim() || null,
      status: 'draft',
      initiator_id: initiatorId,
      client_id: clientId,
      freelancer_id: freelancerId,
      currency,
      total_budget: input.totalBudget ?? null,
      payment_arrangement: input.paymentArrangement ?? null,
      ai_scope_data: input.aiScopeData ?? null,
      review_period_days: reviewPeriodDays,
    })
    .select('*')
    .single();

  if (projectError || !projectRow) {
    throw new ProjectError(500, `Failed to create project: ${projectError?.message || 'Database error'}`);
  }

  // 2. Insert Initiator Membership
  const { data: memberRow, error: memberError } = await supabaseAdmin
    .from('project_members')
    .insert({
      project_id: projectRow.id,
      user_id: initiatorId,
      role: input.role,
    })
    .select('*')
    .single();

  if (memberError || !memberRow) {
    // Rollback project creation if membership insert fails
    await supabaseAdmin.from('projects').delete().eq('id', projectRow.id);
    throw new ProjectError(500, `Failed to initialize project membership: ${memberError?.message}`);
  }

  // 3. Record Audit Log
  await logActivity({
    projectId: projectRow.id,
    actorId: initiatorId,
    eventType: 'project_created',
    entityType: 'project',
    entityId: projectRow.id,
    newData: {
      title: projectRow.title,
      role: input.role,
      status: 'draft',
    },
  });

  return {
    project: mapProjectRow(projectRow),
    membership: {
      id: memberRow.id,
      projectId: memberRow.project_id,
      userId: memberRow.user_id,
      role: memberRow.role,
      joinedAt: memberRow.joined_at,
    },
  };
}

/**
 * Lists all projects where the user is an active member.
 */
export async function listUserProjects(
  userId: string,
  filters?: { status?: string; role?: string }
): Promise<Array<Project & { currentUserRole: 'client' | 'freelancer' }>> {
  let memberQuery = supabaseAdmin
    .from('project_members')
    .select('project_id, role')
    .eq('user_id', userId);

  if (filters?.role) {
    memberQuery = memberQuery.eq('role', filters.role);
  }

  const { data: memberRows, error: memberError } = await memberQuery;
  if (memberError || !memberRows || memberRows.length === 0) {
    return [];
  }

  const projectIds = memberRows.map(m => m.project_id);
  const roleMap = new Map<string, 'client' | 'freelancer'>(
    memberRows.map(m => [m.project_id, m.role])
  );

  let projectQuery = supabaseAdmin
    .from('projects')
    .select('*')
    .in('id', projectIds)
    .order('created_at', { ascending: false });

  if (filters?.status) {
    projectQuery = projectQuery.eq('status', filters.status);
  }

  const { data: projectRows, error: projectError } = await projectQuery;
  if (projectError || !projectRows) {
    throw new ProjectError(500, `Failed to retrieve projects: ${projectError?.message}`);
  }

  return projectRows.map(p => ({
    ...mapProjectRow(p),
    currentUserRole: roleMap.get(p.id) || 'client',
  }));
}

/**
 * Gets project details if and only if the authenticated user is a project member.
 */
export async function getProjectById(
  projectId: string,
  userId: string
): Promise<ProjectDetailResponse> {
  // 1. Verify membership
  const { data: memberRecord, error: memberErr } = await supabaseAdmin
    .from('project_members')
    .select('*')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memberErr) {
    throw new ProjectError(500, `Database error: ${memberErr.message}`);
  }

  if (!memberRecord) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }

  // 2. Fetch project
  const { data: projectRow, error: projectErr } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .maybeSingle();

  if (projectErr || !projectRow) {
    throw new ProjectError(404, 'Project not found.');
  }

  // 3. Fetch all members with profile details
  const { data: allMembers, error: allMembersErr } = await supabaseAdmin
    .from('project_members')
    .select('id, user_id, role, joined_at, profiles:user_id(display_name, avatar_url)')
    .eq('project_id', projectId);

  if (allMembersErr) {
    throw new ProjectError(500, `Failed to retrieve project members: ${allMembersErr.message}`);
  }

  // 4. Fetch active invitation (if exists and visible to members)
  const { data: activeInv } = await supabaseAdmin
    .from('invitations')
    .select('id, invited_email, role, status, expires_at, created_at')
    .eq('project_id', projectId)
    .eq('status', 'pending')
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  // 5. Fetch planned milestones
  const { data: milestoneRows } = await supabaseAdmin
    .from('milestones')
    .select('*')
    .eq('project_id', projectId)
    .order('order_index', { ascending: true })
    .order('created_at', { ascending: true });

  return {
    project: mapProjectRow(projectRow),
    currentUserRole: memberRecord.role,
    members: (allMembers || []).map((m: any) => ({
      id: m.id,
      userId: m.user_id,
      role: m.role,
      joinedAt: m.joined_at,
      profile: {
        displayName: m.profiles?.display_name || 'Member',
        avatarUrl: m.profiles?.avatar_url || undefined,
      },
    })),
    activeInvitation: activeInv
      ? {
          id: activeInv.id,
          invitedEmail: activeInv.invited_email,
          role: activeInv.role,
          status: activeInv.status,
          expiresAt: activeInv.expires_at,
          createdAt: activeInv.created_at,
        }
      : null,
    milestones: (milestoneRows || []).map(mapMilestoneRow),
  };
}

/**
 * Updates editable project fields.
 */
export async function updateProject(
  projectId: string,
  userId: string,
  input: UpdateProjectInput
): Promise<Project> {
  // Check membership
  const { data: member, error: memberErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memberErr || !member) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }

  // Fetch current project
  const { data: currentProject, error: fetchErr } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .maybeSingle();

  if (fetchErr || !currentProject) {
    throw new ProjectError(404, 'Project not found.');
  }

  // Can only update project fields in pre-activation states
  const editableStatuses: ProjectStatus[] = ['draft', 'invitation_pending', 'awaiting_agreement'];
  if (!editableStatuses.includes(currentProject.status)) {
    throw new ProjectError(
      400,
      `Project fields cannot be modified while project is in '${currentProject.status}' state.`
    );
  }

  const updates: Record<string, unknown> = {
    updated_at: new Date().toISOString(),
  };

  if (input.title !== undefined) {
    const trimmed = input.title.trim();
    if (!trimmed) throw new ProjectError(400, 'Project title cannot be empty.');
    if (trimmed.length > 200) throw new ProjectError(400, 'Project title cannot exceed 200 characters.');
    updates.title = trimmed;
  }

  if (input.description !== undefined) {
    updates.description = input.description.trim() || null;
  }

  if (input.currency !== undefined) {
    updates.currency = input.currency.trim().toUpperCase().slice(0, 3);
  }

  if (input.totalBudget !== undefined) {
    if (input.totalBudget !== null && (typeof input.totalBudget !== 'number' || input.totalBudget <= 0)) {
      throw new ProjectError(400, 'Total budget must be a positive number.');
    }
    updates.total_budget = input.totalBudget;
  }

  if (input.paymentArrangement !== undefined) {
    updates.payment_arrangement = input.paymentArrangement;
  }

  if (input.reviewPeriodDays !== undefined) {
    if (!Number.isInteger(input.reviewPeriodDays) || input.reviewPeriodDays < 1) {
      throw new ProjectError(400, 'Review period days must be an integer greater than or equal to 1.');
    }
    updates.review_period_days = input.reviewPeriodDays;
  }

  const { data: updatedProject, error: updateErr } = await supabaseAdmin
    .from('projects')
    .update(updates)
    .eq('id', projectId)
    .select('*')
    .single();

  if (updateErr || !updatedProject) {
    throw new ProjectError(500, `Failed to update project: ${updateErr?.message}`);
  }

  return mapProjectRow(updatedProject);
}

/**
 * Cancels a project where permitted.
 */
export async function cancelProject(projectId: string, userId: string): Promise<Project> {
  const { data: member, error: memberErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memberErr || !member) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }

  const { data: currentProject, error: fetchErr } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .maybeSingle();

  if (fetchErr || !currentProject) {
    throw new ProjectError(404, 'Project not found.');
  }

  if (currentProject.status === 'completed' || currentProject.status === 'cancelled') {
    throw new ProjectError(400, `Project is already ${currentProject.status}.`);
  }

  const { data: updatedProject, error: updateErr } = await supabaseAdmin
    .from('projects')
    .update({
      status: 'cancelled',
      updated_at: new Date().toISOString(),
    })
    .eq('id', projectId)
    .select('*')
    .single();

  if (updateErr || !updatedProject) {
    throw new ProjectError(500, `Failed to cancel project: ${updateErr?.message}`);
  }

  // Cancel any remaining pending invitations
  await supabaseAdmin
    .from('invitations')
    .update({ status: 'cancelled', responded_at: new Date().toISOString() })
    .eq('project_id', projectId)
    .eq('status', 'pending');

  await logActivity({
    projectId,
    actorId: userId,
    eventType: 'project_status_changed',
    entityType: 'project',
    entityId: projectId,
    oldData: { status: currentProject.status },
    newData: { status: 'cancelled' },
  });

  return mapProjectRow(updatedProject);
}

function mapProjectRow(row: any): Project {
  return {
    id: row.id,
    title: row.title,
    description: row.description || undefined,
    status: row.status,
    initiatorId: row.initiator_id,
    clientId: row.client_id || undefined,
    freelancerId: row.freelancer_id || undefined,
    currency: row.currency,
    totalBudget: row.total_budget !== null ? Number(row.total_budget) : undefined,
    paymentArrangement: row.payment_arrangement || undefined,
    aiScopeData: row.ai_scope_data || undefined,
    reviewPeriodDays: row.review_period_days,
    sourceVersion: Number(row.source_version ?? 1),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}
