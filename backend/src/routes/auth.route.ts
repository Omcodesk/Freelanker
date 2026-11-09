import { Router } from 'express';
import { getMe } from '../controllers/auth.controller.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();

// GET /api/auth/me — returns current authenticated user and profile
router.get('/me', requireAuth, getMe);

export default router;
