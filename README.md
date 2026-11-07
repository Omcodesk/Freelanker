# WorkBridge — Person 3 Module (FreelanceOS · PayPal Hackathon)

Project management, collaboration & deliverables module. Manages all work **after a contract is approved**.

## Modules in FreelanceOS
| Person | Module | Owns |
|---|---|---|
| 1 | Core Platform | PayPal payments on approved milestones |
| 2 | ContractFlow | Contracts / agreements |
| **3** | **WorkBridge (this repo)** | **Projects, tasks, milestones, collaboration, deliverables** |

## Tech stack
- **Frontend:** React (Vite) + React Router
- **Backend:** FastAPI + SQLAlchemy
- **Database:** SQLite (`backend/workbridge.db`)

## Run

### Backend (port 8000)
```bash
cd backend
pip install -r requirements.txt
python seed.py          # demo data (once)
python -m uvicorn main:app --port 8000
```

### Frontend (port 5173)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## Screens
1. **Project Dashboard** — all projects, progress, budget, filters, create
2. **Project Details** — overview, team, status, quick links
3. **Task Management** — kanban (To do / In progress / Done), assignees, priorities, due dates
4. **Milestone Tracking** — timeline, amounts, approve → payout hook
5. **Team Collaboration** — comment thread client ↔ freelancer
6. **Deliverables** — file upload, client review, approve / request revision (version bump)

## Integration endpoints (for teammates)

### Person 2 → WorkBridge (contract approved creates a project)
```http
POST /api/contracts/approved
{
  "contract_ref": "CTR-123",
  "project_name": "Website Development",
  "client_name": "Priya",
  "freelancer_name": "Arjun",
  "budget": 20000,
  "milestones": [{"title": "Design", "amount": 7000, "due_date": "2026-11-10"}]
}
```

### Person 1 ← WorkBridge (milestones ready for PayPal payout)
```http
GET /api/milestones/approved
```
Returns every approved milestone with amount + client/freelancer + contract ref → trigger PayPal payout.

## Demo flow (2 minutes)
1. Open dashboard → open **Website Development** project
2. **Tasks** → move a card Start → Done (watch progress + notifications)
3. **Milestones** → approve a milestone (toast: ready for PayPal payout)
4. **Collaboration** → post a message as client
5. **Deliverables** → upload a file → approve / request revision
6. Show the 🔔 bell — all activity appears there
