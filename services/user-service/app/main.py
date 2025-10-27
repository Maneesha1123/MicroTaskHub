from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status

from . import crud, schemas
from .config import get_settings
from .database import Base, engine, get_session
from .security import require_auth
from .task_client import TaskServiceClient, get_task_service_client

app = FastAPI(title="User Service", version="1.0.0")
secured_router = APIRouter(dependencies=[Depends(require_auth)])


def get_task_client_dependency():
    client = get_task_service_client()
    try:
        yield client
    finally:
        client.close()


@app.on_event("startup")
def setup_database() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name}


@secured_router.post("/users", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED, tags=["users"])
def create_user(payload: schemas.UserCreate, session=Depends(get_session)):
    try:
        user = crud.create_user(session, payload)
    except crud.UserAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from None
    return user


@secured_router.get("/users", response_model=list[schemas.UserRead], tags=["users"])
def list_users(session=Depends(get_session)):
    return list(crud.list_users(session))


@secured_router.get("/users/{user_id}", response_model=schemas.UserRead, tags=["users"])
def get_user(user_id: UUID, session=Depends(get_session)):
    user = crud.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@secured_router.patch("/users/{user_id}", response_model=schemas.UserRead, tags=["users"])
def update_user(user_id: UUID, payload: schemas.UserUpdate, session=Depends(get_session)):
    user = crud.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not payload.model_dump(exclude_unset=True):
        return user

    try:
        updated = crud.update_user(session, user, payload)
    except crud.UserAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from None
    return updated


@secured_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["users"])
def delete_user(
    user_id: UUID,
    session=Depends(get_session),
    task_client: TaskServiceClient = Depends(get_task_client_dependency),
):
    user = crud.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        has_active_tasks = task_client.user_has_in_progress_tasks(user.id)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify user tasks",
        ) from exc
    if has_active_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has in-progress tasks and cannot be deleted",
        )

    crud.delete_user(session, user)
    return


app.include_router(secured_router)
