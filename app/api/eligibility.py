"""Read-only NFV eligibility endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_session
from app.rules.nfv import EligibilityStatus
from app.services.eligibility import calculate_team_eligibilities

router = APIRouter(prefix="/teams", tags=["eligibility"])


class PlayerEligibilityItem(BaseModel):
    player_id: int
    player_name: str
    player_fussballde_id: str | None
    jersey_number: int | None
    status: EligibilityStatus
    matches_to_skip: int
    eligible_on: date | None


class TeamEligibilityResponse(BaseModel):
    team_id: int
    team_name: str
    as_of: date
    lower_team_distance: int
    players: list[PlayerEligibilityItem]


@router.get("/{team_id}/eligibility", response_model=TeamEligibilityResponse)
def get_team_eligibility(
    team_id: int,
    as_of: date | None = None,
    lower_team_distance: int = Query(default=1, ge=1),
    session: Session = Depends(get_session),
) -> TeamEligibilityResponse:
    """Calculate current or historical eligibility from locally imported data."""
    calculation_date = as_of or date.today()
    team, eligibilities = calculate_team_eligibilities(
        session,
        team_id=team_id,
        as_of=calculation_date,
        lower_team_distance=lower_team_distance,
    )
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    return TeamEligibilityResponse(
        team_id=team.id,
        team_name=team.name,
        as_of=calculation_date,
        lower_team_distance=lower_team_distance,
        players=[
            PlayerEligibilityItem(
                player_id=item.player.id,
                player_name=item.player.display_name or item.player.name,
                player_fussballde_id=item.player.fussballde_id,
                jersey_number=item.preferred_jersey_number,
                status=item.result.status,
                matches_to_skip=item.result.matches_to_skip,
                eligible_on=item.result.eligible_on,
            )
            for item in eligibilities
        ],
    )
