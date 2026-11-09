// Supabase client placeholder
// Will be fully configured when Supabase Auth is implemented (next task).
// Keys are loaded from VITE_ environment variables only.

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

// Log a warning in development if not yet configured
if (import.meta.env.DEV && (!supabaseUrl || !supabaseAnonKey)) {
  console.warn(
    '[Supabase] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY is not set. ' +
    'Copy frontend/.env.example to frontend/.env and add your Supabase credentials.'
  );
}

export const supabaseConfig = {
  url: supabaseUrl ?? '',
  anonKey: supabaseAnonKey ?? '',
  isConfigured: Boolean(supabaseUrl && supabaseAnonKey),
} as const;

// Supabase client will be initialized here once @supabase/supabase-js is added.
// import { createClient } from '@supabase/supabase-js';
// export const supabase = createClient(supabaseConfig.url, supabaseConfig.anonKey);
