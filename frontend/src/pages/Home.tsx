import { useEffect, useState } from 'react';
import { api, ApiError } from '../services/api.ts';
import { useAuth } from '../features/auth/AuthContext.tsx';
import { AuthModal } from '../features/auth/AuthModal.tsx';
import type { HealthData, Profile } from '../types/index.ts';

type HealthState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; data: HealthData }
  | { status: 'error'; message: string };

interface MeResponse {
  user: {
    id: string;
    email: string;
    createdAt: string;
    userMetadata?: Record<string, unknown>;
  };
  profile: Profile | null;
}

export function Home() {
  const { user, profile, isConfigured, isEmailConfirmed, signOut } = useAuth();

  const [health, setHealth] = useState<HealthState>({ status: 'idle' });
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'login' | 'signup'>('login');

  const [backendAuthTest, setBackendAuthTest] = useState<{
    loading: boolean;
    data: MeResponse | null;
    error: string | null;
  }>({
    loading: false,
    data: null,
    error: null,
  });

  useEffect(() => {
    setHealth({ status: 'loading' });

    api
      .get<HealthData>('/health')
      .then((data) => setHealth({ status: 'ok', data }))
      .catch((err) => {
        const message =
          err instanceof ApiError
            ? err.message
            : 'Could not reach the backend';
        setHealth({ status: 'error', message });
      });
  }, []);

  // Test protected Express endpoint GET /api/auth/me
  const testProtectedBackend = async () => {
    setBackendAuthTest({ loading: true, data: null, error: null });
    try {
      const data = await api.get<MeResponse>('/auth/me');
      setBackendAuthTest({ loading: false, data, error: null });
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Protected API call failed';
      setBackendAuthTest({ loading: false, data: null, error: msg });
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6 md:p-12">
      <div className="max-w-2xl w-full space-y-8">
        {/* Hero */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 bg-brand-50 text-brand-700 text-xs font-medium px-3 py-1.5 rounded-full border border-brand-200">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
            Core Platform · feature/core-platform
          </div>
          <h1 className="text-4xl font-bold text-slate-900 tracking-tight">
            Freelanker
          </h1>
          <p className="text-base sm:text-lg text-slate-500 max-w-md mx-auto leading-relaxed">
            AI-powered freelance collaboration and payment platform.
            From project idea to successful payment.
          </p>
        </div>

        {/* Authentication Status Card */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Supabase Authentication Status
              </h2>
              <p className="text-xs text-slate-500">
                Persistent sessions, email verification & server-side JWT verification
              </p>
            </div>
            <span
              className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
                !isConfigured
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : user
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-50 text-slate-600 border-slate-200'
              }`}
            >
              {!isConfigured
                ? 'Unconfigured'
                : user
                ? 'Authenticated'
                : 'Guest Mode'}
            </span>
          </div>

          {!isConfigured ? (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-xs text-amber-900 space-y-2">
              <p className="font-semibold">Configuration Required</p>
              <p>
                Add your Supabase credentials to <code className="bg-amber-100 px-1 rounded font-mono">frontend/.env</code>:
              </p>
              <pre className="bg-white/80 p-2.5 rounded font-mono text-[11px] overflow-x-auto border border-amber-200/50">
                VITE_SUPABASE_URL=https://your-project.supabase.co{'\n'}
                VITE_SUPABASE_ANON_KEY=your-anon-key-here
              </pre>
            </div>
          ) : user ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-0.5">Signed in as</span>
                  <span className="font-semibold text-slate-800 break-all">{user.email}</span>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-0.5">Display Name (Profiles trigger)</span>
                  <span className="font-semibold text-slate-800">
                    {profile?.displayName || 'Loading profile…'}
                  </span>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-0.5">Email Verification</span>
                  <span
                    className={`inline-flex items-center gap-1 font-semibold ${
                      isEmailConfirmed ? 'text-emerald-700' : 'text-amber-700'
                    }`}
                  >
                    <span>{isEmailConfirmed ? '✓ Verified' : '⏳ Pending verification'}</span>
                  </span>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-slate-400 block mb-0.5">User ID</span>
                  <span className="font-mono text-slate-600 text-[11px] truncate block">
                    {user.id}
                  </span>
                </div>
              </div>

              {/* Server-Side Auth Verification Test */}
              <div className="pt-2 border-t border-slate-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-700">
                    Express Backend Verification (Bearer JWT)
                  </span>
                  <button
                    type="button"
                    onClick={testProtectedBackend}
                    disabled={backendAuthTest.loading}
                    className="text-xs bg-slate-900 hover:bg-slate-800 text-white px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 font-medium"
                  >
                    {backendAuthTest.loading && (
                      <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    )}
                    Test GET /api/auth/me
                  </button>
                </div>

                {backendAuthTest.data && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs space-y-1 font-mono text-emerald-900">
                    <p className="font-semibold">✓ Backend verified JWT successfully!</p>
                    <p className="text-[11px] text-emerald-700">
                      User ID: {backendAuthTest.data.user.id} · Profile:{' '}
                      {backendAuthTest.data.profile?.displayName ?? 'None'}
                    </p>
                  </div>
                )}

                {backendAuthTest.error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-800">
                    Error from backend: {backendAuthTest.error}
                  </div>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => signOut()}
                  className="text-xs text-red-600 hover:text-red-700 font-medium transition-colors"
                >
                  Sign Out
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-4 space-y-4">
              <p className="text-xs text-slate-600">
                You are currently browsing in guest mode. Sign in to test authentication and protected workspaces.
              </p>
              <div className="flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setModalMode('login');
                    setModalOpen(true);
                  }}
                  className="py-2 px-4 border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                >
                  Log In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setModalMode('signup');
                    setModalOpen(true);
                  }}
                  className="py-2 px-4 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                >
                  Sign Up
                </button>
              </div>
            </div>
          )}
        </div>

        {/* API Health Card */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">
              Backend Health Check
            </h2>
            <code className="text-xs text-slate-400 bg-slate-50 px-2 py-1 rounded font-mono">
              GET /api/health
            </code>
          </div>

          {health.status === 'idle' && (
            <p className="text-sm text-slate-400">Waiting…</p>
          )}

          {health.status === 'loading' && (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <span className="w-3 h-3 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
              Checking backend…
            </div>
          )}

          {health.status === 'ok' && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                <span className="text-sm font-medium text-emerald-700">
                  Backend is reachable
                </span>
              </div>
              <div className="bg-slate-50 rounded-lg p-4 font-mono text-xs text-slate-600 space-y-1">
                <div>
                  <span className="text-slate-400">status: </span>
                  <span className="text-emerald-600">"{health.data.status}"</span>
                </div>
                <div>
                  <span className="text-slate-400">environment: </span>
                  <span className="text-brand-600">"{health.data.environment}"</span>
                </div>
                <div>
                  <span className="text-slate-400">version: </span>
                  <span className="text-slate-700">"{health.data.version}"</span>
                </div>
                <div>
                  <span className="text-slate-400">timestamp: </span>
                  <span className="text-slate-700">"{health.data.timestamp}"</span>
                </div>
              </div>
            </div>
          )}

          {health.status === 'error' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
                <span className="text-sm font-medium text-red-700">
                  Backend not reachable
                </span>
              </div>
              <p className="text-xs text-red-500 bg-red-50 px-3 py-2 rounded-lg">
                {health.message}
              </p>
            </div>
          )}
        </div>

        {/* Module Status Grid */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'ContractFlow', owner: 'Person 2', status: 'planned' },
            { label: 'WorkBridge', owner: 'Person 3', status: 'planned' },
            { label: 'PayFlow', owner: 'Person 1', status: 'planned' },
            { label: 'Freelanker AI', owner: 'Person 1', status: 'planned' },
          ].map((mod) => (
            <div
              key={mod.label}
              className="bg-white border border-slate-200 rounded-lg p-4 space-y-1"
            >
              <p className="text-xs font-semibold text-slate-700">{mod.label}</p>
              <p className="text-xs text-slate-400">{mod.owner}</p>
              <span className="inline-block text-xs bg-amber-50 text-amber-600 border border-amber-200 px-2 py-0.5 rounded-full">
                {mod.status}
              </span>
            </div>
          ))}
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
