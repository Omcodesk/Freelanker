import { createClient } from '@supabase/supabase-js';
import { env } from '../config/env.js';

const supabaseUrl = env.SUPABASE_URL || 'https://placeholder-project.supabase.co';
const supabaseAnonKey = env.SUPABASE_ANON_KEY || 'placeholder-anon-key';
const supabaseServiceKey = env.SUPABASE_SERVICE_ROLE_KEY || supabaseAnonKey;

// Standard Supabase client used for verifying user JWTs
export const supabaseAuth = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});

// Admin Supabase client with service-role privileges (backend-only!)
// Used strictly for server-side trusted operations (e.g. PayPal state transitions)
export const supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});

export const isBackendSupabaseConfigured = Boolean(
  env.SUPABASE_URL &&
  env.SUPABASE_ANON_KEY &&
  !env.SUPABASE_URL.includes('your-project')
);
