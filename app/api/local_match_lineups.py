"""Controlled lineup import for a locally stored fixture."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.fussballde_imports import get_fussballde_client
from app.database import get_session
from app.models import Appearance
from app.scrapers.fussballde_client import FussballDeClient, FussballDeFetchError
from app.services.fussballde_local_match_sync import sync_local_match_lineup
from app.services.fussballde_sync import FussballDeSyncError

router = APIRouter(prefix="/matches", tags=["FUSSBALL.DE imports"])


class LocalMatchLineupImportRequest(BaseModel):
    monitored_team_side: Literal["home", "away"] | None = None
    home_score: int | None = None
    away_score: int | None = None


class LocalMatchLineupImportResponse(BaseModel):
    match_id: int
    appearance_count: int


@router.post(
    "/{match_id}/lineup",
    response_model=LocalMatchLineupImportResponse,
    status_code=status.HTTP_200_OK,
)
def import_local_match_lineup(
    match_id: int,
    payload: LocalMatchLineupImportRequest,
    session: Session = Depends(get_session),
    source: FussballDeClient = Depends(get_fussballde_client),
) -> LocalMatchLineupImportResponse:
    """Import one completed match lineup without requiring the fixture metadata again."""
    try:
        match = sync_local_match_lineup(
            session,
            source,
            match_id=match_id,
            **payload.model_dump(),
        )
        appearance_count = session.scalar(
            select(func.count(Appearance.id)).where(Appearance.match_id == match.id)
        )
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

    return LocalMatchLineupImportResponse(match_id=match.id, appearance_count=appearance_count)
