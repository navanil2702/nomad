"""Runtime configuration.

Every external provider is optional. When a key is missing the matching
service falls back to its deterministic offline engine, so the whole product
runs end-to-end with zero configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "backend" / ".data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nomad API"
    environment: str = "development"

    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Optional provider credentials -------------------------------------
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    openweather_api_key: str | None = None
    google_maps_api_key: str | None = None

    supabase_url: str | None = None
    supabase_service_key: str | None = None

    # Where the JSON-file store keeps trips when Supabase is not configured.
    data_dir: Path = DATA_DIR

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def live_ai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def live_weather(self) -> bool:
        return bool(self.openweather_api_key)

    @property
    def live_maps(self) -> bool:
        return bool(self.google_maps_api_key)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
