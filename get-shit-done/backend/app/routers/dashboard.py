from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, user_prefs
from ..models import FocusSession, MoodEnergyLog, Task, TaskStatus, User, UserPreferences
from ..schemas import DashboardOut, TaskOut
from ..services import progress_service, tracking_service
from ..timeutils import today_local, start_of_day

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(user: User = Depends(current_user),
              prefs: UserPreferences = Depends(user_prefs),
              db: Session = Depends(get_db)):
    today = today_local()
    start = start_of_day(today)
    end = start + timedelta(days=1)

    today_tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.scheduled_start >= start, Task.scheduled_start < end,
    ).order_by(Task.scheduled_start.asc()).all()

    done = [t for t in today_tasks if t.status == TaskStatus.completed]
    overdue = db.query(func.count(Task.id)).filter(
        Task.user_id == user.id, Task.status == TaskStatus.overdue
    ).scalar() or 0
    blocked = db.query(func.count(Task.id)).filter(
        Task.user_id == user.id, Task.status == TaskStatus.blocked
    ).scalar() or 0

    next_task = next((t for t in today_tasks if t.status in (TaskStatus.planned, TaskStatus.active)), None)

    focus_min = db.query(func.coalesce(func.sum(FocusSession.planned_minutes), 0)).filter(
        FocusSession.user_id == user.id,
        FocusSession.started_at >= start, FocusSession.started_at < end,
        FocusSession.completed == True,  # noqa: E712
    ).scalar() or 0

    monday = today - timedelta(days=today.weekday())
    goals = progress_service.goal_progress(db, user.id, monday.isoformat())

    hydration = tracking_service.hydration_today(db, user.id)
    #me = tracking_service.mood_energy_series(db, user.id, days=2)
    me = tracking_service.mood_energy_series(db, user.id, days=30)

    summary = (
        f"{len(done)}/{len(today_tasks)} tasks done today"
        f"{f', next: {next_task.title}' if next_task else ''}. "
        f"{overdue} overdue, {blocked} blocked."
    )

    return DashboardOut(
        today_tasks=[TaskOut.model_validate(t) for t in today_tasks],
        next_task=TaskOut.model_validate(next_task) if next_task else None,
        completed_today=len(done),
        planned_today=len(today_tasks),
        focus_minutes_today=int(focus_min),
        overdue_count=int(overdue),
        blocked_count=int(blocked),
        weekly_goal_progress=goals,
        hydration_ml_today=hydration,
        hydration_goal_ml=prefs.hydration_goal_ml,
        mood_energy=me,
        agent_summary=summary,
    )