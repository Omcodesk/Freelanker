import { useEffect, useState } from 'react';
import { api, ApiError } from '../services/api.ts';
import type { HealthData } from '../types/index.ts';

type HealthState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; data: HealthData }
  | { status: 'error'; message: string };

export function Home() {
  const [health, setHealth] = useState<HealthState>({ status: 'idle' });

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

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-8">
        {/* Hero */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 bg-brand-50 text-brand-700 text-xs font-medium px-3 py-1.5 rounded-full border border-brand-200">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
            Foundation — feature/core-platform
          </div>
          <h1 className="text-4xl font-bold text-slate-900 tracking-tight">
            Freelanker
          </h1>
          <p className="text-lg text-slate-500 max-w-md mx-auto leading-relaxed">
            AI-powered freelance collaboration and payment platform.
            From project idea to successful payment.
          </p>
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
              <p className="text-xs text-slate-400">
                Make sure the backend is running:{' '}
                <code className="font-mono bg-slate-100 px-1 rounded">
                  cd backend && npm run dev
                </code>
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
    </div>
  );
}
