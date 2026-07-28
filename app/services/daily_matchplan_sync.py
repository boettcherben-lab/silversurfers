"""Opt-in daily runner for the bounded FUSSBALL.DE match-plan synchronization."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Team, TeamSyncStatus
from app.scrapers.fussballde_client import FussballDeClient, FussballDeFetchError
from app.services.fussballde_matchplan_sync import sync_team_matchplan
from app.services.fussballde_recent_lineup_sync import sync_recent_higher_team_lineups
from app.services.fussballde_sync import FussballDeSyncError
from app.settings import MatchplanSyncSettings

logger = logging.getLogger(__name__)


def next_sync_at(now: datetime, *, hour: int, minute: int) -> datetime:
    """Return the next local daily run time strictly after ``now``."""
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return scheduled if scheduled > now else scheduled + timedelta(days=1)


def record_successful_matchplan_sync(
    session: Session,
    *,
    team_fussballde_id: str,
    synced_at: datetime,
) -> None:
    """Record a successful source check, even if no fixture changed."""
    team = session.scalar(select(Team).where(Team.fussballde_id == team_fussballde_id))
    if team is None:
        raise ValueError("Configured team was not found after match-plan synchronization")

    sync_status = session.scalar(
        select(TeamSyncStatus).where(TeamSyncStatus.team_id == team.id)
    )
    if sync_status is None:
        session.add(
            TeamSyncStatus(team_id=team.id, last_successful_sync_at=synced_at)
        )
    else:
        sync_status.last_successful_sync_at = synced_at


def run_configured_matchplan_sync(settings: MatchplanSyncSettings) -> None:
    """Run one synchronous update with its own session and bounded HTTP client."""
    client = FussballDeClient()
    try:
        with SessionLocal() as session:
            for team_fussballde_id in settings.team_fussballde_ids:
                try:
                    summary = sync_team_matchplan(
                        session,
                        client,
                        team_fussballde_id=team_fussballde_id,
                    )
                    lineup_summary = None
                    if team_fussballde_id == settings.team_fussballde_id:
                        lineup_summary = sync_recent_higher_team_lineups(
                            session,
                            client,
                            team_fussballde_id=team_fussballde_id,
                        )
                    record_successful_matchplan_sync(
                        session,
                        team_fussballde_id=team_fussballde_id,
                        synced_at=datetime.now(),
                    )
                    session.commit()
                    logger.info(
                        "Daily sync finished for %s: created=%s updated=%s skipped=%s lineups=%s",
                        team_fussballde_id,
                        summary.created,
                        summary.updated,
                        summary.skipped,
                        lineup_summary,
                    )
                except (FussballDeFetchError, FussballDeSyncError, ValueError):
                    session.rollback()
                    logger.exception("Daily match-plan sync failed for %s", team_fussballde_id)
    finally:
        client.close()


async def run_daily_matchplan_sync(
    stop_event: asyncio.Event,
    *,
    settings: MatchplanSyncSettings,
    now: Callable[[], datetime] = datetime.now,
    run_once: Callable[[MatchplanSyncSettings], None] = run_configured_matchplan_sync,
) -> None:
    """Wait until the configured local time, run once, then repeat until stopped."""
    while not stop_event.is_set():
        current_time = now()
        scheduled_time = next_sync_at(
            current_time,
            hour=settings.hour,
            minute=settings.minute,
        )
        delay = (scheduled_time - current_time).total_seconds()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(delay, 0))
        except TimeoutError:
            await asyncio.to_thread(run_once, settings)
