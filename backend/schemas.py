from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MemberIn(BaseModel):
    name: str
    role: str = "member"


class ProjectIn(BaseModel):
    name: str
    description: str = ""
    client_name: str = ""
    freelancer_name: str = ""
    budget: float = 0
    contract_ref: str = ""
    members: list[MemberIn] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    freelancer_name: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[str] = None
    contract_ref: Optional[str] = None


class TaskIn(BaseModel):
    title: str
    description: str = ""
    assignee: str = ""
    status: str = "todo"
    priority: str = "medium"
    due_date: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None


class MilestoneIn(BaseModel):
    title: str
    description: str = ""
    due_date: str = ""
    amount: float = 0


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None


class CommentIn(BaseModel):
    author: str
    role: str = "member"
    body: str


class DeliverableIn(BaseModel):
    title: str
    submitted_by: str = ""


class ReviewIn(BaseModel):
    status: str  # approved | revision_requested
    review_note: str = ""


class ContractApprovedIn(BaseModel):
    contract_ref: str = ""
    project_name: str
    description: str = ""
    client_name: str = ""
    freelancer_name: str = ""
    budget: float = 0
    milestones: list[MilestoneIn] = []
