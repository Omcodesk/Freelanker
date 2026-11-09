import { createClient } from '@supabase/supabase-js';

const supabaseUrl = (import.meta.env.VITE_SUPABASE_URL as string | undefined) ?? '';
const supabaseAnonKey = (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) ?? '';

export const isSupabaseConfigured = Boolean(
  supabaseUrl &&
  supabaseAnonKey &&
  !supabaseUrl.includes('your-project') &&
  !supabaseAnonKey.includes('your-anon-key')
);

if (import.meta.env.DEV && !isSupabaseConfigured) {
  console.warn(
    '[Freelanker Supabase] Credentials not detected. ' +
    'Please configure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env'
  );
}

// Initialize Supabase browser client with session persistence & URL token detection
export const supabase = createClient(
  supabaseUrl || 'https://placeholder-project.supabase.co',
  supabaseAnonKey || 'placeholder-anon-key',
  {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true,
      storageKey: 'freelanker-auth-token',
    },
  }
);
