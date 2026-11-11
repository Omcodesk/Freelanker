import { Request, Response } from 'express';
import {
  getProjectAgreements,
  saveAgreementDraft,
  submitAgreementForReview,
  decideAgreement,
} from '../services/agreement.service.js';
import { ProjectError } from '../services/project.service.js';
import { errorResponse, successResponse } from '../types/index.js';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function handleAgreementError(res: Response, err: unknown, fallback: string): void {
  if (err instanceof ProjectError) {
    res.status(err.statusCode).json(errorResponse(err.message));
    return;
  }
  const message = err instanceof Error ? err.message : fallback;
  res.status(500).json(errorResponse(message));
}

export async function handleGetCurrentAgreement(req: Request, res: Response): Promise<void> {
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
    const bundle = await getProjectAgreements(req.params.id, user.id);
    res.status(200).json(successResponse(bundle));
  } catch (err: unknown) {
    handleAgreementError(res, err, 'Failed to load agreement');
  }
}

export async function handleSaveAgreementDraft(req: Request, res: Response): Promise<void> {
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
    const bundle = await saveAgreementDraft(req.params.id, user.id, req.body);
    res.status(200).json(successResponse(bundle));
  } catch (err: unknown) {
    handleAgreementError(res, err, 'Failed to save agreement draft');
  }
}

export async function handleSubmitAgreementForReview(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }
  if (!UUID_REGEX.test(req.params.id) || !UUID_REGEX.test(req.params.agreementId)) {
    res.status(400).json(errorResponse('Invalid project or agreement ID format.'));
    return;
  }
  const { expectedVersion, expectedDigest } = req.body ?? {};
  if (!Number.isInteger(expectedVersion) || expectedVersion < 1 || typeof expectedDigest !== 'string' || !/^[0-9a-f]{64}$/i.test(expectedDigest)) {
    res.status(422).json(errorResponse('Valid expectedVersion and 64-character hex expectedDigest are required.'));
    return;
  }
  try {
    const bundle = await submitAgreementForReview(req.params.id, req.params.agreementId, user.id, expectedVersion, expectedDigest);
    res.status(200).json(successResponse(bundle));
  } catch (err: unknown) {
    handleAgreementError(res, err, 'Failed to submit agreement for review');
  }
}

export async function handleDecideAgreement(req: Request, res: Response): Promise<void> {
  const user = req.user;
  if (!user) {
    res.status(401).json(errorResponse('Unauthorized'));
    return;
  }
  if (!UUID_REGEX.test(req.params.id) || !UUID_REGEX.test(req.params.agreementId)) {
    res.status(400).json(errorResponse('Invalid project or agreement ID format.'));
    return;
  }
  try {
    const bundle = await decideAgreement(req.params.id, req.params.agreementId, user.id, req.body);
    res.status(200).json(successResponse(bundle));
  } catch (err: unknown) {
    handleAgreementError(res, err, 'Failed to record agreement decision');
  }
}

