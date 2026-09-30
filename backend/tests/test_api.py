"""The HTTP API end to end (demo data), in both job modes."""

import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

TRIP = {"origin": "Kolkata", "destination": "Goa", "start_date": "2026-11-12", "end_date": "2026-11-16",
        "travellers": 2, "budget": 60000, "style": "balanced", "interests": ["beaches"], "transport": "any"}


@pytest.fixture
def client():
    with TestClient(app) as c:  # runs the lifespan, which creates the tables
        yield c


def _wait_for(client, job_id, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


@pytest.mark.parametrize("inline", [False, True])
def test_plan_a_trip_over_http(client, monkeypatch, inline):
    monkeypatch.setattr(get_settings(), "inline_jobs", inline)
    r = client.post("/api/trips", json=TRIP)
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    if inline:  # serverless mode: the plan is ready as soon as the POST returns
        assert client.get(f"/api/jobs/{job_id}").json()["status"] == "done"
    job = _wait_for(client, job_id)
    assert job["status"] == "done", job
    plan = client.get(f"/api/trips/{job['trip_id']}").json()
    assert plan["request"]["destination"] == "Goa" and plan["days"]


def test_bad_request_is_rejected(client):
    assert client.post("/api/trips", json={**TRIP, "end_date": "2026-11-10"}).status_code == 422


def test_unknown_trip_404(client):
    assert client.get("/api/trips/nope").status_code == 404


def test_inline_jobs_turn_on_under_vercel(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    assert Settings().inline_jobs is False
    monkeypatch.setenv("VERCEL", "1")
    assert Settings().inline_jobs is True


def test_cors_only_allows_configured_sites():
    s = Settings(cors_origins="https://tripwise.vercel.app/")
    assert s.cors_origin_list == ["https://tripwise.vercel.app"]


def test_all_cities_for_the_search_box(client):
    r = client.get("/api/cities/all")
    assert r.status_code == 200 and "max-age" in r.headers["cache-control"]
    cities = r.json()
    assert len(cities) >= 100
    kolkata = next(c for c in cities if c["name"] == "Kolkata")
    assert kolkata["state"] == "West Bengal" and "calcutta" in kolkata["aliases"]
