import { Request, Response } from 'express';
import {
  createProject,
  listUserProjects,
  getProjectById,
  updateProject,
  cancelProject,
  ProjectError,
} from '../services/project.service.js';
import { successResponse, errorResponse } from '../types/index.js';

export async function handleCreateProject(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  try {
    const result = await createProject(user.id, req.body);
    res.status(201).json(successResponse(result));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to create project');
  }
}

export async function handleListProjects(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  try {
    const status = typeof req.query.status === 'string' ? req.query.status : undefined;
    const role = typeof req.query.role === 'string' ? req.query.role : undefined;
    const projects = await listUserProjects(user.id, { status, role });
    res.status(200).json(successResponse({ projects }));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to list projects');
  }
}

export async function handleGetProjectById(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  const { id } = req.params;
  if (!id) {
    res.status(400).json(errorResponse('Project ID is required.'));
    return;
  }

  try {
    const detail = await getProjectById(id, user.id);
    res.status(200).json(successResponse(detail));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to retrieve project details');
  }
}

export async function handleUpdateProject(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  const { id } = req.params;
  if (!id) {
    res.status(400).json(errorResponse('Project ID is required.'));
    return;
  }

  try {
    const updated = await updateProject(id, user.id, req.body);
    res.status(200).json(successResponse({ project: updated }));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to update project');
  }
}

export async function handleCancelProject(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  const { id } = req.params;
  if (!id) {
    res.status(400).json(errorResponse('Project ID is required.'));
    return;
  }

  try {
    const cancelled = await cancelProject(id, user.id);
    res.status(200).json(successResponse({ project: cancelled }));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to cancel project');
  }
}

function handleError(res: Response, err: unknown, fallbackMessage: string): void {
  if (err instanceof ProjectError) {
    res.status(err.statusCode).json(errorResponse(err.message));
    return;
  }
  const message = err instanceof Error ? err.message : fallbackMessage;
  res.status(500).json(errorResponse(message));
}
