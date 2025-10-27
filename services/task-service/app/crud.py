from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


def create_task(session: Session, payload: schemas.TaskCreate) -> models.Task:
    task = models.Task(**payload.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def list_tasks(
    session: Session,
    *,
    assignee_id: UUID | None = None,
    status: models.TaskStatus | None = None,
) -> Iterable[models.Task]:
    stmt = select(models.Task)
    if assignee_id:
        stmt = stmt.where(models.Task.assignee_id == assignee_id)
    if status:
        stmt = stmt.where(models.Task.status == status)
    stmt = stmt.order_by(models.Task.created_at.desc())
    result = session.execute(stmt)
    return (row[0] for row in result.all())


def get_task(session: Session, task_id: UUID) -> models.Task | None:
    return session.get(models.Task, task_id)


def update_task(session: Session, task: models.Task, payload: schemas.TaskUpdate) -> models.Task:
    update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, task: models.Task) -> None:
    session.delete(task)
    session.commit()
