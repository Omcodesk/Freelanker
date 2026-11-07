from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    client_name = Column(String, default="")
    freelancer_name = Column(String, default="")
    budget = Column(Float, default=0)
    status = Column(String, default="active")  # active | completed | paused
    contract_ref = Column(String, default="")  # link to Person 2 ContractFlow
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="project", cascade="all, delete-orphan")
    deliverables = relationship("Deliverable", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="member")  # client | freelancer | member

    project = relationship("Project", back_populates="members")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    assignee = Column(String, default="")
    status = Column(String, default="todo")  # todo | in_progress | done
    priority = Column(String, default="medium")  # low | medium | high
    due_date = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    due_date = Column(String, default="")
    status = Column(String, default="pending")  # pending | in_progress | completed | approved
    amount = Column(Float, default=0)  # payment amount released on approval (Person 1 / PayPal)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="milestones")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    author = Column(String, nullable=False)
    role = Column(String, default="member")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="comments")


class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    filename = Column(String, default="")
    filepath = Column(String, default="")
    version = Column(Integer, default=1)
    status = Column(String, default="submitted")  # submitted | approved | revision_requested
    submitted_by = Column(String, default="")
    review_note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="deliverables")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, default=0)
    title = Column(String, nullable=False)
    body = Column(Text, default="")
    type = Column(String, default="info")  # info | task | milestone | deliverable
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
