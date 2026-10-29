"""Singleton BackgroundScheduler: reminders, overdue marking, agent monitoring."""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import Reminder, Task, TaskStatus, User
from .notifications import dispatch_due
from .timeutils import now_local

log = logging.getLogger("gsd.scheduler")
_sched: BackgroundScheduler | None = None
_push_subs: dict[int, list[dict]] = {}
_monitor_every = 20  # seconds between monitor passes; agent itself is throttled hourly per-user
_tick_count = 0


def set_push_subscriptions(user_id: int, subs: list[dict]) -> None:
    _push_subs[user_id] = subs


def _tick():
    global _tick_count
    _tick_count += 1
    db: Session = SessionLocal()
    try:
        dispatch_due(db, _push_subs)
        _mark_overdue(db)
        _schedule_pending_task_reminders(db)
        if _tick_count % _monitor_every == 0:
            _run_monitor(db)
    except Exception as e:
        log.exception("scheduler tick failed: %s", e)
    finally:
        db.close()


def _run_monitor(db: Session) -> None:
    """Ask the monitor to consider each user. Internal throttling prevents spam."""
    from .agent.monitor import maybe_checkin
    users = db.query(User).all()
    for u in users:
        try:
            maybe_checkin(db, u)
        except Exception as e:
            log.exception("monitor error for user %s: %s", u.id, e)


def _mark_overdue(db: Session) -> None:
    now = now_local()
    stale = db.query(Task).filter(
        Task.status.in_([TaskStatus.planned, TaskStatus.active]),
        Task.scheduled_end.isnot(None),
        Task.scheduled_end < now,
    ).all()
    for t in stale:
        t.status = TaskStatus.overdue
        db.add(t)
    db.commit()


def _schedule_pending_task_reminders(db: Session) -> None:
    now = now_local()
    horizon = now + timedelta(hours=1)
    tasks = db.query(Task).filter(
        Task.status == TaskStatus.planned,
        Task.scheduled_start.isnot(None),
        Task.scheduled_start > now,
        Task.scheduled_start <= horizon,
    ).all()
    for t in tasks:
        exists = db.query(Reminder).filter_by(task_id=t.id, kind="task_start").first()
        if exists:
            continue
        db.add(Reminder(
            user_id=t.user_id, task_id=t.id, kind="task_start",
            remind_at=t.scheduled_start - timedelta(minutes=5),
            message=f"Starting soon: {t.title}",
        ))
    db.commit()

def start_scheduler() -> None:
    global _sched
    if not settings.ENABLE_SCHEDULER or _sched is not None:
        return
    _sched = BackgroundScheduler()
    _sched.add_job(_tick, "interval", seconds=30, id="gsd-tick", max_instances=1, coalesce=True)
    _sched.start()
    log.info("GSD scheduler started (monitor every %ss)", 30 * _monitor_every)