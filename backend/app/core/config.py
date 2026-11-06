from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_name: str = "FLIPBELT 40秒能装挑战 API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://flipbelt:change-me@localhost:5432/flipbelt_challenge"

    jwt_secret: str = "replace-with-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=720, gt=0)

    cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5188",
            "http://localhost:5188",
            "http://127.0.0.1:5189",
            "http://localhost:5189",
        ]
    )

    storage_backend: str = "local"
    local_upload_dir: Path = BASE_DIR.parent / "uploads"
    oss_region: str | None = None
    oss_endpoint: str | None = None
    oss_bucket: str | None = None
    oss_ram_role: str | None = None
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None
    oss_public_base_url: str | None = None
    oss_object_prefix: str = "flipbelt"

    seed_demo_data: bool = True
    demo_admin_username: str = "admin"
    demo_admin_password: str = "admin123"

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.app_env not in {"development", "test"} and (
            len(self.jwt_secret) < 32 or self.jwt_secret == "replace-with-a-long-random-secret"
        ):
            raise ValueError("正式环境必须通过环境变量配置独立的JWT_SECRET（至少32字符）")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
