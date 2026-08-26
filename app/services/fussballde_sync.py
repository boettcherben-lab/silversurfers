"""Orchestrate a single FUSSBALL.DE lineup import."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Match
from app.scrapers.fussballde import (
    LineupEntry,
    parse_lineup_html,
    parse_substituted_player_ids,
)
from app.scrapers.fussballde_profiles import parse_player_profile_name
from app.services.fussballde_import import MatchImport, import_match


class FussballDeSource(Protocol):
    """The limited source operations needed for one match synchronization."""

    def fetch_lineup_html(self, match_id: str) -> str: ...

    def fetch_match_course_html(self, match_id: str) -> str: ...

    def fetch_player_profile_html(self, profile_url: str) -> str: ...


class FussballDeSyncError(RuntimeError):
    """Raised when an otherwise fetched FUSSBALL.DE record cannot be imported safely."""


class FussballDeLineupUnavailableError(FussballDeSyncError):
    """Raised when a completed fixture has no public lineup yet."""


def sync_match(session: Session, source: FussballDeSource, match_import: MatchImport) -> Match:
    """Fetch, parse, resolve names, and import one explicitly selected match.

    The function only retrieves the lineup and player profiles for the monitored team side.
    It does not commit the session; the caller owns the transaction boundary.
    """
    lineup_entries = parse_lineup_html(source.fetch_lineup_html(match_import.fussballde_id))
    substituted_player_ids = parse_substituted_player_ids(
        source.fetch_match_course_html(match_import.fussballde_id)
    )
    monitored_entries = [
        replace(
            entry,
            appeared=entry.starter or entry.fussballde_id in substituted_player_ids,
        )
        for entry in lineup_entries
        if entry.side == match_import.monitored_team_side
    ]
    if not monitored_entries:
        raise FussballDeLineupUnavailableError(
            f"No public lineup is available for match {match_import.fussballde_id}"
        )
    actual_entries = [entry for entry in monitored_entries if entry.appeared]
    player_names = _resolve_player_names(source, actual_entries)

    return import_match(session, match_import, actual_entries, player_names)


def _resolve_player_names(
    source: FussballDeSource, lineup_entries: list[LineupEntry]
) -> dict[str, str]:
    player_names: dict[str, str] = {}
    for entry in lineup_entries:
        if entry.fussballde_id in player_names:
            continue
        if not entry.profile_url:
            raise FussballDeSyncError(f"Missing profile URL for player {entry.fussballde_id}")

        player_name = parse_player_profile_name(source.fetch_player_profile_html(entry.profile_url))
        if player_name is None:
            raise FussballDeSyncError(f"Could not resolve name for player {entry.fussballde_id}")
        player_names[entry.fussballde_id] = player_name

    return player_names
