import { supabaseAdmin } from '../lib/supabase.js';

export const DELIVERABLES_BUCKET = 'deliverables';

/**
 * Ensures the deliverables bucket exists in Supabase Storage.
 * Called lazily or on initialization.
 */
export async function ensureDeliverablesBucket(): Promise<void> {
  const { data: buckets, error: listError } = await supabaseAdmin.storage.listBuckets();
  if (listError) {
    console.warn('[Storage] Warning checking buckets:', listError.message);
    return;
  }

  const exists = buckets?.some((b) => b.name === DELIVERABLES_BUCKET);
  if (!exists) {
    const { error: createError } = await supabaseAdmin.storage.createBucket(DELIVERABLES_BUCKET, {
      public: false, // private bucket requiring signed URLs
      fileSizeLimit: 52428800, // 50MB
    });
    if (createError) {
      console.warn('[Storage] Warning creating deliverables bucket:', createError.message);
    } else {
      console.log(`[Storage] Created private bucket: ${DELIVERABLES_BUCKET}`);
    }
  }
}

/**
 * Upload a deliverable file to Supabase Storage in project-scoped directory:
 * projects/<projectId>/deliverables/<uuid>.<ext>
 */
export async function uploadDeliverableFile(
  projectId: string,
  fileName: string,
  fileBuffer: Buffer,
  mimeType: string
): Promise<{ path: string; signedUrl?: string }> {
  await ensureDeliverablesBucket();

  const ext = fileName.includes('.') ? fileName.split('.').pop() : 'bin';
  const cleanExt = (ext || 'bin').toLowerCase().replace(/[^a-z0-9]/g, '');
  const storagePath = `projects/${projectId}/${Date.now()}_${Math.random().toString(36).slice(2, 9)}.${cleanExt}`;

  const { error: uploadErr } = await supabaseAdmin.storage
    .from(DELIVERABLES_BUCKET)
    .upload(storagePath, fileBuffer, {
      contentType: mimeType || 'application/octet-stream',
      upsert: false,
    });

  if (uploadErr) {
    throw new Error(`Failed to upload deliverable to storage: ${uploadErr.message}`);
  }

  // Create a 1-day signed URL for secure previewing
  const { data: signedData } = await supabaseAdmin.storage
    .from(DELIVERABLES_BUCKET)
    .createSignedUrl(storagePath, 86400);

  return {
    path: storagePath,
    signedUrl: signedData?.signedUrl,
  };
}

/**
 * Create a fresh signed URL for reading a stored deliverable file.
 */
export async function getDeliverableSignedUrl(storagePath: string): Promise<string | null> {
  const { data, error } = await supabaseAdmin.storage
    .from(DELIVERABLES_BUCKET)
    .createSignedUrl(storagePath, 86400);

  if (error || !data) return null;
  return data.signedUrl;
}
