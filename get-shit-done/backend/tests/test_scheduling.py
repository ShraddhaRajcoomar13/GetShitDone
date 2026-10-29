from datetime import date, datetime, timedelta

from app.models import DailyAvailability, FixedCommitment, Task
from app.services import schedule_service


def test_build_day_slots_respects_commitments():
    d = date(2025, 1, 6)  # Monday
    blocks = schedule_service.build_day_slots(
        d, [(datetime.combine(d, datetime.min.time()).replace(hour=12).time(),
              datetime.combine(d, datetime.min.time()).replace(hour=13).time())]
    )
    total = sum(int((e - s).total_seconds() // 60) for s, e in blocks)
    assert total == 8 * 60  # 9–18 minus 1h lunch


def test_suggest_schedule_fills_within_capacity(auth_client, db_session=None):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # find user
        from app.models import User
        user = db.query(User).first() or User(email="x2@x.com", hashed_password="x")
        if user.id is None:
            db.add(user); db.commit()
        # 1 task of 120 min, 60 min availability
        db.add(Task(user_id=user.id, title="Big", estimated_minutes=120))
        db.add(DailyAvailability(user_id=user.id, date="2025-01-06", available_minutes=60))
        db.commit()
        plan = schedule_service.suggest_schedule(db, user.id, "2025-01-06")
        assert len(plan["unscheduled"]) >= 1
    finally:
        db.close()