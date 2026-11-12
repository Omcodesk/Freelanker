import assert from 'node:assert/strict';
import test from 'node:test';
import { parseAllowedOrigins } from '../src/config/env.js';

test('parseAllowedOrigins includes primary FRONTEND_URL and localhost development origins', () => {
  const origins = parseAllowedOrigins('https://freelanker-web.onrender.com');

  assert.ok(origins.includes('https://freelanker-web.onrender.com'));
  assert.ok(origins.includes('http://localhost:5173'));
  assert.ok(origins.includes('http://127.0.0.1:5173'));
});

test('parseAllowedOrigins normalizes trailing slashes', () => {
  const origins = parseAllowedOrigins('https://freelanker-web.onrender.com/');

  assert.ok(origins.includes('https://freelanker-web.onrender.com'));
  assert.equal(origins.some((o) => o.endsWith('/') && o !== '/'), false);
});

test('parseAllowedOrigins parses optional ADDITIONAL_ALLOWED_ORIGINS correctly', () => {
  const origins = parseAllowedOrigins(
    'https://freelanker-web.onrender.com',
    'https://freelanker.io, https://staging.freelanker.io/'
  );

  assert.ok(origins.includes('https://freelanker.io'));
  assert.ok(origins.includes('https://staging.freelanker.io'));
  assert.ok(origins.includes('http://localhost:5173'));
});

test('invitation links format correctly based on FRONTEND_URL', () => {
  const mockToken = 'mock-invitation-token-12345';
  const prodFrontend = 'https://freelanker-web.onrender.com';
  const localFrontend = 'http://localhost:5173';

  const prodLink = `${prodFrontend}/invitations/${mockToken}`;
  const localLink = `${localFrontend}/invitations/${mockToken}`;

  assert.equal(prodLink, 'https://freelanker-web.onrender.com/invitations/mock-invitation-token-12345');
  assert.equal(localLink, 'http://localhost:5173/invitations/mock-invitation-token-12345');
});

