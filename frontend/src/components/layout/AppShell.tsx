import type { ReactNode } from 'react';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-surface-secondary flex flex-col">
      {/* Top navigation bar — full implementation comes with auth task */}
      <header className="bg-white border-b border-slate-200 h-14 flex items-center px-6 shrink-0">
        <div className="flex items-center gap-2">
          {/* Logo mark */}
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold">F</span>
          </div>
          <span className="font-semibold text-slate-900 text-sm tracking-tight">
            Freelanker
          </span>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono bg-slate-100 px-2 py-1 rounded">
            core-platform
          </span>
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
    </div>
  );
}

