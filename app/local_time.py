"""Time helpers for dates displayed to the FC Burgwedel team."""

from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN_TIMEZONE = ZoneInfo("Europe/Berlin")


def now_in_berlin() -> datetime:
    """Return the current Berlin wall-clock time for persisted sync metadata."""
    return datetime.now(BERLIN_TIMEZONE).replace(tzinfo=None)


def today_in_berlin() -> datetime:
    """Return today's calendar date in Berlin."""
    return datetime.now(BERLIN_TIMEZONE).date()
