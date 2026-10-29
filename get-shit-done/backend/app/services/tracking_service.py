from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import MoodEnergyLog, WaterEntry
from ..timeutils import now_local, start_of_day, today_local


def hydration_today(db: Session, user_id: int) -> int:
    start = start_of_day(today_local())
    val = db.query(func.coalesce(func.sum(WaterEntry.amount_ml), 0)).filter(
        WaterEntry.user_id == user_id, WaterEntry.logged_at >= start
    ).scalar()
    return int(val or 0)


def mood_energy_series(db: Session, user_id: int, days: int = 14) -> list[dict]:
    since = now_local() - timedelta(days=days)
    rows = (
        db.query(MoodEnergyLog)
        .filter(MoodEnergyLog.user_id == user_id, MoodEnergyLog.logged_at >= since)
        .order_by(MoodEnergyLog.logged_at.asc())
        .all()
    )
    return [
        {"logged_at": r.logged_at.isoformat(), "mood": r.mood, "energy": r.energy}
        for r in rows
    ]


def cautious_correlation_note(db: Session, user_id: int) -> str:
    entries = (
        db.query(MoodEnergyLog)
        .filter(MoodEnergyLog.user_id == user_id, MoodEnergyLog.energy.isnot(None))
        .order_by(MoodEnergyLog.logged_at.desc())
        .limit(30)
        .all()
    )
    if len(entries) < 7:
        return "Log at least a week of energy check-ins to unlock gentle pattern notes."
    high = [e for e in entries if e.energy >= 4]
    low = [e for e in entries if e.energy <= 2]
    if not high or not low:
        return "Your energy has been fairly consistent recently."
    return (
        f"You've logged {len(high)} high-energy and {len(low)} low-energy days in the last 30 check-ins. "
        "Consider reserving deep-work for high-energy days and administrative tasks for low-energy ones."
    )