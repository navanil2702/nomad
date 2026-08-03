"""Nomad API entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .routers import companion, expenses, journal, tools, trips
from .seed import seed_if_empty
from .store import get_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("nomad")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info(
        "Providers — ai:%s weather:%s maps:%s store:%s",
        "live" if settings.live_ai else "offline",
        "live" if settings.live_weather else "offline",
        "live" if settings.live_maps else "offline",
        "supabase" if settings.supabase_url else "json-file",
    )
    try:
        seed_if_empty()
    except Exception as exc:
        # A store that is unreachable at boot must not take the API down; the
        # health endpoint and the error surface in the UI are more useful.
        log.warning("Seeding skipped: %s", exc)
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "A travel companion that adapts a live itinerary to what is actually "
        "happening. Every external provider is optional."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips.router)
app.include_router(companion.router)
app.include_router(expenses.router)
app.include_router(journal.router)
app.include_router(tools.router)


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "providers": {
            "ai": "live" if settings.live_ai else "offline-engine",
            "weather": "live" if settings.live_weather else "offline-model",
            "maps": "live" if settings.live_maps else "offline-catalog",
            "database": "supabase" if settings.supabase_url else "json-file",
        },
    }


@app.post("/api/seed")
def seed() -> dict:
    """Create the demo trip if the store is empty.

    Idempotent. Exists because some serverless runtimes never run ASGI
    lifespan events, so the boot-time seed may not have fired.
    """
    created = seed_if_empty()
    return {"seeded": created, "trips": len(get_store().list())}
