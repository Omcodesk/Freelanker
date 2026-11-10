import { AuthProvider, useAuth } from './features/auth/AuthContext.tsx';
import { RouterProvider, useRouter } from './lib/router.tsx';
import { AppShell } from './components/layout/AppShell.tsx';
import { ProjectDashboard } from './features/projects/ProjectDashboard.tsx';
import { ProjectDetailView } from './features/projects/ProjectDetailView.tsx';
import { InvitationLanding } from './pages/InvitationLanding.tsx';
import { Home } from './pages/Home.tsx';

function AppContent() {
  const { route } = useRouter();
  const { user } = useAuth();

  switch (route.type) {
    case 'invitation-landing':
      return <InvitationLanding token={route.token} />;
    case 'project-detail':
      return <ProjectDetailView projectId={route.projectId} />;
    case 'dashboard':
      return user ? <ProjectDashboard /> : <Home />;
    case 'not-found':
    default:
      return (
        <div className="flex-1 flex items-center justify-center p-8 text-center space-y-4">
          <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
            <h2 className="text-xl font-bold text-slate-900">404 - Page Not Found</h2>
            <p className="text-xs text-slate-500 mt-1">
              The page you are looking for does not exist.
            </p>
          </div>
        </div>
      );
  }
}

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider>
        <AppShell>
          <AppContent />
        </AppShell>
      </RouterProvider>
    </AuthProvider>
  );
}
