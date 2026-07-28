"""Tests for the dashboard's Berlin-time clock."""

from datetime import datetime
from zoneinfo import ZoneInfo

import app.local_time as local_time


class _FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        assert tz == ZoneInfo("Europe/Berlin")
        return datetime(2026, 7, 29, 1, 0, tzinfo=tz)


def test_dashboard_time_uses_berlin_calendar_day(monkeypatch) -> None:
    monkeypatch.setattr(local_time, "datetime", _FixedDatetime)

    assert local_time.today_in_berlin().isoformat() == "2026-07-29"
    assert local_time.now_in_berlin() == datetime(2026, 7, 29, 1, 0)
