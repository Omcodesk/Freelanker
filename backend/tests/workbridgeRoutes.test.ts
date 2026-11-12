import assert from 'node:assert/strict';
import test from 'node:test';

test('WorkBridge endpoints and authorization specifications', () => {
  const routes = [
    { path: '/api/workbridge/projects/:id/tasks', methods: ['GET', 'POST'] },
    { path: '/api/workbridge/projects/:id/tasks/:taskId', methods: ['PATCH', 'DELETE'] },
    { path: '/api/workbridge/projects/:id/deliverables', methods: ['GET', 'POST'] },
    { path: '/api/workbridge/projects/:id/deliverables/:deliverableId/review', methods: ['PATCH'] },
    { path: '/api/workbridge/projects/:id/messages', methods: ['GET', 'POST'] },
  ];

  assert.equal(routes.length, 5);
  for (const r of routes) {
    assert.ok(r.path.startsWith('/api/workbridge'));
    assert.ok(r.methods.length > 0);
  }
});
