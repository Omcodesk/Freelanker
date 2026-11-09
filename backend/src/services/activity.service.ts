import { supabaseAdmin } from '../lib/supabase.js';
import type { ActivityEventType } from '../types/index.js';

interface LogActivityParams {
  projectId?: string;
  actorId?: string;
  eventType: ActivityEventType;
  entityType: string;
  entityId: string;
  oldData?: Record<string, unknown>;
  newData?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export async function logActivity(params: LogActivityParams): Promise<void> {
  try {
    const { error } = await supabaseAdmin.from('activity_logs').insert({
      project_id: params.projectId ?? null,
      actor_id: params.actorId ?? null,
      event_type: params.eventType,
      entity_type: params.entityType,
      entity_id: params.entityId,
      old_data: params.oldData ?? null,
      new_data: params.newData ?? null,
      metadata: params.metadata ?? null,
    });

    if (error) {
      console.warn('[ActivityLog] Failed to record log entry:', error.message);
    }
  } catch (err: unknown) {
    console.warn('[ActivityLog] Exception recording log entry:', err);
  }
}
