from pathlib import Path

from app.scrapers.fussballde_profiles import parse_player_profile_name


def test_parse_player_profile_name_from_profile_fixture() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "fussballde_player_profile.html"

    assert parse_player_profile_name(fixture_path.read_text(encoding="utf-8")) == "Maik Fischer"


def test_parse_player_profile_name_removes_team_suffix() -> None:
    html = (
        "<html><head><title>Patrick Heldt (FC Burgwedel) "
        "Spielerprofil | FUSSBALL.DE</title></head></html>"
    )

    assert parse_player_profile_name(html) == "Patrick Heldt"


def test_parse_player_profile_name_returns_none_for_unknown_page() -> None:
    assert parse_player_profile_name("<html><head><title>Fehler</title></head></html>") is None
