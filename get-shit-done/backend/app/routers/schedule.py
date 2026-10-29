from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import DailyAvailability, FixedCommitment, Task, User
from ..schemas import AvailabilityIn, CommitmentIn, TaskOut
from ..services import schedule_service
from ..timeutils import today_local, start_of_day, end_of_day

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.post("/availability")
def set_availability(payload: AvailabilityIn,
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(DailyAvailability).filter_by(user_id=user.id, date=payload.date).first()
    if row:
        row.available_minutes = payload.available_minutes
    else:
        db.add(DailyAvailability(user_id=user.id, **payload.model_dump()))
    db.commit()
    return {"ok": True}


@router.post("/commitments")
def add_commitment(payload: CommitmentIn,
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = FixedCommitment(user_id=user.id, **payload.model_dump())
    db.add(c)
    db.commit()
    return {"id": c.id}


@router.get("/commitments")
def list_commitments(date: str | None = None,
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(FixedCommitment).filter_by(user_id=user.id)
    if date:
        q = q.filter_by(date=date)
    return [
        {"id": c.id, "title": c.title, "date": c.date, "start_time": c.start_time, "end_time": c.end_time}
        for c in q.all()
    ]


@router.get("/suggest")
def suggest(week_start: str,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import UserPreferences
    prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
    plan = schedule_service.suggest_schedule(
        db, user.id, week_start,
        work_hours_start=prefs.work_hours_start if prefs else "09:00",
        work_hours_end=prefs.work_hours_end if prefs else "18:00",
    )
    return plan


@router.post("/apply")
def apply(week_start: str,
          user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import UserPreferences
    prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
    plan = schedule_service.suggest_schedule(
        db, user.id, week_start,
        work_hours_start=prefs.work_hours_start if prefs else "09:00",
        work_hours_end=prefs.work_hours_end if prefs else "18:00",
    )
    tasks = schedule_service.apply_schedule(db, user.id, plan)
    return {"scheduled": [t.id for t in tasks], "unscheduled": plan["unscheduled"]}


@router.get("/today", response_model=list[TaskOut])
def today_tasks(user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_local()
    start = start_of_day(today)
    end = end_of_day(today)
    return db.query(Task).filter(
        Task.user_id == user.id,
        Task.scheduled_start >= start, Task.scheduled_start <= end,
    ).order_by(Task.scheduled_start.asc()).all()