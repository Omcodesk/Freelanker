import { Request, Response } from 'express';
import {
  listProjectTasks,
  createTask,
  updateTask,
  deleteTask,
} from '../services/task.service.js';
import {
  listProjectDeliverables,
  submitDeliverable,
  reviewDeliverable,
} from '../services/deliverable.service.js';
import {
  listProjectMessages,
  createMessage,
} from '../services/message.service.js';
import { verifyProjectMembership } from './contractflow.controller.js';
import { errorResponse, successResponse } from '../types/index.js';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// ─── TASKS ───────────────────────────────────────────────────────────────────

export async function handleListTasks(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const tasks = await listProjectTasks(projectId);
    res.json(successResponse(tasks));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'TASK_ERROR'));
  }
}

export async function handleCreateTask(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const task = await createTask(projectId, req.user!.id, req.body);
    res.status(201).json(successResponse(task));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'TASK_ERROR'));
  }
}

export async function handleUpdateTask(req: Request, res: Response): Promise<void> {
  const { id: projectId, taskId } = req.params;
  if (!UUID_REGEX.test(projectId) || !UUID_REGEX.test(taskId)) {
    res.status(400).json(errorResponse('Invalid ID format.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const task = await updateTask(projectId, taskId, req.body);
    res.json(successResponse(task));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'TASK_ERROR'));
  }
}

export async function handleDeleteTask(req: Request, res: Response): Promise<void> {
  const { id: projectId, taskId } = req.params;
  if (!UUID_REGEX.test(projectId) || !UUID_REGEX.test(taskId)) {
    res.status(400).json(errorResponse('Invalid ID format.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    await deleteTask(projectId, taskId);
    res.json(successResponse({ success: true }));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'TASK_ERROR'));
  }
}

// ─── DELIVERABLES ────────────────────────────────────────────────────────────

export async function handleListDeliverables(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const deliverables = await listProjectDeliverables(projectId);
    res.json(successResponse(deliverables));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'DELIVERABLE_ERROR'));
  }
}

export async function handleSubmitDeliverable(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const file = req.file
      ? {
          originalname: req.file.originalname,
          buffer: req.file.buffer,
          mimetype: req.file.mimetype,
        }
      : undefined;

    const deliverable = await submitDeliverable(projectId, req.user!.id, {
      title: req.body.title,
      description: req.body.description,
      submissionNote: req.body.submissionNote,
      milestoneId: req.body.milestoneId,
      linkUrl: req.body.linkUrl,
      file,
    });
    res.status(201).json(successResponse(deliverable));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'DELIVERABLE_ERROR'));
  }
}

export async function handleReviewDeliverable(req: Request, res: Response): Promise<void> {
  const { id: projectId, deliverableId } = req.params;
  if (!UUID_REGEX.test(projectId) || !UUID_REGEX.test(deliverableId)) {
    res.status(400).json(errorResponse('Invalid ID format.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const reviewed = await reviewDeliverable(projectId, deliverableId, req.user!.id, {
      status: req.body.status,
      clientFeedback: req.body.clientFeedback,
    });
    res.json(successResponse(reviewed));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'DELIVERABLE_ERROR'));
  }
}

// ─── MESSAGES / COLLABORATION ────────────────────────────────────────────────

export async function handleListMessages(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const messages = await listProjectMessages(projectId);
    res.json(successResponse(messages));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'MESSAGE_ERROR'));
  }
}

export async function handleCreateMessage(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID.', 'INVALID_PARAMETERS'));
    return;
  }
  const isMember = await verifyProjectMembership(req.user!.id, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: Not a project member.', 'FORBIDDEN'));
    return;
  }

  try {
    const message = await createMessage(projectId, req.user!.id, {
      content: req.body.content,
      fileUrls: req.body.fileUrls,
      isAiSummary: req.body.isAiSummary,
    });
    res.status(201).json(successResponse(message));
  } catch (err: any) {
    res.status(err.statusCode || 500).json(errorResponse(err.message, 'MESSAGE_ERROR'));
  }
}
