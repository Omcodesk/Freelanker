import { useEffect, useState } from 'react';
import { api, ApiError } from '../services/api.ts';
import { useRouter } from '../lib/router.tsx';
import { useAuth } from '../features/auth/AuthContext.tsx';
import { AuthModal } from '../features/auth/AuthModal.tsx';
import type { InvitationPreview } from '../types/index.ts';

interface InvitationLandingProps {
  token: string;
}

export function InvitationLanding({ token }: InvitationLandingProps) {
  const { user, isEmailConfirmed } = useAuth();
  const { navigate } = useRouter();

  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Auth modal trigger for unauthenticated visitors
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'signup'>('signup');

  // Acceptance / Rejection State
  const [processing, setProcessing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [acceptedSuccess, setAcceptedSuccess] = useState(false);

  const fetchPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<{ invitation: InvitationPreview }>(
        `/invitations/token/${token}`
      );
      setPreview(res.invitation);
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError
          ? err.message
          : 'Invalid or unrecognized invitation link.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreview();
  }, [token]);

  const handleAccept = async () => {
    if (!preview) return;
    setActionError(null);
    setProcessing(true);

    try {
      await api.post(`/invitations/${preview.id}/accept`, {});
      setAcceptedSuccess(true);
      setTimeout(() => {
        navigate(`/projects/${preview.projectId}`);
      }, 1500);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to accept invitation.';
      setActionError(msg);
      setProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!preview) return;
    if (!window.confirm('Are you sure you want to decline this invitation?')) return;

    setActionError(null);
    setProcessing(true);

    try {
      await api.post(`/invitations/${preview.id}/reject`, {});
      navigate('/');
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to decline invitation.';
      setActionError(msg);
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="flex items-center gap-3 text-slate-500 text-sm font-medium">
          <span className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          Resolving invitation...
        </div>
      </div>
    );
  }

  if (error || !preview) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-8 text-center space-y-4 shadow-sm">
          <div className="w-12 h-12 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto text-xl">
            ⚠️
          </div>
          <h2 className="text-lg font-bold text-slate-900">Invalid Invitation Link</h2>
          <p className="text-xs sm:text-sm text-slate-500">
            {error || 'This invitation does not exist or the link is invalid.'}
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors"
          >
            Go to Freelanker Home
          </button>
        </div>
      </div>
    );
  }

  const isPending = preview.status === 'pending' && !preview.isExpired;
  const isFreelancer = preview.role === 'freelancer';

  return (
    <div className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-lg w-full bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-md space-y-6 animate-in fade-in zoom-in-95 duration-200">
        {/* Inviter Info Header */}
        <div className="text-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-brand-100 text-brand-700 font-bold text-lg flex items-center justify-center mx-auto shadow-inner border border-brand-200">
            {preview.inviter.displayName.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">
              Project Collaboration Invite
            </p>
            <h1 className="text-xl font-bold text-slate-900 mt-1">
              {preview.inviter.displayName} invited you to join
            </h1>
          </div>
        </div>

        {/* Project Card Preview */}
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-white border border-slate-200 text-slate-700 capitalize">
              Role: {isFreelancer ? '🛠️ Freelancer' : '💼 Client'}
            </span>
            {preview.totalBudget && (
              <span className="text-xs font-bold text-slate-900">
                {preview.currency} {Number(preview.totalBudget).toLocaleString()}
              </span>
            )}
          </div>
          <h2 className="text-base font-bold text-slate-900">{preview.projectTitle}</h2>
          {preview.projectDescription && (
            <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">
              {preview.projectDescription}
            </p>
          )}
          <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-400">
            <span>Sent to: <strong className="text-slate-600 font-mono">{preview.maskedEmail}</strong></span>
            <span>Expires: {new Date(preview.expiresAt).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Status Handling Banner */}
        {!isPending && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-center space-y-1">
            <p className="text-xs font-bold text-amber-900 capitalize">
              Invitation {preview.status}
            </p>
            <p className="text-[11px] text-amber-700">
              {preview.status === 'accepted'
                ? 'This invitation has already been accepted and processed.'
                : preview.status === 'expired' || preview.isExpired
                ? 'This invitation link has expired. Please request a new invitation.'
                : 'This invitation is no longer active.'}
            </p>
          </div>
        )}

        {/* Success Banner */}
        {acceptedSuccess && (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center space-y-1 animate-in fade-in">
            <p className="text-xs font-bold text-emerald-900">
              🎉 Invitation Accepted!
            </p>
            <p className="text-[11px] text-emerald-700">
              You are now a member of this project. Redirecting to workspace...
            </p>
          </div>
        )}

        {/* Action Error Banner */}
        {actionError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
            {actionError}
          </div>
        )}

        {/* Action Controls */}
        {isPending && !acceptedSuccess && (
          <div>
            {!user ? (
              /* Unauthenticated Flow */
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 text-center space-y-3">
                <p className="text-xs text-slate-600 leading-relaxed">
                  To accept this invitation and join the workspace, please sign in or register with your email account.
                </p>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setAuthModalMode('login');
                      setAuthModalOpen(true);
                    }}
                    className="flex-1 py-2 px-3 border border-slate-300 hover:bg-slate-100 rounded-xl text-xs font-semibold text-slate-700 transition-colors"
                  >
                    Log In
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthModalMode('signup');
                      setAuthModalOpen(true);
                    }}
                    className="flex-1 py-2 px-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors"
                  >
                    Create Account
                  </button>
                </div>
              </div>
            ) : (
              /* Authenticated Flow */
              <div className="space-y-4">
                {!isEmailConfirmed && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
                    ⚠️ Your email address (<strong>{user.email}</strong>) is not yet verified. Please verify your email before accepting this invitation.
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handleReject}
                    disabled={processing}
                    className="flex-1 py-2.5 px-4 border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl transition-colors disabled:opacity-50"
                  >
                    Decline
                  </button>
                  <button
                    type="button"
                    onClick={handleAccept}
                    disabled={processing || !isEmailConfirmed}
                    className="flex-1 py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-sm transition-colors flex items-center justify-center gap-2"
                  >
                    {processing && (
                      <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    )}
                    Accept Invitation
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Back to Home if already resolved */}
        {(!isPending || acceptedSuccess) && (
          <button
            type="button"
            onClick={() => navigate('/')}
            className="w-full py-2.5 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl hover:bg-slate-50 transition-colors"
          >
            Go to Projects Dashboard
          </button>
        )}

        {/* Auth Modal with preserved destination */}
        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          initialMode={authModalMode}
          onSuccess={() => {
            // Re-fetch preview or stay on landing page
            fetchPreview();
          }}
        />
      </div>
    </div>
  );
}
