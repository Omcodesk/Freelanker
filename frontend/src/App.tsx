import { AuthProvider } from './features/auth/AuthContext.tsx';
import { AppShell } from './components/layout/AppShell.tsx';
import { Home } from './pages/Home.tsx';

export default function App() {
  return (
    <AuthProvider>
      <AppShell>
        <Home />
      </AppShell>
    </AuthProvider>
  );
}
