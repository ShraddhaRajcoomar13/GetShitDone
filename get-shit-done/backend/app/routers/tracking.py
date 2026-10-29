from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, user_prefs
from ..models import FoodEntry, MoodEnergyLog, User, UserPreferences, WaterEntry
from ..schemas import (
    FoodIn, FoodOut, FoodUpdate,
    MoodEnergyIn, MoodEnergyOut, MoodEnergyUpdate,
    WaterIn,
)
from ..services import tracking_service

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


# ---------- Mood / Energy ----------

@router.post("/mood", response_model=MoodEnergyOut)
def log_mood(payload: MoodEnergyIn,
             user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = MoodEnergyLog(user_id=user.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.get("/mood", response_model=list[MoodEnergyOut])
def get_mood(user: User = Depends(current_user), days: int = 30,
             db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(MoodEnergyLog)
        .filter(MoodEnergyLog.user_id == user.id, MoodEnergyLog.logged_at >= since)
        .order_by(MoodEnergyLog.logged_at.desc())
        .all()
    )


@router.patch("/mood/{entry_id}", response_model=MoodEnergyOut)
def update_mood(entry_id: int, payload: MoodEnergyUpdate,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(MoodEnergyLog, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row


@router.delete("/mood/{entry_id}")
def delete_mood(entry_id: int,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(MoodEnergyLog, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404)
    db.delete(row); db.commit()
    return {"deleted": entry_id}


# ---------- Food ----------

@router.post("/food", response_model=FoodOut)
def log_food(payload: FoodIn,
             user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = FoodEntry(user_id=user.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row


@router.get("/food", response_model=list[FoodOut])
def get_food(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return (
        db.query(FoodEntry)
        .filter_by(user_id=user.id)
        .order_by(FoodEntry.logged_at.desc())
        .limit(100)
        .all()
    )


@router.patch("/food/{entry_id}", response_model=FoodOut)
def update_food(entry_id: int, payload: FoodUpdate,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(FoodEntry, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit(); db.refresh(row)
    return row


@router.delete("/food/{entry_id}")
def delete_food(entry_id: int,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(FoodEntry, entry_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404)
    db.delete(row); db.commit()
    return {"deleted": entry_id}


# ---------- Water ----------

@router.post("/water")
def log_water(payload: WaterIn,
              user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = WaterEntry(user_id=user.id, **payload.model_dump())
    db.add(row); db.commit()
    return {"id": row.id, "today_ml": tracking_service.hydration_today(db, user.id)}


@router.get("/water")
def get_water(user: User = Depends(current_user),
              prefs: UserPreferences = Depends(user_prefs),
              db: Session = Depends(get_db)):
    return {"today_ml": tracking_service.hydration_today(db, user.id),
            "goal_ml": prefs.hydration_goal_ml}


@router.get("/insights")
def insights(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"note": tracking_service.cautious_correlation_note(db, user.id)}