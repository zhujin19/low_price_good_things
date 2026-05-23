from pathlib import Path

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.paths import DEFAULT_SQLITE_DB, ENV_FILE, PROJECT_ROOT


DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_DB}"


def _normalize_sqlite_url(database_url: str) -> str:
    if database_url == "sqlite:///:memory:":
        return database_url
    if not database_url.startswith("sqlite:///") or database_url.startswith("sqlite:////"):
        return database_url

    sqlite_path = database_url.removeprefix("sqlite:///")
    if not sqlite_path or Path(sqlite_path).is_absolute():
        return database_url

    return f"sqlite:///{PROJECT_ROOT / sqlite_path}"


def _normalize_project_path(value: str | None) -> str | None:
    if not value:
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8")

    app_name: str = Field(default="Flight Price Monitor", alias="APP_NAME")
    database_url: str = Field(default=DEFAULT_DATABASE_URL, alias="DATABASE_URL")
    check_interval_minutes: int = Field(default=30, alias="CHECK_INTERVAL_MINUTES")
    target_dates_count: int = Field(default=4, alias="TARGET_DATES_COUNT")
    ctrip_api_url: str | None = Field(default=None, alias="CTRIP_API_URL")
    ctrip_api_key: str | None = Field(default=None, alias="CTRIP_API_KEY")
    ctrip_api_timeout: int = Field(default=15, alias="CTRIP_API_TIMEOUT")
    playwright_headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    playwright_timeout_ms: int = Field(default=30000, alias="PLAYWRIGHT_TIMEOUT_MS")
    playwright_executable_path: str | None = Field(
        default=None,
        alias="PLAYWRIGHT_EXECUTABLE_PATH",
    )
    ctrip_storage_state_path: str | None = Field(
        default=None,
        alias="CTRIP_STORAGE_STATE_PATH",
    )

    @model_validator(mode="after")
    def normalize_relative_paths(self):
        self.database_url = _normalize_sqlite_url(self.database_url)
        self.playwright_executable_path = _normalize_project_path(
            self.playwright_executable_path,
        )
        self.ctrip_storage_state_path = _normalize_project_path(
            self.ctrip_storage_state_path,
        )
        return self


settings = Settings()
