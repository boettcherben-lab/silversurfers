from datetime import date, datetime, time

from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, create_sqlite_engine
from app.models import Appearance, Match, Player, Team, TeamSyncStatus
from scripts import export_dashboard


def test_static_dashboard_export_contains_current_dashboard_data(tmp_path, monkeypatch) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'static-dashboard.db'}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(export_dashboard, "SessionLocal", session_factory)

    with Session(engine) as session:
        higher_team = Team(name="FC Burgwedel Ü40 I")
        lower_team = Team(name="FC Burgwedel Ü40 II")
        player = Player(name="Ben Boettcher", display_name="Ben")
        session.add_all([higher_team, lower_team, player])
        session.flush()
        session.add_all(
            [
                Match(
                    team_id=higher_team.id,
                    played_on=date(2026, 8, 7),
                    kickoff_time=time(19, 0),
                    competition="Kreispokal",
                    home_team="SSV Thönse",
                    away_team="FC Burgwedel",
                    finished=False,
                    is_competitive=True,
                ),
                Match(
                    team_id=lower_team.id,
                    played_on=date(2026, 8, 14),
                    competition="2. Kreisklasse",
                    home_team="FC Burgwedel II",
                    away_team="SG Adler",
                    finished=False,
                    is_competitive=True,
                ),
                Match(
                    team_id=higher_team.id,
                    played_on=date(2026, 6, 3),
                    competition="1. Kreisklasse",
                    home_team="FC Burgwedel",
                    away_team="Heesseler SV",
                    finished=True,
                    is_competitive=True,
                ),
            ]
        )
        session.flush()
        session.add(Appearance(player_id=player.id, match_id=3, jersey_number=10))
        session.add(
            TeamSyncStatus(
                team_id=higher_team.id,
                last_successful_sync_at=datetime(2026, 7, 29, 4, 17),
            )
        )
        session.commit()

    payload = export_dashboard.build_dashboard_payload(
        higher_team_id=1,
        lower_team_id=2,
        as_of=date(2026, 7, 29),
    )

    assert payload["next_higher_match"]["competition"] == "Kreispokal"
    assert payload["next_lower_match"]["competition"] == "2. Kreisklasse"
    assert payload["eligibility"]["players"][0]["player_name"] == "Ben"
    assert payload["eligibility"]["players"][0]["jersey_number"] == 10
    assert payload["sync_status"]["last_successful_sync_at"] == "2026-07-29T04:17:00"
