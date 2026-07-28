"""Build NFV eligibility results from persisted match and appearance history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Appearance, Match, Player, Team
from app.rules.nfv import EligibilityResult, HigherTeamMatch, NFVEligibilityCalculator


def season_start(as_of: date) -> date:
    """Return the NFV season start date (1 July) for a calculation date."""
    start_year = as_of.year if as_of.month >= 7 else as_of.year - 1
    return date(start_year, 7, 1)


@dataclass(frozen=True, slots=True)
class PlayerEligibility:
    """A calculated status together with the local player identity."""

    player: Player
    result: EligibilityResult
    preferred_jersey_number: int | None


def calculate_team_eligibilities(
    session: Session,
    *,
    team_id: int,
    as_of: date,
    lower_team_distance: int = 1,
) -> tuple[Team | None, list[PlayerEligibility]]:
    """Calculate statuses for players with relevant imported higher-team appearances.

    Friendlies, unfinished matches, and future matches are excluded. Players remain visible
    from historical appearances, while the rule calculation begins anew on 1 July each season.
    The returned status is always calculated on demand.
    """
    team = session.get(Team, team_id)
    if team is None:
        return None, []

    matches = session.scalars(
        select(Match)
        .where(Match.team_id == team_id)
        .options(selectinload(Match.appearances).selectinload(Appearance.player))
        .order_by(Match.played_on, Match.id)
    ).all()
    relevant_matches = [
        match
        for match in matches
        if match.finished and match.is_competitive and match.played_on <= as_of
    ]
    current_season_start = season_start(as_of)
    current_season_matches = [
        match for match in relevant_matches if match.played_on >= current_season_start
    ]
    players_by_id = {
        appearance.player.id: appearance.player
        for match in relevant_matches
        for appearance in match.appearances
    }
    jersey_number_counts: dict[int, dict[int, tuple[int, int]]] = {}
    for match in relevant_matches:
        for appearance in match.appearances:
            if appearance.jersey_number is None:
                continue
            player_counts = jersey_number_counts.setdefault(appearance.player_id, {})
            count, _last_match_id = player_counts.get(appearance.jersey_number, (0, 0))
            player_counts[appearance.jersey_number] = (count + 1, match.id)
    calculator = NFVEligibilityCalculator()
    results: list[PlayerEligibility] = []

    for player in sorted(players_by_id.values(), key=lambda candidate: candidate.name.casefold()):
        history = [
            HigherTeamMatch(
                played_on=match.played_on,
                appeared=any(appearance.player_id == player.id for appearance in match.appearances),
                finished=match.finished,
                is_competitive=match.is_competitive,
                sequence=match.id,
            )
            for match in current_season_matches
        ]
        results.append(
            PlayerEligibility(
                player=player,
                result=calculator.calculate(
                    history,
                    as_of=as_of,
                    lower_team_distance=lower_team_distance,
                ),
                preferred_jersey_number=_most_frequent_jersey_number(
                    jersey_number_counts.get(player.id, {})
                ),
            )
        )

    return team, results


def _most_frequent_jersey_number(counts: dict[int, tuple[int, int]]) -> int | None:
    """Choose the most common number, preferring its most recent use on ties."""
    if not counts:
        return None
    return max(
        counts,
        key=lambda jersey_number: (
            counts[jersey_number][0],
            counts[jersey_number][1],
            -jersey_number,
        ),
    )
