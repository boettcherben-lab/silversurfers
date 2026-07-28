"""Import a lineup for a fixture that already exists in the local match plan."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Match
from app.scrapers.fussballde import TeamSide
from app.services.fussballde_import import MatchImport
from app.services.fussballde_sync import FussballDeSource, sync_match


def sync_local_match_lineup(
    session: Session,
    source: FussballDeSource,
    *,
    match_id: int,
    monitored_team_side: TeamSide | None = None,
    home_score: int | None = None,
    away_score: int | None = None,
) -> Match:
    """Fetch a lineup using locally stored fixture metadata and mark the match completed."""
    local_match = session.get(Match, match_id)
    if local_match is None:
        raise ValueError(f"Unknown local match ID: {match_id}")
    if local_match.fussballde_id is None:
        raise ValueError(f"Local match {match_id} has no FUSSBALL.DE match ID")
    if local_match.team.fussballde_id is None:
        raise ValueError(f"Local team {local_match.team_id} has no FUSSBALL.DE team ID")
    team_side = monitored_team_side or local_match.monitored_team_side
    if team_side not in {"home", "away"}:
        raise ValueError(f"Local match {match_id} has no monitored team side")

    return sync_match(
        session,
        source,
        MatchImport(
            fussballde_id=local_match.fussballde_id,
            team_fussballde_id=local_match.team.fussballde_id,
            monitored_team_side=team_side,
            played_on=local_match.played_on,
            kickoff_time=local_match.kickoff_time,
            competition=local_match.competition,
            home_team=local_match.home_team,
            away_team=local_match.away_team,
            home_score=local_match.home_score if home_score is None else home_score,
            away_score=local_match.away_score if away_score is None else away_score,
            report_url=local_match.report_url,
            finished=True,
            is_competitive=local_match.is_competitive,
        ),
    )
