import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..config import get_settings
from ..db import JobRecord, TripRecord, get_session
from ..models.schemas import City, JobCreated, JobStatus, Plan, TripRequest
from ..providers.destination import demo_destinations
from ..providers.geocode import search_cities
from ..services.planner import run_job

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "ok": True,
        "demo_mode": settings.demo_mode,
        "demo_destinations": demo_destinations() if settings.demo_mode else [],
    }


@router.get("/cities", response_model=list[City])
def cities(q: str = ""):
    return search_cities(q)


@router.post("/trips", response_model=JobCreated, status_code=202)
def create_trip(req: TripRequest, background: BackgroundTasks):
    job_id = uuid.uuid4().hex
    with get_session() as s:
        s.add(JobRecord(id=job_id, request_json=req.model_dump_json()))
        s.commit()
    background.add_task(run_job, job_id, req)
    return JobCreated(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str):
    with get_session() as s:
        job = s.get(JobRecord, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return JobStatus(id=job.id, status=job.status, step=job.step, progress=job.progress,
                         trip_id=job.trip_id, error=job.error)


@router.get("/trips/{trip_id}", response_model=Plan)
def get_trip(trip_id: str):
    with get_session() as s:
        rec = s.get(TripRecord, trip_id)
        if not rec:
            raise HTTPException(404, "Trip not found")
        return Plan.model_validate_json(rec.plan_json)
