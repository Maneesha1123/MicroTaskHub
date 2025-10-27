from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas


class UserAlreadyExistsError(Exception):
    pass


def create_user(session: Session, payload: schemas.UserCreate) -> models.User:
    user = models.User(**payload.model_dump())
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:  # pragma: no cover - relies on DB constraint
        session.rollback()
        raise UserAlreadyExistsError from exc
    session.refresh(user)
    return user


def list_users(session: Session) -> Iterable[models.User]:
    result = session.execute(select(models.User).order_by(models.User.created_at.desc()))
    return (row[0] for row in result.all())


def get_user(session: Session, user_id) -> models.User | None:
    return session.get(models.User, user_id)


def update_user(session: Session, user: models.User, payload: schemas.UserUpdate) -> models.User:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise UserAlreadyExistsError from exc
    session.refresh(user)
    return user


def delete_user(session: Session, user: models.User) -> None:
    session.delete(user)
    session.commit()
