from datetime import datetime

from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine
from app.models import Team, TeamSyncStatus
from app.services.daily_matchplan_sync import (
    next_sync_at,
    record_successful_matchplan_sync,
)


def test_next_sync_at_uses_same_day_when_time_is_still_in_the_future() -> None:
    now = datetime(2026, 7, 28, 3, 59, 59)

    assert next_sync_at(now, hour=4, minute=0) == datetime(2026, 7, 28, 4, 0)


def test_next_sync_at_uses_following_day_at_or_after_scheduled_time() -> None:
    now = datetime(2026, 7, 28, 4, 0)

    assert next_sync_at(now, hour=4, minute=0) == datetime(2026, 7, 29, 4, 0)


def test_successful_sync_is_recorded_even_when_no_match_changed(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'sync-status.db'}")
    Base.metadata.create_all(bind=engine)
    first_sync = datetime(2026, 7, 28, 4, 0)
    second_sync = datetime(2026, 7, 29, 4, 0)

    with Session(engine) as session:
        session.add(Team(name="FC Burgwedel Ü40 I", fussballde_id="HIGHER"))
        session.commit()

        record_successful_matchplan_sync(
            session,
            team_fussballde_id="HIGHER",
            synced_at=first_sync,
        )
        session.commit()
        record_successful_matchplan_sync(
            session,
            team_fussballde_id="HIGHER",
            synced_at=second_sync,
        )
        session.commit()

        statuses = session.query(TeamSyncStatus).all()

    assert len(statuses) == 1
    assert statuses[0].last_successful_sync_at == second_sync
