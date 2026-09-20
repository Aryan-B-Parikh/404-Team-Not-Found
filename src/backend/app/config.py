"""Application settings (pydantic-settings, loaded from .env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/portflow"
    db_echo: bool = False
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    llm_provider: str = "auto"
    bob_api_key: str = ""
    bob_team_id: str = ""
    bob_cli: str = "bob"
    bob_max_turns: int = 3
    bob_timeout_s: int = 240
    open_meteo_base: str = "https://api.open-meteo.com"
    reference_lat: float = 33.74
    reference_lon: float = -118.20
    sim_seed: int = 20240817
    sim_horizon_hours: int = 72
    feature_weather: bool = True
    feature_quality: bool = True
    feature_upload: bool = True
    feature_tidal: bool = True
    feature_incremental: bool = True
    feature_scenarios_ext: bool = True
    # Explicit planning assumption; deployment configuration may override it.
    under_keel_margin_ft: float = 1.0

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
