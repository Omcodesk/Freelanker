import { Request, Response } from 'express';
import {
  listMilestones,
  createMilestone,
  updateMilestone,
  deleteMilestone,
} from '../services/milestone.service.js';
import { ProjectError } from '../services/project.service.js';
import { errorResponse, successResponse } from '../types/index.js';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function handleMilestoneError(res: Response, err: unknown, fallback: string): void {
  if (err instanceof ProjectError) {
    res.status(err.statusCode).json(errorResponse(err.message));
    return;
  }
  const message = err instanceof Error ? err.message : fallback;
  res.status(500).json(errorResponse(message));
}

export async function handleListMilestones(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }
  if (!UUID_REGEX.test(req.params.id)) {
    res.status(400).json(errorResponse('Invalid project ID format.'));
    return;
  }
  try {
    const result = await listMilestones(req.params.id, user.id);
    res.status(200).json(successResponse(result));
  } catch (err: unknown) {
    handleMilestoneError(res, err, 'Failed to list milestones');
  }
}

export async function handleCreateMilestone(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }
  if (!UUID_REGEX.test(req.params.id)) {
    res.status(400).json(errorResponse('Invalid project ID format.'));
    return;
  }
  try {
    const result = await createMilestone(req.params.id, user.id, req.body);
    res.status(201).json(successResponse(result));
  } catch (err: unknown) {
    handleMilestoneError(res, err, 'Failed to create milestone');
  }
}

export async function handleUpdateMilestone(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }
  if (!UUID_REGEX.test(req.params.id) || !UUID_REGEX.test(req.params.milestoneId)) {
    res.status(400).json(errorResponse('Invalid project or milestone ID format.'));
    return;
  }
  try {
    const result = await updateMilestone(req.params.id, req.params.milestoneId, user.id, req.body);
    res.status(200).json(successResponse(result));
  } catch (err: unknown) {
    handleMilestoneError(res, err, 'Failed to update milestone');
  }
}

export async function handleDeleteMilestone(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }
  if (!UUID_REGEX.test(req.params.id) || !UUID_REGEX.test(req.params.milestoneId)) {
    res.status(400).json(errorResponse('Invalid project or milestone ID format.'));
    return;
  }
  try {
    const result = await deleteMilestone(req.params.id, req.params.milestoneId, user.id);
    res.status(200).json(successResponse(result));
  } catch (err: unknown) {
    handleMilestoneError(res, err, 'Failed to delete milestone');
  }
}

