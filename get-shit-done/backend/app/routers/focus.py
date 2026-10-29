from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import FocusSession, Task, User
from ..schemas import FocusEnd, FocusStart

router = APIRouter(prefix="/api/focus", tags=["focus"])


@router.post("/start")
def start(payload: FocusStart, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = FocusSession(user_id=user.id, task_id=payload.task_id, planned_minutes=payload.planned_minutes)
    db.add(s)
    if payload.task_id:
        t = db.get(Task, payload.task_id)
        if t and t.user_id == user.id:
            t.status = "active"
    db.commit()
    return {"session_id": s.id}


@router.post("/end")
def end(payload: FocusEnd, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.get(FocusSession, payload.session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404)
    s.ended_at = datetime.utcnow()
    s.notes = payload.notes
    s.completed = payload.completed
    if s.task_id and payload.completed:
        t = db.get(Task, s.task_id)
        if t and t.user_id == user.id:
            t.status = "completed"
            t.actual_minutes = (t.actual_minutes or 0) + s.planned_minutes
    db.commit()
    return {"ok": True}