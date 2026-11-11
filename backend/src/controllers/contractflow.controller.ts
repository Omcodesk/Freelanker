/**
 * ContractFlow Controller.
 *
 * Implements authenticated Express gateway handlers:
 * - Validates project and amendment UUIDs.
 * - Resolves amendment owning project before checking authorization (prevents cross-project access).
 * - Enforces verified project membership.
 * - Proxies authenticated requests to FastAPI with original Bearer token.
 * - Standardizes API responses and upstream error envelopes.
 */

import { Request, Response } from 'express';
import { supabaseAdmin } from '../lib/supabase.js';
import { contractflowProxy } from '../services/contractflowProxy.service.js';
import { errorResponse, successResponse } from '../types/index.js';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DIGEST_REGEX = /^[0-9a-f]{64}$/i;

function extractBearerToken(req: Request): string | null {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  return authHeader.substring(7).trim();
}

/**
 * Check if the given user is an active member of the specified project.
 */
async function verifyProjectMembership(userId: string, projectId: string): Promise<boolean> {
  const { data, error } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (error || !data) {
    return false;
  }
  return true;
}

export interface OwnershipResolution {
  projectId: string | null;
  error?: boolean;
}

/**
 * Resolve the owning project ID for a given amendment UUID.
 *
 * Queries cf_artifacts -> project_id,
 * or cf_approval_versions -> agreements -> project_id.
 *
 * Fails closed: if an unexpected DB error or connectivity error occurs,
 * returns { projectId: null, error: true }.
 */
export async function resolveAmendmentOwningProject(amendmentId: string): Promise<OwnershipResolution> {
  // 1. Try resolving via cf_artifacts
  try {
    const { data: artData, error: artError } = await supabaseAdmin
      .from('cf_artifacts')
      .select('project_id')
      .eq('artifact_id', amendmentId)
      .limit(1)
      .maybeSingle();

    if (artError) {
      // Missing table in unmigrated environment (Postgres 42P01 or PostgREST schema cache)
      const isMissingTable =
        artError.code === '42P01' ||
        artError.code === 'PGRST204' ||
        artError.code === 'PGRST205' ||
        (artError.message && (
          artError.message.includes('schema cache') ||
          artError.message.includes('does not exist') ||
          artError.message.includes('not found')
        ));
      if (!isMissingTable) {
        return { projectId: null, error: true };
      }
    } else if (artData?.project_id) {
      return { projectId: artData.project_id };
    }
  } catch {
    return { projectId: null, error: true };
  }

  // 2. Try resolving via cf_approval_versions -> agreements
  try {
    const { data: verData, error: verError } = await supabaseAdmin
      .from('cf_approval_versions')
      .select('original_agreement_id')
      .eq('amendment_id', amendmentId)
      .limit(1)
      .maybeSingle();

    if (verError) {
      const isMissingTable =
        verError.code === '42P01' ||
        verError.code === 'PGRST204' ||
        verError.code === 'PGRST205' ||
        (verError.message && (
          verError.message.includes('schema cache') ||
          verError.message.includes('does not exist') ||
          verError.message.includes('not found')
        ));
      if (!isMissingTable) {
        return { projectId: null, error: true };
      }
    } else if (verData?.original_agreement_id) {
      const { data: agData, error: agError } = await supabaseAdmin
        .from('agreements')
        .select('project_id')
        .eq('id', verData.original_agreement_id)
        .maybeSingle();

      if (agError) {
        return { projectId: null, error: true };
      }
      if (agData?.project_id) {
        return { projectId: agData.project_id };
      }
    }
  } catch {
    return { projectId: null, error: true };
  }

  return { projectId: null };
}

// ─── Project Scoped Handlers ────────────────────────────────────────────────

export async function handleGenerateContract(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.', 'FORBIDDEN'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('POST', '/contracts/generate', token, {
    project_id: projectId,
    expected_source_version: req.body?.expected_source_version ?? 1,
  });

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Contract generation failed.', result.error?.code));
  }
}

export async function handleDraftAgreement(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.', 'FORBIDDEN'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('POST', '/agreements/draft', token, {
    project_id: projectId,
    expected_source_version: req.body?.expected_source_version ?? 1,
  });

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Agreement draft failed.', result.error?.code));
  }
}

export async function handleAssessScope(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.', 'FORBIDDEN'));
    return;
  }

  const clientRequest = req.body?.client_request;
  if (!clientRequest || typeof clientRequest !== 'string' || !clientRequest.trim()) {
    res.status(422).json(errorResponse('client_request text is required for scope assessment.', 'VALIDATION_ERROR'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('POST', '/scope/assess', token, {
    project_id: projectId,
    expected_source_version: req.body?.expected_source_version ?? 1,
    client_request: clientRequest.trim(),
    supporting_context: req.body?.supporting_context ?? [],
  });

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Scope assessment failed.', result.error?.code));
  }
}

export async function handleGenerateAmendment(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.', 'FORBIDDEN'));
    return;
  }

  const assessmentId = req.body?.assessment_id;
  const reviewReference = req.body?.review_reference;
  if (!assessmentId || !UUID_REGEX.test(assessmentId) || !reviewReference) {
    res.status(422).json(errorResponse('Valid assessment_id (UUID) and review_reference are required.', 'VALIDATION_ERROR'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('POST', '/amendments/generate', token, {
    project_id: projectId,
    expected_source_version: req.body?.expected_source_version ?? 1,
    assessment_id: assessmentId,
    review_reference: reviewReference,
  });

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Amendment generation failed.', result.error?.code));
  }
}

// ─── Amendment Scoped Handlers (Failing Closed on Unresolved Ownership) ──────

export async function handleRegisterAmendment(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  // Resolve owning project first to prevent cross-project access (fail-closed)
  const ownership = await resolveAmendmentOwningProject(amendmentId);
  if (ownership.error) {
    res.status(503).json(errorResponse('Database service unavailable to resolve amendment ownership.', 'SERVICE_UNAVAILABLE'));
    return;
  }
  if (!ownership.projectId) {
    res.status(404).json(errorResponse('Amendment not found.', 'NOT_FOUND'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, ownership.projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.', 'FORBIDDEN'));
    return;
  }

  const { expected_version, expected_digest } = req.body ?? {};
  if (!expected_version || typeof expected_version !== 'number' || !Number.isInteger(expected_version) || expected_version < 1) {
    res.status(422).json(errorResponse('expected_version must be a positive integer (>= 1).', 'VALIDATION_ERROR'));
    return;
  }
  if (!expected_digest || typeof expected_digest !== 'string' || !DIGEST_REGEX.test(expected_digest)) {
    res.status(422).json(errorResponse('expected_digest must be a 64-character lowercase hex string.', 'VALIDATION_ERROR'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('POST', `/amendments/${amendmentId}/register`, token, req.body);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Amendment registration failed.', result.error?.code));
  }
}

export async function handleSubmitDecision(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  // Resolve owning project first to prevent cross-project access (fail-closed)
  const ownership = await resolveAmendmentOwningProject(amendmentId);
  if (ownership.error) {
    res.status(503).json(errorResponse('Database service unavailable to resolve amendment ownership.', 'SERVICE_UNAVAILABLE'));
    return;
  }
  if (!ownership.projectId) {
    res.status(404).json(errorResponse('Amendment not found.', 'NOT_FOUND'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, ownership.projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.', 'FORBIDDEN'));
    return;
  }

  // Strict decision body validation
  const { decision, idempotency_key, expected_version, expected_digest, rejection_reason } = req.body ?? {};

  if (!expected_version || typeof expected_version !== 'number' || !Number.isInteger(expected_version) || expected_version < 1) {
    res.status(422).json(errorResponse('expected_version must be a positive integer (>= 1).', 'VALIDATION_ERROR'));
    return;
  }

  if (!expected_digest || typeof expected_digest !== 'string' || !DIGEST_REGEX.test(expected_digest)) {
    res.status(422).json(errorResponse('expected_digest must be a 64-character lowercase hex string.', 'VALIDATION_ERROR'));
    return;
  }

  if (decision !== 'APPROVE' && decision !== 'REJECT') {
    res.status(422).json(errorResponse("decision must be either 'APPROVE' or 'REJECT'.", 'VALIDATION_ERROR'));
    return;
  }

  if (!idempotency_key || typeof idempotency_key !== 'string' || idempotency_key.length < 1 || idempotency_key.length > 128) {
    res.status(422).json(errorResponse('idempotency_key must be a non-empty string between 1 and 128 characters.', 'VALIDATION_ERROR'));
    return;
  }

  if (decision === 'APPROVE' && rejection_reason) {
    res.status(422).json(errorResponse('rejection_reason cannot be provided when decision is APPROVE.', 'VALIDATION_ERROR'));
    return;
  }

  if (decision === 'REJECT' && rejection_reason !== undefined && rejection_reason !== null) {
    if (typeof rejection_reason !== 'string' || rejection_reason.trim().length === 0 || rejection_reason.length > 1000) {
      res.status(422).json(errorResponse('rejection_reason must be a non-empty string up to 1000 characters when provided.', 'VALIDATION_ERROR'));
      return;
    }
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('POST', `/amendments/${amendmentId}/decisions`, token, req.body);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Decision submission failed.', result.error?.code));
  }
}

export async function handleGetAmendmentStatus(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  const ownership = await resolveAmendmentOwningProject(amendmentId);
  if (ownership.error) {
    res.status(503).json(errorResponse('Database service unavailable to resolve amendment ownership.', 'SERVICE_UNAVAILABLE'));
    return;
  }
  if (!ownership.projectId) {
    res.status(404).json(errorResponse('Amendment not found.', 'NOT_FOUND'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, ownership.projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.', 'FORBIDDEN'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('GET', `/amendments/${amendmentId}/status`, token);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Failed to retrieve amendment status.', result.error?.code));
  }
}

export async function handleGetAmendmentHistory(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.', 'INVALID_PARAMETERS'));
    return;
  }

  const ownership = await resolveAmendmentOwningProject(amendmentId);
  if (ownership.error) {
    res.status(503).json(errorResponse('Database service unavailable to resolve amendment ownership.', 'SERVICE_UNAVAILABLE'));
    return;
  }
  if (!ownership.projectId) {
    res.status(404).json(errorResponse('Amendment not found.', 'NOT_FOUND'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, ownership.projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.', 'FORBIDDEN'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.', 'UNAUTHENTICATED'));
    return;
  }

  const result = await contractflowProxy.forward('GET', `/amendments/${amendmentId}/history`, token);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Failed to retrieve amendment history.', result.error?.code));
  }
}
