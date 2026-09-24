from pathlib import Path
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Escapadas en Tren"
    DEBUG: bool = False

    # Providers
    ACCOMMODATION_PROVIDER: str = "mock"  # mock | rapidapi | scraper
    RAPIDAPI_KEY: str = ""
    RAPIDAPI_HOST: str = "booking-com15.p.rapidapi.com"
    RAPIDAPI_PRICE_CACHE_HOURS: int = 3  # Live prices are reused this long to save API quota

    # Paths & storage
    DATA_DIR: Path = BASE_DIR / "data"
    SEED_ROUTES_PATH: Path = BASE_DIR / "data" / "seed_routes.json"
    GTFS_PATH: Optional[Path] = None  # GTFS feed (.zip or folder); falls back to the seed network if unset
    SQLITE_CACHE_DB: Path = BASE_DIR / "data" / "cache.db"
    CACHE_TTL_HOURS: int = 24

    # Routing defaults
    DEFAULT_MAX_TRAVEL_HOURS: float = 2.5
    DEFAULT_MIN_TRANSFER_MARGIN_MINUTES: int = 15
    DEFAULT_MAX_TRANSFER_MARGIN_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATA_DIR", "SEED_ROUTES_PATH", "GTFS_PATH", "SQLITE_CACHE_DB", mode="after")
    @classmethod
    def _resolve_relative_to_project(cls, value: Optional[Path]) -> Optional[Path]:
        """Relative paths from .env are resolved against the project root, not the current directory."""
        if value is None or value.is_absolute():
            return value
        return BASE_DIR / value

    @field_validator("GTFS_PATH", mode="before")
    @classmethod
    def _empty_gtfs_path_is_none(cls, value):
        return value or None


settings = Settings()
