"""Server-side reminder dispatcher. Adds Reminder rows; scheduler loop fires them.
Delivery: creates an in-app notification row + optional Web Push if VAPID configured.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from .models import Reminder, UserPreferences

from .timeutils import now_local

try:
    from pywebpush import webpush, WebPushException  # type: ignore
except Exception:  # pywebpush optional
    webpush = None


def dispatch_due(db: Session, push_subscriptions: dict[int, list[dict]]) -> int:
    now = now_local()
    due = (
        db.query(Reminder)
        .filter(Reminder.sent_at.is_(None), Reminder.remind_at <= now)
        .limit(200)
        .all()
    )
    count = 0
    for r in due:
        prefs = db.query(UserPreferences).filter_by(user_id=r.user_id).first()
        if prefs and _in_quiet_hours(now, prefs.quiet_hours_start, prefs.quiet_hours_end):
            r.remind_at = now.replace(hour=_parse_hour(prefs.quiet_hours_end), minute=0, second=0)
            db.add(r)
            continue
        r.sent_at = now
        db.add(r)
        count += 1
        if push_subscriptions.get(r.user_id) and webpush is not None:
            from .config import settings
            if settings.VAPID_PRIVATE_KEY:
                for sub in push_subscriptions[r.user_id]:
                    try:
                        webpush(
                            subscription_info=sub,
                            data=r.message or f"Reminder: {r.kind}",
                            vapid_private_key=settings.VAPID_PRIVATE_KEY,
                            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}"},
                        )
                    except WebPushException:
                        pass
    db.commit()
    return count

def _parse_hour(hhmm: str) -> int:
    try:
        return int(hhmm.split(":")[0])
    except Exception:
        return 22


def _in_quiet_hours(now: datetime, start: str, end: str) -> bool:
    s, e = _parse_hour(start), _parse_hour(end)
    h = now.hour
    if s <= e:
        return s <= h < e
    return h >= s or h < e