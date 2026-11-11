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
import {
  handleListMilestones,
  handleCreateMilestone,
  handleUpdateMilestone,
  handleDeleteMilestone,
} from '../controllers/milestone.controller.js';
import {
  handleGetCurrentAgreement,
  handleSaveAgreementDraft,
  handleSubmitAgreementForReview,
  handleDecideAgreement,
} from '../controllers/agreement.controller.js';

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

// Project-scoped milestones CRUD
router.get('/:id/milestones', handleListMilestones);
router.post('/:id/milestones', handleCreateMilestone);
router.patch('/:id/milestones/:milestoneId', handleUpdateMilestone);
router.delete('/:id/milestones/:milestoneId', handleDeleteMilestone);

// Project-scoped initial agreement lifecycle (Core public.agreements + agreement_approvals)
router.get('/:id/agreements/current', handleGetCurrentAgreement);
router.post('/:id/agreements/draft', handleSaveAgreementDraft);
router.post('/:id/agreements/:agreementId/submit', handleSubmitAgreementForReview);
router.post('/:id/agreements/:agreementId/decide', handleDecideAgreement);

export default router;
