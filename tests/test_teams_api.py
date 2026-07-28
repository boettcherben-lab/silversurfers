from datetime import date, datetime, time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine, get_session
from app.main import app
from app.models import Match, Team, TeamSyncStatus


def test_next_match_endpoint_returns_next_competitive_fixture(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'teams-api.db'}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        team = Team(name="FC Burgwedel Ü40 I")
        session.add(team)
        session.flush()
        session.add_all(
            [
                Match(
                    team_id=team.id,
                    played_on=date(2026, 8, 1),
                    competition="Kreispokal",
                    home_team="FC Burgwedel",
                    away_team="SSV Thönse",
                    finished=True,
                    is_competitive=True,
                ),
                Match(
                    fussballde_id="NEXT1",
                    team_id=team.id,
                    played_on=date(2026, 8, 7),
                    kickoff_time=time(19, 0),
                    competition="Kreispokal",
                    home_team="SSV Thönse",
                    away_team="FC Burgwedel",
                    finished=False,
                    is_competitive=True,
                ),
                Match(
                    team_id=team.id,
                    played_on=date(2026, 8, 2),
                    competition="Freundschaftsspiel",
                    home_team="FC Burgwedel",
                    away_team="Gastverein",
                    finished=False,
                    is_competitive=False,
                ),
            ]
        )
        session.commit()

    app.dependency_overrides[get_session] = lambda: Session(engine)
    try:
        with TestClient(app) as client:
            response = client.get("/teams/1/next-match?as_of=2026-08-01")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["fussballde_id"] == "NEXT1"
    assert response.json()["kickoff_time"] == "19:00:00"


def test_sync_status_endpoint_returns_last_successful_sync(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'sync-api.db'}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        team = Team(name="FC Burgwedel Ü40 I")
        session.add(team)
        session.flush()
        session.add(
            TeamSyncStatus(
                team_id=team.id,
                last_successful_sync_at=datetime(2026, 7, 28, 4, 0),
            )
        )
        session.commit()

    app.dependency_overrides[get_session] = lambda: Session(engine)
    try:
        with TestClient(app) as client:
            response = client.get("/teams/1/sync-status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["last_successful_sync_at"] == "2026-07-28T04:00:00"
