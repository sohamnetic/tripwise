import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import trips

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Trip Planner API", lifespan=lifespan)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_origin_regex=_settings.cors_origin_regex or None,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(trips.router)


@app.get("/")
def root():
    # Render pings this; also a friendly answer if someone opens the API URL in a browser.
    return {"service": "Tripwise API", "health": "/api/health"}
