from datetime import date, timedelta

import pytest

from app.rules.nfv import (
    EligibilityStatus,
    HigherTeamMatch,
    NFVEligibilityCalculator,
)


def match(
    day: int,
    *,
    appeared: bool,
    competitive: bool = True,
    finished: bool = True,
) -> HigherTeamMatch:
    return HigherTeamMatch(
        played_on=date(2026, 8, 1) + timedelta(days=day),
        appeared=appeared,
        finished=finished,
        is_competitive=competitive,
    )


def test_one_competitive_appearance_marks_player_at_risk() -> None:
    result = NFVEligibilityCalculator().calculate([match(0, appeared=True)], as_of=date(2026, 8, 1))

    assert result.status is EligibilityStatus.AT_RISK
    assert result.matches_to_skip == 0


def test_two_consecutive_competitive_appearances_lock_player() -> None:
    result = NFVEligibilityCalculator().calculate(
        [match(0, appeared=True), match(7, appeared=True)],
        as_of=date(2026, 8, 8),
    )

    assert result.status is EligibilityStatus.LOCKED
    assert result.matches_to_skip == 2
    assert result.eligible_on is None


def test_two_missed_competitive_matches_make_player_eligible_on_following_day() -> None:
    calculator = NFVEligibilityCalculator()
    history = [
        match(0, appeared=True),
        match(7, appeared=True),
        match(14, appeared=False),
        match(21, appeared=False),
    ]

    before_release = calculator.calculate(history, as_of=date(2026, 8, 22))
    after_release = calculator.calculate(history, as_of=date(2026, 8, 23))

    assert before_release.status is EligibilityStatus.LOCKED
    assert before_release.matches_to_skip == 0
    assert before_release.eligible_on == date(2026, 8, 23)
    assert after_release.status is EligibilityStatus.ELIGIBLE


def test_friendly_and_unfinished_matches_do_not_interrupt_competitive_sequence() -> None:
    result = NFVEligibilityCalculator().calculate(
        [
            match(0, appeared=True),
            match(2, appeared=False, competitive=False),
            match(4, appeared=False, finished=False),
            match(7, appeared=True),
        ],
        as_of=date(2026, 8, 8),
    )

    assert result.status is EligibilityStatus.LOCKED


def test_another_lower_team_level_requires_one_more_missed_match() -> None:
    result = NFVEligibilityCalculator().calculate(
        [
            match(0, appeared=True),
            match(7, appeared=True),
            match(14, appeared=False),
            match(21, appeared=False),
        ],
        as_of=date(2026, 8, 22),
        lower_team_distance=2,
    )

    assert result.status is EligibilityStatus.LOCKED
    assert result.matches_to_skip == 1


def test_lower_team_distance_must_be_positive() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        NFVEligibilityCalculator().calculate([], as_of=date(2026, 8, 1), lower_team_distance=0)
