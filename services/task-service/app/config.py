from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "task-service"
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/microtaskhub"
    user_service_base_url: str = "http://user-service:8000"
    user_service_timeout: float = 3.0
    auth_token: str | None = None
    user_service_auth_token: str | None = None

    class Config:
        env_prefix = "TASK_SERVICE_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
