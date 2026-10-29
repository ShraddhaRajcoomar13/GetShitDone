from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

from sqlalchemy.orm import Session

from ..models import DailyAvailability, FixedCommitment, Task, TaskStatus

DEFAULT_WORK_START = time(9, 0)
DEFAULT_WORK_END = time(18, 0)
MIN_SLOT = 15


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_time(s: str) -> time:
    h, m = s.split(":")[:2]
    return time(int(h), int(m))


def week_dates(week_start: str) -> list[date]:
    start = _parse_date(week_start)
    return [start + timedelta(days=i) for i in range(7)]


def get_day_availability(db: Session, user_id: int, day: date) -> int:
    row = db.query(DailyAvailability).filter_by(user_id=user_id, date=day.isoformat()).first()
    return row.available_minutes if row else 240


def get_day_commitments(db: Session, user_id: int, day: date) -> list[tuple[time, time]]:
    rows = db.query(FixedCommitment).filter_by(user_id=user_id, date=day.isoformat()).all()
    return [(_parse_time(r.start_time), _parse_time(r.end_time)) for r in rows]


def build_day_slots(
    day: date, commitments: list[tuple[time, time]],
    work_start: time = DEFAULT_WORK_START, work_end: time = DEFAULT_WORK_END,
) -> list[tuple[datetime, datetime]]:
    """Return contiguous free time blocks within working hours, excluding commitments."""
    day_dt = datetime.combine(day, time(0, 0))
    ws = day_dt.replace(hour=work_start.hour, minute=work_start.minute)
    we = day_dt.replace(hour=work_end.hour, minute=work_end.minute)
    blocks = [(ws, we)]
    for cs, ce in sorted(commitments):
        cs_dt = day_dt.replace(hour=cs.hour, minute=cs.minute)
        ce_dt = day_dt.replace(hour=ce.hour, minute=ce.minute)
        new_blocks = []
        for bs, be in blocks:
            if ce_dt <= bs or cs_dt >= be:
                new_blocks.append((bs, be))
                continue
            if bs < cs_dt:
                new_blocks.append((bs, cs_dt))
            if be > ce_dt:
                new_blocks.append((ce_dt, be))
        blocks = new_blocks
    return [(s, e) for s, e in blocks if (e - s).total_seconds() >= MIN_SLOT * 60]


def suggest_schedule(
    db: Session,
    user_id: int,
    week_start: str,
    work_hours_start: str = "09:00",
    work_hours_end: str = "18:00",
) -> dict:
    """Greedy scheduler: sorts tasks by (deadline, priority desc, size asc) and places them
    into available slots. Returns {scheduled: [...], unscheduled: [...], conflicts: [...]}."""
    days = week_dates(week_start)
    ws = _parse_time(work_hours_start)
    we = _parse_time(work_hours_end)
    
    parent_ids = {
    row[0]
    for row in db.query(Task.parent_task_id)
    .filter(Task.user_id == user_id, Task.parent_task_id.isnot(None))
    .distinct()
    .all()
    }   

    pending = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status.in_([TaskStatus.planned, TaskStatus.postponed, TaskStatus.overdue]),
            Task.id.notin_(parent_ids) if parent_ids else True,
        )
        .all()
    )
    pending.sort(key=lambda t: (
        t.deadline or datetime.max,
        -t.priority,
        t.estimated_minutes,
    ))

    scheduled: list[dict] = []
    unscheduled: list[dict] = []
    conflicts: list[dict] = []

    # Per-day capacity in minutes and free blocks
    day_state: dict[str, dict] = {}
    for d in days:
        caps = get_day_availability(db, user_id, d)
        day_state[d.isoformat()] = {
            "remaining": caps,
            "blocks": build_day_slots(d, get_day_commitments(db, user_id, d), ws, we),
        }

    for task in pending:
        placed = False
        # Prefer days before the deadline
        deadline_dt = task.deadline
        candidate_days = days
        if deadline_dt:
            candidate_days = [d for d in days if datetime.combine(d, time(23, 59)) <= deadline_dt] or days

        for d in candidate_days:
            state = day_state[d.isoformat()]
            if state["remaining"] < task.estimated_minutes:
                continue
            for i, (bs, be) in enumerate(state["blocks"]):
                free_min = int((be - bs).total_seconds() // 60)
                if free_min < task.estimated_minutes:
                    continue
                end = bs + timedelta(minutes=task.estimated_minutes)
                scheduled.append({
                    "task_id": task.id,
                    "scheduled_start": bs.isoformat(),
                    "scheduled_end": end.isoformat(),
                })
                state["remaining"] -= task.estimated_minutes
                # Trim the block
                state["blocks"][i] = (end, be)
                placed = True
                break
            if placed:
                break

        if not placed:
            unscheduled.append({"task_id": task.id, "reason": "insufficient_capacity"})
            conflicts.append({
                "task_id": task.id,
                "issue": "No slot fits based on declared availability.",
            })

    return {"scheduled": scheduled, "unscheduled": unscheduled, "conflicts": conflicts}


def apply_schedule(db: Session, user_id: int, plan: dict) -> list[Task]:
    updated = []
    for entry in plan["scheduled"]:
        task = db.get(Task, entry["task_id"])
        if not task or task.user_id != user_id:
            continue
        if task.original_scheduled_start is None and task.scheduled_start is not None:
            task.original_scheduled_start = task.scheduled_start
        task.scheduled_start = datetime.fromisoformat(entry["scheduled_start"])
        task.scheduled_end = datetime.fromisoformat(entry["scheduled_end"])
        task.status = TaskStatus.planned
        db.add(task)
        updated.append(task)
    db.commit()
    return updated


def reschedule_unfinished(db: Session, user_id: int, task: Task, reason: str = "missed") -> Task:
    """Carry a task forward by postponing. Increments postpone_count. Does NOT duplicate."""
    task.postpone_count = (task.postpone_count or 0) + 1
    task.status = TaskStatus.postponed
    if task.original_scheduled_start is None:
        task.original_scheduled_start = task.scheduled_start
    task.scheduled_start = None
    task.scheduled_end = None
    task.blocker = reason
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def conflicts_for_task(db: Session, user_id: int, task_id: int, new_start: datetime) -> list[dict]:
    task = db.get(Task, task_id)
    if not task:
        return []
    d = new_start.date()
    # Exclude this task when checking
    others = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.id != task_id,
                Task.scheduled_start != None, Task.scheduled_end != None)  # noqa: E711
        .all()
    )
    new_end = new_start + timedelta(minutes=task.estimated_minutes)
    conflicts = []
    for o in others:
        if o.scheduled_start.date() != d:
            continue
        if new_start < o.scheduled_end and new_end > o.scheduled_start:
            conflicts.append({"task_id": o.id, "title": o.title})
    for cs, ce in get_day_commitments(db, user_id, d):
        cs_dt = datetime.combine(d, cs)
        ce_dt = datetime.combine(d, ce)
        if new_start < ce_dt and new_end > cs_dt:
            conflicts.append({"commitment": f"{cs.strftime('%H:%M')}-{ce.strftime('%H:%M')}"})
    return conflicts

