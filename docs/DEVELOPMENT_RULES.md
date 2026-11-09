# Freelanker — Development Rules

**Version:** 1.0  
**Branch:** `feature/core-platform`  
**Last Updated:** 2026-11-09

---

## 1. Branch Ownership

| Person | Branch | Owns |
|--------|--------|------|
| Person 1 | `feature/core-platform` | Foundation, auth, DB schema, shared types, core APIs, PayPal integration, deployment |
| Person 2 | `feature/contractflow` | ContractFlow module (agreements, project planning) |
| Person 3 | `feature/workbridge` | WorkBridge module (project collaboration workspace) |

**Rule:** Never commit directly to `main`. All work goes through feature branches and pull requests.

---

## 2. Cross-Branch Collaboration Rules

- Person 2 and Person 3 **must** import shared types only from paths documented in `docs/API_CONTRACTS.md`.
- Never modify files owned by another person's module without prior agreement.
- Database migrations are exclusively owned by **Person 1**. Other developers request schema additions via issue/discussion.
- Shared TypeScript types live in:
  - `frontend/src/types/index.ts` (Person 1 owns, others read-only)
  - `backend/src/types/index.ts` (Person 1 owns, others read-only)
- Route registration for ContractFlow and WorkBridge is added to `backend/src/app.ts` via agreed import pattern. Person 1 coordinates merges.

---

## 3. Folder Ownership

```
Freelanker/
├── .gitignore              Person 1
├── README.md               Person 1
├── docs/                   Person 1 (shared reading)
├── frontend/
│   ├── src/types/          Person 1 (read-only for P2, P3)
│   ├── src/lib/            Person 1
│   ├── src/services/       Person 1
│   ├── src/pages/          Shared (each person adds their own pages)
│   ├── src/components/
│   │   ├── layout/         Person 1
│   │   ├── contractflow/   Person 2
│   │   └── workbridge/     Person 3
│   └── src/features/
│       ├── auth/           Person 1
│       ├── contractflow/   Person 2
│       └── workbridge/     Person 3
└── backend/
    ├── src/config/         Person 1
    ├── src/middleware/     Person 1
    ├── src/types/          Person 1 (read-only for P2, P3)
    ├── src/routes/
    │   ├── health.route.ts           Person 1
    │   ├── auth.route.ts             Person 1
    │   ├── contractflow.route.ts     Person 2
    │   └── workbridge.route.ts       Person 3
    └── src/controllers/
        ├── contractflow/   Person 2
        └── workbridge/     Person 3
```

---

## 4. Code Standards

### TypeScript
- Strict mode enabled on both frontend and backend.
- No `any` types — use `unknown` and narrow where needed.
- All exports should be explicitly typed.
- Prefer `interface` for objects, `type` for unions/aliases.

### Naming Conventions
- Files: `kebab-case.ts`
- React components: `PascalCase.tsx`
- Functions/variables: `camelCase`
- Constants: `SCREAMING_SNAKE_CASE`
- Database columns: `snake_case`
- TypeScript types/interfaces: `PascalCase`

### API
- All routes prefixed with `/api`.
- Always return `{ success: boolean, data?: T, error?: string }` envelope.
- Use HTTP status codes correctly (200, 201, 400, 401, 403, 404, 500).
- Never trust client-supplied amounts or payment status — always verify server-side.

---

## 5. Environment Variables

- Never commit `.env` files.
- Each application has its own `.env.example` with placeholder values.
- All secrets stay server-side (backend only).
- Frontend may only use public keys prefixed with `VITE_`.
- PayPal Client Secret and OpenAI API Key must **never** appear in frontend code or env.

---

## 6. Git Workflow

```bash
# Start work
git checkout feature/your-branch
git pull origin feature/your-branch

# Commit often with descriptive messages
git commit -m "feat(module): describe the change"

# Before requesting a merge to main
git fetch origin main
git rebase origin/main
# Resolve conflicts, then push
git push origin feature/your-branch
```

### Commit message prefixes
- `feat:` — new feature
- `fix:` — bug fix
- `chore:` — tooling, deps, config
- `docs:` — documentation
- `refactor:` — code restructure without behavior change
- `test:` — adding tests

---

## 7. Security Rules

- Validate all inputs on the backend before processing.
- Never return raw database error messages to the client.
- Project resource access must check membership before returning data.
- Payment amounts are always retrieved from the database, never from the request body.
- Supabase service-role key stays on the backend only.

---

## 8. What Is Not Allowed in MVP

- Claiming escrow functionality without a supported PayPal integration.
- Silently approving deliverables or releasing payments automatically.
- AI making binding decisions without human approval.
- Exposing any secret keys in frontend bundles.

