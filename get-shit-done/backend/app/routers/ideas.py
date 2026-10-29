from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Idea, Task, User
from ..schemas import IdeaIn, IdeaOut, IdeaUpdate

router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@router.get("", response_model=list[IdeaOut])
def list_ideas(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.query(Idea).filter_by(user_id=user.id).order_by(Idea.created_at.desc()).all()


@router.post("", response_model=IdeaOut)
def add_idea(payload: IdeaIn,
             user: User = Depends(current_user), db: Session = Depends(get_db)):
    i = Idea(user_id=user.id, **payload.model_dump())
    db.add(i); db.commit(); db.refresh(i)
    return i


@router.patch("/{idea_id}", response_model=IdeaOut)
def update_idea(idea_id: int, payload: IdeaUpdate,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    i = db.get(Idea, idea_id)
    if not i or i.user_id != user.id:
        raise HTTPException(404)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(i, k, v)
    db.commit(); db.refresh(i)
    return i


@router.post("/{idea_id}/to-task")
def idea_to_task(idea_id: int,
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    i = db.get(Idea, idea_id)
    if not i or i.user_id != user.id:
        raise HTTPException(404)
    t = Task(user_id=user.id, title=i.content[:140], estimated_minutes=30)
    db.add(t); i.status = "converted"; db.commit()
    return {"task_id": t.id}


@router.post("/{idea_id}/archive")
def archive(idea_id: int,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    i = db.get(Idea, idea_id)
    if not i or i.user_id != user.id:
        raise HTTPException(404)
    i.status = "archived"; db.commit()
    return {"ok": True}


@router.delete("/{idea_id}")
def delete_idea(idea_id: int,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    i = db.get(Idea, idea_id)
    if not i or i.user_id != user.id:
        raise HTTPException(404)
    db.delete(i); db.commit()
    return {"deleted": idea_id}