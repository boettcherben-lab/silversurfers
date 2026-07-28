"""Controlled import of relevant FUSSBALL.DE team fixtures."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.fussballde_imports import get_fussballde_client
from app.database import get_session
from app.scrapers.fussballde_client import FussballDeClient, FussballDeFetchError
from app.services.fussballde_matchplan_sync import sync_team_matchplan

router = APIRouter(prefix="/imports/fussballde", tags=["FUSSBALL.DE imports"])


class FussballDeMatchplanImportResponse(BaseModel):
    created: int
    updated: int
    skipped: int


@router.post(
    "/teams/{team_fussballde_id}/matchplan",
    response_model=FussballDeMatchplanImportResponse,
    status_code=status.HTTP_200_OK,
)
def import_fussballde_matchplan(
    team_fussballde_id: str,
    session: Session = Depends(get_session),
    source: FussballDeClient = Depends(get_fussballde_client),
) -> FussballDeMatchplanImportResponse:
    """Store a manually triggered team's relevant fixture metadata without fetching lineups."""
    try:
        summary = sync_team_matchplan(
            session,
            source,
            team_fussballde_id=team_fussballde_id,
        )
        session.commit()
    except FussballDeFetchError as error:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except ValueError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return FussballDeMatchplanImportResponse(**asdict(summary))
