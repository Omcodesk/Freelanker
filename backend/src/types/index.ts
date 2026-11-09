// ─── Shared Server-Side Types ─────────────────────────────────────────────────
// These are the canonical type definitions for the backend.
// Person 2 (ContractFlow) and Person 3 (WorkBridge) import from here.
// See docs/API_CONTRACTS.md for the full type reference.

// ─── API Response Envelope ────────────────────────────────────────────────────
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

export function successResponse<T>(data: T): ApiResponse<T> {
  return { success: true, data };
}

export function errorResponse(message: string): ApiResponse<never> {
  return { success: false, error: message };
}

// ─── User & Auth ──────────────────────────────────────────────────────────────
export type UserRole = 'client' | 'freelancer';

export interface AuthUser {
  id: string;
  email: string;
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

export type PaymentStatus =
  | 'pending'
  | 'completed'
  | 'failed'
  | 'cancelled';

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
