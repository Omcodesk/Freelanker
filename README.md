# Freelanker

**AI-powered freelance collaboration and payment platform.**  
From project idea to successful payment.

> PayPal AI Hackathon — MVP

---

## Modules

| Module | Description | Branch |
|--------|-------------|--------|
| **ContractFlow** | Agreements and project planning | `feature/contractflow` |
| **WorkBridge** | Project collaboration workspace | `feature/workbridge` |
| **PayFlow** | PayPal payment management | `feature/core-platform` |
| **Freelanker AI** | Shared AI assistant | `feature/core-platform` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript (strict), Vite, Tailwind CSS v3 |
| Backend | Node.js 22, Express 4, TypeScript (strict) |
| Database | Supabase (PostgreSQL + Auth + Storage) |
| AI | OpenAI API |
| Payments | PayPal Developer Sandbox |
| Deployment | Vercel (frontend), Render (backend), Supabase |

---

## Project Structure

```
Freelanker/
├── docs/
│   ├── PRD.md                  Product requirements
│   ├── API_CONTRACTS.md        API contracts and shared types
│   └── DEVELOPMENT_RULES.md   Developer collaboration rules
├── frontend/                   React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── types/              Shared TypeScript types (Person 1)
│       ├── lib/                Supabase client
│       ├── services/           API client (native fetch)
│       ├── pages/              Page components
│       └── components/
│           └── layout/         App shell and layout
└── backend/                    Express + TypeScript
    └── src/
        ├── config/             Environment configuration
        ├── types/              Shared server-side types
        ├── routes/             Route definitions
        ├── controllers/        Route handlers
        └── middleware/         Error handling, auth (coming next)
```

---

## Getting Started

### Prerequisites

- Node.js v22+
- npm v10+
- A Supabase project (for auth and database — set up before running auth tasks)

---

### 1. Clone the repository

```bash
git clone https://github.com/Omcodesk/Freelanker.git
cd Freelanker
```

### 2. Set up the backend

```bash
cd backend
cp .env.example .env
# Edit .env and fill in your credentials
npm install
npm run dev
```

The backend will start at **http://localhost:4000**

Verify: `GET http://localhost:4000/api/health` → should return `{ "success": true, "data": { "status": "ok", ... } }`

### 3. Set up the frontend

Open a second terminal:

```bash
cd frontend
cp .env.example .env
# Edit .env — VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are required for auth (later task)
npm install
npm run dev
```

The frontend will start at **http://localhost:5173**

---

## Development Commands

### Backend

```bash
npm run dev        # Start with hot-reload (tsx + nodemon)
npm run build      # Compile TypeScript
npm run start      # Run compiled output
npm run typecheck  # TypeScript check without compiling
```

### Frontend

```bash
npm run dev        # Start Vite dev server
npm run build      # Production build
npm run preview    # Preview production build locally
npm run typecheck  # TypeScript check without compiling
```

---

## Environment Variables

Both applications have `.env.example` files documenting all required variables.

**Security rules:**
- Never commit `.env` files.
- Never put secret keys (`PAYPAL_CLIENT_SECRET`, `OPENAI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) in the frontend.
- Frontend may only use `VITE_` prefixed public keys.

---

## API

Base URL: `http://localhost:4000/api`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Service health check |

Full API documentation: [docs/API_CONTRACTS.md](./docs/API_CONTRACTS.md)

---

## Contributing

See [docs/DEVELOPMENT_RULES.md](./docs/DEVELOPMENT_RULES.md) for branch ownership, code standards, and git workflow.

---

## License

MIT License — see [LICENSE](./LICENSE)

