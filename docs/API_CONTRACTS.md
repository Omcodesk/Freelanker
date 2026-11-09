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

## 4. Projects & Invitations (Core Platform)

All endpoints below require an authenticated Supabase user session (`Authorization: Bearer <supabase_jwt>`). User identity is derived strictly from the verified JWT server-side.

| Method | Path | Description | Access Control |
|--------|------|-------------|----------------|
| `POST` | `/api/projects` | Create a new project | Authenticated user (becomes initiator & first member) |
| `GET` | `/api/projects` | List projects accessible to current user | Authenticated project members |
| `GET` | `/api/projects/:id` | Get project details, members & invitations | Project members only |
| `PATCH`| `/api/projects/:id` | Update editable project fields | Project members only (pre-agreement states) |
| `POST` | `/api/projects/:id/cancel` | Cancel an active project | Project members only (non-terminal states) |
| `POST` | `/api/projects/:id/invitations` | Invite collaborator by email | Project members only; unoccupied role only |
| `GET` | `/api/invitations` | List invitations received by current user | Authenticated user matching recipient email/ID |
| `POST` | `/api/invitations/:id/accept` | Accept project invitation | Verified recipient email matching invitation |
| `POST` | `/api/invitations/:id/reject` | Reject project invitation | Recipient matching invitation |

---

### `POST /api/projects`
Creates a project in `draft` status and registers the authenticated user as the initiator with their chosen role.

**Request Body:**
```json
{
  "title": "Fintech Mobile App Redesign",
  "description": "Redesign UX/UI and mobile onboarding flow",
  "role": "client",
  "currency": "USD",
  "totalBudget": 5000,
  "paymentArrangement": "milestone",
  "reviewPeriodDays": 3
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "project": {
      "id": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
      "title": "Fintech Mobile App Redesign",
      "description": "Redesign UX/UI and mobile onboarding flow",
      "status": "draft",
      "initiatorId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
      "clientId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
      "freelancerId": null,
      "currency": "USD",
      "totalBudget": 5000,
      "paymentArrangement": "milestone",
      "reviewPeriodDays": 3,
      "createdAt": "2026-11-09T16:30:00.000Z",
      "updatedAt": "2026-11-09T16:30:00.000Z"
    },
    "membership": {
      "id": "11111111-2222-3333-4444-555555555555",
      "projectId": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
      "userId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
      "role": "client",
      "joinedAt": "2026-11-09T16:30:00.000Z"
    }
  }
}
```

**Errors:**
- `400 Bad Request`: Missing title, invalid role, invalid budget or reviewPeriodDays.
- `401 Unauthorized`: Missing or invalid JWT.

---

### `GET /api/projects`
Retrieves projects where the user is an active member. Supports optional query filters: `?status=...&role=...`.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "projects": [
      {
        "id": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
        "title": "Fintech Mobile App Redesign",
        "status": "draft",
        "initiatorId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
        "clientId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
        "currency": "USD",
        "totalBudget": 5000,
        "currentUserRole": "client",
        "reviewPeriodDays": 3,
        "createdAt": "2026-11-09T16:30:00.000Z",
        "updatedAt": "2026-11-09T16:30:00.000Z"
      }
    ]
  }
}
```

---

### `GET /api/projects/:id`
Returns full project details, member profiles, and active pending invitation.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "project": {
      "id": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
      "title": "Fintech Mobile App Redesign",
      "status": "draft",
      "initiatorId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
      "clientId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
      "currency": "USD",
      "totalBudget": 5000,
      "reviewPeriodDays": 3,
      "createdAt": "2026-11-09T16:30:00.000Z",
      "updatedAt": "2026-11-09T16:30:00.000Z"
    },
    "currentUserRole": "client",
    "members": [
      {
        "id": "11111111-2222-3333-4444-555555555555",
        "userId": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
        "role": "client",
        "joinedAt": "2026-11-09T16:30:00.000Z",
        "profile": {
          "displayName": "Jane Doe",
          "avatarUrl": null
        }
      }
    ],
    "activeInvitation": null
  }
}
```

**Errors:**
- `401 Unauthorized`: Missing or invalid JWT.
- `403 Forbidden`: User is not a member of the project.
- `404 Not Found`: Project not found.

---

### `PATCH /api/projects/:id`
Updates permitted project fields (`title`, `description`, `currency`, `totalBudget`, `paymentArrangement`, `reviewPeriodDays`).

**Errors:**
- `400 Bad Request`: Field validation error, or project is already active / completed.
- `403 Forbidden`: User is not a member of the project.
- `404 Not Found`: Project not found.

---

### `POST /api/projects/:id/cancel`
Cancels the project and any open invitations.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "project": {
      "id": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
      "status": "cancelled",
      "updatedAt": "2026-11-09T16:32:00.000Z"
    }
  }
}
```

---

### `POST /api/projects/:id/invitations`
Invites a collaborator by email. Role is assigned automatically to the unoccupied counterpart role (client &harr; freelancer).

**Request Body:**
```json
{
  "email": "dev@example.com",
  "message": "We would love for you to develop our mobile app!"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "invitation": {
      "id": "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
      "projectId": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
      "invitedBy": "59744a81-1e51-4589-aef3-1fb2eda6eb8c",
      "invitedEmail": "dev@example.com",
      "role": "freelancer",
      "status": "pending",
      "token": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "expiresAt": "2026-11-16T16:30:00.000Z",
      "createdAt": "2026-11-09T16:30:00.000Z"
    },
    "invitationLink": "http://localhost:5173/invitations/3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "delivery": {
      "method": "link",
      "status": "ready",
      "recipientEmail": "dev@example.com"
    }
  }
}
```

**Errors:**
- `400 Bad Request`: Self-invitation, invalid email, or project in invalid state.
- `403 Forbidden`: Requester is not a member of the project.
- `409 Conflict`: Role already occupied, competing pending invitation already active, or user already a project member.

---

### `GET /api/invitations`
Lists invitations received by the authenticated user (`status=pending` by default).

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "invitations": [
      {
        "id": "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
        "projectId": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
        "role": "freelancer",
        "status": "pending",
        "expiresAt": "2026-11-16T16:30:00.000Z",
        "project": {
          "id": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
          "title": "Fintech Mobile App Redesign",
          "currency": "USD",
          "totalBudget": 5000,
          "status": "invitation_pending"
        },
        "inviter": {
          "displayName": "Jane Doe",
          "avatarUrl": null
        }
      }
    ]
  }
}
```

---

### `POST /api/invitations/:id/accept`
Atomically accepts an invitation: updates invitation status, inserts membership into `project_members`, assigns role in `projects`, advances status to `awaiting_agreement`, cancels competing invitations, and records activity logs.

**Guards:**
- Recipient must be authenticated and have a **verified email address**.
- Email or user ID must match the invitation recipient.
- Project role must not be already occupied.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "projectId": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c",
    "role": "freelancer"
  }
}
```

**Errors:**
- `400 Bad Request`: Invitation not pending or expired.
- `401 Unauthorized`: Unauthenticated.
- `403 Forbidden`: Unverified email, or invitation addressed to different user/email.
- `409 Conflict`: Target role already filled, user already a member, or concurrent modification conflict.

---

### `POST /api/invitations/:id/reject`
Rejects an invitation and reverts project status to `draft` if no other collaborators remain.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "success": true,
    "projectId": "e4f8d22c-a07e-40e9-b5bf-7da2665e317c"
  }
}
```

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

