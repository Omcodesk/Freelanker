/**
 * ContractFlow Express Gateway Routes.
 *
 * Exposes authenticated endpoints that authorize project access before
 * proxying requests to the isolated Python FastAPI microservice.
 *
 * Invariants:
 * - All routes require verified authentication (requireAuth).
 * - Body size limit: 128 KB.
 * - Rate limiting: 60 requests/min per IP.
 * - Amendment routes resolve owning project before verifying membership.
 * - Zero automatic retries on state-changing requests.
 */

import express, { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import { publicRateLimiter } from '../middleware/rateLimiter.js';
import {
  handleContractFlowHealth,
  handleGenerateContract,
  handleDraftAgreement,
  handleAssessScope,
  handleGenerateAmendment,
  handleRegisterAmendment,
  handleSubmitDecision,
  handleGetAmendmentStatus,
  handleGetAmendmentHistory,
} from '../controllers/contractflow.controller.js';

const router = Router();

// Middleware: Authenticated only, 128KB payload limit, rate-limited
router.use(requireAuth);
router.use(express.json({ limit: '128kb' }));
router.use(publicRateLimiter({ maxRequests: 60, windowMs: 60 * 1000 }));

// ─── Service Health (Authenticated) ─────────────────────────────────────────
router.get('/health', handleContractFlowHealth);

// ─── Project Scoped Routes ──────────────────────────────────────────────────
router.post(['/projects/:id/contracts/generate', '/:id/contracts/generate'], handleGenerateContract);
router.post(['/projects/:id/agreements/draft', '/:id/agreements/draft'], handleDraftAgreement);
router.post(['/projects/:id/scope/assess', '/:id/scope/assess'], handleAssessScope);
router.post(['/projects/:id/amendments/generate', '/:id/amendments/generate'], handleGenerateAmendment);

// ─── Amendment Scoped Routes (Resolved to Owning Project) ────────────────────
router.post('/amendments/:amendmentId/register', handleRegisterAmendment);
router.post('/amendments/:amendmentId/decisions', handleSubmitDecision);
router.get('/amendments/:amendmentId/status', handleGetAmendmentStatus);
router.get('/amendments/:amendmentId/history', handleGetAmendmentHistory);

export default router;
