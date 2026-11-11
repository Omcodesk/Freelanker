import { api } from './api.ts';
import type {
  AgreementBundleResponse,
  ContractFlowAmendmentReview,
  ContractFlowApprovalStatus,
  ContractFlowAssessmentReview,
  ContractFlowAuditEvent,
  ContractFlowOverview,
  Milestone,
  PaymentArrangement,
} from '../types/index.ts';

export interface MilestonePayload {
  title: string;
  description?: string;
  amount: number;
  dueDate: string;
  orderIndex?: number;
}

export interface SaveAgreementDraftPayload {
  title: string;
  scopeOfWork: string;
  deliverablesText?: string;
  acceptanceCriteria?: string;
  paymentArrangement: PaymentArrangement;
  totalAmount: number;
  currency: string;
  revisionLimit?: number | null;
  reviewPeriodDays: number;
  startDate?: string | null;
  endDate?: string | null;
  additionalTerms?: string;
  isAiGenerated?: boolean;
  aiSummary?: string;
}

export const contractflowService = {
  // ─── Milestones ────────────────────────────────────────────────────────────
  listMilestones(projectId: string) {
    return api.get<{ milestones: Milestone[]; sourceVersion: number }>(`/projects/${projectId}/milestones`);
  },

  createMilestone(projectId: string, body: MilestonePayload) {
    return api.post<{ milestone: Milestone; sourceVersion: number }>(`/projects/${projectId}/milestones`, body);
  },

  updateMilestone(projectId: string, milestoneId: string, body: Partial<MilestonePayload>) {
    return api.patch<{ milestone: Milestone; sourceVersion: number }>(
      `/projects/${projectId}/milestones/${milestoneId}`,
      body
    );
  },

  deleteMilestone(projectId: string, milestoneId: string) {
    return api.delete<{ deletedId: string; sourceVersion: number }>(
      `/projects/${projectId}/milestones/${milestoneId}`
    );
  },

  // ─── Initial Agreement Lifecycle ───────────────────────────────────────────
  getCurrentAgreement(projectId: string) {
    return api.get<AgreementBundleResponse>(`/projects/${projectId}/agreements/current`);
  },

  saveAgreementDraft(projectId: string, body: SaveAgreementDraftPayload) {
    return api.post<AgreementBundleResponse>(`/projects/${projectId}/agreements/draft`, body);
  },

  submitAgreementForReview(projectId: string, agreementId: string, expectedVersion: number, expectedDigest: string) {
    return api.post<AgreementBundleResponse>(`/projects/${projectId}/agreements/${agreementId}/submit`, {
      expectedVersion,
      expectedDigest,
    });
  },

  decideAgreement(
    projectId: string,
    agreementId: string,
    body: { decision: 'APPROVE' | 'REJECT'; expectedVersion: number; expectedDigest: string; notes?: string }
  ) {
    return api.post<AgreementBundleResponse>(`/projects/${projectId}/agreements/${agreementId}/decide`, body);
  },

  // ─── ContractFlow Service Proxy Endpoints ──────────────────────────────────
  getOverview(projectId: string) {
    return api.get<ContractFlowOverview>(`/contractflow/projects/${projectId}/overview`);
  },

  generateContract(projectId: string, expectedSourceVersion: number) {
    return api.post<Record<string, unknown>>(`/contractflow/projects/${projectId}/contracts/generate`, {
      expected_source_version: expectedSourceVersion,
    });
  },

  generateAgreementDraft(projectId: string, expectedSourceVersion: number) {
    return api.post<Record<string, unknown>>(`/contractflow/projects/${projectId}/agreements/draft`, {
      expected_source_version: expectedSourceVersion,
    });
  },

  assessScope(
    projectId: string,
    expectedSourceVersion: number,
    clientRequest: string,
    supportingContext: Array<{ id: string; text: string }> = []
  ) {
    return api.post<Record<string, unknown>>(`/contractflow/projects/${projectId}/scope/assess`, {
      expected_source_version: expectedSourceVersion,
      client_request: clientRequest,
      supporting_context: supportingContext,
    });
  },

  issueAssessmentReview(projectId: string, assessmentId: string, expectedVersion: number, expectedDigest: string) {
    return api.post<ContractFlowAssessmentReview>(
      `/contractflow/projects/${projectId}/assessments/${assessmentId}/reviews`,
      {
        expected_version: expectedVersion,
        expected_digest: expectedDigest,
        confirm_human_review: true,
      }
    );
  },

  generateAmendment(
    projectId: string,
    expectedSourceVersion: number,
    assessmentId: string,
    reviewReference: string
  ) {
    return api.post<Record<string, unknown>>(`/contractflow/projects/${projectId}/amendments/generate`, {
      expected_source_version: expectedSourceVersion,
      assessment_id: assessmentId,
      review_reference: reviewReference,
    });
  },

  issueAmendmentReview(
    amendmentId: string,
    expectedVersion: number,
    expectedDigest: string,
    expiresInHours = 24
  ) {
    return api.post<ContractFlowAmendmentReview>(`/contractflow/amendments/${amendmentId}/reviews`, {
      expected_version: expectedVersion,
      expected_digest: expectedDigest,
      human_review: true,
      semantic_review: true,
      expires_in_hours: expiresInHours,
    });
  },

  revokeAmendmentReview(amendmentId: string, reviewId: string, reason: string) {
    return api.post<{ review_id: string; revoked: boolean }>(
      `/contractflow/amendments/${amendmentId}/reviews/${reviewId}/revoke`,
      { reason }
    );
  },

  registerAmendment(amendmentId: string, expectedVersion: number, expectedDigest: string) {
    return api.post<ContractFlowApprovalStatus>(`/contractflow/amendments/${amendmentId}/register`, {
      expected_version: expectedVersion,
      expected_digest: expectedDigest,
    });
  },

  submitAmendmentDecision(
    amendmentId: string,
    body: {
      decision: 'APPROVE' | 'REJECT';
      expected_version: number;
      expected_digest: string;
      idempotency_key: string;
      rejection_reason?: string;
    }
  ) {
    return api.post<ContractFlowApprovalStatus>(`/contractflow/amendments/${amendmentId}/decisions`, body);
  },

  getAmendmentStatus(amendmentId: string) {
    return api.get<ContractFlowApprovalStatus>(`/contractflow/amendments/${amendmentId}/status`);
  },

  getAmendmentHistory(amendmentId: string) {
    return api.get<ContractFlowAuditEvent[]>(`/contractflow/amendments/${amendmentId}/history`);
  },
};

