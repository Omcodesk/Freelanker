import { supabaseAdmin } from '../lib/supabase.js';
import { logActivity } from './activity.service.js';
import { ProjectError } from './project.service.js';
import type { Milestone, ProjectStatus } from '../types/index.js';

const EDITABLE_MILESTONE_STATUSES: ProjectStatus[] = ['draft', 'invitation_pending', 'awaiting_agreement'];
const ISO_DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;

export interface CreateMilestoneInput {
  title: string;
  description?: string;
  amount: number;
  dueDate: string;
  orderIndex?: number;
}

export interface UpdateMilestoneInput {
  title?: string;
  description?: string;
  amount?: number;
  dueDate?: string;
  orderIndex?: number;
}

export function mapMilestoneRow(row: any): Milestone {
  return {
    id: row.id,
    projectId: row.project_id,
    title: row.title,
    description: row.description || undefined,
    status: row.status,
    amount: Number(row.amount),
    orderIndex: Number(row.order_index ?? 0),
    dueDate: row.due_date || undefined,
    isAiGenerated: Boolean(row.is_ai_generated),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function validateDueDate(dueDate: unknown, projectCreatedAt: string): string {
  if (typeof dueDate !== 'string' || !ISO_DATE_REGEX.test(dueDate.trim())) {
    throw new ProjectError(400, 'Milestone due date must be a valid YYYY-MM-DD date.');
  }
  const normalized = dueDate.trim();
  const parsed = new Date(`${normalized}T00:00:00.000Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== normalized) {
    throw new ProjectError(400, 'Milestone due date is not a valid calendar date.');
  }
  const projectStart = new Date(projectCreatedAt).toISOString().slice(0, 10);
  if (normalized < projectStart) {
    throw new ProjectError(400, `Milestone due date (${normalized}) cannot precede project creation date (${projectStart}).`);
  }
  return normalized;
}

async function requireMemberAndProject(projectId: string, userId: string, requireEditable: boolean) {
  const { data: member, error: memberErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memberErr) {
    throw new ProjectError(500, `Failed to verify membership: ${memberErr.message}`);
  }
  if (!member) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }

  const { data: project, error: projErr } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .maybeSingle();

  if (projErr || !project) {
    throw new ProjectError(404, 'Project not found.');
  }

  if (requireEditable && !EDITABLE_MILESTONE_STATUSES.includes(project.status)) {
    throw new ProjectError(400, `Milestones cannot be modified while project is in '${project.status}' status.`);
  }

  return { member, project };
}

async function getProjectSourceVersion(projectId: string): Promise<number> {
  const { data } = await supabaseAdmin
    .from('projects')
    .select('source_version')
    .eq('id', projectId)
    .maybeSingle();
  return Number(data?.source_version ?? 1);
}

export async function listMilestones(projectId: string, userId: string): Promise<{ milestones: Milestone[]; sourceVersion: number }> {
  const { project } = await requireMemberAndProject(projectId, userId, false);

  const { data, error } = await supabaseAdmin
    .from('milestones')
    .select('*')
    .eq('project_id', projectId)
    .order('order_index', { ascending: true })
    .order('created_at', { ascending: true });

  if (error) {
    throw new ProjectError(500, `Failed to load milestones: ${error.message}`);
  }

  return {
    milestones: (data || []).map(mapMilestoneRow),
    sourceVersion: Number(project.source_version ?? 1),
  };
}

export async function createMilestone(
  projectId: string,
  userId: string,
  input: CreateMilestoneInput
): Promise<{ milestone: Milestone; sourceVersion: number }> {
  const { project } = await requireMemberAndProject(projectId, userId, true);

  const title = input.title?.trim();
  if (!title) {
    throw new ProjectError(400, 'Milestone title is required.');
  }
  if (title.length > 200) {
    throw new ProjectError(400, 'Milestone title cannot exceed 200 characters.');
  }

  if (typeof input.amount !== 'number' || !Number.isFinite(input.amount) || input.amount < 0) {
    throw new ProjectError(400, 'Milestone amount must be a non-negative number.');
  }
  const amount = Math.round(input.amount * 100) / 100;
  const dueDate = validateDueDate(input.dueDate, project.created_at);

  const { data: existingRows, error: existingErr } = await supabaseAdmin
    .from('milestones')
    .select('id, amount, order_index')
    .eq('project_id', projectId);

  if (existingErr) {
    throw new ProjectError(500, `Failed to inspect existing milestones: ${existingErr.message}`);
  }

  if (project.total_budget !== null && project.total_budget !== undefined) {
    const existingSum = (existingRows || []).reduce((sum: number, m: any) => sum + Number(m.amount || 0), 0);
    if (existingSum + amount > Number(project.total_budget) + 0.001) {
      throw new ProjectError(
        400,
        `Milestone amounts (${(existingSum + amount).toFixed(2)}) would exceed project budget (${Number(project.total_budget).toFixed(2)} ${project.currency}).`
      );
    }
  }

  const nextOrder =
    input.orderIndex !== undefined && Number.isInteger(input.orderIndex) && input.orderIndex >= 0
      ? input.orderIndex
      : (existingRows || []).length + 1;

  const { data: inserted, error: insertErr } = await supabaseAdmin
    .from('milestones')
    .insert({
      project_id: projectId,
      title,
      description: input.description?.trim() || null,
      amount,
      due_date: dueDate,
      order_index: nextOrder,
    })
    .select('*')
    .single();

  if (insertErr || !inserted) {
    throw new ProjectError(500, `Failed to create milestone: ${insertErr?.message || 'Database error'}`);
  }

  await logActivity({
    projectId,
    actorId: userId,
    eventType: 'milestone_created',
    entityType: 'milestone',
    entityId: inserted.id,
    newData: { title, amount, dueDate },
  });

  const sourceVersion = await getProjectSourceVersion(projectId);
  return { milestone: mapMilestoneRow(inserted), sourceVersion };
}

export async function updateMilestone(
  projectId: string,
  milestoneId: string,
  userId: string,
  input: UpdateMilestoneInput
): Promise<{ milestone: Milestone; sourceVersion: number }> {
  const { project } = await requireMemberAndProject(projectId, userId, true);

  const { data: existing, error: findErr } = await supabaseAdmin
    .from('milestones')
    .select('*')
    .eq('id', milestoneId)
    .eq('project_id', projectId)
    .maybeSingle();

  if (findErr) {
    throw new ProjectError(500, `Failed to load milestone: ${findErr.message}`);
  }
  if (!existing) {
    throw new ProjectError(404, 'Milestone not found in this project.');
  }

  const updates: Record<string, unknown> = {
    updated_at: new Date().toISOString(),
  };

  if (input.title !== undefined) {
    const trimmed = input.title.trim();
    if (!trimmed) throw new ProjectError(400, 'Milestone title cannot be empty.');
    if (trimmed.length > 200) throw new ProjectError(400, 'Milestone title cannot exceed 200 characters.');
    updates.title = trimmed;
  }

  if (input.description !== undefined) {
    updates.description = input.description.trim() || null;
  }

  if (input.dueDate !== undefined) {
    updates.due_date = validateDueDate(input.dueDate, project.created_at);
  }

  if (input.orderIndex !== undefined) {
    if (!Number.isInteger(input.orderIndex) || input.orderIndex < 0) {
      throw new ProjectError(400, 'Milestone orderIndex must be a non-negative integer.');
    }
    updates.order_index = input.orderIndex;
  }

  if (input.amount !== undefined) {
    if (typeof input.amount !== 'number' || !Number.isFinite(input.amount) || input.amount < 0) {
      throw new ProjectError(400, 'Milestone amount must be a non-negative number.');
    }
    const newAmount = Math.round(input.amount * 100) / 100;
    if (project.total_budget !== null && project.total_budget !== undefined) {
      const { data: otherRows } = await supabaseAdmin
        .from('milestones')
        .select('id, amount')
        .eq('project_id', projectId)
        .neq('id', milestoneId);
      const otherSum = (otherRows || []).reduce((sum: number, m: any) => sum + Number(m.amount || 0), 0);
      if (otherSum + newAmount > Number(project.total_budget) + 0.001) {
        throw new ProjectError(
          400,
          `Updated milestone total (${(otherSum + newAmount).toFixed(2)}) exceeds project budget (${Number(project.total_budget).toFixed(2)} ${project.currency}).`
        );
      }
    }
    updates.amount = newAmount;
  }

  const { data: updated, error: updErr } = await supabaseAdmin
    .from('milestones')
    .update(updates)
    .eq('id', milestoneId)
    .eq('project_id', projectId)
    .select('*')
    .single();

  if (updErr || !updated) {
    throw new ProjectError(500, `Failed to update milestone: ${updErr?.message || 'Database error'}`);
  }

  const sourceVersion = await getProjectSourceVersion(projectId);
  return { milestone: mapMilestoneRow(updated), sourceVersion };
}

export async function deleteMilestone(
  projectId: string,
  milestoneId: string,
  userId: string
): Promise<{ deletedId: string; sourceVersion: number }> {
  await requireMemberAndProject(projectId, userId, true);

  const { data: existing, error: findErr } = await supabaseAdmin
    .from('milestones')
    .select('id')
    .eq('id', milestoneId)
    .eq('project_id', projectId)
    .maybeSingle();

  if (findErr) {
    throw new ProjectError(500, `Failed to load milestone: ${findErr.message}`);
  }
  if (!existing) {
    throw new ProjectError(404, 'Milestone not found in this project.');
  }

  const { error: delErr } = await supabaseAdmin
    .from('milestones')
    .delete()
    .eq('id', milestoneId)
    .eq('project_id', projectId);

  if (delErr) {
    throw new ProjectError(500, `Failed to delete milestone: ${delErr.message}`);
  }

  const sourceVersion = await getProjectSourceVersion(projectId);
  return { deletedId: milestoneId, sourceVersion };
}

