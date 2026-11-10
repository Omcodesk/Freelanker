import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
  type MouseEvent,
} from 'react';

export type RouteState =
  | { type: 'home' }
  | { type: 'dashboard' }
  | { type: 'project-detail'; projectId: string }
  | { type: 'invitation-landing'; token: string }
  | { type: 'not-found' };

interface RouterContextType {
  path: string;
  route: RouteState;
  navigate: (to: string) => void;
  goBack: () => void;
}

const RouterContext = createContext<RouterContextType | undefined>(undefined);

export function parseRoute(pathname: string): RouteState {
  const cleanPath = pathname.replace(/\/+$/, '') || '/';

  if (cleanPath === '/') {
    return { type: 'dashboard' };
  }

  if (cleanPath === '/projects' || cleanPath === '/dashboard') {
    return { type: 'dashboard' };
  }

  const projectMatch = cleanPath.match(/^\/projects\/([a-zA-Z0-9_-]+)$/);
  if (projectMatch && projectMatch[1]) {
    return { type: 'project-detail', projectId: projectMatch[1] };
  }

  const invitationMatch = cleanPath.match(/^\/invitations\/([a-zA-Z0-9_-]+)$/);
  if (invitationMatch && invitationMatch[1]) {
    return { type: 'invitation-landing', token: invitationMatch[1] };
  }

  return { type: 'not-found' };
}

export function RouterProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState<string>(() => window.location.pathname);

  useEffect(() => {
    const handleLocationChange = () => {
      setPath(window.location.pathname);
    };

    window.addEventListener('popstate', handleLocationChange);
    window.addEventListener('pushstate', handleLocationChange);
    window.addEventListener('replacestate', handleLocationChange);

    return () => {
      window.removeEventListener('popstate', handleLocationChange);
      window.removeEventListener('pushstate', handleLocationChange);
      window.removeEventListener('replacestate', handleLocationChange);
    };
  }, []);

  const navigate = (to: string) => {
    if (to === window.location.pathname) return;
    window.history.pushState(null, '', to);
    setPath(to);
    window.dispatchEvent(new Event('pushstate'));
  };

  const goBack = () => {
    window.history.back();
  };

  const route = parseRoute(path);

  return (
    <RouterContext.Provider value={{ path, route, navigate, goBack }}>
      {children}
    </RouterContext.Provider>
  );
}

export function useRouter(): RouterContextType {
  const context = useContext(RouterContext);
  if (!context) {
    throw new Error('useRouter must be used within a RouterProvider');
  }
  return context;
}

export function Link({
  href,
  children,
  className,
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  const { navigate } = useRouter();

  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    // Let browser handle modifier keys (Cmd+Click / Ctrl+Click for new tab)
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(href);
  };

  return (
    <a href={href} onClick={handleClick} className={className}>
      {children}
    </a>
  );
}
