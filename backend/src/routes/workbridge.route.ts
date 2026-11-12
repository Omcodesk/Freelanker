import { Router } from 'express';
import multer from 'multer';
import { requireAuth } from '../middleware/auth.js';
import {
  handleListTasks,
  handleCreateTask,
  handleUpdateTask,
  handleDeleteTask,
  handleListDeliverables,
  handleSubmitDeliverable,
  handleReviewDeliverable,
  handleListMessages,
  handleCreateMessage,
} from '../controllers/workbridge.controller.js';

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 52428800 }, // 50MB
});

const router = Router();

router.use(requireAuth);

// ─── Tasks ───────────────────────────────────────────────────────────────────
router.get('/projects/:id/tasks', handleListTasks);
router.post('/projects/:id/tasks', handleCreateTask);
router.patch('/projects/:id/tasks/:taskId', handleUpdateTask);
router.delete('/projects/:id/tasks/:taskId', handleDeleteTask);

// ─── Deliverables ────────────────────────────────────────────────────────────
router.get('/projects/:id/deliverables', handleListDeliverables);
router.post('/projects/:id/deliverables', upload.single('file'), handleSubmitDeliverable);
router.patch('/projects/:id/deliverables/:deliverableId/review', handleReviewDeliverable);

// ─── Messages & Collaboration ────────────────────────────────────────────────
router.get('/projects/:id/messages', handleListMessages);
router.post('/projects/:id/messages', handleCreateMessage);

export default router;
