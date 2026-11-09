// Base API client using native fetch (Node 22 / browser built-in)
// Automatically attaches Supabase session Bearer token when authenticated
// See docs/API_CONTRACTS.md for all available endpoints.

import type { ApiResponse } from '../types/index.ts';
import { supabase } from '../lib/supabase.ts';

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  'http://localhost:4000/api';

class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  // Retrieve current session token if available
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };

  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }
  } catch {
    // Session retrieval failure should not block request execution
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const json = (await response.json()) as ApiResponse<T>;

  if (!response.ok || !json.success) {
    throw new ApiError(
      json.error ?? `Request failed with status ${response.status}`,
      response.status
    );
  }

  return json.data as T;
}

export const api = {
  get: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'GET', ...options }),

  post: <T>(path: string, body: unknown, options?: RequestInit) =>
    request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
      ...options,
    }),

  put: <T>(path: string, body: unknown, options?: RequestInit) =>
    request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body),
      ...options,
    }),

  patch: <T>(path: string, body: unknown, options?: RequestInit) =>
    request<T>(path, {
      method: 'PATCH',
      body: JSON.stringify(body),
      ...options,
    }),

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'DELETE', ...options }),
};

export { ApiError };
