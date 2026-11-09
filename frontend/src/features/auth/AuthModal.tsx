import { useState, type FormEvent } from 'react';
import { useAuth } from './AuthContext.tsx';
import type { UserRole } from '../../types/index.ts';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialMode?: 'login' | 'signup';
}

export function AuthModal({
  isOpen,
  onClose,
  initialMode = 'login',
}: AuthModalProps) {
  const { signIn, signUp, error, clearError, isConfigured } = useAuth();

  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState<UserRole>('client');
  const [submitting, setSubmitting] = useState(false);
  const [verificationSent, setVerificationSent] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleTabSwitch = (newMode: 'login' | 'signup') => {
    setMode(newMode);
    clearError();
    setFormError(null);
    setVerificationSent(false);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    clearError();

    if (!isConfigured) {
      setFormError(
        'Supabase is not configured yet. Please configure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env'
      );
      return;
    }

    if (!email || !password) {
      setFormError('Please enter both email and password.');
      return;
    }

    if (password.length < 8) {
      setFormError('Password must be at least 8 characters long.');
      return;
    }

    if (mode === 'signup' && !displayName.trim()) {
      setFormError('Please enter your full name or display name.');
      return;
    }

    setSubmitting(true);

    try {
      if (mode === 'login') {
        await signIn(email, password);
        onClose();
      } else {
        const result = await signUp(email, password, displayName, role);
        if (result.needsEmailVerification) {
          setVerificationSent(true);
        } else {
          onClose();
        }
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An error occurred during authentication.';
      setFormError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 pt-6 pb-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <span className="text-white text-sm font-bold">F</span>
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                {mode === 'login' ? 'Welcome back' : 'Create your account'}
              </h3>
              <p className="text-xs text-slate-500">
                {mode === 'login'
                  ? 'Sign in to access your projects and payments'
                  : 'Get started with AI-assisted freelance collaboration'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1.5 transition-colors"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Verification Success View */}
        {verificationSent ? (
          <div className="p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto text-xl">
              ✉️
            </div>
            <h4 className="text-lg font-semibold text-slate-900">
              Check your email
            </h4>
            <p className="text-sm text-slate-600 leading-relaxed">
              We have sent a verification link to{' '}
              <strong className="text-slate-900 font-medium">{email}</strong>.
              Click the link in the email to activate your Freelanker account.
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={onClose}
                className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Close & Return
              </button>
            </div>
          </div>
        ) : (
          /* Form View */
          <div className="p-6 space-y-5">
            {/* Tabs */}
            <div className="flex rounded-lg bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => handleTabSwitch('login')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  mode === 'login'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Log In
              </button>
              <button
                type="button"
                onClick={() => handleTabSwitch('signup')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  mode === 'signup'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Sign Up
              </button>
            </div>

            {/* Error alerts */}
            {(formError || error) && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg p-3">
                {formError || error}
              </div>
            )}

            {!isConfigured && (
              <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg p-3 space-y-1">
                <p className="font-semibold">Supabase Keys Required</p>
                <p>
                  Set <code className="bg-amber-100 px-1 rounded">VITE_SUPABASE_URL</code> and{' '}
                  <code className="bg-amber-100 px-1 rounded">VITE_SUPABASE_ANON_KEY</code> in{' '}
                  <code className="bg-amber-100 px-1 rounded">frontend/.env</code> to enable live authentication.
                </p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'signup' && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Full Name
                    </label>
                    <input
                      type="text"
                      required
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Jane Doe"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      I want to
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setRole('client')}
                        className={`p-2.5 text-left border rounded-lg text-xs transition-all ${
                          role === 'client'
                            ? 'border-brand-600 bg-brand-50/50 text-brand-900'
                            : 'border-slate-200 text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        <p className="font-semibold">Hire Talent</p>
                        <p className="text-[10px] text-slate-500">I am a client</p>
                      </button>
                      <button
                        type="button"
                        onClick={() => setRole('freelancer')}
                        className={`p-2.5 text-left border rounded-lg text-xs transition-all ${
                          role === 'freelancer'
                            ? 'border-brand-600 bg-brand-50/50 text-brand-900'
                            : 'border-slate-200 text-slate-700 hover:border-slate-300'
                        }`}
                      >
                        <p className="font-semibold">Work & Earn</p>
                        <p className="text-[10px] text-slate-500">I am a freelancer</p>
                      </button>
                    </div>
                  </div>
                </>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Password (min 8 characters)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-colors flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Processing…</span>
                  </>
                ) : mode === 'login' ? (
                  'Sign In'
                ) : (
                  'Create Account'
                )}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
