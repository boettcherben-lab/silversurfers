from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.fussballde_imports import get_fussballde_client
from app.database import Base, create_sqlite_engine, get_session
from app.main import app
from app.models import Appearance, Team


class FakeFussballDeSource:
    def __init__(self, lineup_html: str, profile_html_by_url: dict[str, str]) -> None:
        self.lineup_html = lineup_html
        self.profile_html_by_url = profile_html_by_url

    def fetch_lineup_html(self, match_id: str) -> str:
        assert match_id == "match-1"
        return self.lineup_html

    def fetch_player_profile_html(self, profile_url: str) -> str:
        return self.profile_html_by_url[profile_url]


def test_manual_import_endpoint_imports_one_explicit_match(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'api-import.db'}")
    Base.metadata.create_all(bind=engine)
    fixture_directory = Path(__file__).parent / "fixtures"
    source = FakeFussballDeSource(
        (fixture_directory / "fussballde_lineup.html").read_text(encoding="utf-8"),
        {
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_CAPTAIN": (
                "<title>Maik Fischer Basisprofil | FUSSBALL.DE</title>"
            ),
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_STARTER": (
                "<title>Christian Goldenstein Basisprofil | FUSSBALL.DE</title>"
            ),
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_SUB": (
                "<title>Thomas Martens Basisprofil | FUSSBALL.DE</title>"
            ),
        },
    )

    with Session(engine) as session:
        session.add(Team(name="FC Burgwedel Ü40 I", fussballde_id="higher-team"))
        session.commit()

    def test_session() -> Session:
        return Session(engine)

    app.dependency_overrides[get_session] = test_session
    app.dependency_overrides[get_fussballde_client] = lambda: source
    try:
        with TestClient(app) as client:
            response = client.post(
                "/imports/fussballde/matches/match-1",
                json={
                    "team_fussballde_id": "higher-team",
                    "monitored_team_side": "home",
                    "played_on": "2026-08-07",
                    "competition": "Kreispokal",
                    "home_team": "FC Burgwedel",
                    "away_team": "SSV Thönse",
                    "finished": True,
                    "is_competitive": True,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"match_id": 1, "fussballde_id": "match-1"}

    with Session(engine) as session:
        assert len(session.scalars(select(Appearance)).all()) == 3
