import { useEffect, useState, useRef } from 'react';
import { api, ApiError } from '../../services/api.ts';
import { supabase } from '../../lib/supabase.ts';

export interface DeliverableItem {
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
  clientFeedback: string | null;
  reviewedBy: string | null;
  reviewedAt: string | null;
  createdAt: string;
  submitterProfile?: {
    id: string;
    displayName: string;
    avatarUrl: string | null;
  } | null;
}

interface DeliverablesViewProps {
  projectId: string;
  currentUserRole?: 'client' | 'freelancer' | 'member';
}

export function DeliverablesView({ projectId, currentUserRole }: DeliverablesViewProps) {
  const [deliverables, setDeliverables] = useState<DeliverableItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload Form
  const [title, setTitle] = useState('');
  const [note, setNote] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Review state
  const [feedbackNotes, setFeedbackNotes] = useState<Record<string, string>>({});
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  const loadDeliverables = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<DeliverableItem[]>(`/workbridge/projects/${projectId}/deliverables`);
      setDeliverables(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load deliverables.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDeliverables();
  }, [projectId]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('title', title.trim());
      if (note.trim()) formData.append('submissionNote', note.trim());
      if (file) formData.append('file', file);

      // Using token from active supabase session
      const sessionRes = await supabase.auth.getSession();
      const token = sessionRes.data.session?.access_token;

      const baseUrl =
        (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:4000/api';

      const resp = await fetch(`${baseUrl}/workbridge/projects/${projectId}/deliverables`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      const json = await resp.json();
      if (!resp.ok || !json.success) {
        throw new Error(json.error?.message || 'Failed to upload deliverable.');
      }

      setDeliverables((prev) => [json.data, ...prev]);
      setTitle('');
      setNote('');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: any) {
      alert(err.message || 'Upload error');
    } finally {
      setUploading(false);
    }
  };

  const handleReview = async (deliverableId: string, status: 'approved' | 'rejected') => {
    setReviewingId(deliverableId);
    try {
      const feedback = feedbackNotes[deliverableId] || '';
      const updated = await api.patch<DeliverableItem>(
        `/workbridge/projects/${projectId}/deliverables/${deliverableId}/review`,
        { status, clientFeedback: feedback }
      );
      setDeliverables((prev) => prev.map((d) => (d.id === deliverableId ? updated : d)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Review update failed.');
    } finally {
      setReviewingId(null);
    }
  };

  const isClient = currentUserRole === 'client';

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900">Deliverables & Reviews</h3>
        <p className="text-xs text-slate-500">
          Submit completed files for client review, request revisions, and track approvals.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Submission Form */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4">
        <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
          Submit Work Deliverable
        </h4>
        <form onSubmit={handleUpload} className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Design assets v1"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Attach File (Supabase Storage)
              </label>
              <input
                ref={fileInputRef}
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Submission Note
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Summary of changes or instructions for client"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <button
            type="submit"
            disabled={uploading || !title.trim()}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold disabled:opacity-50 transition-colors"
          >
            {uploading ? 'Uploading...' : 'Submit Deliverable'}
          </button>
        </form>
      </div>

      {/* Deliverables List */}
      {loading ? (
        <div className="p-8 text-center text-slate-500 text-xs">Loading deliverables...</div>
      ) : deliverables.length === 0 ? (
        <div className="p-8 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-2xl">
          No deliverables submitted yet.
        </div>
      ) : (
        <div className="space-y-3">
          {deliverables.map((del) => (
            <div
              key={del.id}
              className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-900">{del.title}</h4>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                      v{del.version}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        del.status === 'approved'
                          ? 'bg-emerald-100 text-emerald-800'
                          : del.status === 'rejected'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {del.status === 'rejected' ? 'Revision Requested' : del.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">
                    Submitted by {del.submitterProfile?.displayName || 'Team'} on{' '}
                    {new Date(del.createdAt).toLocaleDateString()}
                  </p>
                </div>

                {del.fileUrls.length > 0 && (
                  <a
                    href={del.fileUrls[0]}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
                  >
                    Download File ↗
                  </a>
                )}
              </div>

              {del.submissionNote && (
                <div className="p-3 bg-slate-50 rounded-xl text-xs text-slate-700">
                  <span className="font-semibold text-slate-900">Note:</span> {del.submissionNote}
                </div>
              )}

              {del.clientFeedback && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900">
                  <span className="font-semibold">Client Feedback:</span> {del.clientFeedback}
                </div>
              )}

              {/* Client Review Controls */}
              {isClient && del.status === 'submitted' && (
                <div className="pt-3 border-t border-slate-100 space-y-2">
                  <input
                    type="text"
                    placeholder="Feedback / revision note..."
                    value={feedbackNotes[del.id] || ''}
                    onChange={(e) =>
                      setFeedbackNotes({ ...feedbackNotes, [del.id]: e.target.value })
                    }
                    className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      disabled={reviewingId === del.id}
                      onClick={() => handleReview(del.id, 'rejected')}
                      className="px-3 py-1.5 border border-amber-300 text-amber-800 hover:bg-amber-50 text-xs font-semibold rounded-lg"
                    >
                      Request Revision
                    </button>
                    <button
                      type="button"
                      disabled={reviewingId === del.id}
                      onClick={() => handleReview(del.id, 'approved')}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg"
                    >
                      Approve Deliverable
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
