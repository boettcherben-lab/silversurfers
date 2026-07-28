"""NFV eligibility rules, independent from persistence and HTTP concerns."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class EligibilityStatus(StrEnum):
    """Eligibility state for a player in a lower team."""

    ELIGIBLE = "eligible"
    AT_RISK = "at_risk"
    LOCKED = "locked"


@dataclass(frozen=True, slots=True)
class HigherTeamMatch:
    """One higher-team match from the perspective of a single player.

    ``sequence`` provides a deterministic ordering for multiple matches on the same date.
    Only finished competitive matches on or before the calculation date influence the rule.
    """

    played_on: date
    appeared: bool
    finished: bool
    is_competitive: bool
    sequence: int = 0


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    """Calculated, non-persisted eligibility state."""

    status: EligibilityStatus
    matches_to_skip: int
    eligible_on: date | None


class NFVEligibilityCalculator:
    """Calculate a player's eligibility according to the supplied NFV rule definition."""

    def calculate(
        self,
        matches: Iterable[HigherTeamMatch],
        *,
        as_of: date,
        lower_team_distance: int = 1,
    ) -> EligibilityResult:
        """Return status for a lower team at ``as_of``.

        ``lower_team_distance=1`` represents the next lower team and requires two missed
        consecutive higher-team compulsory matches to become eligible again. Every additional
        lower-team level requires one further missed match.
        """
        if lower_team_distance < 1:
            raise ValueError("lower_team_distance must be at least 1")

        required_misses = lower_team_distance + 1
        relevant_matches = sorted(
            (
                match
                for match in matches
                if match.finished and match.is_competitive and match.played_on <= as_of
            ),
            key=lambda match: (match.played_on, match.sequence),
        )

        locked = False
        previous_match_appearance = False
        missed_matches = 0
        eligible_on: date | None = None

        for match in relevant_matches:
            if locked and eligible_on is not None and match.played_on >= eligible_on:
                locked = False
                missed_matches = 0
                eligible_on = None
                previous_match_appearance = False

            if match.appeared:
                if locked:
                    missed_matches = 0
                    eligible_on = None
                elif previous_match_appearance:
                    locked = True
                    missed_matches = 0
                    eligible_on = None
                previous_match_appearance = True
                continue

            previous_match_appearance = False
            if not locked:
                continue

            missed_matches += 1
            if missed_matches >= required_misses:
                eligible_on = match.played_on + timedelta(days=1)

        if locked and eligible_on is not None and eligible_on <= as_of:
            locked = False
            missed_matches = 0
            eligible_on = None
            previous_match_appearance = False

        if locked:
            return EligibilityResult(
                status=EligibilityStatus.LOCKED,
                matches_to_skip=max(required_misses - missed_matches, 0),
                eligible_on=eligible_on,
            )
        if previous_match_appearance:
            return EligibilityResult(
                status=EligibilityStatus.AT_RISK,
                matches_to_skip=0,
                eligible_on=None,
            )
        return EligibilityResult(
            status=EligibilityStatus.ELIGIBLE,
            matches_to_skip=0,
            eligible_on=None,
        )
