from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Task, TaskStatus, User
from ..schemas import TaskCreate, TaskOut, TaskUpdate
from ..services.schedule_service import conflicts_for_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(status: str | None = None,
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Task).filter(Task.user_id == user.id)
    if status:
        q = q.filter(Task.status == status)
    tasks_out = q.order_by(Task.scheduled_start.asc().nulls_last(), Task.priority.desc()).all()

    # Roll up subtask progress onto parent tasks
    counts: dict[int, Counter] = {}
    for t in tasks_out:
        if t.parent_task_id:
            c = counts.setdefault(t.parent_task_id, Counter())
            c["total"] += 1
            if t.status == TaskStatus.completed:
                c["done"] += 1
    for t in tasks_out:
        c = counts.get(t.id)
        if c:
            setattr(t, "subtask_progress", {"done": c["done"], "total": c["total"]})

    return tasks_out


@router.post("", response_model=TaskOut)
def create_task(payload: TaskCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = Task(user_id=user.id, **payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Task, task_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.post("/{task_id}/start", response_model=TaskOut)
def start_task(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Task, task_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Not found")
    t.status = TaskStatus.active
    db.commit()
    db.refresh(t)
    return t


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Task, task_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Not found")

    t.status = TaskStatus.completed
    if t.scheduled_start and t.scheduled_end:
        t.actual_minutes = int((t.scheduled_end - t.scheduled_start).total_seconds() // 60)

    # Option B: if this task is a subtask, auto-complete the parent when all siblings are done
    if t.parent_task_id is not None:
        siblings = (
            db.query(Task)
            .filter(Task.parent_task_id == t.parent_task_id, Task.user_id == user.id)
            .all()
        )
        if siblings and all(s.status == TaskStatus.completed for s in siblings):
            parent = db.get(Task, t.parent_task_id)
            if parent and parent.user_id == user.id and parent.status != TaskStatus.completed:
                parent.status = TaskStatus.completed
                db.add(parent)

    db.commit()
    db.refresh(t)
    return t


@router.get("/{task_id}/conflicts")
def task_conflicts(task_id: int, new_start: str,
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        dt = datetime.fromisoformat(new_start)
    except ValueError:
        raise HTTPException(400, "new_start must be ISO datetime")
    return {"conflicts": conflicts_for_task(db, user.id, task_id, dt)}


@router.delete("/{task_id}")
def delete_task(task_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Task, task_id)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(t)
    db.commit()
    return {"deleted": task_id}