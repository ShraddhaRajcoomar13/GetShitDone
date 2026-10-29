from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import FocusSession, Goal, Task, TaskStatus


def weekly_summary(db: Session, user_id: int, week_start: str) -> dict:
    """Return a factual weekly summary. No scoring. No shaming."""
    start = datetime.fromisoformat(week_start + "T00:00:00")
    end = start + timedelta(days=7)
    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.created_at >= start, Task.created_at < end,
    ).all()
    completed = [t for t in tasks if t.status == TaskStatus.completed]
    postponed = [t for t in tasks if t.postpone_count >= 2 and t.status != TaskStatus.completed]
    overdue = [t for t in tasks if t.status == TaskStatus.overdue]
    blocked = [t for t in tasks if t.status == TaskStatus.blocked]

    est_sum = sum(t.estimated_minutes for t in completed) or 0
    act_sum = sum(t.actual_minutes for t in completed) or est_sum
    accuracy = (est_sum / act_sum) if act_sum else 1.0

    focus_minutes = db.query(func.coalesce(func.sum(FocusSession.planned_minutes), 0)).filter(
        FocusSession.user_id == user_id,
        FocusSession.started_at >= start, FocusSession.started_at < end,
        FocusSession.completed == True,  # noqa: E712
    ).scalar() or 0

    return {
        "week_start": week_start,
        "completed": len(completed),
        "total": len(tasks),
        "postponed": len(postponed),
        "overdue": len(overdue),
        "blocked": len(blocked),
        "focus_minutes": int(focus_minutes),
        "est_vs_actual_ratio": round(accuracy, 2),
        "notes": _summary_notes(completed, postponed, accuracy),
    }


def _summary_notes(completed: list, postponed: list, accuracy: float) -> list[str]:
    notes: list[str] = []
    if accuracy and accuracy < 0.7:
        notes.append("You consistently underestimate task duration. Try +50% on estimates for similar tasks.")
    elif accuracy and accuracy > 1.3:
        notes.append("You have spare capacity — you may be over-scheduling estimates.")
    if postponed:
        notes.append(f"{len(postponed)} task(s) were repeatedly postponed. Consider breaking them down or dropping them.")
    if not notes:
        notes.append("Progress noted. Keep going without over-correcting.")
    return notes


def goal_progress(db: Session, user_id: int, week_start: str) -> list[dict]:
    goals = db.query(Goal).filter_by(user_id=user_id, week_start=week_start).all()
    out = []
    for g in goals:
        tasks = db.query(Task).filter_by(goal_id=g.id, user_id=user_id).all()
        done = sum(1 for t in tasks if t.status == TaskStatus.completed)
        out.append({
            "goal_id": g.id,
            "title": g.title,
            "total": len(tasks),
            "completed": done,
            "progress_pct": int(100 * done / len(tasks)) if tasks else 0,
        })
    return out