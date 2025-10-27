from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "user-service"
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/microtaskhub"
    log_level: str = "info"
    auth_token: str | None = None
    task_service_base_url: str = "http://task-service:8000"
    task_service_timeout: float = 3.0
    task_service_auth_token: str | None = None

    class Config:
        env_prefix = "USER_SERVICE_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
