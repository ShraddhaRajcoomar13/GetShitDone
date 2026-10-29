from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Goal, Task, User
from ..schemas import GoalCreate, GoalOut, GoalUpdate, TaskOut

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=list[GoalOut])
def list_goals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.query(Goal).filter_by(user_id=user.id).order_by(Goal.week_start.desc()).all()


@router.post("", response_model=GoalOut)
def create_goal(payload: GoalCreate,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = Goal(user_id=user.id, **payload.model_dump())
    db.add(g); db.commit(); db.refresh(g)
    return g


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, payload: GoalUpdate,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.get(Goal, goal_id)
    if not g or g.user_id != user.id:
        raise HTTPException(404, "Not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(g, k, v)
    db.commit(); db.refresh(g)
    return g


@router.get("/{goal_id}/tasks", response_model=list[TaskOut])
def goal_tasks(goal_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.get(Goal, goal_id)
    if not g or g.user_id != user.id:
        raise HTTPException(404, "Not found")
    return db.query(Task).filter_by(goal_id=goal_id, user_id=user.id).all()


@router.delete("/{goal_id}")
def delete_goal(goal_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.get(Goal, goal_id)
    if not g or g.user_id != user.id:
        raise HTTPException(404, "Not found")
    # Detach any tasks so they survive (become unscheduled, goal-less)
    db.query(Task).filter_by(goal_id=goal_id, user_id=user.id).update({Task.goal_id: None})
    db.delete(g)
    db.commit()
    return {"deleted": goal_id}