import { type ReactNode, useState } from 'react';
import { useAuth } from './AuthContext.tsx';
import { AuthModal } from './AuthModal.tsx';

interface ProtectedRouteProps {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
}

export function ProtectedRoute({
  children,
  fallbackTitle = 'Authentication Required',
  fallbackMessage = 'Please sign in or create an account to access this project workspace.',
}: ProtectedRouteProps) {
  const { user, loading, isEmailConfirmed } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'login' | 'signup'>('login');

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="flex items-center gap-3 text-slate-500 text-sm font-medium">
          <span className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          Authenticating…
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-xl p-8 text-center space-y-5 shadow-sm">
          <div className="w-12 h-12 bg-brand-50 text-brand-600 rounded-full flex items-center justify-center mx-auto text-xl">
            🔒
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-slate-900">
              {fallbackTitle}
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              {fallbackMessage}
            </p>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                setModalMode('login');
                setModalOpen(true);
              }}
              className="flex-1 py-2 px-4 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-sm font-medium transition-colors"
            >
              Log In
            </button>
            <button
              type="button"
              onClick={() => {
                setModalMode('signup');
                setModalOpen(true);
              }}
              className="flex-1 py-2 px-4 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Sign Up
            </button>
          </div>
        </div>

        <AuthModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          initialMode={modalMode}
        />
      </div>
    );
  }

  return (
    <>
      {!isEmailConfirmed && (
        <div className="bg-amber-50 border-b border-amber-200 px-6 py-2.5 text-xs text-amber-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>
              Your email address (<strong>{user.email}</strong>) is not yet verified.
              Please check your inbox to confirm your account.
            </span>
          </div>
        </div>
      )}
      {children}
    </>
  );
}
