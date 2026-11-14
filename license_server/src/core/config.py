from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "License Server"

    ENVIRONMENT: Literal["dev", "prod", "test"] = "dev"
    DEBUG: bool = False

    APP_NAME: str = "license_service"
    APP_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: PostgresDsn
    TEST_DATABASE_URL: PostgresDsn | None = None

    PRIVATE_KEY_PATH: Path = Path("config/private_key.pem")

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @field_validator("PRIVATE_KEY_PATH")
    @classmethod
    def _check_private_key_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Private key not found: {v}")
        return v

    @property
    def is_prod(self) -> bool:
        return self.ENVIRONMENT == "prod"

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT == "dev"


settings = Settings()
