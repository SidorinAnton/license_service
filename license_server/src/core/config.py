import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_database_url() -> str:
    in_docker = os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER") == "true"

    if in_docker:
        return os.getenv("DATABASE_URL")
    return "postgresql+psycopg://admin:admin@localhost:5432/license_db"


class Settings(BaseSettings):
    PROJECT_NAME: str = "License Server"
    DATABASE_URL: str = get_database_url()

    PRIVATE_KEY_PATH: str = "config/private_key.pem"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
