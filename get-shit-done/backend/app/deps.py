from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserPreferences
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    uid = decode_token(token)
    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def user_prefs(user: User = Depends(current_user), db: Session = Depends(get_db)) -> UserPreferences:
    pref = db.query(UserPreferences).filter_by(user_id=user.id).first()
    if not pref:
        pref = UserPreferences(user_id=user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref