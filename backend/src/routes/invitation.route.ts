import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import { publicRateLimiter } from '../middleware/rateLimiter.js';
import {
  handleResolveInvitationByToken,
  handleListInvitations,
  handleAcceptInvitation,
  handleRejectInvitation,
} from '../controllers/invitation.controller.js';

const router = Router();

// ─── Public Routes (Rate-limited, unauthenticated preview) ───────────────────
// GET /api/invitations/token/:token
router.get(
  '/token/:token',
  publicRateLimiter({ maxRequests: 30, windowMs: 60 * 1000 }),
  handleResolveInvitationByToken
);

// ─── Authenticated Routes ────────────────────────────────────────────────────
router.use(requireAuth);

router.get('/', handleListInvitations);
router.post('/:id/accept', handleAcceptInvitation);
router.post('/:id/reject', handleRejectInvitation);

export default router;
