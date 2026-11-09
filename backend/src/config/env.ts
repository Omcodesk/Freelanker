import dotenv from 'dotenv';

dotenv.config();

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function optionalEnv(key: string, defaultValue: string): string {
  return process.env[key] ?? defaultValue;
}

export const env = {
  PORT: parseInt(optionalEnv('PORT', '4000'), 10),
  NODE_ENV: optionalEnv('NODE_ENV', 'development'),
  FRONTEND_URL: optionalEnv('FRONTEND_URL', 'http://localhost:5173'),

  // These will throw at startup if missing in production
  // In development, they can be empty placeholders
  SUPABASE_URL: optionalEnv('SUPABASE_URL', ''),
  SUPABASE_ANON_KEY: optionalEnv('SUPABASE_ANON_KEY', ''),
  SUPABASE_SERVICE_ROLE_KEY: optionalEnv('SUPABASE_SERVICE_ROLE_KEY', ''),

  OPENAI_API_KEY: optionalEnv('OPENAI_API_KEY', ''),

  PAYPAL_CLIENT_ID: optionalEnv('PAYPAL_CLIENT_ID', ''),
  PAYPAL_CLIENT_SECRET: optionalEnv('PAYPAL_CLIENT_SECRET', ''),
  PAYPAL_MODE: optionalEnv('PAYPAL_MODE', 'sandbox'),

  get isDevelopment(): boolean {
    return this.NODE_ENV === 'development';
  },

  get isProduction(): boolean {
    return this.NODE_ENV === 'production';
  },

  /**
   * Call this to validate critical env vars before production startup.
   * Not called automatically in development to allow incremental setup.
   */
  validateProduction(): void {
    if (this.isProduction) {
      requireEnv('SUPABASE_URL');
      requireEnv('SUPABASE_SERVICE_ROLE_KEY');
      requireEnv('OPENAI_API_KEY');
      requireEnv('PAYPAL_CLIENT_ID');
      requireEnv('PAYPAL_CLIENT_SECRET');
      requireEnv('FRONTEND_URL');
    }
  },
} as const;

