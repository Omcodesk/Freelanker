import { Request, Response } from 'express';
import {
  createInvitation,
  listUserInvitations,
  acceptInvitation,
  rejectInvitation,
  InvitationError,
} from '../services/invitation.service.js';
import { successResponse, errorResponse } from '../types/index.js';

export async function handleCreateInvitation(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  const { id: projectId } = req.params;
  if (!projectId) {
    res.status(400).json(errorResponse('Project ID is required.'));
    return;
  }

  try {
    const result = await createInvitation(projectId, user.id, user.email, req.body);
    res.status(201).json(successResponse(result));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to create invitation');
  }
}

export async function handleListInvitations(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  try {
    const status = typeof req.query.status === 'string' ? req.query.status : undefined;
    const invitations = await listUserInvitations(
      user.id,
      user.email,
      user.isEmailVerified,
      status
    );
    res.status(200).json(successResponse({ invitations }));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to retrieve invitations');
  }
}

export async function handleAcceptInvitation(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  const { id } = req.params;
  if (!id) {
    res.status(400).json(errorResponse('Invitation ID is required.'));
    return;
  }

  try {
    const result = await acceptInvitation(id, {
      id: user.id,
      email: user.email,
      isEmailVerified: user.isEmailVerified,
    });
    res.status(200).json(successResponse(result));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to accept invitation');
  }
}

export async function handleRejectInvitation(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }

  const { id } = req.params;
  if (!id) {
    res.status(400).json(errorResponse('Invitation ID is required.'));
    return;
  }

  try {
    const result = await rejectInvitation(id, {
      id: user.id,
      email: user.email,
      isEmailVerified: user.isEmailVerified,
    });
    res.status(200).json(successResponse(result));
  } catch (err: unknown) {
    handleError(res, err, 'Failed to reject invitation');
  }
}

function handleError(res: Response, err: unknown, fallbackMessage: string): void {
  if (err instanceof InvitationError) {
    res.status(err.statusCode).json(errorResponse(err.message));
    return;
  }
  const message = err instanceof Error ? err.message : fallbackMessage;
  res.status(500).json(errorResponse(message));
}
