from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..agent.service import run_agent_turn
from ..database import get_db
from ..deps import current_user, user_prefs
from ..models import User, UserPreferences
from ..schemas import ChatIn, ChatOut

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn,
         user: User = Depends(current_user),
         prefs: UserPreferences = Depends(user_prefs),
         db: Session = Depends(get_db)):
    result = run_agent_turn(db, user, prefs, payload.message)
    return ChatOut(reply=result["reply"], tool_calls=result["tool_calls"])


@router.get("/history")
def history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import AgentMessage
    rows = (
        db.query(AgentMessage).filter_by(user_id=user.id)
        .order_by(AgentMessage.created_at.asc()).limit(100).all()
    )
    return [{"role": r.role, "content": r.content, "tool": r.tool_name,
             "created_at": r.created_at.isoformat()} for r in rows]
@router.get("/checkins")
def recent_checkins(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    from ..models import AgentMessage
    cutoff = datetime.utcnow() - timedelta(hours=24)
    rows = (
        db.query(AgentMessage)
        .filter(
            AgentMessage.user_id == user.id,
            AgentMessage.role == "checkin",
            AgentMessage.created_at > cutoff,
        )
        .order_by(AgentMessage.created_at.desc())
        .limit(10)
        .all()
    )
    return [{"id": r.id, "content": r.content, "created_at": r.created_at.isoformat()} for r in rows]

@router.get("/debug_context")
def debug_context(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Run get_today_context directly and return its raw result or the exception."""
    import traceback
    from ..agent.tools import TOOLS, _SCHEMA_MAP, _get_today_context
    try:
        from ..agent.tools import EmptyInput
        result = _get_today_context(db, user.id, EmptyInput())
        return {"ok": True, "result": result}
    except Exception as e:
        return {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }

@router.get("/debug_agent_state")
def debug_agent_state(user: User = Depends(current_user), db: Session = Depends(get_db)):
    from ..models import AgentMessage
    rows = (
        db.query(AgentMessage)
        .filter_by(user_id=user.id)
        .order_by(AgentMessage.created_at.desc())
        .limit(10)
        .all()
    )
    return [
        {"id": r.id, "role": r.role, "content": (r.content or "")[:120],
         "tool_name": r.tool_name, "created_at": r.created_at.isoformat()}
        for r in rows
    ]