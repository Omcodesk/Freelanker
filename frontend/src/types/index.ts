// ─── Shared Frontend Types ────────────────────────────────────────────────────
// Person 2 (ContractFlow) and Person 3 (WorkBridge) import from here.
// See docs/API_CONTRACTS.md for the full type reference.

// ─── API Response Envelope ────────────────────────────────────────────────────
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

// ─── User & Auth ──────────────────────────────────────────────────────────────
export type UserRole = 'client' | 'freelancer';

export interface User {
  id: string;
  email: string;
  createdAt: string;
}

export interface UserProfile {
  userId: string;
  displayName: string;
  headline?: string;
  bio?: string;
  skills: string[];
  avatarUrl?: string;
  portfolioLinks: string[];
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
  description: string;
  status: ProjectStatus;
  clientId: string;
  freelancerId?: string;
  budget?: number;
  currency: string;
  createdAt: string;
  updatedAt: string;
}

// ─── Milestone ────────────────────────────────────────────────────────────────
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
  description: string;
  status: MilestoneStatus;
  amount: number;
  dueDate?: string;
  order: number;
}

// ─── Agreement ────────────────────────────────────────────────────────────────
export type AgreementStatus =
  | 'draft'
  | 'sent_for_review'
  | 'changes_requested'
  | 'approved'
  | 'active'
  | 'completed'
  | 'cancelled';

// ─── Payment ──────────────────────────────────────────────────────────────────
export type PaymentArrangement =
  | 'upfront'
  | 'milestone_prepayment'
  | 'payment_after_approval';

export type PaymentStatus = 'pending' | 'completed' | 'failed' | 'cancelled';

// ─── Dispute ──────────────────────────────────────────────────────────────────
export type DisputeStatus =
  | 'open'
  | 'under_review'
  | 'awaiting_response'
  | 'resolution_proposed'
  | 'resolved'
  | 'closed';

// ─── Health ───────────────────────────────────────────────────────────────────
export interface HealthData {
  status: 'ok' | 'degraded';
  timestamp: string;
  version: string;
  environment: string;
}
