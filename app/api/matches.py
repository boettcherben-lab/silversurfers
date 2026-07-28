"""Read-only API endpoints for locally imported matches and appearances."""

from __future__ import annotations

from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_session
from app.models import Appearance, Match, Player

router = APIRouter(prefix="/matches", tags=["matches"])


class MatchListItem(BaseModel):
    id: int
    fussballde_id: str | None
    played_on: date
    kickoff_time: time | None
    competition: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    finished: bool
    is_competitive: bool
    monitored_team_side: str | None
    report_url: str | None


class AppearanceItem(BaseModel):
    player_id: int
    player_name: str
    player_fussballde_id: str | None
    starter: bool
    captain: bool
    jersey_number: int | None


class MatchDetail(MatchListItem):
    appearances: list[AppearanceItem]


@router.get("", response_model=list[MatchListItem])
def list_matches(session: Session = Depends(get_session)) -> list[MatchListItem]:
    """List locally imported matches, newest first."""
    matches = session.scalars(select(Match).order_by(Match.played_on.desc(), Match.id.desc())).all()
    return [_match_list_item(match) for match in matches]


@router.get("/{match_id}", response_model=MatchDetail)
def get_match(match_id: int, session: Session = Depends(get_session)) -> MatchDetail:
    """Return one locally imported match together with its monitored-team appearances."""
    match = session.scalar(
        select(Match)
        .where(Match.id == match_id)
        .options(selectinload(Match.appearances).selectinload(Appearance.player))
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    appearances = sorted(
        match.appearances,
        key=lambda appearance: appearance.player.name.casefold(),
    )
    return MatchDetail(
        **_match_list_item(match).model_dump(),
        appearances=[_appearance_item(appearance) for appearance in appearances],
    )


def _match_list_item(match: Match) -> MatchListItem:
    return MatchListItem(
        id=match.id,
        fussballde_id=match.fussballde_id,
        played_on=match.played_on,
        kickoff_time=match.kickoff_time,
        competition=match.competition,
        home_team=match.home_team,
        away_team=match.away_team,
        home_score=match.home_score,
        away_score=match.away_score,
        finished=match.finished,
        is_competitive=match.is_competitive,
        monitored_team_side=match.monitored_team_side,
        report_url=match.report_url,
    )


def _appearance_item(appearance: Appearance) -> AppearanceItem:
    player: Player = appearance.player
    return AppearanceItem(
        player_id=player.id,
        player_name=player.display_name or player.name,
        player_fussballde_id=player.fussballde_id,
        starter=appearance.starter,
        captain=appearance.captain,
        jersey_number=appearance.jersey_number,
    )
