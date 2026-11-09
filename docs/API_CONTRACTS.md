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

## 2. Authentication (Person 1 — Coming Next)

> Not yet implemented. Routes will be added after Supabase Auth setup.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Log in |
| `POST` | `/api/auth/logout` | Log out |
| `GET`  | `/api/auth/me` | Get current user |

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
```
