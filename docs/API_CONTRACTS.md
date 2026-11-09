# Freelanker — API Contracts

**Version:** 1.0  
**Last Updated:** 2026-11-09  
**Base URL (dev):** `http://localhost:4000/api`

All responses follow the standard envelope:

```ts
// Success
{ "success": true, "data": T }

// Error
{ "success": false, "error": "Human-readable message" }
```

---

## Standard Response Envelope (TypeScript)

```ts
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}
```

---

## 1. Health

### `GET /api/health`

Returns service status. No authentication required.

**Owner:** Person 1

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "timestamp": "2026-11-09T12:00:00.000Z",
    "version": "1.0.0",
    "environment": "development"
  }
}
```

---

## 2. Authentication (Person 1 — Active)

Supabase Auth is used directly for user registration, email verification, login, and session persistence. The Express backend verifies Supabase access tokens server-side using the `requireAuth` middleware.

| Method | Path | Auth Required | Description |
|--------|------|:-------------:|-------------|
| `GET`  | `/api/auth/me` | ✅ Bearer JWT | Returns the verified user identity and associated `profiles` row |

### `GET /api/auth/me`

**Headers:**
```
Authorization: Bearer <supabase_access_token>
```

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "11111111-2222-3333-4444-555555555555",
      "email": "jane@example.com",
      "createdAt": "2026-11-09T10:00:00.000Z",
      "userMetadata": {
        "full_name": "Jane Doe",
        "default_role": "client"
      }
    },
    "profile": {
      "id": "11111111-2222-3333-4444-555555555555",
      "displayName": "Jane Doe",
      "headline": null,
      "bio": null,
      "avatarUrl": null,
      "skills": [],
      "portfolioLinks": [],
      "isAvailable": true,
      "isAdmin": false,
      "createdAt": "2026-11-09T10:00:00.000Z",
      "updatedAt": "2026-11-09T10:00:00.000Z"
    }
  }
}
```

**Error `401`:**
```json
{
  "success": false,
  "error": "Authentication required: Missing or malformed Authorization header."
}
```

---

## 3. Users & Profiles (Person 1 — Coming Next)

> Not yet implemented.

| Method | Path | Description |
|--------|------|-------------|
| `GET`    | `/api/users/:id` | Get user profile |
| `PUT`    | `/api/users/:id` | Update profile |
| `GET`    | `/api/users/:id/projects` | Get user's projects |

---

## 4. Projects (Person 1 — Coming Next)

> Not yet implemented.

| Method | Path | Description |
|--------|------|-------------|
| `POST`   | `/api/projects` | Create project |
| `GET`    | `/api/projects/:id` | Get project |
| `PUT`    | `/api/projects/:id` | Update project |
| `GET`    | `/api/projects` | List user's projects |

---

## 5. ContractFlow (Person 2 — Separate Branch)

> Routes will be registered at `/api/contractflow/...`  
> Person 2 defines the full route list in their branch.  
> Person 1 integrates the router into `backend/src/app.ts` on merge.

---

## 6. WorkBridge (Person 3 — Separate Branch)

> Routes will be registered at `/api/workbridge/...`  
> Person 3 defines the full route list in their branch.  
> Person 1 integrates the router into `backend/src/app.ts` on merge.

---

## 7. PayPal Payments (Person 1 — Coming Later)

> Not yet implemented.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/payments/create-order` | Create PayPal order (server-side) |
| `POST` | `/api/payments/capture-order` | Capture PayPal order (server-side) |
| `POST` | `/api/payments/webhook` | PayPal webhook receiver |
| `GET`  | `/api/payments/:projectId` | Get payment history for project |

---

## 8. Shared TypeScript Types

Both frontend and backend share compatible type definitions.

**Frontend types:** `frontend/src/types/index.ts`  
**Backend types:** `backend/src/types/index.ts`

### Core Entities

```ts
// User roles
type UserRole = 'client' | 'freelancer';

// Project statuses (PRD §10)
type ProjectStatus =
  | 'draft'
  | 'invitation_pending'
  | 'awaiting_agreement'
  | 'active'
  | 'in_progress'
  | 'under_review'
  | 'completed'
  | 'cancelled'
  | 'disputed';

// Milestone statuses (PRD §10)
type MilestoneStatus =
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

// Agreement lifecycle (PRD §4.1)
type AgreementStatus =
  | 'draft'
  | 'sent_for_review'
  | 'changes_requested'
  | 'approved'
  | 'active'
  | 'completed'
  | 'cancelled';

// Payment arrangements (PRD §4.3)
type PaymentArrangement =
  | 'upfront'
  | 'milestone_prepayment'
  | 'payment_after_approval';

// Dispute statuses (PRD §8)
type DisputeStatus =
  | 'open'
  | 'under_review'
  | 'awaiting_response'
  | 'resolution_proposed'
  | 'resolved'
  | 'closed';

// Deliverable status
type DeliverableStatus =
  | 'submitted'
  | 'under_review'
  | 'revision_requested'
  | 'approved'
  | 'rejected';

// Task status
type TaskStatus = 'todo' | 'in_progress' | 'done' | 'cancelled';

// Invitation status
type InvitationStatus = 'pending' | 'accepted' | 'rejected' | 'expired' | 'cancelled';

// Activity event types
type ActivityEventType =
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

// Detailed entity structures
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
  createdAt: string;
  updatedAt: string;
}

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
```

