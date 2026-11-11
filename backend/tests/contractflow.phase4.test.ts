/**
 * Phase 4 Express Backend Tests: Milestones, SourceVersion, Initial Agreements, and ContractFlow Review Access.
 */

import http from 'node:http';
import express from 'express';
import projectRouter from '../src/routes/project.route.js';
import contractflowRouter from '../src/routes/contractflow.route.js';
import { supabaseAuth, supabaseAdmin } from '../src/lib/supabase.js';

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

/**
 * In-memory PostgreSQL-like store backing supabaseAdmin queries for Express service logic verification.
 */
function installMockDb(seed: {
  clientId: string;
  freelancerId: string;
  outsiderId: string;
  projectId: string;
}) {
  const state: any = {
    projects: [
      {
        id: seed.projectId,
        title: 'Phase 4 App',
        description: 'Build portal',
        status: 'awaiting_agreement',
        initiator_id: seed.clientId,
        client_id: seed.clientId,
        freelancer_id: seed.freelancerId,
        currency: 'USD',
        total_budget: 3000,
        payment_arrangement: 'milestone_prepayment',
        review_period_days: 3,
        source_version: 1,
        created_at: '2026-11-01T00:00:00.000Z',
        updated_at: '2026-11-01T00:00:00.000Z',
      },
    ],
    project_members: [
      { id: 'm-c', project_id: seed.projectId, user_id: seed.clientId, role: 'client', joined_at: '2026-11-01T00:00:00.000Z' },
      { id: 'm-f', project_id: seed.projectId, user_id: seed.freelancerId, role: 'freelancer', joined_at: '2026-11-02T00:00:00.000Z' },
    ],
    profiles: [
      { id: seed.clientId, display_name: 'Alice Client' },
      { id: seed.freelancerId, display_name: 'Bob Freelancer' },
    ],
    milestones: [],
    agreements: [],
    agreement_approvals: [],
    activity_logs: [],
    cf_artifacts: [],
    cf_approval_versions: [],
  };

  let seq = 1;
  const origFrom = (supabaseAdmin as any).from;

  (supabaseAdmin as any).from = (table: string) => {
    const ctx: any = {
      filters: [] as Array<(r: any) => boolean>,
      orders: [] as Array<{ col: string; asc: boolean }>,
      op: 'select',
      payload: null,
      singleMode: null as null | 'single' | 'maybeSingle',
    };

    const runQuery = () => {
      const rows = (state[table] || []) as any[];
      if (ctx.op === 'insert') {
        const items = Array.isArray(ctx.payload) ? ctx.payload : [ctx.payload];
        const inserted = items.map((item) => {
          const row = {
            id: item.id || `00000000-0000-4000-8000-${String(seq++).padStart(12, '0')}`,
            created_at: item.created_at || new Date().toISOString(),
            updated_at: item.updated_at || new Date().toISOString(),
            ...item,
          };
          state[table].push(row);
          if (table === 'milestones' || table === 'agreements') {
            const p = state.projects.find((pr: any) => pr.id === row.project_id);
            if (p) p.source_version += 1;
          }
          return row;
        });
        if (ctx.singleMode) return { data: inserted[0] ?? null, error: null };
        return { data: inserted, error: null };
      }

      const matched = rows.filter((r) => ctx.filters.every((fn: any) => fn(r)));

      if (ctx.op === 'update') {
        for (const r of matched) {
          Object.assign(r, ctx.payload);
          if (table === 'milestones' || table === 'agreements') {
            const p = state.projects.find((pr: any) => pr.id === r.project_id);
            if (p) p.source_version += 1;
          }
        }
        if (ctx.singleMode) return { data: matched[0] ?? null, error: null };
        return { data: matched, error: null };
      }

      if (ctx.op === 'delete') {
        for (const r of matched) {
          if (table === 'milestones') {
            const p = state.projects.find((pr: any) => pr.id === r.project_id);
            if (p) p.source_version += 1;
          }
        }
        state[table] = rows.filter((r) => !matched.includes(r));
        return { data: matched, error: null };
      }

      const sorted = [...matched];
      for (const ord of ctx.orders) {
        sorted.sort((a, b) => {
          if (a[ord.col] === b[ord.col]) return 0;
          return (a[ord.col] > b[ord.col] ? 1 : -1) * (ord.asc ? 1 : -1);
        });
      }
      if (ctx.singleMode) return { data: sorted[0] ?? null, error: null };
      return { data: sorted, error: null };
    };

    const builder: any = {
      select() { return builder; },
      insert(p: any) { ctx.op = 'insert'; ctx.payload = p; return builder; },
      update(p: any) { ctx.op = 'update'; ctx.payload = p; return builder; },
      delete() { ctx.op = 'delete'; return builder; },
      eq(col: string, val: any) { ctx.filters.push((r: any) => r[col] === val); return builder; },
      neq(col: string, val: any) { ctx.filters.push((r: any) => r[col] !== val); return builder; },
      in(col: string, vals: any[]) { ctx.filters.push((r: any) => vals.includes(r[col])); return builder; },
      order(col: string, opts?: { ascending?: boolean }) { ctx.orders.push({ col, asc: opts?.ascending !== false }); return builder; },
      limit() { return builder; },
      maybeSingle: async () => { ctx.singleMode = 'maybeSingle'; return runQuery(); },
      single: async () => { ctx.singleMode = 'single'; return runQuery(); },
      then(resolve: any, reject: any) {
        return Promise.resolve(runQuery()).then(resolve, reject);
      },
    };
    return builder;
  };

  return { state, restore: () => { (supabaseAdmin as any).from = origFrom; } };
}

async function run() {
  console.log('\n=== RUNNING PHASE 4 EXPRESS MILESTONE & AGREEMENT TESTS ===\n');

  const clientId = '11111111-1111-4111-8111-111111111111';
  const freelancerId = '22222222-2222-4222-8222-222222222222';
  const outsiderId = '33333333-3333-4333-8333-333333333333';
  const projectId = '44444444-4444-4444-8444-444444444444';

  const tokenToUser: Record<string, string> = {
    'tok-client': clientId,
    'tok-freelancer': freelancerId,
    'tok-outsider': outsiderId,
  };

  const origGetUser = supabaseAuth.auth.getUser.bind(supabaseAuth.auth);
  (supabaseAuth.auth as any).getUser = async (tok: string) => ({
    data: { user: tokenToUser[tok] ? { id: tokenToUser[tok], email: `${tok}@example.com`, email_confirmed_at: new Date().toISOString(), created_at: new Date().toISOString() } : null },
    error: tokenToUser[tok] ? null : { message: 'Invalid token' },
  });

  const db = installMockDb({ clientId, freelancerId, outsiderId, projectId });

  const app = express();
  app.use(express.json());
  app.use('/api/projects', projectRouter);
  app.use('/api/contractflow', contractflowRouter);
  const server = http.createServer(app);
  await new Promise<void>((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${(server.address() as any).port}/api`;

  async function req(method: string, path: string, token: string, body?: any) {
    const res = await fetch(`${base}${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return { status: res.status, json: (await res.json()) as any };
  }

  try {
    // 1. Project exposes sourceVersion & outsider blocked
    await test('Project exposes sourceVersion and blocks unauthorized outsider with 403', async () => {
      const ok = await req('GET', `/projects/${projectId}`, 'tok-client');
      assert(ok.status === 200 && ok.json.data.project.sourceVersion === 1, 'Expected sourceVersion=1');
      const denied = await req('GET', `/projects/${projectId}`, 'tok-outsider');
      assert(denied.status === 403, `Expected 403 for outsider, got ${denied.status}`);
    });

    // 2. Milestone validation & CRUD increments sourceVersion
    let m1Id = '';
    await test('Milestone CRUD validates dates/budget and increments sourceVersion', async () => {
      const missingDate = await req('POST', `/projects/${projectId}/milestones`, 'tok-client', { title: 'Bad', amount: 500 });
      assert(missingDate.status === 400, 'Expected 400 when dueDate missing');

      const overBudget = await req('POST', `/projects/${projectId}/milestones`, 'tok-client', { title: 'Over', amount: 5000, dueDate: '2026-11-20' });
      assert(overBudget.status === 400, 'Expected 400 when milestone exceeds budget');

      const m1 = await req('POST', `/projects/${projectId}/milestones`, 'tok-client', { title: 'M1 Core', description: 'API + UI', amount: 1500, dueDate: '2026-11-20' });
      assert(m1.status === 201 && m1.json.data.sourceVersion === 2, 'Expected M1 created and sourceVersion=2');
      m1Id = m1.json.data.milestone.id;

      const m2 = await req('POST', `/projects/${projectId}/milestones`, 'tok-client', { title: 'M2 Launch', amount: 1500, dueDate: '2026-12-01' });
      assert(m2.status === 201 && m2.json.data.sourceVersion === 3, 'Expected M2 created and sourceVersion=3');

      const upd = await req('PATCH', `/projects/${projectId}/milestones/${m1Id}`, 'tok-client', { title: 'M1 Core Updated' });
      assert(upd.status === 200 && upd.json.data.sourceVersion === 4, 'Expected update to bump sourceVersion=4');
    });

    // 3. Initial agreement: Freelancer cannot author; Client drafts, edits, submits; Freelancer rejects; Client revises v2; Both approve
    await test('Initial agreement requires client drafting, digest match, dual approval, and activates only after both approve', async () => {
      const fAttempt = await req('POST', `/projects/${projectId}/agreements/draft`, 'tok-freelancer', {
        title: 'Freelancer hijack',
        scopeOfWork: 'No',
        paymentArrangement: 'milestone_prepayment',
        totalAmount: 3000,
        currency: 'USD',
        reviewPeriodDays: 3,
      });
      assert(fAttempt.status === 403, `Expected 403 when freelancer tries to edit agreement draft, got ${fAttempt.status}`);

      const draft = await req('POST', `/projects/${projectId}/agreements/draft`, 'tok-client', {
        title: 'Master Agreement v1',
        scopeOfWork: 'Deliver full Freelanker module',
        deliverablesText: 'API + React Workspace',
        paymentArrangement: 'milestone_prepayment',
        totalAmount: 3000,
        currency: 'USD',
        reviewPeriodDays: 3,
        startDate: '2026-11-01',
        endDate: '2026-12-01',
      });
      assert(draft.status === 200 && draft.json.data.currentAgreement.status === 'draft', 'Expected draft status');
      const ag1 = draft.json.data.currentAgreement;
      assert(typeof ag1.contentDigest === 'string' && ag1.contentDigest.length === 64, 'Expected 64-char digest');

      const sub1 = await req('POST', `/projects/${projectId}/agreements/${ag1.id}/submit`, 'tok-client', {
        expectedVersion: ag1.versionNumber,
        expectedDigest: ag1.contentDigest,
      });
      assert(sub1.status === 200 && sub1.json.data.currentAgreement.status === 'sent_for_review', 'Expected sent_for_review');
      const frozen1 = sub1.json.data.currentAgreement;

      // Stale digest rejected with 409
      const stale = await req('POST', `/projects/${projectId}/agreements/${frozen1.id}/decide`, 'tok-freelancer', {
        decision: 'APPROVE',
        expectedVersion: frozen1.versionNumber,
        expectedDigest: '0'.repeat(64),
      });
      assert(stale.status === 409, `Expected 409 on stale digest, got ${stale.status}`);

      // Freelancer requests changes
      const rej = await req('POST', `/projects/${projectId}/agreements/${frozen1.id}/decide`, 'tok-freelancer', {
        decision: 'REJECT',
        expectedVersion: frozen1.versionNumber,
        expectedDigest: frozen1.contentDigest,
        notes: 'Clarify acceptance criteria',
      });
      assert(rej.status === 200 && rej.json.data.currentAgreement.status === 'changes_requested', 'Expected changes_requested');

      // Client edits draft and resubmits; if sent_for_review was edited later, version increments
      const edited = await req('POST', `/projects/${projectId}/agreements/draft`, 'tok-client', {
        title: 'Master Agreement v1 Updated',
        scopeOfWork: 'Deliver full Freelanker module with tests',
        acceptanceCriteria: 'All tests passing',
        paymentArrangement: 'milestone_prepayment',
        totalAmount: 3000,
        currency: 'USD',
        reviewPeriodDays: 5,
        startDate: '2026-11-01',
        endDate: '2026-12-01',
      });
      const agEdited = edited.json.data.currentAgreement;
      const sub2 = await req('POST', `/projects/${projectId}/agreements/${agEdited.id}/submit`, 'tok-client', {
        expectedVersion: agEdited.versionNumber,
        expectedDigest: agEdited.contentDigest,
      });
      const frozen2 = sub2.json.data.currentAgreement;

      // Edit while sent_for_review creates new version v2 and supersedes v1
      const rev2 = await req('POST', `/projects/${projectId}/agreements/draft`, 'tok-client', {
        title: 'Master Agreement v2',
        scopeOfWork: 'Deliver full Freelanker module with acceptance tests',
        acceptanceCriteria: 'All tests passing + documented',
        paymentArrangement: 'milestone_prepayment',
        totalAmount: 3000,
        currency: 'USD',
        reviewPeriodDays: 5,
        startDate: '2026-11-01',
        endDate: '2026-12-01',
      });
      assert(rev2.json.data.currentAgreement.versionNumber === 2, 'Expected editing sent_for_review to bump versionNumber to 2');
      const v2 = rev2.json.data.currentAgreement;

      const subV2 = await req('POST', `/projects/${projectId}/agreements/${v2.id}/submit`, 'tok-client', {
        expectedVersion: v2.versionNumber,
        expectedDigest: v2.contentDigest,
      });
      const frozenV2 = subV2.json.data.currentAgreement;

      // Freelancer approves v2 (not yet active!)
      const fApp = await req('POST', `/projects/${projectId}/agreements/${frozenV2.id}/decide`, 'tok-freelancer', {
        decision: 'APPROVE',
        expectedVersion: frozenV2.versionNumber,
        expectedDigest: frozenV2.contentDigest,
      });
      assert(fApp.status === 200 && fApp.json.data.currentAgreement.status === 'sent_for_review', 'Single party approval must NOT activate agreement');

      // Duplicate freelancer approval rejected 409
      const dupApp = await req('POST', `/projects/${projectId}/agreements/${frozenV2.id}/decide`, 'tok-freelancer', {
        decision: 'APPROVE',
        expectedVersion: frozenV2.versionNumber,
        expectedDigest: frozenV2.contentDigest,
      });
      assert(dupApp.status === 409, `Expected 409 on duplicate decision, got ${dupApp.status}`);

      // Client approves v2 -> active!
      const cApp = await req('POST', `/projects/${projectId}/agreements/${frozenV2.id}/decide`, 'tok-client', {
        decision: 'APPROVE',
        expectedVersion: frozenV2.versionNumber,
        expectedDigest: frozenV2.contentDigest,
      });
      assert(cApp.status === 200 && cApp.json.data.currentAgreement.status === 'active', 'Expected active after both approve');
      assert(Boolean(cApp.json.data.currentAgreement.activatedAt), 'Expected activatedAt set');
      assert(db.state.projects[0].status === 'active', 'Expected project status transitioned to active');

      // Subsequent draft mutation rejected 409
      const locked = await req('POST', `/projects/${projectId}/agreements/draft`, 'tok-client', {
        title: 'Illegal edit',
        scopeOfWork: 'Overwrite',
        paymentArrangement: 'milestone_prepayment',
        totalAmount: 3000,
        currency: 'USD',
        reviewPeriodDays: 3,
      });
      assert(locked.status === 400 || locked.status === 409, `Expected locked status 400/409, got ${locked.status}`);
    });

    // 4. Cross-project / outsider blocked on overview & reviews
    await test('ContractFlow overview and assessment review reject outsider with 403', async () => {
      const ov = await req('GET', `/contractflow/projects/${projectId}/overview`, 'tok-outsider');
      assert(ov.status === 403 && ov.json.code === 'FORBIDDEN', `Expected 403 FORBIDDEN, got ${ov.status}`);
      const ar = await req('POST', `/contractflow/projects/${projectId}/assessments/99999999-9999-4999-8999-999999999999/reviews`, 'tok-outsider', {
        expected_version: 1,
        expected_digest: 'a'.repeat(64),
        confirm_human_review: true,
      });
      assert(ar.status === 403 && ar.json.code === 'FORBIDDEN', `Expected 403 FORBIDDEN, got ${ar.status}`);
    });
  } finally {
    (supabaseAuth.auth as any).getUser = origGetUser;
    db.restore();
    server.close();
  }

  console.log(`\n=== PHASE 4 EXPRESS TEST SUMMARY: Total ${passed + failed} | Passed ${passed} | Failed ${failed} ===\n`);
  if (failed > 0) process.exit(1);
}

run().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});

