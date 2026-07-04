from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Smart Resume Platform API"
    env: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    database_url: str = Field(
        default="mysql+pymysql://resume_user:resume_password@127.0.0.1:3306/smart_resume_platform?charset=utf8mb4"
    )
    db_connect_timeout: int = 60
    db_read_timeout: int = 60
    db_write_timeout: int = 60
    db_pool_recycle: int = 1800
    db_ssl: bool = True

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    max_pdf_size_mb: int = 10
    upload_dir: str = "uploads/pdf"
    generated_latex_dir: str = "generated/latex"

    llm_mock: bool = True
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def backend_root(self) -> Path:
        return BACKEND_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
