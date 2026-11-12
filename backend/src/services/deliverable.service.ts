import { supabaseAdmin } from '../lib/supabase.js';
import { ProjectError } from './project.service.js';
import { uploadDeliverableFile, getDeliverableSignedUrl } from './storage.service.js';

export interface DeliverableRecord {
  id: string;
  projectId: string;
  milestoneId: string | null;
  submittedBy: string;
  status: 'submitted' | 'approved' | 'rejected';
  title: string;
  description: string | null;
  submissionNote: string | null;
  fileUrls: string[];
  linkUrl: string | null;
  version: number;
  parentId: string | null;
  reviewDeadline: string | null;
  clientFeedback: string | null;
  reviewedBy: string | null;
  reviewedAt: string | null;
  createdAt: string;
  updatedAt: string;
  submitterProfile?: {
    id: string;
    displayName: string;
    avatarUrl: string | null;
  } | null;
}

export interface CreateDeliverableInput {
  title: string;
  description?: string;
  submissionNote?: string;
  milestoneId?: string;
  linkUrl?: string;
  file?: {
    originalname: string;
    buffer: Buffer;
    mimetype: string;
  };
}

export interface ReviewDeliverableInput {
  status: 'approved' | 'rejected';
  clientFeedback?: string;
}

function mapDeliverableRow(row: Record<string, any>): DeliverableRecord {
  return {
    id: row.id,
    projectId: row.project_id,
    milestoneId: row.milestone_id,
    submittedBy: row.submitted_by,
    status: row.status,
    title: row.title,
    description: row.description,
    submissionNote: row.submission_note,
    fileUrls: row.file_urls || [],
    linkUrl: row.link_url,
    version: row.version ?? 1,
    parentId: row.parent_id,
    reviewDeadline: row.review_deadline,
    clientFeedback: row.client_feedback,
    reviewedBy: row.reviewed_by,
    reviewedAt: row.reviewed_at,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    submitterProfile: row.submitter_profile
      ? {
          id: row.submitter_profile.id,
          displayName: row.submitter_profile.display_name,
          avatarUrl: row.submitter_profile.avatar_url,
        }
      : null,
  };
}

/**
 * List deliverables for a project with signed URLs refreshed for private files.
 */
export async function listProjectDeliverables(projectId: string): Promise<DeliverableRecord[]> {
  const { data, error } = await supabaseAdmin
    .from('deliverables')
    .select(`
      *,
      submitter_profile:profiles!deliverables_submitted_by_fkey(id, display_name, avatar_url)
    `)
    .eq('project_id', projectId)
    .order('created_at', { ascending: false });

  if (error) {
    throw new ProjectError(500, `Failed to list deliverables: ${error.message}`);
  }

  const deliverables = (data || []).map(mapDeliverableRow);

  // Refresh signed URLs for private storage files
  for (const del of deliverables) {
    if (del.fileUrls && del.fileUrls.length > 0) {
      const refreshed: string[] = [];
      for (const rawUrl of del.fileUrls) {
        if (rawUrl.startsWith('projects/')) {
          const signed = await getDeliverableSignedUrl(rawUrl);
          refreshed.push(signed || rawUrl);
        } else {
          refreshed.push(rawUrl);
        }
      }
      del.fileUrls = refreshed;
    }
  }

  return deliverables;
}

/**
 * Submit a deliverable with optional file upload to Supabase Storage.
 */
export async function submitDeliverable(
  projectId: string,
  userId: string,
  input: CreateDeliverableInput
): Promise<DeliverableRecord> {
  const title = input.title?.trim();
  if (!title) {
    throw new ProjectError(400, 'Deliverable title is required.');
  }

  const fileUrls: string[] = [];
  if (input.file) {
    const uploadRes = await uploadDeliverableFile(
      projectId,
      input.file.originalname,
      input.file.buffer,
      input.file.mimetype
    );
    fileUrls.push(uploadRes.path);
  }

  const { data, error } = await supabaseAdmin
    .from('deliverables')
    .insert({
      project_id: projectId,
      submitted_by: userId,
      title,
      description: input.description?.trim() || null,
      submission_note: input.submissionNote?.trim() || null,
      milestone_id: input.milestoneId || null,
      link_url: input.linkUrl?.trim() || null,
      file_urls: fileUrls,
      status: 'submitted',
      version: 1,
    })
    .select(`
      *,
      submitter_profile:profiles!deliverables_submitted_by_fkey(id, display_name, avatar_url)
    `)
    .single();

  if (error || !data) {
    throw new ProjectError(500, `Failed to create deliverable: ${error?.message}`);
  }

  const mapped = mapDeliverableRow(data);
  if (fileUrls.length > 0 && fileUrls[0].startsWith('projects/')) {
    const signed = await getDeliverableSignedUrl(fileUrls[0]);
    if (signed) mapped.fileUrls = [signed];
  }
  return mapped;
}

/**
 * Review a deliverable (client approves or rejects/requests revision).
 */
export async function reviewDeliverable(
  projectId: string,
  deliverableId: string,
  reviewerId: string,
  input: ReviewDeliverableInput
): Promise<DeliverableRecord> {
  const { data: member } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', reviewerId)
    .maybeSingle();

  if (!member || member.role !== 'client') {
    throw new ProjectError(403, 'Forbidden: Only the client can approve or reject deliverables.');
  }

  const valid = ['approved', 'rejected'];
  if (!valid.includes(input.status)) {
    throw new ProjectError(400, 'Invalid status: Must be approved or rejected.');
  }

  const { data, error } = await supabaseAdmin
    .from('deliverables')
    .update({
      status: input.status,
      client_feedback: input.clientFeedback?.trim() || null,
      reviewed_by: reviewerId,
      reviewed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    .eq('id', deliverableId)
    .eq('project_id', projectId)
    .select(`
      *,
      submitter_profile:profiles!deliverables_submitted_by_fkey(id, display_name, avatar_url)
    `)
    .maybeSingle();

  if (error || !data) {
    throw new ProjectError(404, `Deliverable not found: ${error?.message}`);
  }

  return mapDeliverableRow(data);
}
