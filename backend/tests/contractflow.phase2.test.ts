/**
 * Phase 2 Express Backend Regression & Proxy Integration Tests.
 *
 * Verifies:
 * 1. requireAuth / optionalAuth reject caller-writable user_metadata.email_verified.
 * 2. ContractFlowProxyService translates known FastAPI error codes safely while preserving code.
 * 3. ContractFlowProxyService handles upstream unavailability (503) and timeouts (504).
 * 4. Real HTTP Express-to-FastAPI communication (Bearer forwarding, /health, error propagation).
 */

import http from 'node:http';
import crypto from 'node:crypto';
import express from 'express';
import { requireAuth, optionalAuth } from '../src/middleware/auth.js';
import { supabaseAuth, supabaseAdmin } from '../src/lib/supabase.js';
import { normalizeServiceUrl } from '../src/config/env.js';
import {
  ContractFlowProxyService,
  translateContractFlowErrorMessage,
} from '../src/services/contractflowProxy.service.js';
import contractflowRouter from '../src/routes/contractflow.route.js';

let passed = 0;
let failed = 0;

async function test(name: string, fn: () => Promise<void>) {
  try {
    await fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err: any) {
    console.error(`  ✗ ${name}: ${err?.message || err}`);
    failed++;
  }
}

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

function createHs256Jwt(payload: Record<string, unknown>, secret: string): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig = crypto.createHmac('sha256', secret).update(`${header}.${body}`).digest('base64url');
  return `${header}.${body}.${sig}`;
}

async function run() {
  console.log('\n=== RUNNING PHASE 2 EXPRESS AUTH & PROXY TESTS ===\n');

  // 1. Auth email_confirmed_at regression tests
  await test('requireAuth ignores caller-writable user_metadata.email_verified when email_confirmed_at is null', async () => {
    const origGetUser = supabaseAuth.auth.getUser.bind(supabaseAuth.auth);
    (supabaseAuth.auth as any).getUser = async () => ({
      data: {
        user: {
          id: '11111111-1111-1111-1111-111111111111',
          email: 'attacker@example.com',
          email_confirmed_at: null,
          created_at: new Date().toISOString(),
          user_metadata: { email_verified: true },
        },
      },
      error: null,
    });
    try {
      const req: any = { headers: { authorization: 'Bearer test-jwt' } };
      const res: any = {
        statusCode: 200,
        status(c: number) { this.statusCode = c; return this; },
        json(d: any) { this.body = d; return this; },
      };
      let nextCalled = false;
      await requireAuth(req, res, () => { nextCalled = true; });
      assert(nextCalled, 'requireAuth should attach req.user and call next()');
      assert(req.user.isEmailVerified === false, 'isEmailVerified must be false when email_confirmed_at is null');
    } finally {
      (supabaseAuth.auth as any).getUser = origGetUser;
    }
  });

  await test('optionalAuth sets isEmailVerified=true only when email_confirmed_at is populated', async () => {
    const origGetUser = supabaseAuth.auth.getUser.bind(supabaseAuth.auth);
    (supabaseAuth.auth as any).getUser = async () => ({
      data: {
        user: {
          id: '22222222-2222-2222-2222-222222222222',
          email: 'verified@example.com',
          email_confirmed_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          user_metadata: { email_verified: false },
        },
      },
      error: null,
    });
    try {
      const req: any = { headers: { authorization: 'Bearer verified-jwt' } };
      await optionalAuth(req, {} as any, () => {});
      assert(req.user.isEmailVerified === true, 'isEmailVerified must be true when email_confirmed_at is set');
    } finally {
      (supabaseAuth.auth as any).getUser = origGetUser;
    }
  });

  // 2. Error translation helper & service URL normalization
  await test('normalizeServiceUrl handles Render host:port, trailing slashes, and https URLs', async () => {
    assert(normalizeServiceUrl('freelanker-contractflow:10000') === 'http://freelanker-contractflow:10000', 'Expected http:// prefix on bare host:port');
    assert(normalizeServiceUrl('https://contractflow.onrender.com/') === 'https://contractflow.onrender.com', 'Expected trailing slash stripped');
    assert(normalizeServiceUrl('') === 'http://127.0.0.1:8000', 'Expected default loopback URL');
  });

  await test('translateContractFlowErrorMessage maps known FastAPI error codes safely', async () => {
    const msg = translateContractFlowErrorMessage('STALE_SOURCE', undefined, 409);
    assert(msg.toLowerCase().includes('source version') || msg.toLowerCase().includes('changed'), `Unexpected message: ${msg}`);
    const unavail = translateContractFlowErrorMessage('UNAVAILABLE', undefined, 503);
    assert(unavail.toLowerCase().includes('unavailable'), `Unexpected unavailable message: ${unavail}`);
  });

  // 3. Proxy unavailable & timeout handling
  await test('ContractFlowProxyService returns 503 SERVICE_UNAVAILABLE when upstream is unreachable', async () => {
    const proxy = new ContractFlowProxyService('http://127.0.0.1:59997', 1000);
    const resp = await proxy.forward('POST', '/contracts/generate', 'tok', { project_id: 'p1', expected_source_version: 1 });
    assert(resp.status === 503, `Expected 503, got ${resp.status}`);
    assert(resp.error?.code === 'SERVICE_UNAVAILABLE', `Expected SERVICE_UNAVAILABLE, got ${resp.error?.code}`);
  });

  await test('ContractFlowProxyService returns 504 GATEWAY_TIMEOUT on upstream timeout', async () => {
    const slowServer = http.createServer((_req, res) => {
      setTimeout(() => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end('{}');
      }, 400);
    });
    await new Promise<void>((resolve) => slowServer.listen(0, '127.0.0.1', resolve));
    const addr = slowServer.address() as { port: number };
    try {
      const proxy = new ContractFlowProxyService(`http://127.0.0.1:${addr.port}`, 60);
      const resp = await proxy.forward('GET', '/amendments/00000000-0000-0000-0000-000000000001/status', 'tok');
      assert(resp.status === 504, `Expected 504, got ${resp.status}`);
      assert(resp.error?.code === 'GATEWAY_TIMEOUT', `Expected GATEWAY_TIMEOUT, got ${resp.error?.code}`);
    } finally {
      slowServer.close();
    }
  });

  // 4. Real Express <-> Upstream HTTP server token forwarding + error code/message translation
  await test('Express /api/contractflow forwards Bearer token and preserves translated FastAPI errors', async () => {
    let seenAuth = '';
    let seenPath = '';
    const upstream = http.createServer((req, res) => {
      seenAuth = req.headers.authorization || '';
      seenPath = req.url || '';
      if (req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', service_running: true, database_connected: true, jwt_configured: true, runtime_configured: true, groq_enabled: false }));
        return;
      }
      if (req.url === '/api/v1/contractflow/contracts/generate') {
        res.writeHead(503, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { code: 'UNAVAILABLE' } }));
        return;
      }
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: { code: 'NOT_FOUND' } }));
    });
    await new Promise<void>((resolve) => upstream.listen(0, '127.0.0.1', resolve));
    const upstreamPort = (upstream.address() as { port: number }).port;

    // Temporarily point global proxy instance at mock upstream to test full Express route+controller+proxy pipeline
    const { contractflowProxy } = await import('../src/services/contractflowProxy.service.js');
    const origBaseUrl = (contractflowProxy as any).baseUrl;
    (contractflowProxy as any).baseUrl = `http://127.0.0.1:${upstreamPort}`;

    const origGetUser = supabaseAuth.auth.getUser.bind(supabaseAuth.auth);
    const origFrom = (supabaseAdmin as any).from;
    const projectId = '33333333-3333-3333-3333-333333333333';
    const userId = '44444444-4444-4444-4444-444444444444';
    const jwtToken = createHs256Jwt({ sub: userId, aud: 'authenticated', exp: Math.floor(Date.now() / 1000) + 300 }, 'test-secret');

    (supabaseAuth.auth as any).getUser = async (tok: string) => {
      assert(tok === jwtToken, 'Unexpected token passed to supabaseAuth');
      return {
        data: { user: { id: userId, email: 'member@example.com', email_confirmed_at: new Date().toISOString(), created_at: new Date().toISOString() } },
        error: null,
      };
    };
    (supabaseAdmin as any).from = (table: string) => ({
      select: () => ({
        eq: () => ({
          eq: () => ({
            maybeSingle: async () => (table === 'project_members' ? { data: { role: 'client' }, error: null } : { data: null, error: null }),
          }),
        }),
      }),
    });

    const testApp = express();
    testApp.use('/api/contractflow', contractflowRouter);
    const gwServer = http.createServer(testApp);
    await new Promise<void>((resolve) => gwServer.listen(0, '127.0.0.1', resolve));
    const gwPort = (gwServer.address() as { port: number }).port;

    try {
      // A. Health check through Express
      const hRes = await fetch(`http://127.0.0.1:${gwPort}/api/contractflow/health`, {
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      assert(hRes.status === 200, `Expected 200 on health, got ${hRes.status}`);
      const hJson: any = await hRes.json();
      assert(hJson.success === true && hJson.data?.groq_enabled === false, 'Unexpected health response payload');

      // B. Authenticated POST forwards exact token and translates UNAVAILABLE
      const gRes = await fetch(`http://127.0.0.1:${gwPort}/api/contractflow/projects/${projectId}/contracts/generate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${jwtToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ expected_source_version: 1 }),
      });
      assert(seenPath === '/api/v1/contractflow/contracts/generate', `Unexpected upstream path: ${seenPath}`);
      assert(seenAuth === `Bearer ${jwtToken}`, 'Express did not forward exact Bearer token');
      assert(gRes.status === 503, `Expected 503 when AI disabled, got ${gRes.status}`);
      const gJson: any = await gRes.json();
      assert(gJson.success === false && gJson.code === 'UNAVAILABLE', `Expected UNAVAILABLE code, got ${JSON.stringify(gJson)}`);
      assert(typeof gJson.error === 'string' && gJson.error.includes('unavailable'), `Expected translated message, got ${gJson.error}`);
    } finally {
      (contractflowProxy as any).baseUrl = origBaseUrl;
      (supabaseAuth.auth as any).getUser = origGetUser;
      (supabaseAdmin as any).from = origFrom;
      gwServer.close();
      upstream.close();
    }
  });

  console.log(`\n=== PHASE 2 TEST SUMMARY: Total ${passed + failed} | Passed ${passed} | Failed ${failed} ===\n`);
  if (failed > 0) process.exit(1);
}

run().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
