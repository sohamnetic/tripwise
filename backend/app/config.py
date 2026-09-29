import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # When true, every provider reads from backend/fixtures and no paid API is called.
    demo_mode: bool = True
    # Pause between progress steps in demo mode so the loading screen is visible.
    demo_step_delay: float = 0.6

    serpapi_key: str = ""
    # Fresh SerpApi searches allowed per day (UTC), so one busy day can't use up the month's
    # 250 free searches. Past it, cached data and estimates are used. 0 = no daily cap.
    serpapi_daily_limit: int = 8
    # Per visitor, per 24 hours: new trips (a new origin/destination/dates) and all planning
    # requests (replans of the same trip mostly reuse cached data). 0 = no limit.
    visitor_daily_trips: int = 5
    visitor_daily_requests: int = 40
    # https://www.geoapify.com (free: 3,000 credits/day, no card). Restaurants and beaches from
    # OpenStreetMap when Google results aren't available.
    geoapify_key: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"

    # Local SQLite by default; in production a Postgres URL (e.g. from Neon).
    database_url: str = f"sqlite:///{BACKEND_DIR / 'tripplanner.db'}"
    # Serverless hosts (Vercel) may stop work that continues after the response, so there we
    # plan the trip before answering. Vercel sets VERCEL=1, which turns this on automatically.
    inline_jobs: bool = Field(default_factory=lambda: bool(os.environ.get("VERCEL")))
    # Which websites may call this API: comma-separated origins, plus an optional regex
    # (e.g. for Vercel preview deployments).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_origin_regex: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """Neon/Render give 'postgres://' or 'postgresql://' URLs; SQLAlchemy needs the driver named."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
