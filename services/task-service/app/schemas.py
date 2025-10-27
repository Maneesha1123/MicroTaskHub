from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .models import TaskStatus


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    due_date: date | None = None
    status: TaskStatus = TaskStatus.TODO


class TaskCreate(TaskBase):
    assignee_id: UUID


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    due_date: date | None = None
    status: TaskStatus | None = None
    assignee_id: UUID | None = None


class TaskRead(TaskBase):
    id: UUID
    assignee_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str


class TaskReadWithAssignee(TaskRead):
    assignee: UserSummary | None = None
