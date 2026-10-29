from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, user_prefs
from ..models import AgentMemory, FoodEntry, Idea, MoodEnergyLog, Task, User, UserPreferences, WaterEntry
from ..schemas import PrefsOut, PrefsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/prefs", response_model=PrefsOut)
def get_prefs(prefs: UserPreferences = Depends(user_prefs)):
    return prefs


@router.patch("/prefs", response_model=PrefsOut)
def update_prefs(payload: PrefsUpdate,
                 prefs: UserPreferences = Depends(user_prefs),
                 db: Session = Depends(get_db)):
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, k, v)
    db.commit()
    db.refresh(prefs)
    return prefs


@router.get("/export")
def export_all(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Full user data export (JSON). Nothing sensitive leaves your machine unless you deploy."""
    def rows(q, model):
        return [dict((c.name, getattr(r, c.name)) for c in model.__table__.columns) for r in q]
    return {
        "user": {"id": user.id, "email": user.email},
        "prefs": rows(db.query(UserPreferences).filter_by(user_id=user.id), UserPreferences),
        "tasks": rows(db.query(Task).filter_by(user_id=user.id), Task),
        "mood": rows(db.query(MoodEnergyLog).filter_by(user_id=user.id), MoodEnergyLog),
        "food": rows(db.query(FoodEntry).filter_by(user_id=user.id), FoodEntry),
        "water": rows(db.query(WaterEntry).filter_by(user_id=user.id), WaterEntry),
        "ideas": rows(db.query(Idea).filter_by(user_id=user.id), Idea),
        "memory": rows(db.query(AgentMemory).filter_by(user_id=user.id), AgentMemory),
    }


@router.delete("/account")
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"deleted": True}