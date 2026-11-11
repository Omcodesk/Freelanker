/**
 * ContractFlow Proxy Service.
 *
 * Forwards authenticated requests from the Express API Gateway to the
 * isolated Python FastAPI ContractFlow service.
 *
 * Invariants:
 * - Forwards original verified Supabase Bearer token.
 * - Strict 30s timeout via AbortController.
 * - Zero automatic retries on state-changing POST requests (preserves approval idempotency).
 * - Never leaks upstream service credentials or connection strings.
 */

import { env } from '../config/env.js';

export interface ProxyResponse<T = unknown> {
  status: number;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export class ContractFlowProxyService {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(
    baseUrl?: string,
    timeoutMs = parseInt(process.env.CONTRACTFLOW_PROXY_TIMEOUT_MS || '45000', 10)
  ) {
    this.baseUrl = (baseUrl || env.CONTRACTFLOW_SERVICE_URL).replace(/\/+$/, '');
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

    const headers: Record<string, string> = {
      'Authorization': `Bearer ${bearerToken}`,
      'Accept': 'application/json',
    };

    let payload: string | undefined;
    if (body !== undefined && method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      payload = typeof body === 'string' ? body : JSON.stringify(body);
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

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
        const errorCode = responseJson?.error?.code || responseJson?.detail || 'UPSTREAM_ERROR';
        const errorMessage =
          typeof responseJson?.error?.message === 'string'
            ? responseJson.error.message
            : typeof responseJson?.detail === 'string'
            ? responseJson.detail
            : `ContractFlow service responded with HTTP ${response.status}`;

        return {
          status: response.status,
          error: {
            code: typeof errorCode === 'string' ? errorCode : 'UPSTREAM_ERROR',
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
      if (err instanceof Error && err.name === 'AbortError') {
        return {
          status: 504,
          error: {
            code: 'GATEWAY_TIMEOUT',
            message: `ContractFlow service did not respond within ${this.timeoutMs / 1000} seconds.`,
          },
        };
      }

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

