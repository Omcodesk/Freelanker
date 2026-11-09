import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import {
  handleCreateProject,
  handleListProjects,
  handleGetProjectById,
  handleUpdateProject,
  handleCancelProject,
} from '../controllers/project.controller.js';
import { handleCreateInvitation } from '../controllers/invitation.controller.js';

const router = Router();

// All project routes require valid authenticated session
router.use(requireAuth);

router.post('/', handleCreateProject);
router.get('/', handleListProjects);
router.get('/:id', handleGetProjectById);
router.patch('/:id', handleUpdateProject);
router.post('/:id/cancel', handleCancelProject);

// Nested invitation route: POST /api/projects/:id/invitations
router.post('/:id/invitations', handleCreateInvitation);

export default router;
