from pathlib import Path

from app.scrapers.fussballde import (
    LineupEntry,
    parse_lineup_html,
    parse_substituted_player_ids,
)


def test_parse_lineup_extracts_starters_bench_and_metadata() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "fussballde_lineup.html"

    entries = parse_lineup_html(fixture_path.read_text(encoding="utf-8"))

    assert entries == [
        LineupEntry(
            "HOME_CAPTAIN",
            "home",
            True,
            True,
            1,
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_CAPTAIN",
            True,
        ),
        LineupEntry(
            "HOME_STARTER",
            "home",
            True,
            False,
            24,
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_STARTER",
            True,
        ),
        LineupEntry(
            "AWAY_STARTER",
            "away",
            True,
            False,
            7,
            "https://www.fussball.de/spielerprofil/-/userid/AWAY_STARTER",
            True,
        ),
        LineupEntry(
            "HOME_SUB",
            "home",
            False,
            False,
            9,
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_SUB",
            False,
        ),
        LineupEntry(
            "AWAY_SUB",
            "away",
            False,
            False,
            None,
            "https://www.fussball.de/spielerprofil/-/player-id/AWAY_SUB",
            False,
        ),
    ]


def test_parse_match_course_extracts_only_players_brought_on() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "fussballde_match_course.html"

    assert parse_substituted_player_ids(fixture_path.read_text(encoding="utf-8")) == {
        "HOME_SUB",
        "AWAY_SUB",
    }
