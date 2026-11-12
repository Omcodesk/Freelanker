import { supabaseAdmin } from '../lib/supabase.js';
import { ProjectError } from './project.service.js';

export interface MessageRecord {
  id: string;
  projectId: string;
  senderId: string;
  content: string;
  fileUrls: string[];
  isAiSummary: boolean;
  createdAt: string;
  senderProfile?: {
    id: string;
    displayName: string;
    avatarUrl: string | null;
  } | null;
}

export interface CreateMessageInput {
  content: string;
  fileUrls?: string[];
  isAiSummary?: boolean;
}

function mapMessageRow(row: Record<string, any>): MessageRecord {
  return {
    id: row.id,
    projectId: row.project_id,
    senderId: row.sender_id,
    content: row.content,
    fileUrls: row.file_urls || [],
    isAiSummary: row.is_ai_summary ?? false,
    createdAt: row.created_at,
    senderProfile: row.sender_profile
      ? {
          id: row.sender_profile.id,
          displayName: row.sender_profile.display_name,
          avatarUrl: row.sender_profile.avatar_url,
        }
      : null,
  };
}

/**
 * List messages for a project discussion thread.
 */
export async function listProjectMessages(projectId: string): Promise<MessageRecord[]> {
  const { data, error } = await supabaseAdmin
    .from('messages')
    .select(`
      *,
      sender_profile:profiles!messages_sender_id_fkey(id, display_name, avatar_url)
    `)
    .eq('project_id', projectId)
    .order('created_at', { ascending: true });

  if (error) {
    throw new ProjectError(500, `Failed to load messages: ${error.message}`);
  }

  return (data || []).map(mapMessageRow);
}

/**
 * Post a new message to a project discussion thread.
 */
export async function createMessage(
  projectId: string,
  senderId: string,
  input: CreateMessageInput
): Promise<MessageRecord> {
  const content = input.content?.trim();
  if (!content) {
    throw new ProjectError(400, 'Message content cannot be empty.');
  }

  const { data, error } = await supabaseAdmin
    .from('messages')
    .insert({
      project_id: projectId,
      sender_id: senderId,
      content,
      file_urls: input.fileUrls || [],
      is_ai_summary: input.isAiSummary ?? false,
    })
    .select(`
      *,
      sender_profile:profiles!messages_sender_id_fkey(id, display_name, avatar_url)
    `)
    .single();

  if (error || !data) {
    throw new ProjectError(500, `Failed to send message: ${error?.message}`);
  }

  return mapMessageRow(data);
}
