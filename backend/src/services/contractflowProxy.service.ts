/**
 * ContractFlow Proxy Service.
 *
 * Forwards authenticated requests from the Express API Gateway to the
 * isolated Python FastAPI ContractFlow service.
 *
 * Invariants:
 * - Forwards original verified Supabase Bearer token.
 * - Strict request timeout via AbortController (default 45s; health checks 5s).
 * - Zero automatic retries on state-changing POST requests (preserves approval idempotency).
 * - Translates known FastAPI error codes into safe user messages while preserving error codes.
 * - Never leaks upstream service credentials or connection strings.
 */

import { env, normalizeServiceUrl } from '../config/env.js';

export interface ProxyResponse<T = unknown> {
  status: number;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
}

const CONTRACTFLOW_ERROR_MESSAGES: Record<string, string> = {
  UNAUTHENTICATED: 'Authentication required or session token is invalid.',
  FORBIDDEN: 'You are not authorized to perform this ContractFlow operation.',
  NOT_FOUND: 'Requested ContractFlow resource was not found.',
  STALE_SOURCE: 'Project data changed before completion. Refresh and retry with the current source version.',
  MISSING_AGREEMENT: 'An active current agreement is required before running scope assessment or amendments.',
  INVALID_SOURCE: 'Project details are incomplete for ContractFlow. Ensure both parties, positive budget, and planned milestones with due dates are configured.',
  REVIEW_INVALID: 'Required review verification is missing, expired, or has been revoked.',
  WORKFLOW_CONFLICT: 'Conflict with current amendment state, revision, or idempotency key.',
  IDEMPOTENCY_CONFLICT: 'Idempotency key has already been used for a conflicting decision.',
  INVALID_REQUEST: 'Invalid ContractFlow request payload or parameters.',
  REQUEST_TOO_LARGE: 'Request body exceeds the 128 KB ContractFlow limit.',
  PROVIDER_TIMEOUT: 'AI contract generation timed out. Please try again.',
  PROVIDER_FAILED: 'AI contract provider failed to return a valid draft.',
  UNAVAILABLE: 'ContractFlow service or AI generation is currently unavailable.',
  INTEGRATION_UNAVAILABLE: 'ContractFlow integration dependency is temporarily unavailable.',
};

export function translateContractFlowErrorMessage(code: string, upstreamMessage?: unknown, status?: number): string {
  if (typeof upstreamMessage === 'string' && upstreamMessage.trim().length > 0) {
    return upstreamMessage;
  }
  if (code in CONTRACTFLOW_ERROR_MESSAGES) {
    return CONTRACTFLOW_ERROR_MESSAGES[code];
  }
  return `ContractFlow service responded with HTTP ${status ?? 502}.`;
}

export class ContractFlowProxyService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(
    baseUrl?: string,
    timeoutMs = parseInt(process.env.CONTRACTFLOW_PROXY_TIMEOUT_MS || '45000', 10)
  ) {
    this.baseUrl = normalizeServiceUrl(baseUrl || env.CONTRACTFLOW_SERVICE_URL);
    this.timeoutMs = timeoutMs;
  }

  /**
   * Forward a request to the ContractFlow FastAPI service.
   *
   * @param method HTTP method (GET, POST)
   * @param path Upstream path relative to /api/v1/contractflow
   * @param bearerToken User's Supabase JWT access token
   * @param body Optional JSON payload
   */
  async forward<T = unknown>(
    method: 'GET' | 'POST',
    path: string,
    bearerToken: string,
    body?: unknown
  ): Promise<ProxyResponse<T>> {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const url = `${this.baseUrl}/api/v1/contractflow${cleanPath}`;
    return this._request<T>(method, url, { bearerToken, body, timeoutMs: this.timeoutMs });
  }

  /**
   * Query the FastAPI ContractFlow /health endpoint.
   */
  async checkHealth<T = Record<string, unknown>>(timeoutMs = 5000): Promise<ProxyResponse<T>> {
    return this._request<T>('GET', `${this.baseUrl}/health`, { timeoutMs });
  }

  private async _request<T>(
    method: 'GET' | 'POST',
    url: string,
    options: { bearerToken?: string; body?: unknown; timeoutMs: number }
  ): Promise<ProxyResponse<T>> {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
    };
    if (options.bearerToken) {
      headers['Authorization'] = `Bearer ${options.bearerToken}`;
    }

    let payload: string | undefined;
    if (options.body !== undefined && method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      payload = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: payload,
        signal: controller.signal,
      });

      const responseText = await response.text();
      let responseJson: any = null;
      try {
        responseJson = JSON.parse(responseText);
      } catch {
        responseJson = null;
      }

      if (!response.ok) {
        const rawCode = responseJson?.error?.code || responseJson?.detail || (response.status === 503 ? 'UNAVAILABLE' : 'UPSTREAM_ERROR');
        const errorCode = typeof rawCode === 'string' ? rawCode : 'UPSTREAM_ERROR';
        const errorMessage = translateContractFlowErrorMessage(
          errorCode,
          responseJson?.error?.message ?? (typeof responseJson?.detail === 'string' ? responseJson.detail : undefined),
          response.status
        );

        return {
          status: response.status,
          error: {
            code: errorCode,
            message: errorMessage,
            details: responseJson?.error?.details || responseJson,
          },
        };
      }

      return {
        status: response.status,
        data: responseJson as T,
      };
    } catch (err: unknown) {
      const safeTarget = (() => {
        try {
          const parsed = new URL(url);
          return `${parsed.origin}${parsed.pathname}`;
        } catch {
          return 'contractflow-upstream';
        }
      })();
      if (err instanceof Error && err.name === 'AbortError') {
        console.warn(`[ContractFlowProxy] Timeout reaching ${safeTarget} after ${options.timeoutMs}ms`);
        return {
          status: 504,
          error: {
            code: 'GATEWAY_TIMEOUT',
            message: `ContractFlow service did not respond within ${options.timeoutMs / 1000} seconds.`,
          },
        };
      }

      const causeCode = (err as any)?.cause?.code || (err as any)?.code || (err instanceof Error ? err.name : 'FETCH_ERROR');
      console.error(`[ContractFlowProxy] Connection failed for ${safeTarget} (${causeCode})`);
      return {
        status: 503,
        error: {
          code: 'SERVICE_UNAVAILABLE',
          message: 'Unable to connect to the ContractFlow service. Service may be unconfigured or restarting.',
        },
      };
    } finally {
      clearTimeout(timeout);
    }
  }
}

export const contractflowProxy = new ContractFlowProxyService();
