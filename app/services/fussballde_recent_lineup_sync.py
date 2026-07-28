"""Bounded import of newly published lineups from recent higher-team fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Appearance, Match
from app.scrapers.fussballde_matchplan import parse_team_matchplan_html
from app.services.fussballde_import import MatchImport
from app.services.fussballde_matchplan_import import (
    is_relevant_competition,
    monitored_team_side,
)
from app.services.fussballde_sync import (
    FussballDeLineupUnavailableError,
    FussballDeSource,
    sync_match,
)


class RecentLineupSource(FussballDeSource, Protocol):
    """Public resources required to synchronize recent completed fixtures."""

    def fetch_previous_games_html(self, team_id: str) -> str: ...


@dataclass(frozen=True, slots=True)
class RecentLineupSyncSummary:
    """Outcome of one bounded recent-lineup synchronization."""

    imported: int
    already_imported: int
    pending_lineup: int
    ignored: int


def sync_recent_higher_team_lineups(
    session: Session,
    source: RecentLineupSource,
    *,
    team_fussballde_id: str,
) -> RecentLineupSyncSummary:
    """Import available lineups from the source's bounded recent-fixtures list.

    Only competitive fixtures of the explicitly configured higher team are considered. A match
    is marked finished only after the source exposes a lineup for the monitored team.
    """
    recent_matches = parse_team_matchplan_html(
        source.fetch_previous_games_html(team_fussballde_id)
    )
    imported = 0
    already_imported = 0
    pending_lineup = 0
    ignored = 0

    for fixture in recent_matches:
        if not is_relevant_competition(fixture.competition):
            ignored += 1
            continue

        team_side = monitored_team_side(
            fixture,
            team_fussballde_id=team_fussballde_id,
        )
        if team_side is None:
            ignored += 1
            continue

        existing_match = session.scalar(
            select(Match).where(Match.fussballde_id == fixture.fussballde_id)
        )
        if existing_match is not None and existing_match.finished:
            appearance_count = session.scalar(
                select(func.count(Appearance.id)).where(Appearance.match_id == existing_match.id)
            )
            if appearance_count > 0:
                already_imported += 1
                continue

        try:
            sync_match(
                session,
                source,
                MatchImport(
                    fussballde_id=fixture.fussballde_id,
                    team_fussballde_id=team_fussballde_id,
                    monitored_team_side=team_side,
                    played_on=fixture.played_on,
                    kickoff_time=fixture.kickoff_time,
                    competition=fixture.competition,
                    home_team=fixture.home_team,
                    away_team=fixture.away_team,
                    report_url=fixture.report_url,
                    finished=True,
                    is_competitive=True,
                ),
            )
        except FussballDeLineupUnavailableError:
            pending_lineup += 1
            continue
        imported += 1

    return RecentLineupSyncSummary(
        imported=imported,
        already_imported=already_imported,
        pending_lineup=pending_lineup,
        ignored=ignored,
    )
