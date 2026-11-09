import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import {
  handleListInvitations,
  handleAcceptInvitation,
  handleRejectInvitation,
} from '../controllers/invitation.controller.js';

const router = Router();

// All invitation routes require valid authenticated session
router.use(requireAuth);

router.get('/', handleListInvitations);
router.post('/:id/accept', handleAcceptInvitation);
router.post('/:id/reject', handleRejectInvitation);

export default router;
