from datetime import date, datetime, timezone

from sqlmodel import Field, Session, SQLModel, create_engine

from .config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TripRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    plan_json: str
    created_at: datetime = Field(default_factory=utcnow)


class JobRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    request_json: str
    status: str = "queued"
    step: str = "Queued"
    progress: int = 0
    trip_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class CacheEntry(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
    expires_at: datetime


class ApiCall(SQLModel, table=True):
    """One paid search we made, for the daily cap."""
    id: int | None = Field(default=None, primary_key=True)
    provider: str = Field(index=True)
    at: datetime = Field(default_factory=utcnow, index=True)


class RouteFare(SQLModel, table=True):
    """The cheapest fare a live search found for one route on one travel date, so later
    estimates for that route can use real prices. One row per route and date."""
    id: str = Field(primary_key=True)  # "DEL-GOI-2026-12-10"
    route: str = Field(index=True)  # "DEL-GOI"
    travel_date: date
    cheapest: int  # per person, among the flights with the fewest stops
    duration_min: int
    seen_at: datetime = Field(default_factory=utcnow, index=True)


class PlanRequest(SQLModel, table=True):
    """One planning request, for per-visitor limits. `client` is a hash, never the raw IP."""
    id: int | None = Field(default=None, primary_key=True)
    client: str = Field(index=True)
    trip_key: str
    at: datetime = Field(default_factory=utcnow, index=True)


_settings = get_settings()
_url = _settings.sqlalchemy_url
engine = create_engine(
    _url,
    connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {},
    # Neon closes idle connections when it scales to zero; check before reuse.
    pool_pre_ping=not _url.startswith("sqlite"),
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
