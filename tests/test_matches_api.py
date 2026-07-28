from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine, get_session
from app.main import app
from app.models import Appearance, Match, Player, Team


def test_match_endpoints_list_and_show_imported_appearances(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'matches-api.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        team = Team(name="FC Burgwedel Ü40 I", fussballde_id="higher-team")
        player = Player(name="Maik Fischer", display_name="Maik", fussballde_id="player-1")
        session.add_all([team, player])
        session.flush()
        match = Match(
            fussballde_id="match-1",
            team_id=team.id,
            played_on=date(2026, 8, 7),
            competition="Kreispokal",
            home_team="FC Burgwedel",
            away_team="SSV Thönse",
            home_score=3,
            away_score=1,
            finished=True,
            is_competitive=True,
            report_url="https://example.test/match-1",
        )
        session.add(match)
        session.flush()
        session.add(
            Appearance(
                player_id=player.id,
                match_id=match.id,
                starter=True,
                captain=True,
                jersey_number=1,
            )
        )
        session.commit()

    def test_session() -> Session:
        return Session(engine)

    app.dependency_overrides[get_session] = test_session
    try:
        with TestClient(app) as client:
            list_response = client.get("/matches")
            detail_response = client.get("/matches/1")
            missing_response = client.get("/matches/99")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()[0]["fussballde_id"] == "match-1"
    assert detail_response.status_code == 200
    assert detail_response.json()["appearances"] == [
        {
            "player_id": 1,
            "player_name": "Maik",
            "player_fussballde_id": "player-1",
            "starter": True,
            "captain": True,
            "jersey_number": 1,
        }
    ]
    assert missing_response.status_code == 404
