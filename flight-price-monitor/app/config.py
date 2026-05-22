from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field(default="Flight Price Monitor", alias="APP_NAME")
    database_url: str = Field(default="sqlite:///./flight_monitor.db", alias="DATABASE_URL")
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


settings = Settings()
