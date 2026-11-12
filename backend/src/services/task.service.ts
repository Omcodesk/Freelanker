import { supabaseAdmin } from '../lib/supabase.js';
import { ProjectError } from './project.service.js';

export interface TaskRecord {
  id: string;
  projectId: string;
  milestoneId: string | null;
  title: string;
  description: string | null;
  status: 'todo' | 'in_progress' | 'done';
  assignedTo: string | null;
  dueDate: string | null;
  orderIndex: number;
  isAiGenerated: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  assignedProfile?: {
    id: string;
    displayName: string;
    avatarUrl: string | null;
  } | null;
}

export interface CreateTaskInput {
  title: string;
  description?: string;
  status?: 'todo' | 'in_progress' | 'done';
  assignedTo?: string;
  milestoneId?: string;
  dueDate?: string;
  orderIndex?: number;
}

export interface UpdateTaskInput {
  title?: string;
  description?: string;
  status?: 'todo' | 'in_progress' | 'done';
  assignedTo?: string | null;
  milestoneId?: string | null;
  dueDate?: string | null;
  orderIndex?: number;
}

function mapTaskRow(row: Record<string, any>): TaskRecord {
  return {
    id: row.id,
    projectId: row.project_id,
    milestoneId: row.milestone_id,
    title: row.title,
    description: row.description,
    status: row.status,
    assignedTo: row.assigned_to,
    dueDate: row.due_date,
    orderIndex: row.order_index ?? 0,
    isAiGenerated: row.is_ai_generated ?? false,
    createdBy: row.created_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    assignedProfile: row.assigned_profile
      ? {
          id: row.assigned_profile.id,
          displayName: row.assigned_profile.display_name,
          avatarUrl: row.assigned_profile.avatar_url,
        }
      : null,
  };
}

/**
 * List tasks for a project.
 */
export async function listProjectTasks(projectId: string): Promise<TaskRecord[]> {
  const { data, error } = await supabaseAdmin
    .from('tasks')
    .select(`
      *,
      assigned_profile:profiles!tasks_assigned_to_fkey(id, display_name, avatar_url)
    `)
    .eq('project_id', projectId)
    .order('order_index', { ascending: true })
    .order('created_at', { ascending: true });

  if (error) {
    throw new ProjectError(500, `Failed to list tasks: ${error.message}`);
  }

  return (data || []).map(mapTaskRow);
}

/**
 * Create a new task in a project.
 */
export async function createTask(
  projectId: string,
  userId: string,
  input: CreateTaskInput
): Promise<TaskRecord> {
  const title = input.title?.trim();
  if (!title) {
    throw new ProjectError(400, 'Task title is required.');
  }

  const validStatuses = ['todo', 'in_progress', 'done'];
  const status = input.status && validStatuses.includes(input.status) ? input.status : 'todo';

  const { data, error } = await supabaseAdmin
    .from('tasks')
    .insert({
      project_id: projectId,
      created_by: userId,
      title,
      description: input.description?.trim() || null,
      status,
      assigned_to: input.assignedTo || null,
      milestone_id: input.milestoneId || null,
      due_date: input.dueDate || null,
      order_index: input.orderIndex ?? 0,
    })
    .select(`
      *,
      assigned_profile:profiles!tasks_assigned_to_fkey(id, display_name, avatar_url)
    `)
    .single();

  if (error || !data) {
    throw new ProjectError(500, `Failed to create task: ${error?.message}`);
  }

  return mapTaskRow(data);
}

/**
 * Update a task.
 */
export async function updateTask(
  projectId: string,
  taskId: string,
  input: UpdateTaskInput
): Promise<TaskRecord> {
  const updates: Record<string, any> = {
    updated_at: new Date().toISOString(),
  };

  if (input.title !== undefined) {
    const t = input.title.trim();
    if (!t) throw new ProjectError(400, 'Task title cannot be empty.');
    updates.title = t;
  }
  if (input.description !== undefined) {
    updates.description = input.description?.trim() || null;
  }
  if (input.status !== undefined) {
    const valid = ['todo', 'in_progress', 'done'];
    if (!valid.includes(input.status)) throw new ProjectError(400, 'Invalid task status.');
    updates.status = input.status;
  }
  if (input.assignedTo !== undefined) {
    updates.assigned_to = input.assignedTo;
  }
  if (input.milestoneId !== undefined) {
    updates.milestone_id = input.milestoneId;
  }
  if (input.dueDate !== undefined) {
    updates.due_date = input.dueDate;
  }
  if (input.orderIndex !== undefined) {
    updates.order_index = input.orderIndex;
  }

  const { data, error } = await supabaseAdmin
    .from('tasks')
    .update(updates)
    .eq('id', taskId)
    .eq('project_id', projectId)
    .select(`
      *,
      assigned_profile:profiles!tasks_assigned_to_fkey(id, display_name, avatar_url)
    `)
    .maybeSingle();

  if (error || !data) {
    throw new ProjectError(404, `Task not found or update failed: ${error?.message}`);
  }

  return mapTaskRow(data);
}

/**
 * Delete a task.
 */
export async function deleteTask(projectId: string, taskId: string): Promise<void> {
  const { error } = await supabaseAdmin
    .from('tasks')
    .delete()
    .eq('id', taskId)
    .eq('project_id', projectId);

  if (error) {
    throw new ProjectError(500, `Failed to delete task: ${error.message}`);
  }
}
