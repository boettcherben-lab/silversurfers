from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine
from app.models import Match, Team
from app.scrapers.fussballde_matchplan import ScheduledMatch
from app.services.fussballde_matchplan_import import (
    import_team_matchplan,
    is_relevant_competition,
)


def scheduled_match(match_id: str, competition: str) -> ScheduledMatch:
    return ScheduledMatch(
        fussballde_id=match_id,
        played_on=date(2026, 8, 7),
        kickoff_time=time(19, 0),
        competition=competition,
        home_team="SSV Thönse",
        away_team="FC Burgwedel",
        report_url=f"https://www.fussball.de/spiel/-/spiel/{match_id}",
        away_team_fussballde_id="TEAM123",
    )


def test_competition_classifier_accepts_only_relevant_competitions() -> None:
    assert is_relevant_competition("Kreispokal") is True
    assert is_relevant_competition("1. Kreisklasse") is True
    assert is_relevant_competition("Relegation") is True
    assert is_relevant_competition("Kreisfreundschaftsspiele") is False
    assert is_relevant_competition("Testspiel") is False


def test_import_team_matchplan_is_idempotent_and_skips_friendlies(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'matchplan-import.db'}")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        session.add(Team(name="FC Burgwedel Ü40 I", fussballde_id="TEAM123"))
        session.commit()

        summary = import_team_matchplan(
            session,
            team_fussballde_id="TEAM123",
            scheduled_matches=[
                scheduled_match("CUP1", "Kreispokal"),
                scheduled_match("LEAGUE1", "1. Kreisklasse"),
                scheduled_match("FRIENDLY1", "Kreisfreundschaftsspiele"),
            ],
        )
        session.commit()

        assert summary.created == 2
        assert summary.skipped == 1
        imported_matches = session.scalars(select(Match).order_by(Match.fussballde_id)).all()
        assert [match.fussballde_id for match in imported_matches] == ["CUP1", "LEAGUE1"]
        assert imported_matches[0].kickoff_time == time(19, 0)
        assert imported_matches[0].monitored_team_side == "away"
        assert all(match.is_competitive for match in imported_matches)

        imported_matches[0].finished = True
        session.commit()
        summary = import_team_matchplan(
            session,
            team_fussballde_id="TEAM123",
            scheduled_matches=[scheduled_match("CUP1", "Kreispokal")],
        )
        session.commit()

        assert summary.created == 0
        assert summary.updated == 1
        assert session.scalar(select(Match).where(Match.fussballde_id == "CUP1")).finished is True
