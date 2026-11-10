import { type ReactNode, useState } from 'react';
import { useAuth } from '../../features/auth/AuthContext.tsx';
import { AuthModal } from '../../features/auth/AuthModal.tsx';
import { useRouter } from '../../lib/router.tsx';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { user, profile, loading, signOut, isConfigured } = useAuth();
  const { navigate } = useRouter();
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'login' | 'signup'>('login');

  const displayName = profile?.displayName || user?.email?.split('@')[0] || 'User';
  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="min-h-screen bg-surface-secondary flex flex-col">
      {/* Top navigation bar */}
      <header className="bg-white border-b border-slate-200 h-14 flex items-center px-6 shrink-0 justify-between">
        <div
          onClick={() => navigate('/')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          {/* Logo mark */}
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center shadow-sm group-hover:bg-brand-700 transition-colors">
            <span className="text-white text-xs font-bold">F</span>
          </div>
          <span className="font-semibold text-slate-900 text-sm tracking-tight group-hover:text-brand-600 transition-colors">
            Freelanker
          </span>
          <span className="text-[10px] text-slate-400 font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
            core-platform
          </span>
        </div>

        {/* User Session Nav */}
        <div className="flex items-center gap-3">
          {loading ? (
            <span className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          ) : user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 font-semibold text-xs flex items-center justify-center border border-brand-200">
                  {initials}
                </div>
                <div className="hidden sm:block text-left">
                  <p className="text-xs font-semibold text-slate-900 leading-none">
                    {displayName}
                  </p>
                  <p className="text-[10px] text-slate-400 leading-tight">
                    {user.email}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => signOut()}
                className="text-xs text-slate-600 hover:text-red-600 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:border-red-200 hover:bg-red-50/50 transition-colors"
              >
                Log Out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              {!isConfigured && (
                <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  Supabase unconfigured
                </span>
              )}
              <button
                type="button"
                onClick={() => {
                  setModalMode('login');
                  setModalOpen(true);
                }}
                className="text-xs font-medium text-slate-700 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              >
                Log In
              </button>
              <button
                type="button"
                onClick={() => {
                  setModalMode('signup');
                  setModalOpen(true);
                }}
                className="text-xs font-semibold bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded-lg shadow-sm transition-colors"
              >
                Sign Up
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col">{children}</main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white px-6 py-3">
        <p className="text-xs text-slate-400 text-center">
          Freelanker MVP · PayPal AI Hackathon · 2026
        </p>
      </footer>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        initialMode={modalMode}
      />
    </div>
  );
}
