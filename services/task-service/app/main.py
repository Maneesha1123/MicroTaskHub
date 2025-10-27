from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status

from . import crud, schemas
from .clients import UserNotFoundError, UserServiceClient, get_user_service_client
from .config import get_settings
from .database import Base, engine, get_session
from .models import TaskStatus
from .security import require_auth

app = FastAPI(title="Task Service", version="1.0.0")
secured_router = APIRouter(dependencies=[Depends(require_auth)])


@app.on_event("startup")
def setup_database() -> None:
    Base.metadata.create_all(bind=engine)


def get_user_client_dependency():
    client = get_user_service_client()
    try:
        yield client
    finally:
        client.close()


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name}


@secured_router.post("/tasks", response_model=schemas.TaskReadWithAssignee, status_code=status.HTTP_201_CREATED, tags=["tasks"])
def create_task(
    payload: schemas.TaskCreate,
    session=Depends(get_session),
    user_client: UserServiceClient = Depends(get_user_client_dependency),
):
    try:
        assignee_raw = user_client.get_user(payload.assignee_id)
    except UserNotFoundError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assignee not found") from None
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User service unavailable") from exc

    task = crud.create_task(session, payload)
    task_read = schemas.TaskRead.from_orm(task)
    assignee = schemas.UserSummary(
        id=assignee_raw["id"],
        email=assignee_raw["email"],
        full_name=assignee_raw["full_name"],
        role=assignee_raw["role"],
    )
    return schemas.TaskReadWithAssignee(**task_read.model_dump(), assignee=assignee)


@secured_router.get("/tasks", response_model=list[schemas.TaskRead], tags=["tasks"])
def list_tasks(
    session=Depends(get_session),
    assignee_id: UUID | None = Query(default=None, description="Filter tasks by assignee"),
    status: TaskStatus | None = Query(default=None, description="Filter tasks by status"),
):
    tasks = crud.list_tasks(session, assignee_id=assignee_id, status=status)
    return [schemas.TaskRead.from_orm(task) for task in tasks]


@secured_router.get("/tasks/{task_id}", response_model=schemas.TaskReadWithAssignee, tags=["tasks"])
def get_task(
    task_id: UUID,
    include_assignee: bool = Query(True, description="Include assignee details"),
    session=Depends(get_session),
    user_client: UserServiceClient = Depends(get_user_client_dependency),
):
    task = crud.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task_read = schemas.TaskRead.from_orm(task)
    response = task_read.model_dump()
    if include_assignee:
        try:
            assignee_raw = user_client.get_user(task.assignee_id)
        except UserNotFoundError:
            raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail="Assignee lookup failed") from None
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User service unavailable") from exc
        assignee = schemas.UserSummary(
            id=assignee_raw["id"],
            email=assignee_raw["email"],
            full_name=assignee_raw["full_name"],
            role=assignee_raw["role"],
        )
        response["assignee"] = assignee
    else:
        response["assignee"] = None
    return schemas.TaskReadWithAssignee(**response)


@secured_router.patch("/tasks/{task_id}", response_model=schemas.TaskRead, tags=["tasks"])
def update_task(
    task_id: UUID,
    payload: schemas.TaskUpdate,
    session=Depends(get_session),
    user_client: UserServiceClient = Depends(get_user_client_dependency),
):
    task = crud.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return schemas.TaskRead.from_orm(task)

    if payload.assignee_id:
        try:
            user_client.get_user(payload.assignee_id)
        except UserNotFoundError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assignee not found") from None
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User service unavailable") from exc

    updated = crud.update_task(session, task, payload)
    return schemas.TaskRead.from_orm(updated)


@secured_router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
def delete_task(task_id: UUID, session=Depends(get_session)):
    task = crud.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status != TaskStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only tasks marked as done can be deleted",
        )

    crud.delete_task(session, task)
    return


app.include_router(secured_router)
