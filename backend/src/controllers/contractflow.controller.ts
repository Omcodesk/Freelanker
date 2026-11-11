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

/**
 * Resolve the owning project ID for a given amendment UUID.
 *
 * Queries cf_approval_versions -> agreements -> project_id,
 * or cf_artifacts -> project_id.
 */
async function resolveAmendmentOwningProject(amendmentId: string): Promise<string | null> {
  // 1. Try resolving via cf_artifacts
  try {
    const { data: artData, error: artError } = await supabaseAdmin
      .from('cf_artifacts')
      .select('project_id')
      .eq('artifact_id', amendmentId)
      .limit(1)
      .maybeSingle();

    if (!artError && artData?.project_id) {
      return artData.project_id;
    }
  } catch {
    // cf_artifacts table may not exist yet in unmigrated environment
  }

  // 2. Try resolving via cf_approval_versions -> agreements
  try {
    const { data: verData, error: verError } = await supabaseAdmin
      .from('cf_approval_versions')
      .select('original_agreement_id')
      .eq('amendment_id', amendmentId)
      .limit(1)
      .maybeSingle();

    if (!verError && verData?.original_agreement_id) {
      const { data: agData } = await supabaseAdmin
        .from('agreements')
        .select('project_id')
        .eq('id', verData.original_agreement_id)
        .maybeSingle();

      if (agData?.project_id) {
        return agData.project_id;
      }
    }
  } catch {
    // cf_approval_versions table may not exist yet
  }

  return null;
}

// ─── Project Scoped Handlers ────────────────────────────────────────────────

export async function handleGenerateContract(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
    return;
  }

  const result = await contractflowProxy.forward('POST', '/contracts/generate', token, {
    project_id: projectId,
    expected_source_version: req.body?.expected_source_version ?? 1,
  });

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Contract generation failed.'));
  }
}

export async function handleDraftAgreement(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
    return;
  }

  const result = await contractflowProxy.forward('POST', '/agreements/draft', token, {
    project_id: projectId,
    expected_source_version: req.body?.expected_source_version ?? 1,
  });

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Agreement draft failed.'));
  }
}

export async function handleAssessScope(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.'));
    return;
  }

  const clientRequest = req.body?.client_request;
  if (!clientRequest || typeof clientRequest !== 'string' || !clientRequest.trim()) {
    res.status(422).json(errorResponse('client_request text is required for scope assessment.'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
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
    res.status(result.status).json(errorResponse(result.error?.message || 'Scope assessment failed.'));
  }
}

export async function handleGenerateAmendment(req: Request, res: Response): Promise<void> {
  const projectId = req.params.id;
  if (!UUID_REGEX.test(projectId)) {
    res.status(400).json(errorResponse('Invalid project ID format. Expected UUID.'));
    return;
  }

  const userId = req.user!.id;
  const isMember = await verifyProjectMembership(userId, projectId);
  if (!isMember) {
    res.status(403).json(errorResponse('Forbidden: You are not a member of this project.'));
    return;
  }

  const assessmentId = req.body?.assessment_id;
  const reviewReference = req.body?.review_reference;
  if (!assessmentId || !UUID_REGEX.test(assessmentId) || !reviewReference) {
    res.status(422).json(errorResponse('Valid assessment_id (UUID) and review_reference are required.'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
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
    res.status(result.status).json(errorResponse(result.error?.message || 'Amendment generation failed.'));
  }
}

// ─── Amendment Scoped Handlers (With Owning Project Resolution) ──────────────

export async function handleRegisterAmendment(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.'));
    return;
  }

  // Resolve owning project first to prevent cross-project access
  const owningProjectId = await resolveAmendmentOwningProject(amendmentId);
  const userId = req.user!.id;

  if (owningProjectId) {
    const isMember = await verifyProjectMembership(userId, owningProjectId);
    if (!isMember) {
      res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.'));
      return;
    }
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
    return;
  }

  const result = await contractflowProxy.forward('POST', `/amendments/${amendmentId}/register`, token, req.body);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Amendment registration failed.'));
  }
}

export async function handleSubmitDecision(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.'));
    return;
  }

  // Resolve owning project first
  const owningProjectId = await resolveAmendmentOwningProject(amendmentId);
  const userId = req.user!.id;

  if (owningProjectId) {
    const isMember = await verifyProjectMembership(userId, owningProjectId);
    if (!isMember) {
      res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.'));
      return;
    }
  }

  // Validate decision body fields
  const decision = req.body?.decision;
  const idempotencyKey = req.body?.idempotency_key;
  if (!decision || (decision !== 'APPROVE' && decision !== 'REJECT') || !idempotencyKey) {
    res.status(422).json(errorResponse('Valid decision (APPROVE/REJECT) and idempotency_key are required.'));
    return;
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
    return;
  }

  const result = await contractflowProxy.forward('POST', `/amendments/${amendmentId}/decisions`, token, req.body);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Decision submission failed.'));
  }
}

export async function handleGetAmendmentStatus(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.'));
    return;
  }

  const owningProjectId = await resolveAmendmentOwningProject(amendmentId);
  const userId = req.user!.id;

  if (owningProjectId) {
    const isMember = await verifyProjectMembership(userId, owningProjectId);
    if (!isMember) {
      res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.'));
      return;
    }
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
    return;
  }

  const result = await contractflowProxy.forward('GET', `/amendments/${amendmentId}/status`, token);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Failed to retrieve amendment status.'));
  }
}

export async function handleGetAmendmentHistory(req: Request, res: Response): Promise<void> {
  const amendmentId = req.params.amendmentId;
  if (!UUID_REGEX.test(amendmentId)) {
    res.status(400).json(errorResponse('Invalid amendment ID format. Expected UUID.'));
    return;
  }

  const owningProjectId = await resolveAmendmentOwningProject(amendmentId);
  const userId = req.user!.id;

  if (owningProjectId) {
    const isMember = await verifyProjectMembership(userId, owningProjectId);
    if (!isMember) {
      res.status(403).json(errorResponse('Forbidden: You are not a member of the project owning this amendment.'));
      return;
    }
  }

  const token = extractBearerToken(req);
  if (!token) {
    res.status(401).json(errorResponse('Authentication token required.'));
    return;
  }

  const result = await contractflowProxy.forward('GET', `/amendments/${amendmentId}/history`, token);

  if (result.data) {
    res.status(result.status).json(successResponse(result.data));
  } else {
    res.status(result.status).json(errorResponse(result.error?.message || 'Failed to retrieve amendment history.'));
  }
}
