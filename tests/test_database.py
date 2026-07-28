from datetime import date

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine
from app.models import Appearance, Match, Player, Team
from app.seed import SEED_TEAM_FUSSBALLDE_ID, SEED_TEAM_NAME, seed_team


def test_schema_creation_and_seed(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'test.db'}")

    Base.metadata.create_all(bind=engine)

    assert set(inspect(engine).get_table_names()) == {
        "appearances",
        "matches",
        "players",
        "team_sync_statuses",
        "teams",
    }

    team_columns = {column["name"] for column in inspect(engine).get_columns("teams")}
    match_columns = {column["name"] for column in inspect(engine).get_columns("matches")}
    appearance_columns = {column["name"] for column in inspect(engine).get_columns("appearances")}
    sync_status_columns = {
        column["name"] for column in inspect(engine).get_columns("team_sync_statuses")
    }

    assert {"id", "name", "fussballde_id"} <= team_columns
    assert {
        "team_id",
        "fussballde_id",
        "played_on",
        "kickoff_time",
        "competition",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "report_url",
        "finished",
        "is_competitive",
        "monitored_team_side",
    } <= match_columns
    player_columns = {column["name"] for column in inspect(engine).get_columns("players")}

    assert {"player_id", "match_id", "starter", "captain", "jersey_number"} <= appearance_columns
    assert {"name", "fussballde_id"} <= player_columns
    assert "display_name" in player_columns
    assert {"team_id", "last_successful_sync_at"} <= sync_status_columns

    with Session(engine) as session:
        team = seed_team(session)
        seeded_team = session.scalar(select(Team).where(Team.name == SEED_TEAM_NAME))

        assert team.name == SEED_TEAM_NAME
        assert team.fussballde_id == SEED_TEAM_FUSSBALLDE_ID
        assert seeded_team is not None
        assert seeded_team.id == team.id
        assert seed_team(session).id == team.id


def test_player_can_appear_for_different_teams_and_foreign_keys_are_enforced(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'relationships.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        first_team = Team(name="FC Burgwedel Ü40 I")
        second_team = Team(name="FC Burgwedel Ü40 II")
        player = Player(name="Max Müller")
        session.add_all([first_team, second_team, player])
        session.flush()

        first_match = Match(
            team_id=first_team.id,
            played_on=date(2026, 8, 1),
            competition="Kreisliga",
            home_team="FC Burgwedel Ü40 I",
            away_team="Gastverein",
            finished=True,
        )
        second_match = Match(
            team_id=second_team.id,
            played_on=date(2026, 8, 8),
            competition="Kreisliga",
            home_team="FC Burgwedel Ü40 II",
            away_team="Gastverein",
            finished=True,
        )
        session.add_all([first_match, second_match])
        session.flush()
        session.add_all(
            [
                Appearance(player_id=player.id, match_id=first_match.id, starter=True),
                Appearance(player_id=player.id, match_id=second_match.id, captain=True),
            ]
        )
        session.commit()

        assert len(player.appearances) == 2
        assert {appearance.match.team_id for appearance in player.appearances} == {
            first_team.id,
            second_team.id,
        }

    with Session(engine) as session:
        session.add(Appearance(player_id=999, match_id=999))
        with pytest.raises(IntegrityError):
            session.commit()


def test_fussballde_source_ids_are_unique(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'source-ids.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        team = Team(name="FC Burgwedel", fussballde_id="team-1")
        player = Player(name="Max Müller", fussballde_id="player-1")
        session.add_all([team, player])
        session.flush()

        match = Match(
            fussballde_id="match-1",
            team_id=team.id,
            played_on=date(2026, 8, 7),
            competition="Kreispokal",
            home_team="SSV Thönse",
            away_team="FC Burgwedel",
            finished=False,
        )
        session.add(match)
        session.commit()

    with Session(engine) as session:
        session.add(Player(name="Anderer Name", fussballde_id="player-1"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        team = session.scalar(select(Team).where(Team.fussballde_id == "team-1"))
        assert team is not None
        session.add(
            Match(
                fussballde_id="match-1",
                team_id=team.id,
                played_on=date(2026, 8, 14),
                competition="Meisterschaftsspiel",
                home_team="FC Burgwedel",
                away_team="SP Hannover 1",
                finished=False,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
