import asyncio
from datetime import date

import pytest

from app.models.schemas import TripRequest
from app.services.planner import build_plan

BASE = dict(origin="Kolkata", destination="Goa", start_date=date(2026, 10, 29), end_date=date(2026, 11, 2),
            travellers=2, interests=["beaches", "food"])


def plan(**kw):
    return asyncio.run(build_plan(TripRequest(**{**BASE, **kw})))


def apply(p, upgrade):
    """What the frontend does when you tap 'Add to my trip'."""
    req = p.request.model_dump()
    o = upgrade.apply
    if o.hotel_id:
        req["hotel_id"] = o.hotel_id
    if o.transport_ids:
        req["transport_ids"] = o.transport_ids
    if o.treat_dinners:
        req["treat_dinners"] = True
    req["must_include"] = sorted(set(req["must_include"]) | set(o.must_include))
    return asyncio.run(build_plan(TripRequest(**req)))


@pytest.mark.parametrize("style,budget", [("budget", 30000), ("balanced", 60000), ("comfort", 150000)])
def test_suggestions_fit_in_the_leftover(style, budget):
    p = plan(style=style, budget=budget)
    assert p.summary.remaining > 0
    assert p.upgrades, "a plan with money left should offer ways to spend it"
    for u in p.upgrades:
        assert 0 < u.extra_cost <= p.summary.remaining


@pytest.mark.parametrize("style,budget", [("budget", 30000), ("balanced", 60000), ("comfort", 150000)])
def test_suggestions_only_add_or_make_a_clear_trade(style, budget):
    p = plan(style=style, budget=budget)
    before = {s.ref_id for d in p.days for s in d.slots if s.kind == "place"}
    for u in p.upgrades:
        q = apply(p, u)
        after = {s.ref_id for d in q.days for s in d.slots if s.kind == "place"}
        dropped = before - after
        assert len(dropped) <= 2, (u.title, dropped)
        assert not dropped or "You'd skip" in u.detail, (u.title, dropped)


@pytest.mark.parametrize("style,budget", [("budget", 30000), ("balanced", 60000), ("comfort", 150000)])
def test_every_suggestion_can_be_applied_and_stays_in_budget(style, budget):
    p = plan(style=style, budget=budget)
    assert len(p.upgrades) >= 2
    for u in p.upgrades:
        q = apply(p, u)
        assert q.summary.within_budget, (u.title, q.summary)
        if u.kind == "hotel":
            assert q.hotel.id == u.apply.hotel_id
        if u.kind == "activity":
            visited = {s.ref_id for d in q.days for s in d.slots if s.kind == "place"}
            assert set(u.apply.must_include) <= visited, u.title
        if u.kind == "transport":
            assert [q.outbound.id, q.inbound.id] == u.apply.transport_ids
        if u.kind == "dining":
            food = lambda x: next(l.spent for l in x.budget if l.key == "food")
            assert q.request.treat_dinners and food(q) > food(p)
        # the suggested extra cost is exact: it's what applying it really changes
        assert q.summary.total_cost - p.summary.total_cost == u.extra_cost, u.title


def test_train_trip_offers_ac_class_and_flight():
    p = plan(style="budget", budget=60000)
    assert p.outbound.mode == "train"
    titles = " | ".join(u.title for u in p.upgrades)
    assert "AC 3-tier" in titles
    assert "flight" in titles


def test_no_suggestions_when_nothing_is_left():
    p = plan(style="budget", budget=22000)
    assert all(u.extra_cost <= p.summary.remaining for u in p.upgrades)
