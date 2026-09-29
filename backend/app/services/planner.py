"""Runs one planning job end to end and records progress for the frontend to poll."""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from ..config import get_settings
from ..db import JobRecord, TripRecord, get_session
from ..models.schemas import BudgetLine, City, Day, Link, Place, Plan, Summary, TripOverrides, TripRequest, Upgrade
from ..providers.base import ProviderError
from ..providers.destination import DemoDataMissingError, DestinationData, get_destination_data
from ..providers.geocode import UnknownCityError, haversine_km, resolve_city
from ..providers.transport import search_transport
from . import links
from .budget import BudgetDecision, BudgetTooLowError, budget_lines, plan_budget
from .itinerary import AiItinerary, plan_with_claude
from .scheduler import ScheduleInput, build_days
from .upgrades import candidate_upgrades, limit_per_kind

log = logging.getLogger(__name__)

# Shown in the UI while a job runs: (progress %, message)
STEPS = {
    "cities": (10, "Understanding your trip"),
    "search": (30, "Finding flights, trains, hotels & places"),
    "budget": (60, "Fitting everything into your budget"),
    "itinerary": (80, "Building your day-by-day plan"),
    "links": (95, "Adding booking links"),
}
MAX_TRIM_ROUNDS = 15
MAX_SWAPPED = 2  # an activity suggestion may replace at most this many free stops


def _update_job(job_id: str, **fields) -> None:
    with get_session() as s:
        job = s.get(JobRecord, job_id)
        for k, v in fields.items():
            setattr(job, k, v)
        s.add(job)
        s.commit()


async def _step(job_id: str, key: str) -> None:
    progress, msg = STEPS[key]
    _update_job(job_id, status="running", step=msg, progress=progress)
    settings = get_settings()
    if settings.demo_mode and settings.demo_step_delay:
        await asyncio.sleep(settings.demo_step_delay)


@dataclass
class Evaluation:
    decision: BudgetDecision
    days: list[Day]
    unscheduled: list[Place]
    lines: list[BudgetLine]
    total: int

    @property
    def visited(self) -> set[str]:
        return {s.ref_id for d in self.days for s in d.slots if s.kind == "place"}


def evaluate(req: TripRequest, outbound, inbound, data: DestinationData, dest: City, ai: AiItinerary | None) -> Evaluation:
    """Budget + day-by-day schedule for one request, using already-fetched data (no network).
    Used for the plan itself and to price each 'spend your savings' suggestion exactly."""
    decision = plan_budget(req, outbound, inbound, data.hotels, data.places)
    assignment = {day: list(ids) for day, ids in ai.assignment.items()} if ai else None
    if assignment is not None:  # places the traveller added must appear even if Claude left them out
        planned = {pid for ids in assignment.values() for pid in ids}
        for pid in req.must_include:
            if pid not in planned:
                day = min(range(2, req.nights + 1) or [1], key=lambda n: len(assignment.get(n, [])))
                assignment.setdefault(day, []).insert(0, pid)
    si = ScheduleInput(
        req=req, arrival=decision.outbound.arrive, departure=decision.inbound.depart,
        departure_mode=decision.inbound.mode, hotel=decision.hotel, places=data.places,
        restaurants=data.restaurants, place_tags=data.place_tags,
        activity_budget=decision.alloc["activities"], food_budget=decision.alloc["food"],
        city_lat=dest.lat, city_lng=dest.lng, city_name=dest.name,
        assignment=assignment, titles=ai.titles if ai else None, exclude=set(),
    )
    transport_cost = decision.outbound.total_price + decision.inbound.total_price
    # Rebuild without the costliest place until the whole trip fits (never drop the traveller's picks).
    for _ in range(MAX_TRIM_ROUNDS):
        days, unscheduled = build_days(si)
        lines = budget_lines(decision.alloc, days, transport_cost, decision.hotel.total_price)
        total = sum(l.spent for l in lines)
        droppable = [s for d in days for s in d.slots if s.kind == "place" and s.ref_id not in req.must_include]
        if total <= req.budget or not droppable:
            break
        h = decision.hotel
        costliest = max(droppable, key=lambda s: s.cost + 2 * haversine_km(h.lat, h.lng, s.lat, s.lng) * 20)
        si.exclude.add(costliest.ref_id)
    return Evaluation(decision, days, unscheduled, lines, total)


def with_overrides(req: TripRequest, o: TripOverrides) -> TripRequest:
    update = {"must_include": sorted(set(req.must_include) | set(o.must_include))}
    if o.hotel_id:
        update["hotel_id"] = o.hotel_id
    if o.transport_ids:
        update["transport_ids"] = o.transport_ids
    if o.treat_dinners:
        update["treat_dinners"] = True
    return req.model_copy(update=update)


def price_upgrades(req: TripRequest, base: Evaluation, candidates: list[Upgrade], outbound, inbound,
                   data: DestinationData, dest: City, ai: AiItinerary | None) -> list[Upgrade]:
    """Re-plan with each suggestion applied; keep those that take effect and stay within budget,
    with the exact change in total and any places they would push out."""
    by_id = {p.id: p for p in data.places}
    priced: list[Upgrade] = []
    for up in candidates:
        try:
            ev = evaluate(with_overrides(req, up.apply), outbound, inbound, data, dest, ai)
        except BudgetTooLowError:
            continue
        took_effect = (
            (not up.apply.hotel_id or ev.decision.hotel.id == up.apply.hotel_id)
            and (not up.apply.transport_ids or [ev.decision.outbound.id, ev.decision.inbound.id] == up.apply.transport_ids)
            and set(up.apply.must_include) <= ev.visited
        )
        extra = ev.total - base.total
        if not took_effect or ev.total > req.budget or extra <= 0:
            continue
        # Spending should add to the trip, not quietly take things away. The only exception is a
        # clearly-labelled trade of at most two stops (e.g. a full-day trip, or a later arrival).
        dropped = [by_id[i] for i in base.visited - ev.visited if i in by_id]
        if len(dropped) > MAX_SWAPPED:
            continue
        detail = up.detail + (f" You'd skip {' and '.join(d.name for d in dropped)} to make time." if dropped else "")
        priced.append(up.model_copy(update={"extra_cost": extra, "detail": detail}))
    return limit_per_kind(priced)


async def build_plan(req: TripRequest, job_id: str | None = None) -> Plan:
    settings = get_settings()

    async def step(key):
        if job_id:
            await _step(job_id, key)

    await step("cities")
    origin, dest = resolve_city(req.origin), resolve_city(req.destination)
    if origin.name == dest.name:
        raise ValueError("Origin and destination are the same city.")

    await step("search")
    (outbound, inbound), data = await asyncio.gather(
        search_transport(origin, dest, req.start_date, req.end_date, req.travellers),
        get_destination_data(dest, req.start_date, req.end_date, req.travellers),
    )
    checked_at = datetime.now(timezone.utc)

    await step("budget")
    decision = plan_budget(req, outbound, inbound, data.hotels, data.places)

    await step("itinerary")
    ai = await plan_with_claude(req, dest, decision.hotel, data.places, data.place_tags,
                                decision.outbound.arrive, decision.inbound.depart, decision.alloc["activities"])
    ev = evaluate(req, outbound, inbound, data, dest, ai)
    decision, days, unscheduled, lines, total = ev.decision, ev.days, ev.unscheduled, ev.lines, ev.total

    await step("links")
    warnings = list(decision.warnings)
    if total > req.budget:
        warnings.append(f"This plan is ₹{total - req.budget:,} over budget. Try the Budget style or fewer nights.")
    for opt in (decision.outbound, decision.inbound):
        if opt.mode != "flight" and opt.depart.date() < req.start_date:
            warnings.append(f"Your {opt.mode} leaves on {opt.depart:%d %b} to reach {dest.name} on the morning of day 1.")
    if settings.demo_mode:
        warnings.append("Demo mode: prices are sample values, not live quotes.")

    scheduled_ids = {s.ref_id for d in days for s in d.slots if s.kind == "place"}
    tips = (ai.tips if ai else []) + [
        "Prices marked 'estimate' can change. Confirm on the booking site before paying.",
    ]
    missing = [p.name for p in data.places if p.id in req.must_include and p.id not in scheduled_ids]
    if missing:
        warnings.append(f"Couldn't fit {', '.join(missing)} into your days. Try a longer trip.")
    if unscheduled:
        tips.append("Didn't fit this time: " + ", ".join(p.name for p in unscheduled[:4]) + ".")

    checklist = [
        Link(label=f"Outbound {decision.outbound.mode}: {decision.outbound.carrier} {decision.outbound.service}",
             url=decision.outbound.links[0].url),
        Link(label=f"Return {decision.inbound.mode}: {decision.inbound.carrier} {decision.inbound.service}",
             url=decision.inbound.links[0].url),
        Link(label=f"Stay: {decision.hotel.name} ({req.nights} nights)", url=decision.hotel.links[0].url),
    ]
    for p in data.places:
        bookable = [l for l in p.links if l.label != "Map"]
        if p.id in scheduled_ids and bookable:
            checklist.append(Link(label=f"Activity: {p.name}", url=bookable[0].url))

    return Plan(
        id=uuid.uuid4().hex[:10],
        request=req, origin=origin, destination=dest,
        created_at=datetime.now(timezone.utc), prices_checked_at=checked_at,
        data_mode="demo" if settings.demo_mode else "live",
        planned_by="ai" if ai else "rules",
        summary=Summary(
            budget=req.budget, total_cost=total, remaining=req.budget - total,
            within_budget=total <= req.budget, per_person=round(total / req.travellers),
            nights=req.nights, rooms=decision.hotel.rooms,
        ),
        budget=lines,
        outbound=decision.outbound, inbound=decision.inbound,
        transport_alternatives=decision.alternatives,
        hotel=decision.hotel, hotel_alternatives=decision.hotel_alternatives,
        days=days, places=data.places,
        packages=links.packages(dest, req.nights),
        checklist=checklist, warnings=warnings, tips=tips,
        upgrades=price_upgrades(
            req, ev,
            candidate_upgrades(req, req.budget - total, decision.hotel, data.hotels, data.places, data.restaurants, days,
                               decision.outbound, decision.inbound, outbound, inbound),
            outbound, inbound, data, dest, ai,
        ),
    )


USER_ERRORS = (BudgetTooLowError, DemoDataMissingError, UnknownCityError, ProviderError, ValueError)


async def run_job(job_id: str, req: TripRequest) -> None:
    try:
        plan = await build_plan(req, job_id)
        with get_session() as s:
            s.add(TripRecord(id=plan.id, plan_json=plan.model_dump_json()))
            s.commit()
        _update_job(job_id, status="done", step="Done", progress=100, trip_id=plan.id)
    except USER_ERRORS as e:
        _update_job(job_id, status="error", step="Failed", error=str(e))
    except Exception:
        log.exception("planning job %s failed", job_id)
        _update_job(job_id, status="error", step="Failed", error="Something went wrong while planning. Please try again.")
