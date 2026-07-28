"""Reusable, bounded synchronization of one explicitly configured team match plan."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.scrapers.fussballde_matchplan import parse_team_matchplan_html
from app.services.fussballde_matchplan_import import MatchplanImportSummary, import_team_matchplan


class MatchplanSource(Protocol):
    """Only the explicit public match-plan resource required for a sync."""

    def fetch_team_matchplan_html(self, team_id: str) -> str: ...


def sync_team_matchplan(
    session: Session,
    source: MatchplanSource,
    *,
    team_fussballde_id: str,
) -> MatchplanImportSummary:
    """Fetch and persist one configured team's relevant fixtures without committing."""
    scheduled_matches = parse_team_matchplan_html(
        source.fetch_team_matchplan_html(team_fussballde_id)
    )
    return import_team_matchplan(
        session,
        team_fussballde_id=team_fussballde_id,
        scheduled_matches=scheduled_matches,
    )
