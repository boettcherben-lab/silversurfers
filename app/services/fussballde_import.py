"""Persist already parsed FUSSBALL.DE match and lineup data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Appearance, Match, Player, Team
from app.scrapers.fussballde import LineupEntry, TeamSide


@dataclass(frozen=True, slots=True)
class MatchImport:
    """Normalized match data that is ready to be persisted."""

    fussballde_id: str
    team_fussballde_id: str
    monitored_team_side: TeamSide
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


def import_match(
    session: Session,
    match_import: MatchImport,
    lineup_entries: list[LineupEntry],
    player_names: Mapping[str, str],
) -> Match:
    """Upsert one match and the monitored team's player appearances.

    The caller supplies parsed source data and a name lookup keyed by FUSSBALL.DE player ID.
    This function neither fetches nor parses network resources and does not commit the session.
    """
    team = session.scalar(
        select(Team).where(Team.fussballde_id == match_import.team_fussballde_id)
    )
    if team is None:
        raise ValueError(f"Unknown FUSSBALL.DE team ID: {match_import.team_fussballde_id}")

    match = session.scalar(select(Match).where(Match.fussballde_id == match_import.fussballde_id))
    if match is None:
        match = Match(
            fussballde_id=match_import.fussballde_id,
            team_id=team.id,
            played_on=match_import.played_on,
            kickoff_time=match_import.kickoff_time,
            competition=match_import.competition,
            home_team=match_import.home_team,
            away_team=match_import.away_team,
            home_score=match_import.home_score,
            away_score=match_import.away_score,
            report_url=match_import.report_url,
            finished=match_import.finished,
            is_competitive=match_import.is_competitive,
            monitored_team_side=match_import.monitored_team_side,
        )
        session.add(match)
    else:
        match.team_id = team.id
        match.played_on = match_import.played_on
        match.kickoff_time = match_import.kickoff_time
        match.competition = match_import.competition
        match.home_team = match_import.home_team
        match.away_team = match_import.away_team
        match.home_score = match_import.home_score
        match.away_score = match_import.away_score
        match.report_url = match_import.report_url
        match.finished = match_import.finished
        match.is_competitive = match_import.is_competitive
        match.monitored_team_side = match_import.monitored_team_side

    session.flush()

    for entry in lineup_entries:
        if entry.side != match_import.monitored_team_side:
            continue

        player = session.scalar(select(Player).where(Player.fussballde_id == entry.fussballde_id))
        player_name = player_names.get(entry.fussballde_id)
        if player is None:
            if player_name is None:
                raise ValueError(f"Missing name for FUSSBALL.DE player ID: {entry.fussballde_id}")
            player = Player(fussballde_id=entry.fussballde_id, name=player_name)
            session.add(player)
            session.flush()
        elif player_name is not None:
            player.name = player_name

        appearance = session.scalar(
            select(Appearance).where(
                Appearance.match_id == match.id,
                Appearance.player_id == player.id,
            )
        )
        if appearance is None:
            appearance = Appearance(player_id=player.id, match_id=match.id)
            session.add(appearance)

        appearance.starter = entry.starter
        appearance.captain = entry.captain
        appearance.jersey_number = entry.jersey_number

    return match
