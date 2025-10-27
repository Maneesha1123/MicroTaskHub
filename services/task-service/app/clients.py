from __future__ import annotations

from uuid import UUID

import httpx

from .config import get_settings


class UserNotFoundError(Exception):
    pass


class UserServiceClient:
    def __init__(self, base_url: str, timeout: float = 3.0, auth_token: str | None = None) -> None:
        headers: dict[str, str] = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    def get_user(self, user_id: UUID) -> dict:
        response = self._client.get(f"/users/{user_id}")
        if response.status_code == 404:
            raise UserNotFoundError("Assignee does not exist")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()


def get_user_service_client() -> UserServiceClient:
    settings = get_settings()
    return UserServiceClient(
        base_url=settings.user_service_base_url,
        timeout=settings.user_service_timeout,
        auth_token=settings.user_service_auth_token or settings.auth_token,
    )
