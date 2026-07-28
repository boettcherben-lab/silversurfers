"""Read-only endpoints derived from locally stored team fixtures."""

from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Match, Team, TeamSyncStatus

router = APIRouter(prefix="/teams", tags=["teams"])


class NextMatchResponse(BaseModel):
    id: int
    fussballde_id: str | None
    played_on: date
    kickoff_time: time | None
    competition: str
    home_team: str
    away_team: str
    report_url: str | None


class SyncStatusResponse(BaseModel):
    last_successful_sync_at: datetime | None


@router.get("/{team_id}/sync-status", response_model=SyncStatusResponse)
def get_sync_status(
    team_id: int,
    session: Session = Depends(get_session),
) -> SyncStatusResponse:
    """Return the time of the last successful scheduled FUSSBALL.DE sync."""
    if session.get(Team, team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    sync_status = session.scalar(
        select(TeamSyncStatus).where(TeamSyncStatus.team_id == team_id)
    )
    return SyncStatusResponse(
        last_successful_sync_at=(
            sync_status.last_successful_sync_at if sync_status is not None else None
        )
    )


@router.get("/{team_id}/next-match", response_model=NextMatchResponse)
def get_next_competitive_match(
    team_id: int,
    as_of: date | None = None,
    session: Session = Depends(get_session),
) -> NextMatchResponse:
    """Return the next locally stored, not yet finished, competitive fixture."""
    if session.get(Team, team_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    start_date = as_of or date.today()
    match = session.scalar(
        select(Match)
        .where(
            Match.team_id == team_id,
            Match.is_competitive.is_(True),
            Match.finished.is_(False),
            Match.played_on >= start_date,
        )
        .order_by(Match.played_on, Match.kickoff_time.is_(None), Match.kickoff_time, Match.id)
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No upcoming match found")

    return NextMatchResponse(
        id=match.id,
        fussballde_id=match.fussballde_id,
        played_on=match.played_on,
        kickoff_time=match.kickoff_time,
        competition=match.competition,
        home_team=match.home_team,
        away_team=match.away_team,
        report_url=match.report_url,
    )
