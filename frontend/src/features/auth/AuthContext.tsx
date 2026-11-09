import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import type { User, Session, AuthError } from '@supabase/supabase-js';
import { supabase, isSupabaseConfigured } from '../../lib/supabase.ts';
import type { Profile, UserRole } from '../../types/index.ts';

interface SignUpResult {
  needsEmailVerification: boolean;
  user: User | null;
}

interface AuthContextType {
  user: User | null;
  session: Session | null;
  profile: Profile | null;
  loading: boolean;
  isConfigured: boolean;
  isEmailConfirmed: boolean;
  error: string | null;
  signUp: (
    email: string,
    password: string,
    displayName: string,
    defaultRole: UserRole
  ) => Promise<SignUpResult>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => setError(null), []);

  // Fetch the user's public.profiles row created by the database trigger
  const fetchProfile = useCallback(async (userId: string) => {
    try {
      const { data, error: profileError } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .maybeSingle();

      if (profileError) {
        console.error('[Auth] Error fetching profile:', profileError.message);
        return null;
      }

      if (data) {
        const mapped: Profile = {
          id: data.id,
          displayName: data.display_name,
          headline: data.headline ?? undefined,
          bio: data.bio ?? undefined,
          avatarUrl: data.avatar_url ?? undefined,
          skills: data.skills ?? [],
          portfolioLinks: data.portfolio_links ?? [],
          isAvailable: data.is_available,
          isAdmin: data.is_admin,
          createdAt: data.created_at,
          updatedAt: data.updated_at,
        };
        setProfile(mapped);
        return mapped;
      }
      return null;
    } catch (err) {
      console.error('[Auth] Failed to load profile:', err);
      return null;
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    if (user?.id) {
      await fetchProfile(user.id);
    }
  }, [user?.id, fetchProfile]);

  // Initial session restoration & auth state listener
  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    let isMounted = true;

    // Get current session on mount
    supabase.auth
      .getSession()
      .then(async ({ data: { session: initialSession }, error: sessionError }) => {
        if (!isMounted) return;

        if (sessionError) {
          console.warn('[Auth] Error restoring session:', sessionError.message);
        }

        setSession(initialSession);
        setUser(initialSession?.user ?? null);

        if (initialSession?.user?.id) {
          await fetchProfile(initialSession.user.id);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    // Subscribe to auth state changes (sign in, sign out, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      if (!isMounted) return;

      setSession(newSession);
      setUser(newSession?.user ?? null);

      if (newSession?.user?.id) {
        await fetchProfile(newSession.user.id);
      } else {
        setProfile(null);
      }
      setLoading(false);
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, [fetchProfile]);

  // Sign up with display_name stored in user_metadata so the trigger populates profiles
  const signUp = async (
    email: string,
    password: string,
    displayName: string,
    defaultRole: UserRole
  ): Promise<SignUpResult> => {
    clearError();
    setLoading(true);

    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: displayName.trim(),
            default_role: defaultRole,
          },
          emailRedirectTo: window.location.origin,
        },
      });

      if (signUpError) {
        throw signUpError;
      }

      const needsVerification = !data.session || !data.user?.email_confirmed_at;
      setUser(data.user);
      setSession(data.session);

      return {
        needsEmailVerification: Boolean(needsVerification),
        user: data.user,
      };
    } catch (err) {
      const msg =
        (err as AuthError).message || 'Failed to sign up. Please try again.';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Log in with email and password
  const signIn = async (email: string, password: string): Promise<void> => {
    clearError();
    setLoading(true);

    try {
      const { data, error: signInError } =
        await supabase.auth.signInWithPassword({
          email,
          password,
        });

      if (signInError) {
        throw signInError;
      }

      setSession(data.session);
      setUser(data.user);

      if (data.user?.id) {
        await fetchProfile(data.user.id);
      }
    } catch (err) {
      const msg =
        (err as AuthError).message || 'Invalid credentials or sign in failed.';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Sign out and clear local state
  const signOut = async (): Promise<void> => {
    clearError();
    setLoading(true);

    try {
      const { error: signOutError } = await supabase.auth.signOut();
      if (signOutError) throw signOutError;

      setSession(null);
      setUser(null);
      setProfile(null);
    } catch (err) {
      const msg = (err as AuthError).message || 'Failed to sign out.';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const isEmailConfirmed = Boolean(user?.email_confirmed_at);

  const value: AuthContextType = {
    user,
    session,
    profile,
    loading,
    isConfigured: isSupabaseConfigured,
    isEmailConfirmed,
    error,
    signUp,
    signIn,
    signOut,
    refreshProfile,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
