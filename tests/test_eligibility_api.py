from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine, get_session
from app.main import app
from app.models import Appearance, Match, Player, Team
from app.rules.nfv import EligibilityStatus
from app.services.eligibility import calculate_team_eligibilities, season_start


def test_eligibility_endpoint_calculates_status_from_imported_history(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'eligibility-api.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        team = Team(name="FC Burgwedel Ü40 I")
        locked_player = Player(name="Maik Fischer", fussballde_id="maik")
        at_risk_player = Player(name="Thomas Martens", fussballde_id="thomas")
        session.add_all([team, locked_player, at_risk_player])
        session.flush()
        matches = [
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
                team_id=team.id,
                played_on=date(2026, 8, 8),
                competition="1. Kreisklasse",
                home_team="FC Burgwedel",
                away_team="SP Hannover 1",
                finished=True,
                is_competitive=True,
            ),
            Match(
                team_id=team.id,
                played_on=date(2026, 8, 15),
                competition="Freundschaftsspiel",
                home_team="FC Burgwedel",
                away_team="Gastverein",
                finished=True,
                is_competitive=False,
            ),
        ]
        session.add_all(matches)
        session.flush()
        session.add_all(
            [
                Appearance(
                    player_id=locked_player.id,
                    match_id=matches[0].id,
                    jersey_number=9,
                ),
                Appearance(
                    player_id=locked_player.id,
                    match_id=matches[1].id,
                    jersey_number=10,
                ),
                Appearance(
                    player_id=at_risk_player.id,
                    match_id=matches[0].id,
                    jersey_number=8,
                ),
            ]
        )
        session.commit()

    def test_session() -> Session:
        return Session(engine)

    app.dependency_overrides[get_session] = test_session
    try:
        with TestClient(app) as client:
            response = client.get("/teams/1/eligibility?as_of=2026-08-15")
            missing_response = client.get("/teams/99/eligibility?as_of=2026-08-15")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "team_id": 1,
        "team_name": "FC Burgwedel Ü40 I",
        "as_of": "2026-08-15",
        "lower_team_distance": 1,
        "players": [
            {
                "player_id": 1,
                "player_name": "Maik Fischer",
                "player_fussballde_id": "maik",
                "jersey_number": 10,
                "status": "locked",
                "matches_to_skip": 2,
                "eligible_on": None,
            },
            {
                "player_id": 2,
                "player_name": "Thomas Martens",
                "player_fussballde_id": "thomas",
                "jersey_number": 8,
                    "status": "eligible",
                "matches_to_skip": 0,
                "eligible_on": None,
            },
        ],
    }
    assert missing_response.status_code == 404


def test_new_season_resets_status_but_keeps_historical_players_visible(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'season-reset.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        team = Team(name="FC Burgwedel Ü40 I")
        player = Player(name="Ben Boettcher")
        session.add_all([team, player])
        session.flush()
        matches = [
            Match(
                team_id=team.id,
                played_on=date(2026, 6, 3),
                competition="1. Kreisklasse",
                home_team="FC Burgwedel",
                away_team="Heesseler SV",
                finished=True,
                is_competitive=True,
            ),
            Match(
                team_id=team.id,
                played_on=date(2026, 6, 10),
                competition="1. Kreisklasse",
                home_team="FC Burgwedel",
                away_team="Gastverein",
                finished=True,
                is_competitive=True,
            ),
        ]
        session.add_all(matches)
        session.flush()
        session.add_all(
            [
                Appearance(player_id=player.id, match_id=match.id)
                for match in matches
            ]
        )
        session.commit()

        _, eligibilities = calculate_team_eligibilities(
            session,
            team_id=team.id,
            as_of=date(2026, 7, 29),
        )

    assert season_start(date(2026, 7, 29)) == date(2026, 7, 1)
    assert [item.player.name for item in eligibilities] == ["Ben Boettcher"]
    assert eligibilities[0].result.status is EligibilityStatus.ELIGIBLE
