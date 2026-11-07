import os
import uuid
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
import schemas

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="WorkBridge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def notify(db, project_id, title, body, type="info"):
    db.add(models.Notification(project_id=project_id, title=title, body=body, type=type))
    db.commit()


def project_progress(p):
    tasks = p.tasks
    done = sum(1 for t in tasks if t.status == "done")
    total = len(tasks)
    return {
        "tasks_total": total,
        "tasks_done": done,
        "progress": round(done / total * 100) if total else 0,
    }


def serialize_project(p, with_details=False):
    data = {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "client_name": p.client_name,
        "freelancer_name": p.freelancer_name,
        "budget": p.budget,
        "status": p.status,
        "contract_ref": p.contract_ref,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        **project_progress(p),
        "members": [{"id": m.id, "name": m.name, "role": m.role} for m in p.members],
        "milestones_total": len(p.milestones),
        "milestones_approved": sum(1 for m in p.milestones if m.status == "approved"),
    }
    if with_details:
        data["tasks"] = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "assignee": t.assignee,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date,
            }
            for t in p.tasks
        ]
        data["milestones"] = [
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "due_date": m.due_date,
                "status": m.status,
                "amount": m.amount,
            }
            for m in p.milestones
        ]
        data["comments"] = [
            {
                "id": c.id,
                "author": c.author,
                "role": c.role,
                "body": c.body,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in sorted(p.comments, key=lambda x: x.created_at or datetime.min)
        ]
        data["deliverables"] = [
            {
                "id": d.id,
                "title": d.title,
                "filename": d.filename,
                "filepath": d.filepath,
                "version": d.version,
                "status": d.status,
                "submitted_by": d.submitted_by,
                "review_note": d.review_note,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in sorted(p.deliverables, key=lambda x: x.created_at or datetime.min)
        ]
    return data


def get_project_or_404(db, project_id):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


# ---------- Projects ----------

@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.created_at.desc()).all()
    return [serialize_project(p) for p in projects]


@app.post("/api/projects", status_code=201)
def create_project(body: schemas.ProjectIn, db: Session = Depends(get_db)):
    p = models.Project(
        name=body.name,
        description=body.description,
        client_name=body.client_name,
        freelancer_name=body.freelancer_name,
        budget=body.budget,
        contract_ref=body.contract_ref,
    )
    db.add(p)
    db.flush()
    for m in body.members:
        db.add(models.ProjectMember(project_id=p.id, name=m.name, role=m.role))
    if not body.members and body.freelancer_name:
        db.add(models.ProjectMember(project_id=p.id, name=body.freelancer_name, role="freelancer"))
    if body.client_name:
        db.add(models.ProjectMember(project_id=p.id, name=body.client_name, role="client"))
    db.commit()
    db.refresh(p)
    notify(db, p.id, "Project created", f'"{p.name}" is now active', "info")
    return serialize_project(p, with_details=True)


@app.get("/api/projects/{project_id}")
def read_project(project_id: int, db: Session = Depends(get_db)):
    return serialize_project(get_project_or_404(db, project_id), with_details=True)


@app.put("/api/projects/{project_id}")
def update_project(project_id: int, body: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    p = get_project_or_404(db, project_id)
    for k, v in body.dict(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return serialize_project(p, with_details=True)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    p = get_project_or_404(db, project_id)
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---------- Members ----------

@app.post("/api/projects/{project_id}/members", status_code=201)
def add_member(project_id: int, body: schemas.MemberIn, db: Session = Depends(get_db)):
    p = get_project_or_404(db, project_id)
    m = models.ProjectMember(project_id=p.id, name=body.name, role=body.role)
    db.add(m)
    db.commit()
    return {"id": m.id, "name": m.name, "role": m.role}


@app.delete("/api/projects/{project_id}/members/{member_id}")
def remove_member(project_id: int, member_id: int, db: Session = Depends(get_db)):
    m = db.query(models.ProjectMember).filter(
        models.ProjectMember.id == member_id,
        models.ProjectMember.project_id == project_id,
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(m)
    db.commit()
    return {"ok": True}


# ---------- Tasks ----------

@app.post("/api/projects/{project_id}/tasks", status_code=201)
def create_task(project_id: int, body: schemas.TaskIn, db: Session = Depends(get_db)):
    p = get_project_or_404(db, project_id)
    t = models.Task(project_id=p.id, **body.dict())
    db.add(t)
    db.commit()
    notify(db, p.id, "Task added", f'"{t.title}" assigned to {t.assignee or "unassigned"}', "task")
    return {"id": t.id}


@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, body: schemas.TaskUpdate, db: Session = Depends(get_db)):
    t = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    old_status = t.status
    for k, v in body.dict(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    if old_status != "done" and t.status == "done":
        notify(db, t.project_id, "Task completed", f'"{t.title}" marked done', "task")
    return {"ok": True, "status": t.status}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ---------- Milestones ----------

@app.post("/api/projects/{project_id}/milestones", status_code=201)
def create_milestone(project_id: int, body: schemas.MilestoneIn, db: Session = Depends(get_db)):
    p = get_project_or_404(db, project_id)
    m = models.Milestone(project_id=p.id, **body.dict())
    db.add(m)
    db.commit()
    notify(db, p.id, "Milestone added", f'"{m.title}" · ₹{m.amount:,.0f}', "milestone")
    return {"id": m.id}


@app.put("/api/milestones/{milestone_id}")
def update_milestone(milestone_id: int, body: schemas.MilestoneUpdate, db: Session = Depends(get_db)):
    m = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    old_status = m.status
    for k, v in body.dict(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    if old_status != "approved" and m.status == "approved":
        notify(
            db, m.project_id, "Milestone approved",
            f'"{m.title}" approved — ₹{m.amount:,.0f} ready for PayPal payout (Person 1)',
            "milestone",
        )
    return {"ok": True, "status": m.status}


@app.delete("/api/milestones/{milestone_id}")
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    m = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    db.delete(m)
    db.commit()
    return {"ok": True}


# ---------- Comments / Collaboration ----------

@app.post("/api/projects/{project_id}/comments", status_code=201)
def add_comment(project_id: int, body: schemas.CommentIn, db: Session = Depends(get_db)):
    p = get_project_or_404(db, project_id)
    c = models.Comment(project_id=p.id, **body.dict())
    db.add(c)
    db.commit()
    notify(db, p.id, f"New message from {c.author}", c.body[:120], "info")
    return {"id": c.id}


# ---------- Deliverables ----------

@app.post("/api/projects/{project_id}/deliverables", status_code=201)
async def upload_deliverable(
    project_id: int,
    title: str = Form(...),
    submitted_by: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    p = get_project_or_404(db, project_id)
    ext = os.path.splitext(file.filename or "")[1]
    stored = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, stored)
    with open(path, "wb") as f:
        f.write(await file.read())
    d = models.Deliverable(
        project_id=p.id,
        title=title,
        filename=file.filename or stored,
        filepath=f"/uploads/{stored}",
        submitted_by=submitted_by,
    )
    db.add(d)
    db.commit()
    notify(db, p.id, "Deliverable submitted", f'"{title}" awaiting client review', "deliverable")
    return {"id": d.id, "filepath": d.filepath}


@app.put("/api/deliverables/{deliverable_id}/review")
def review_deliverable(deliverable_id: int, body: schemas.ReviewIn, db: Session = Depends(get_db)):
    d = db.query(models.Deliverable).filter(models.Deliverable.id == deliverable_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    d.status = body.status
    d.review_note = body.review_note
    if body.status == "revision_requested":
        d.version += 1
    db.commit()
    label = "approved" if body.status == "approved" else "revision requested"
    notify(db, d.project_id, f"Deliverable {label}", f'"{d.title}" — {body.review_note or "no note"}', "deliverable")
    return {"ok": True, "status": d.status, "version": d.version}


# ---------- Notifications ----------

@app.get("/api/notifications")
def list_notifications(limit: int = 20, db: Session = Depends(get_db)):
    rows = db.query(models.Notification).order_by(models.Notification.created_at.desc()).limit(limit).all()
    return [
        {
            "id": n.id,
            "project_id": n.project_id,
            "title": n.title,
            "body": n.body,
            "type": n.type,
            "is_read": bool(n.is_read),
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@app.post("/api/notifications/read")
def mark_all_read(db: Session = Depends(get_db)):
    db.query(models.Notification).filter(models.Notification.is_read == 0).update({"is_read": 1})
    db.commit()
    return {"ok": True}


# ---------- Integration hooks ----------

@app.post("/api/contracts/approved", status_code=201)
def contract_approved(body: schemas.ContractApprovedIn, db: Session = Depends(get_db)):
    """Person 2 (ContractFlow) calls this when a contract is approved → auto-create project."""
    p = models.Project(
        name=body.project_name,
        description=body.description,
        client_name=body.client_name,
        freelancer_name=body.freelancer_name,
        budget=body.budget,
        contract_ref=body.contract_ref or f"CTR-{uuid.uuid4().hex[:8].upper()}",
    )
    db.add(p)
    db.flush()
    if body.freelancer_name:
        db.add(models.ProjectMember(project_id=p.id, name=body.freelancer_name, role="freelancer"))
    if body.client_name:
        db.add(models.ProjectMember(project_id=p.id, name=body.client_name, role="client"))
    for m in body.milestones:
        db.add(models.Milestone(project_id=p.id, **m.dict()))
    db.commit()
    db.refresh(p)
    notify(db, p.id, "Contract approved", f'Project "{p.name}" created from contract {p.contract_ref}', "info")
    return serialize_project(p, with_details=True)


@app.get("/api/milestones/approved")
def approved_milestones(db: Session = Depends(get_db)):
    """Person 1 (Core Platform) polls this for milestones to pay out via PayPal."""
    rows = (
        db.query(models.Milestone, models.Project)
        .join(models.Project, models.Milestone.project_id == models.Project.id)
        .filter(models.Milestone.status == "approved")
        .all()
    )
    return [
        {
            "milestone_id": m.id,
            "title": m.title,
            "amount": m.amount,
            "project_id": p.id,
            "project_name": p.name,
            "client_name": p.client_name,
            "freelancer_name": p.freelancer_name,
            "contract_ref": p.contract_ref,
        }
        for m, p in rows
    ]


@app.get("/api/health")
def health():
    return {"status": "ok", "module": "WorkBridge"}
