from datetime import datetime, timezone

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
