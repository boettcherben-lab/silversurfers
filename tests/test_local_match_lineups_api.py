from datetime import date, time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.fussballde_imports import get_fussballde_client
from app.database import Base, create_sqlite_engine, get_session
from app.main import app
from app.models import Appearance, Match, Team


class FakeFussballDeSource:
    def __init__(self, lineup_html: str, profile_html_by_url: dict[str, str]) -> None:
        self.lineup_html = lineup_html
        self.profile_html_by_url = profile_html_by_url

    def fetch_lineup_html(self, match_id: str) -> str:
        assert match_id == "MATCH1"
        return self.lineup_html

    def fetch_match_course_html(self, match_id: str) -> str:
        assert match_id == "MATCH1"
        return (Path(__file__).parent / "fixtures" / "fussballde_match_course.html").read_text(
            encoding="utf-8"
        )

    def fetch_player_profile_html(self, profile_url: str) -> str:
        return self.profile_html_by_url[profile_url]


def test_local_match_lineup_import_uses_stored_fixture_metadata(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'local-match-lineup.db'}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        team = Team(name="FC Burgwedel Ü40 I", fussballde_id="TEAM123")
        session.add(team)
        session.flush()
        session.add(
            Match(
                fussballde_id="MATCH1",
                team_id=team.id,
                played_on=date(2026, 8, 7),
                kickoff_time=time(19, 0),
                competition="Kreispokal",
                home_team="FC Burgwedel",
                away_team="SSV Thönse",
                report_url="https://www.fussball.de/spiel/fc-burgwedel-ssv-thoense/-/spiel/MATCH1",
                finished=False,
                is_competitive=True,
                monitored_team_side="home",
            )
        )
        session.commit()

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

    app.dependency_overrides[get_session] = lambda: Session(engine)
    app.dependency_overrides[get_fussballde_client] = lambda: source
    try:
        with TestClient(app) as client:
            response = client.post(
                "/matches/1/lineup",
                json={"home_score": 3, "away_score": 1},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"match_id": 1, "appearance_count": 3}
    with Session(engine) as session:
        imported_match = session.get(Match, 1)
        assert imported_match is not None
        assert imported_match.finished is True
        assert (imported_match.home_score, imported_match.away_score) == (3, 1)
        assert len(session.scalars(select(Appearance)).all()) == 3
