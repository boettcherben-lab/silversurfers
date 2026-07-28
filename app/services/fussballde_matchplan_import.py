"""Persist relevant fixtures from an already fetched FUSSBALL.DE match plan."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Match, Team
from app.scrapers.fussballde_matchplan import ScheduledMatch

_EXCLUDED_COMPETITION_TERMS = ("freundschaft", "testspiel", "turnier")
_COMPETITIVE_COMPETITION_TERMS = ("pokal", "relegation", "liga", "klasse")


@dataclass(frozen=True, slots=True)
class MatchplanImportSummary:
    created: int
    updated: int
    skipped: int


def is_relevant_competition(competition: str) -> bool:
    """Return whether a competition is a league, cup, or relegation competition.

    The source label is deliberately classified with a narrow, documented allow-list. Friendly
    and test matches are excluded before evaluating positive terms.
    """
    normalized = competition.casefold()
    if any(term in normalized for term in _EXCLUDED_COMPETITION_TERMS):
        return False
    return any(term in normalized for term in _COMPETITIVE_COMPETITION_TERMS)


def monitored_team_side(
    scheduled_match: ScheduledMatch,
    *,
    team_fussballde_id: str,
) -> str | None:
    """Return the source team's side when the public fixture contains both team IDs."""
    if scheduled_match.home_team_fussballde_id == team_fussballde_id:
        return "home"
    if scheduled_match.away_team_fussballde_id == team_fussballde_id:
        return "away"
    return None


def import_team_matchplan(
    session: Session,
    *,
    team_fussballde_id: str,
    scheduled_matches: list[ScheduledMatch],
) -> MatchplanImportSummary:
    """Idempotently store only relevant fixture metadata for one configured higher team.

    This service does not fetch data, scores, or lineups. Existing imported match results and
    appearances remain untouched when the schedule is refreshed.
    """
    team = session.scalar(select(Team).where(Team.fussballde_id == team_fussballde_id))
    if team is None:
        raise ValueError(f"Unknown FUSSBALL.DE team ID: {team_fussballde_id}")

    created = 0
    updated = 0
    skipped = 0
    for scheduled_match in scheduled_matches:
        if not is_relevant_competition(scheduled_match.competition):
            skipped += 1
            continue

        match = session.scalar(
            select(Match).where(Match.fussballde_id == scheduled_match.fussballde_id)
        )
        if match is None:
            session.add(
                Match(
                    fussballde_id=scheduled_match.fussballde_id,
                    team_id=team.id,
                    played_on=scheduled_match.played_on,
                    kickoff_time=scheduled_match.kickoff_time,
                    competition=scheduled_match.competition,
                    home_team=scheduled_match.home_team,
                    away_team=scheduled_match.away_team,
                    report_url=scheduled_match.report_url,
                    finished=False,
                    is_competitive=True,
                    monitored_team_side=monitored_team_side(
                        scheduled_match,
                        team_fussballde_id=team_fussballde_id,
                    ),
                )
            )
            created += 1
            continue

        match.team_id = team.id
        match.played_on = scheduled_match.played_on
        match.kickoff_time = scheduled_match.kickoff_time
        match.competition = scheduled_match.competition
        match.home_team = scheduled_match.home_team
        match.away_team = scheduled_match.away_team
        match.report_url = scheduled_match.report_url
        match.is_competitive = True
        match.monitored_team_side = monitored_team_side(
            scheduled_match,
            team_fussballde_id=team_fussballde_id,
        )
        updated += 1

    return MatchplanImportSummary(created=created, updated=updated, skipped=skipped)
