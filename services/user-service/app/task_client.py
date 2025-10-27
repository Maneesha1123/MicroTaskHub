from __future__ import annotations

from uuid import UUID

import httpx

from .config import get_settings


class TaskServiceClient:
    def __init__(self, base_url: str, timeout: float = 3.0, auth_token: str | None = None) -> None:
        headers: dict[str, str] = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        self._client = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    def user_has_in_progress_tasks(self, user_id: UUID) -> bool:
        response = self._client.get(
            "/tasks",
            params={"assignee_id": str(user_id), "status": "in_progress"},
        )
        response.raise_for_status()
        payload = response.json()
        return bool(payload)

    def close(self) -> None:
        self._client.close()


def get_task_service_client() -> TaskServiceClient:
    settings = get_settings()
    return TaskServiceClient(
        base_url=settings.task_service_base_url,
        timeout=settings.task_service_timeout,
        auth_token=settings.task_service_auth_token or settings.auth_token,
    )
