"""Manual API endpoint for a single FUSSBALL.DE match import."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date, time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_session
from app.scrapers.fussballde_client import FussballDeClient, FussballDeFetchError
from app.services.fussballde_import import MatchImport
from app.services.fussballde_sync import FussballDeSyncError, sync_match

router = APIRouter(prefix="/imports/fussballde", tags=["FUSSBALL.DE imports"])


class FussballDeMatchImportRequest(BaseModel):
    team_fussballde_id: str
    monitored_team_side: Literal["home", "away"]
    played_on: date
    competition: str
    home_team: str
    away_team: str
    finished: bool
    is_competitive: bool
    kickoff_time: time | None = None
    report_url: str | None = None
    home_score: int | None = None
    away_score: int | None = None


class FussballDeMatchImportResponse(BaseModel):
    match_id: int
    fussballde_id: str


def get_fussballde_client() -> Generator[FussballDeClient, None, None]:
    client = FussballDeClient()
    try:
        yield client
    finally:
        client.close()


@router.post(
    "/matches/{fussballde_match_id}",
    response_model=FussballDeMatchImportResponse,
    status_code=status.HTTP_200_OK,
)
def import_fussballde_match(
    fussballde_match_id: str,
    payload: FussballDeMatchImportRequest,
    session: Session = Depends(get_session),
    source: FussballDeClient = Depends(get_fussballde_client),
) -> FussballDeMatchImportResponse:
    """Manually import one selected FUSSBALL.DE match into the local database."""
    match_import = MatchImport(fussballde_id=fussballde_match_id, **payload.model_dump())
    try:
        match = sync_match(session, source, match_import)
        session.commit()
    except FussballDeFetchError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except (FussballDeSyncError, ValueError) as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return FussballDeMatchImportResponse(match_id=match.id, fussballde_id=match.fussballde_id)
