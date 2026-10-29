"""Proactive monitoring: decide whether to send the user an agent check-in."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import AgentMessage, Task, TaskStatus, User, UserPreferences
from ..timeutils import now_local
from .service import run_agent_turn

log = logging.getLogger("gsd.monitor")

# Per-user throttle
_MIN_MINUTES_BETWEEN_CHECKINS = 30
# Quiet window after check-in where user has replied — don't stack messages
_REPLY_GRACE_MINUTES = 15


def maybe_checkin(db: Session, user: User) -> bool:
    """Returns True if a check-in was generated."""
    now = now_local()

    # 1. Throttle — no more than one check-in per hour
    recent = (
        db.query(AgentMessage)
        .filter(
            AgentMessage.user_id == user.id,
            AgentMessage.role == "checkin",
            AgentMessage.created_at > now - timedelta(minutes=_MIN_MINUTES_BETWEEN_CHECKINS),
        )
        .first()
    )
    if recent:
        return False

    # 2. Don't interrupt if the user is actively chatting
    last_user_msg = (
        db.query(AgentMessage)
        .filter(AgentMessage.user_id == user.id, AgentMessage.role == "user")
        .order_by(AgentMessage.created_at.desc()).first()
    )
    if last_user_msg and last_user_msg.created_at > now - timedelta(minutes=_REPLY_GRACE_MINUTES):
        return False

    # 3. Detect a concrete stall
    reason = _detect_stall(db, user.id, now)
    if not reason:
        return False

    prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
    if not prefs:
        return False

    # 4. Ask the agent to produce the check-in
        prompt = (
        f"[SYSTEM CHECK-IN] The scheduler observed: {reason}. "
        "Call get_today_context. Then ask the user ONE short, tone-matched question: "
        "WHY did they not start / finish that specific task? "
        "Do NOT give advice, do NOT propose a plan, do NOT call any other tool yet. "
        "Just one diagnostic question in your coaching tone."
    )
    try:
        run_agent_turn(db, user, prefs, prompt, trigger="checkin")
        log.info("checkin sent to user %s — reason: %s", user.id, reason)
        return True
    except Exception as e:
        log.exception("checkin failed for user %s: %s", user.id, e)
        return False


def _detect_stall(db: Session, user_id: int, now: datetime) -> str | None:
    # Overdue task whose slot ended >10 min ago
    overdue = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status == TaskStatus.overdue,
        )
        .order_by(Task.scheduled_end.asc())
        .first()
    )
    if overdue and overdue.scheduled_end and overdue.scheduled_end < now - timedelta(minutes=10):
        mins = int((now - overdue.scheduled_end).total_seconds() // 60)
        return f"task #{overdue.id} '{overdue.title}' has been overdue for {mins} min"

    # Repeatedly postponed (>=2) and still not completed
    postponed = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.postpone_count >= 2,
            Task.status.in_([TaskStatus.planned, TaskStatus.postponed]),
        )
        .first()
    )
    if postponed:
        return f"task #{postponed.id} '{postponed.title}' has been postponed {postponed.postpone_count} times"

    # Active task with no update in 45 min
    active = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status == TaskStatus.active,
            Task.updated_at < now - timedelta(minutes=45),
        )
        .first()
    )
    if active:
        return f"task #{active.id} '{active.title}' is marked active but has not been updated in 45+ min"

    return None