import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 - register all models with Base metadata
from app.api.eligibility import router as eligibility_router
from app.api.fussballde_imports import router as fussballde_import_router
from app.api.fussballde_matchplan_imports import router as fussballde_matchplan_import_router
from app.api.fussballde_matchplans import router as fussballde_matchplan_router
from app.api.local_match_lineups import router as local_match_lineup_router
from app.api.matches import router as matches_router
from app.api.teams import router as teams_router
from app.database import Base, engine
from app.services.daily_matchplan_sync import run_daily_matchplan_sync
from app.settings import MatchplanSyncSettings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create schema and, when enabled, run the bounded daily schedule synchronization."""
    Base.metadata.create_all(bind=engine)
    settings = MatchplanSyncSettings.from_environment()
    stop_event = asyncio.Event()
    task = None
    if settings.enabled:
        task = asyncio.create_task(run_daily_matchplan_sync(stop_event, settings=settings))
    try:
        yield
    finally:
        stop_event.set()
        if task is not None:
            await task


app = FastAPI(title="Festspielmonitor API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(fussballde_import_router)
app.include_router(fussballde_matchplan_router)
app.include_router(fussballde_matchplan_import_router)
app.include_router(local_match_lineup_router)
app.include_router(matches_router)
app.include_router(eligibility_router)
app.include_router(teams_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return a small liveness response for local development and deployment checks."""
    return {"status": "ok"}
