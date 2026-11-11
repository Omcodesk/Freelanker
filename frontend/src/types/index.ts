// ─── Shared Frontend Types ────────────────────────────────────────────────────
// Person 2 (ContractFlow) and Person 3 (WorkBridge) import from here.
// See docs/API_CONTRACTS.md and docs/DATABASE_SCHEMA.md for the full specification.

// ─── API Response Envelope ────────────────────────────────────────────────────
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

// ─── User & Roles ─────────────────────────────────────────────────────────────
export type UserRole = 'client' | 'freelancer';

export interface User {
  id: string;
  email: string;
  createdAt: string;
}

export interface Profile {
  id: string;
  displayName: string;
  headline?: string;
  bio?: string;
  avatarUrl?: string;
  skills: string[];
  portfolioLinks: string[];
  isAvailable: boolean;
  isAdmin?: boolean;
  createdAt: string;
  updatedAt: string;
}

// Public marketplace profile view (safe fields)
export interface PublicFreelancerProfile {
  id: string;
  displayName: string;
  headline?: string;
  bio?: string;
  avatarUrl?: string;
  skills: string[];
  portfolioLinks: string[];
  isAvailable: boolean;
  createdAt: string;
}

// ─── Project ──────────────────────────────────────────────────────────────────
export type ProjectStatus =
  | 'draft'
  | 'invitation_pending'
  | 'awaiting_agreement'
  | 'active'
  | 'in_progress'
  | 'under_review'
  | 'completed'
  | 'cancelled'
  | 'disputed';

export interface Project {
  id: string;
  title: string;
  description?: string;
  status: ProjectStatus;
  initiatorId: string;
  clientId?: string;
  freelancerId?: string;
  currency: string;
  totalBudget?: number;
  paymentArrangement?: PaymentArrangement;
  aiScopeData?: Record<string, unknown>;
  reviewPeriodDays: number;
  sourceVersion: number;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectMember {
  id: string;
  projectId: string;
  userId: string;
  role: UserRole;
  joinedAt: string;
}

export interface CreateProjectDTO {
  title: string;
  description?: string;
  role: 'client' | 'freelancer';
  currency?: string;
  totalBudget?: number;
  paymentArrangement?: PaymentArrangement;
  reviewPeriodDays?: number;
  aiScopeData?: Record<string, unknown>;
}

export interface UpdateProjectDTO {
  title?: string;
  description?: string;
  currency?: string;
  totalBudget?: number;
  paymentArrangement?: PaymentArrangement;
  reviewPeriodDays?: number;
}

export interface ProjectDetail {
  project: Project;
  currentUserRole: 'client' | 'freelancer';
  members: Array<{
    id: string;
    userId: string;
    role: 'client' | 'freelancer';
    joinedAt: string;
    profile: {
      displayName: string;
      avatarUrl?: string;
    };
  }>;
  activeInvitation?: {
    id: string;
    invitedEmail: string;
    role: 'client' | 'freelancer';
    status: InvitationStatus;
    expiresAt: string;
    createdAt: string;
  } | null;
  milestones?: Milestone[];
}

export type InvitationStatus = 'pending' | 'accepted' | 'rejected' | 'expired' | 'cancelled';

export interface Invitation {
  id: string;
  projectId: string;
  invitedBy: string;
  invitedEmail: string;
  invitedUserId?: string;
  role: UserRole;
  status: InvitationStatus;
  token: string;
  message?: string;
  expiresAt: string;
  respondedAt?: string;
  createdAt: string;
}

export interface CreateInvitationDTO {
  email: string;
  message?: string;
}

export interface InvitationResponse {
  invitation: Invitation;
  invitationLink: string;
  delivery: {
    method: 'link';
    status: 'ready';
    recipientEmail: string;
  };
}

export interface InvitationDetail extends Invitation {
  invitationLink?: string;
  project?: {
    id: string;
    title: string;
    currency: string;
    totalBudget?: number;
    status: ProjectStatus;
  } | null;
  inviter?: {
    displayName: string;
    avatarUrl?: string;
  } | null;
}

export interface InvitationPreview {
  id: string;
  projectId: string;
  projectTitle: string;
  projectDescription?: string;
  projectStatus: ProjectStatus;
  currency: string;
  totalBudget?: number;
  role: 'client' | 'freelancer';
  status: InvitationStatus;
  maskedEmail: string;
  expiresAt: string;
  isExpired: boolean;
  inviter: {
    displayName: string;
    avatarUrl?: string;
  };
}

// ─── Agreement & Approvals (ContractFlow) ──────────────────────────────────────
export type AgreementStatus =
  | 'draft'
  | 'sent_for_review'
  | 'changes_requested'
  | 'approved'
  | 'active'
  | 'completed'
  | 'cancelled';

export interface Agreement {
  id: string;
  projectId: string;
  versionNumber: number;
  previousVersionId?: string;
  isCurrent: boolean;
  status: AgreementStatus;
  title: string;
  scopeOfWork?: string;
  deliverablesText?: string;
  acceptanceCriteria?: string;
  paymentArrangement: PaymentArrangement;
  totalAmount: number;
  currency: string;
  revisionLimit?: number;
  reviewPeriodDays: number;
  startDate?: string;
  endDate?: string;
  additionalTerms?: string;
  isAiGenerated: boolean;
  pdfUrl?: string;
  aiSummary?: string;
  contentSnapshot?: Record<string, unknown>;
  clientApprovedAt?: string;
  freelancerApprovedAt?: string;
  activatedAt?: string;
  supersededAt?: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface AgreementApproval {
  id: string;
  agreementId: string;
  userId: string;
  role: UserRole;
  action: 'approved' | 'changes_requested' | 'withdrawn';
  notes?: string;
  createdAt: string;
}

export interface AgreementWithDigest extends Agreement {
  contentDigest: string;
}

export interface AgreementBundleResponse {
  currentAgreement: AgreementWithDigest | null;
  versions: AgreementWithDigest[];
  approvals: AgreementApproval[];
}

export type AmendmentApprovalState =
  | 'PENDING_REVIEW'
  | 'PARTIALLY_APPROVED'
  | 'BOTH_APPROVED'
  | 'REJECTED'
  | 'SUPERSEDED';

export interface ContractFlowApprovalStatus {
  amendment_id: string;
  amendment_version: number;
  content_digest: string;
  state: AmendmentApprovalState;
  remaining_approvals: Array<'CLIENT' | 'FREELANCER'>;
  human_review_required: boolean;
  semantic_review_required: boolean;
  effective: boolean;
}

export interface ContractFlowAuditEvent {
  event_id: string;
  amendment_id: string;
  amendment_version: number;
  content_digest: string;
  actor_id: string;
  role: 'CLIENT' | 'FREELANCER';
  action: 'CREATED' | 'APPROVE' | 'REJECT' | 'SUPERSEDED';
  previous_state: AmendmentApprovalState | null;
  new_state: AmendmentApprovalState;
  timestamp: string;
  idempotency_reference?: string | null;
  decision_id?: string | null;
}

export interface ContractFlowAssessmentReview {
  assessment_review_id: string;
  review_reference: string;
  assessment_id: string;
  assessment_revision: number;
  original_agreement_id: string;
  original_agreement_version: number;
  reviewer_id: string;
  decision: string;
  reviewed_at: string;
  revoked: boolean;
}

export interface ContractFlowAmendmentReview {
  review_id: string;
  amendment_id: string;
  revision: number;
  content_digest: string;
  reviewer_id: string;
  reviewed_at: string;
  expires_at: string;
  human_review: boolean;
  semantic_review: boolean;
  revoked: boolean;
  revoked_at?: string | null;
  revocation_reason?: string | null;
}

export interface ContractFlowArtifactItem {
  artifact_id: string;
  revision: number;
  kind: 'CONTRACT' | 'AGREEMENT' | 'ASSESSMENT' | 'AMENDMENT';
  source_version: number;
  content_digest: string;
  created_at: string;
  payload: Record<string, any>;
  assessment_reviews?: ContractFlowAssessmentReview[];
  approval_digest?: string | null;
  approval_head?: {
    current_revision: number;
    is_current_head: boolean;
    state: AmendmentApprovalState;
    approval_digest: string;
    original_agreement_id: string;
    original_agreement_version: number;
    review_reference: string;
    created_at: string;
  } | null;
  reviews?: ContractFlowAmendmentReview[];
  decisions?: Array<{
    decision_id: string;
    actor_id: string;
    role: 'CLIENT' | 'FREELANCER';
    decision: 'APPROVE' | 'REJECT';
    rejection_reason?: string | null;
    created_at: string;
  }>;
}

export interface ContractFlowOverview {
  project_id: string;
  source_version: number;
  source_ready: boolean;
  missing_requirements: string[];
  has_active_agreement: boolean;
  groq_enabled: boolean;
  artifacts: ContractFlowArtifactItem[];
}

// ─── Milestones, Tasks & Deliverables (WorkBridge) ─────────────────────────────
export type MilestoneStatus =
  | 'not_started'
  | 'awaiting_prepayment'
  | 'in_progress'
  | 'submitted'
  | 'under_review'
  | 'revision_requested'
  | 'approved'
  | 'payment_pending'
  | 'paid'
  | 'disputed';

export interface Milestone {
  id: string;
  projectId: string;
  title: string;
  description?: string;
  status: MilestoneStatus;
  amount: number;
  orderIndex: number;
  dueDate?: string;
  isAiGenerated: boolean;
  createdAt: string;
  updatedAt: string;
}

export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'cancelled';

export interface Task {
  id: string;
  projectId: string;
  milestoneId?: string;
  title: string;
  description?: string;
  status: TaskStatus;
  assignedTo?: string;
  dueDate?: string;
  orderIndex: number;
  isAiGenerated: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export type DeliverableStatus =
  | 'submitted'
  | 'under_review'
  | 'revision_requested'
  | 'approved'
  | 'rejected';

export interface Deliverable {
  id: string;
  projectId: string;
  milestoneId?: string;
  submittedBy: string;
  status: DeliverableStatus;
  title: string;
  description?: string;
  submissionNote?: string;
  fileUrls: string[];
  linkUrl?: string;
  version: number;
  parentId?: string;
  reviewDeadline?: string;
  clientFeedback?: string;
  aiAnalysis?: Record<string, unknown>;
  reviewedBy?: string;
  reviewedAt?: string;
  createdAt: string;
  updatedAt: string;
}

// ─── Messages ─────────────────────────────────────────────────────────────────
export interface Message {
  id: string;
  projectId: string;
  senderId: string;
  content: string;
  fileUrls: string[];
  isAiSummary: boolean;
  createdAt: string;
}

// ─── Payments & Transactions (PayFlow) ────────────────────────────────────────
export type PaymentArrangement =
  | 'upfront'
  | 'milestone_prepayment'
  | 'payment_after_approval';

export type PaymentStatus =
  | 'pending'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'refunded';

export interface Payment {
  id: string;
  projectId: string;
  milestoneId?: string;
  payerId: string;
  payeeId: string;
  amountSnapshot: number;
  currencySnapshot: string;
  status: PaymentStatus;
  arrangement: PaymentArrangement;
  paypalOrderId?: string;
  paypalCaptureId?: string;
  paypalResponse?: Record<string, unknown>;
  initiatedAt: string;
  completedAt?: string;
  createdAt: string;
}

export interface PaymentEvent {
  id: string;
  paymentId: string;
  eventType: string;
  oldStatus?: PaymentStatus;
  newStatus?: PaymentStatus;
  paypalEventId?: string;
  payload?: Record<string, unknown>;
  createdAt: string;
}

// ─── Disputes ─────────────────────────────────────────────────────────────────
export type DisputeStatus =
  | 'open'
  | 'under_review'
  | 'awaiting_response'
  | 'resolution_proposed'
  | 'resolved'
  | 'closed';

export interface Dispute {
  id: string;
  projectId: string;
  raisedBy: string;
  againstUserId: string;
  status: DisputeStatus;
  reason: string;
  description?: string;
  aiSummary?: string;
  resolutionNotes?: string;
  resolvedBy?: string;
  resolvedAt?: string;
  createdAt: string;
  updatedAt: string;
}

// ─── Audit & Activity ─────────────────────────────────────────────────────────
export type ActivityEventType =
  | 'project_created'
  | 'project_status_changed'
  | 'agreement_created'
  | 'agreement_version_created'
  | 'agreement_approved'
  | 'agreement_activated'
  | 'milestone_created'
  | 'milestone_status_changed'
  | 'deliverable_submitted'
  | 'deliverable_approved'
  | 'deliverable_revision_requested'
  | 'payment_initiated'
  | 'payment_completed'
  | 'payment_failed'
  | 'dispute_opened'
  | 'dispute_resolved'
  | 'invitation_sent'
  | 'invitation_accepted'
  | 'invitation_rejected'
  | 'message_sent'
  | 'member_added';

export interface ActivityLog {
  id: string;
  projectId?: string;
  actorId?: string;
  eventType: ActivityEventType;
  entityType: string;
  entityId: string;
  oldData?: Record<string, unknown>;
  newData?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

export interface Notification {
  id: string;
  userId: string;
  projectId?: string;
  type: string;
  title: string;
  body?: string;
  isRead: boolean;
  entityType?: string;
  entityId?: string;
  createdAt: string;
  readAt?: string;
}

// ─── Health ───────────────────────────────────────────────────────────────────
export interface HealthData {
  status: 'ok' | 'degraded';
  timestamp: string;
  version: string;
  environment: string;
}
