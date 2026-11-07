"""Seed WorkBridge with demo data (run once: python seed.py)"""
from database import Base, engine, SessionLocal
import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(models.Project).count() == 0:
    p = models.Project(
        name="Website Development — ₹20,000",
        description="Client hired a freelancer to develop a website. Manage tasks, milestones and deliverables after contract approval.",
        client_name="Priya Sharma",
        freelancer_name="Arjun Kumar",
        budget=20000,
        contract_ref="CTR-DEMO-0001",
        status="active",
    )
    db.add(p)
    db.flush()

    db.add_all([
        models.ProjectMember(project_id=p.id, name="Priya Sharma", role="client"),
        models.ProjectMember(project_id=p.id, name="Arjun Kumar", role="freelancer"),
        models.ProjectMember(project_id=p.id, name="Meena Iyer", role="member"),
    ])

    db.add_all([
        models.Task(project_id=p.id, title="Design homepage mockup", assignee="Arjun Kumar", status="done", priority="high", due_date="2026-11-10"),
        models.Task(project_id=p.id, title="Build frontend pages", assignee="Arjun Kumar", status="in_progress", priority="high", due_date="2026-11-14"),
        models.Task(project_id=p.id, title="Setup backend API", assignee="Meena Iyer", status="in_progress", priority="medium", due_date="2026-11-16"),
        models.Task(project_id=p.id, title="Deploy to production", assignee="Arjun Kumar", status="todo", priority="medium", due_date="2026-11-20"),
        models.Task(project_id=p.id, title="Client feedback round", assignee="Priya Sharma", status="todo", priority="low", due_date="2026-11-22"),
    ])

    db.add_all([
        models.Milestone(project_id=p.id, title="Design completion", description="Homepage + inner page designs approved", due_date="2026-11-10", status="approved", amount=7000),
        models.Milestone(project_id=p.id, title="Website completion", description="All pages built and tested", due_date="2026-11-18", status="in_progress", amount=8000),
        models.Milestone(project_id=p.id, title="Launch & handover", description="Deployed, docs shared, final payment", due_date="2026-11-22", status="pending", amount=5000),
    ])

    db.add_all([
        models.Comment(project_id=p.id, author="Priya Sharma", role="client", body="Homepage design looks great! Please keep the same style for inner pages."),
        models.Comment(project_id=p.id, author="Arjun Kumar", role="freelancer", body="Thanks! Frontend is 60% done, will share a preview by tomorrow."),
    ])

    db.add_all([
        models.Deliverable(project_id=p.id, title="Homepage design v1", filename="homepage-v1.png", filepath="", version=1, status="approved", submitted_by="Arjun Kumar", review_note="Approved by client"),
        models.Deliverable(project_id=p.id, title="Website build preview", filename="preview.zip", filepath="", version=2, status="submitted", submitted_by="Arjun Kumar"),
    ])

    db.add_all([
        models.Notification(project_id=p.id, title="Welcome to WorkBridge", body="Demo project loaded — manage tasks, milestones & deliverables here.", type="info"),
        models.Notification(project_id=p.id, title="Milestone approved", body='"Design completion" approved — ₹7,000 ready for PayPal payout (Person 1)', type="milestone"),
    ])

    db.commit()
    print("Seeded demo project.")
else:
    print("Database already has data — skipped seeding.")

db.close()
