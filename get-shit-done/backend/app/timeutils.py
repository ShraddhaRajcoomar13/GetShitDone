"""Timezone helpers. The app operates in APP_TIMEZONE (default Africa/Johannesburg).
All datetimes stored in the DB are naive and represent local (SAST) wall-clock time."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import settings


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.APP_TIMEZONE)


def now_local() -> datetime:
    """Naive local 'now' — matches how datetimes are stored (no tzinfo)."""
    return datetime.now(_tz()).replace(tzinfo=None)


def today_local() -> date:
    return datetime.now(_tz()).date()


def start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min)


def end_of_day(d: date) -> datetime:
    return datetime.combine(d, time.max)


def monday_of(d: date | None = None) -> date:
    d = d or today_local()
    return d - timedelta(days=d.weekday())


def to_local_naive(dt: datetime) -> datetime:
    """Convert any datetime (naive → assumed already local; aware → convert to local, strip tz)."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(_tz()).replace(tzinfo=None)