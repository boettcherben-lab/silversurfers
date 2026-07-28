"""Read-only preview of an explicitly selected FUSSBALL.DE team match plan."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.fussballde_imports import get_fussballde_client
from app.scrapers.fussballde_client import FussballDeClient, FussballDeFetchError
from app.scrapers.fussballde_matchplan import parse_team_matchplan_html

router = APIRouter(prefix="/imports/fussballde", tags=["FUSSBALL.DE schedule"])


class FussballDeScheduledMatch(BaseModel):
    fussballde_id: str
    played_on: date
    kickoff_time: time | None
    competition: str
    home_team: str
    away_team: str
    report_url: str


@router.get("/teams/{team_fussballde_id}/matchplan", response_model=list[FussballDeScheduledMatch])
def preview_fussballde_matchplan(
    team_fussballde_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    source: FussballDeClient = Depends(get_fussballde_client),
) -> list[FussballDeScheduledMatch]:
    """Return a bounded, read-only fixture preview; no matches are imported or stored."""
    try:
        html = source.fetch_team_matchplan_html(team_fussballde_id)
    except FussballDeFetchError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    matches = parse_team_matchplan_html(html)[:limit]
    return [FussballDeScheduledMatch(**asdict(match)) for match in matches]
