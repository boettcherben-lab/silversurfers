from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine
from app.models import Appearance, Match, Player, Team
from app.scrapers.fussballde import LineupEntry
from app.services.fussballde_import import MatchImport, import_match


def test_import_match_is_idempotent_and_imports_only_monitored_team(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'import.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        session.add(Team(name="FC Burgwedel Ü40 I", fussballde_id="higher-team"))
        session.commit()

        match_import = MatchImport(
            fussballde_id="match-1",
            team_fussballde_id="higher-team",
            monitored_team_side="home",
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
        lineup_entries = [
            LineupEntry("home-captain", "home", True, True, 1),
            LineupEntry("home-sub", "home", False, False, 9),
            LineupEntry("away-player", "away", True, False, 7),
        ]

        match = import_match(
            session,
            match_import,
            lineup_entries,
            {"home-captain": "Maik Fischer", "home-sub": "Thomas Martens"},
        )
        session.commit()

        assert match.id is not None
        assert session.scalar(select(Player).where(Player.fussballde_id == "away-player")) is None
        assert session.scalars(select(Appearance)).all()

        import_match(
            session,
            match_import,
            [
                LineupEntry("home-captain", "home", True, False, 1),
                LineupEntry("home-sub", "home", True, False, 10),
            ],
            {"home-captain": "Maik Fischer", "home-sub": "Thomas Martens"},
        )
        session.commit()

        matches = session.scalars(select(Match)).all()
        appearances = session.scalars(select(Appearance).order_by(Appearance.player_id)).all()

        assert len(matches) == 1
        assert matches[0].is_competitive is True
        assert len(appearances) == 2
        appearance_details = {
            (appearance.starter, appearance.captain, appearance.jersey_number)
            for appearance in appearances
        }

        assert appearance_details == {
            (True, False, 1),
            (True, False, 10),
        }
