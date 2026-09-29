"""Per-visitor limits on planning, so one person can't use up the free searches for everyone.

Visitors are told apart by a hash of their IP address (the raw IP is never stored). Replanning
the same trip (same cities and dates, e.g. "Add to my trip") mostly reuses cached data, so only
new trips count toward the smaller limit.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlmodel import delete, select

from ..config import get_settings
from ..db import PlanRequest, get_session
from ..models.schemas import TripRequest

WINDOW = timedelta(hours=24)


class LimitReachedError(Exception):
    pass


def client_id(request: Request) -> str:
    # Vercel puts the visitor's address first in X-Forwarded-For (and overwrites any value the
    # visitor sent). Locally there's no proxy, so use the connection's address.
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    return hashlib.sha256(f"tripwise:{ip}".encode()).hexdigest()[:24]


def trip_key(req: TripRequest) -> str:
    return f"{req.origin.lower()}|{req.destination.lower()}|{req.start_date}|{req.end_date}"


def check_and_record(client: str, key: str) -> None:
    """Raises LimitReachedError if this request is over a limit; otherwise records it."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    with get_session() as s:
        s.exec(delete(PlanRequest).where(PlanRequest.at < now - 2 * WINDOW))
        recent = s.exec(select(PlanRequest.trip_key)
                        .where(PlanRequest.client == client, PlanRequest.at >= now - WINDOW)).all()
        trips = set(recent)
        if settings.visitor_daily_requests and len(recent) >= settings.visitor_daily_requests:
            raise LimitReachedError("You've made a lot of plans today. Please come back tomorrow.")
        if settings.visitor_daily_trips and key not in trips and len(trips) >= settings.visitor_daily_trips:
            raise LimitReachedError(
                f"You've planned {len(trips)} new trips today, the daily limit for this free site. "
                "You can still change the ones you've made; new trips open up again tomorrow."
            )
        s.add(PlanRequest(client=client, trip_key=key, at=now))
        s.commit()
