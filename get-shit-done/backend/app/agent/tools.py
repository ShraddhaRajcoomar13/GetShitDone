from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import (
    AgentMemory, FoodEntry, FocusSession, Goal, Idea, MoodEnergyLog,
    Reminder, Task, TaskStatus, UserPreferences, WaterEntry,
)
from ..services import schedule_service
from ..timeutils import now_local, today_local, start_of_day, to_local_naive

# ============================================================================
# INPUT SCHEMAS
# ============================================================================

class CreateTaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    outcome: str = ""
    smallest_first_action: str = ""
    goal_id: int | None = None
    priority: int = 3
    estimated_minutes: int = 30
    energy_required: int = 3
    task_type: str = "deep_work"
    completion_criteria: str = ""
    deadline: str | None = None


class DecomposeGoalIn(BaseModel):
    goal_id: int
    tasks: list[CreateTaskIn]
    create_parent: bool = True
    parent_title: str | None = None
    parent_estimated_minutes: int = 0


class UpdateTaskIn(BaseModel):
    task_id: int
    title: str | None = None
    outcome: str | None = None
    smallest_first_action: str | None = None
    priority: int | None = None
    estimated_minutes: int | None = None
    status: str | None = None


class TaskIdIn(BaseModel):
    task_id: int
    reason: str = ""


class ScheduleIn(BaseModel):
    week_start: str | None = None


class SetReminderIn(BaseModel):
    task_id: int | None = None
    kind: str = "task_start"
    remind_at: str
    message: str = ""


class MemoryIn(BaseModel):
    key: str
    value: str


class IdeaToTaskIn(BaseModel):
    idea_id: int
    estimated_minutes: int = 30


class DaysIn(BaseModel):
    days: int = 7


class TaskListIn(BaseModel):
    status: str | None = None
    include_completed: bool = False


class LogMoodIn(BaseModel):
    mood: int | None = None
    energy: int | None = None
    notes: str = ""


class LogWaterIn(BaseModel):
    amount_ml: int = 250


class LogFoodIn(BaseModel):
    meal_type: str = "snack"
    description: str = ""
    notes: str = ""


class LogFocusIn(BaseModel):
    task_id: int | None = None
    planned_minutes: int = 25
    
class RecordBlockerIn(BaseModel):
    task_id: int
    reason: str = Field(min_length=1, max_length=500)
    category: str = "other"   # avoidance|too_big|unclear|low_energy|health|external|other
    next_action: str = ""

class EmptyInput(BaseModel):
    """Concrete no-args input. Pydantic v2 refuses BaseModel() — always use a subclass."""
    pass


# ============================================================================
# TOOL TYPE
# ============================================================================

@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    fn: Callable[[Session, int, BaseModel], str]


def _ok(msg: str) -> str:
    return f"OK: {msg}"


def _err(msg: str) -> str:
    return f"ERROR: {msg}"


# ============================================================================
# WRITE TOOLS
# ============================================================================

def _create_task(db: Session, user_id: int, p: CreateTaskIn) -> str:
    t = Task(
        user_id=user_id, goal_id=p.goal_id, title=p.title,
        description=p.description, outcome=p.outcome,
        smallest_first_action=p.smallest_first_action,
        priority=p.priority, estimated_minutes=p.estimated_minutes,
        energy_required=p.energy_required,
        completion_criteria=p.completion_criteria,
        deadline=datetime.fromisoformat(p.deadline) if p.deadline else None,
    )
    db.add(t); db.commit(); db.refresh(t)
    return _ok(f"created task #{t.id} '{t.title}'")


def _decompose_goal(db: Session, user_id: int, p: DecomposeGoalIn) -> str:
    goal = db.get(Goal, p.goal_id)
    if not goal or goal.user_id != user_id:
        return _err("goal not found")

    parent: Task | None = None
    if p.create_parent:
        total = p.parent_estimated_minutes or sum(t.estimated_minutes for t in p.tasks)
        parent = Task(
            user_id=user_id, goal_id=goal.id,
            title=p.parent_title or goal.title,
            outcome=goal.target_outcome or "",
            estimated_minutes=total, priority=goal.priority,
        )
        db.add(parent); db.flush()

    created = []
    for tk in p.tasks:
        kwargs = tk.model_dump(exclude={"goal_id", "deadline"})
        t = Task(
            user_id=user_id, goal_id=goal.id,
            parent_task_id=parent.id if parent else None, **kwargs,
        )
        if tk.deadline:
            t.deadline = datetime.fromisoformat(tk.deadline)
        db.add(t); created.append(t)
    db.commit()

    parent_msg = f" under parent #{parent.id}" if parent else ""
    return _ok(f"created {len(created)} subtask(s){parent_msg}")


def _update_task(db: Session, user_id: int, p: UpdateTaskIn) -> str:
    t = db.get(Task, p.task_id)
    if not t or t.user_id != user_id:
        return _err("task not found")
    data = p.model_dump(exclude_unset=True, exclude={"task_id"})
    if "status" in data and data["status"]:
        try:
            data["status"] = TaskStatus(data["status"])
        except ValueError:
            return _err(f"invalid status {data['status']}")
    for k, v in data.items():
        setattr(t, k, v)
    db.commit()
    return _ok(f"updated task #{t.id}")


def _mark_started(db: Session, user_id: int, p: TaskIdIn) -> str:
    t = db.get(Task, p.task_id)
    if not t or t.user_id != user_id:
        return _err("task not found")
    t.status = TaskStatus.active
    db.commit()
    return _ok(f"task #{t.id} started")


def _complete_task(db: Session, user_id: int, p: TaskIdIn) -> str:
    t = db.get(Task, p.task_id)
    if not t or t.user_id != user_id:
        return _err("task not found")
    t.status = TaskStatus.completed
    if t.parent_task_id is not None:
        siblings = db.query(Task).filter_by(
            parent_task_id=t.parent_task_id, user_id=user_id
        ).all()
        if siblings and all(s.status == TaskStatus.completed for s in siblings):
            parent = db.get(Task, t.parent_task_id)
            if parent and parent.user_id == user_id and parent.status != TaskStatus.completed:
                parent.status = TaskStatus.completed
                db.add(parent)
    db.commit()
    return _ok(f"task #{t.id} completed")


def _postpone_task(db: Session, user_id: int, p: TaskIdIn) -> str:
    t = db.get(Task, p.task_id)
    if not t or t.user_id != user_id:
        return _err("task not found")
    schedule_service.reschedule_unfinished(db, user_id, t, reason=p.reason or "agent")
    return _ok(f"task #{t.id} postponed (count={t.postpone_count})")


def _suggest_and_apply(db: Session, user_id: int, p: ScheduleIn) -> str:
    prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()
    week_start = p.week_start
    if not week_start:
        #today = datetime.utcnow().date()
        today = today_local()
        monday = today - timedelta(days=today.weekday())
        week_start = monday.isoformat()
    plan = schedule_service.suggest_schedule(
        db, user_id, week_start,
        work_hours_start=prefs.work_hours_start if prefs else "09:00",
        work_hours_end=prefs.work_hours_end if prefs else "18:00",
    )
    schedule_service.apply_schedule(db, user_id, plan)
    return _ok(
        f"scheduled {len(plan['scheduled'])} task(s); "
        f"unscheduled={len(plan['unscheduled'])}; conflicts={len(plan['conflicts'])}"
    )


def _set_reminder(db: Session, user_id: int, p: SetReminderIn) -> str:
    try:
        when = to_local_naive(datetime.fromisoformat(p.remind_at))
    except ValueError:
        return _err("invalid remind_at")
    db.add(r); db.commit()
    return _ok(f"reminder #{r.id} at {when.isoformat()}")


def _remember(db: Session, user_id: int, p: MemoryIn) -> str:
    mem = db.query(AgentMemory).filter_by(user_id=user_id, key=p.key).first()
    if mem:
        mem.value = p.value
    else:
        db.add(AgentMemory(user_id=user_id, key=p.key, value=p.value))
    db.commit()
    return _ok(f"memory '{p.key}' stored")


def _idea_to_task(db: Session, user_id: int, p: IdeaToTaskIn) -> str:
    idea = db.get(Idea, p.idea_id)
    if not idea or idea.user_id != user_id:
        return _err("idea not found")
    t = Task(user_id=user_id, title=idea.content[:140],
             estimated_minutes=p.estimated_minutes)
    db.add(t); idea.status = "converted"; db.commit()
    return _ok(f"idea #{idea.id} → task #{t.id}")


def _log_mood(db: Session, user_id: int, p: LogMoodIn) -> str:
    row = MoodEnergyLog(user_id=user_id, mood=p.mood, energy=p.energy, notes=p.notes)
    db.add(row); db.commit()
    return _ok(f"logged mood={p.mood} energy={p.energy}")


def _log_water(db: Session, user_id: int, p: LogWaterIn) -> str:
    db.add(WaterEntry(user_id=user_id, amount_ml=p.amount_ml))
    db.commit()
    today = today_local()
    start = start_of_day(today)
    total = db.query(func.coalesce(func.sum(WaterEntry.amount_ml), 0)).filter(
        WaterEntry.user_id == user_id, WaterEntry.logged_at >= start
    ).scalar() or 0
    return _ok(f"+{p.amount_ml}ml logged; today total {int(total)}ml")


def _log_food(db: Session, user_id: int, p: LogFoodIn) -> str:
    if not p.description.strip():
        return _err("description required")
    db.add(FoodEntry(
        user_id=user_id, meal_type=p.meal_type,
        description=p.description, notes=p.notes,
    ))
    db.commit()
    return _ok(f"logged {p.meal_type}: {p.description[:60]}")


def _log_focus(db: Session, user_id: int, p: LogFocusIn) -> str:
    s = FocusSession(user_id=user_id, task_id=p.task_id,
                     planned_minutes=p.planned_minutes)
    db.add(s)
    if p.task_id:
        t = db.get(Task, p.task_id)
        if t and t.user_id == user_id:
            t.status = TaskStatus.active
    db.commit(); db.refresh(s)
    return _ok(f"focus session #{s.id} started ({p.planned_minutes} min)")

def _record_blocker(db: Session, user_id: int, p: RecordBlockerIn) -> str:
    t = db.get(Task, p.task_id)
    if not t or t.user_id != user_id:
        return _err("task not found")
    allowed = {"avoidance", "too_big", "unclear", "low_energy", "health", "external", "other"}
    cat = p.category if p.category in allowed else "other"
    t.blocker = f"[{cat}] {p.reason}"
    if cat in {"avoidance", "too_big", "unclear", "low_energy"}:
        t.status = TaskStatus.blocked
    db.commit()
    msg = f"recorded blocker on #{t.id} ({cat}): {p.reason[:120]}"
    if p.next_action:
        msg += f" | next: {p.next_action}"
    return _ok(msg)
# ============================================================================
# READ TOOLS
# ============================================================================

def _get_status(db: Session, user_id: int, p: EmptyInput) -> str:
    today = today_local()
    start = start_of_day(today)
    end = start + timedelta(days=1)
    today_tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.scheduled_start >= start, Task.scheduled_start < end,
    ).all()
    done = sum(1 for t in today_tasks if t.status == TaskStatus.completed)
    postponed = db.query(Task).filter(
        Task.user_id == user_id,
        Task.postpone_count >= 2,
        Task.status != TaskStatus.completed,
    ).all()
    lines = [f"Today: {done}/{len(today_tasks)} tasks done."]
    if postponed:
        lines.append("Repeatedly postponed: " + ", ".join(
            f"#{t.id} {t.title}" for t in postponed[:5]
        ))
    return _ok(" ".join(lines))


def _get_today_context(db: Session, user_id: int, p: EmptyInput) -> str:
    today = today_local()
    start = start_of_day(today)
    end = start + timedelta(days=1)

    def status_str(t):
        s = getattr(t, "status", None)
        return s.value if hasattr(s, "value") else str(s)

    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.scheduled_start >= start, Task.scheduled_start < end,
    ).order_by(Task.scheduled_start).all()

    overdue = db.query(Task).filter(
        Task.user_id == user_id, Task.status == TaskStatus.overdue
    ).count()
    blocked = db.query(Task).filter(
        Task.user_id == user_id, Task.status == TaskStatus.blocked
    ).count()

    water = db.query(func.coalesce(func.sum(WaterEntry.amount_ml), 0)).filter(
        WaterEntry.user_id == user_id, WaterEntry.logged_at >= start
    ).scalar() or 0
    prefs = db.query(UserPreferences).filter_by(user_id=user_id).first()
    goal = prefs.hydration_goal_ml if prefs else 2000

    mood = db.query(MoodEnergyLog).filter(
        MoodEnergyLog.user_id == user_id, MoodEnergyLog.logged_at >= start
    ).order_by(MoodEnergyLog.logged_at.desc()).first()

    focus_min = db.query(func.coalesce(func.sum(FocusSession.planned_minutes), 0)).filter(
        FocusSession.user_id == user_id,
        FocusSession.started_at >= start, FocusSession.started_at < end,
        FocusSession.completed == True,  # noqa: E712
    ).scalar() or 0

    foods = db.query(FoodEntry).filter(
        FoodEntry.user_id == user_id, FoodEntry.logged_at >= start
    ).order_by(FoodEntry.logged_at).all()

    lines = [f"TODAY ({today.isoformat()}):"]
    if tasks:
        for t in tasks:
            hh = t.scheduled_start.strftime("%H:%M") if t.scheduled_start else "??"
            lines.append(
                f"  • {hh} #{t.id} '{t.title}' [{status_str(t)}] "
                f"({t.estimated_minutes or 0}m)"
            )
    else:
        lines.append("  no scheduled tasks")
    lines.append(f"Overdue: {overdue} · Blocked: {blocked} · Focus today: {int(focus_min)}m")
    lines.append(f"Water: {int(water)}/{goal} ml")

    if mood:
        lines.append(f"Latest mood/energy: {mood.mood or '?'}/5, {mood.energy or '?'}/5")
    else:
        lines.append("No mood/energy check-in today")

    if foods:
        meal_strs = []
        for f in foods:
            desc = (f.description or "")[:40]
            ts = f.logged_at.strftime("%H:%M") if f.logged_at else "??:??"
            meal_strs.append(f"{f.meal_type or 'meal'} @{ts}: {desc}")
        lines.append(f"Meals logged ({len(foods)}): " + "; ".join(meal_strs))
    else:
        lines.append("No food logged today")

    return _ok("\n".join(lines))


def _get_tracking_summary(db: Session, user_id: int, p: DaysIn) -> str:
    since = now_local() - timedelta(days=p.days)
    moods = db.query(MoodEnergyLog).filter(
        MoodEnergyLog.user_id == user_id, MoodEnergyLog.logged_at >= since
    ).order_by(MoodEnergyLog.logged_at.desc()).limit(30).all()
    waters = db.query(func.coalesce(func.sum(WaterEntry.amount_ml), 0)).filter(
        WaterEntry.user_id == user_id, WaterEntry.logged_at >= since
    ).scalar() or 0
    foods = db.query(FoodEntry).filter(
        FoodEntry.user_id == user_id, FoodEntry.logged_at >= since
    ).order_by(FoodEntry.logged_at.desc()).limit(30).all()

    lines = [f"Last {p.days} days:"]
    mvals = [m.mood for m in moods if m.mood]
    evals = [m.energy for m in moods if m.energy]
    if mvals:
        lines.append(f"  Mood avg: {sum(mvals)/len(mvals):.1f}/5 ({len(mvals)} check-ins)")
    if evals:
        lines.append(f"  Energy avg: {sum(evals)/len(evals):.1f}/5 ({len(evals)} check-ins)")
    if not mvals and not evals:
        lines.append("  No mood/energy check-ins")
    lines.append(f"  Water total: {int(waters)} ml")
    if foods:
        lines.append(f"  Meals ({len(foods)}):")
        for f in foods[:12]:
            lines.append(
                f"    – {f.logged_at.strftime('%a %H:%M')} "
                f"{f.meal_type}: {(f.description or '')[:80]}"
            )
    else:
        lines.append("  No food logged")
    return _ok("\n".join(lines))


def _list_tasks(db: Session, user_id: int, p: TaskListIn) -> str:
    q = db.query(Task).filter(Task.user_id == user_id)
    if p.status:
        try:
            q = q.filter(Task.status == TaskStatus(p.status))
        except ValueError:
            return _err(f"invalid status {p.status}")
    elif not p.include_completed:
        q = q.filter(Task.status != TaskStatus.completed)
    tasks = q.order_by(Task.scheduled_start.asc().nulls_last()).limit(50).all()
    if not tasks:
        return _ok("No matching tasks.")
    lines = []
    for t in tasks:
        when = t.scheduled_start.strftime("%a %H:%M") if t.scheduled_start else "unscheduled"
        lines.append(
            f"#{t.id} [{t.status.value}] {when} '{t.title}' "
            f"({t.estimated_minutes}m, pri {t.priority}, postponed {t.postpone_count}×)"
        )
    return _ok("\n".join(lines))


def _get_ideas(db: Session, user_id: int, p: EmptyInput) -> str:
    ideas = db.query(Idea).filter(
        Idea.user_id == user_id, Idea.status == "inbox"
    ).order_by(Idea.created_at.desc()).limit(20).all()
    if not ideas:
        return _ok("No pending ideas.")
    return _ok("\n".join(f"#{i.id} {i.content[:100]}" for i in ideas))


def _recall_memory(db: Session, user_id: int, p: EmptyInput) -> str:
    rows = db.query(AgentMemory).filter_by(user_id=user_id).all()
    if not rows:
        return _ok("No stored memory about this user yet.")
    return _ok("\n".join(f"{r.key}: {r.value}" for r in rows))


def _list_goals(db: Session, user_id: int, p: EmptyInput) -> str:
    goals = db.query(Goal).filter_by(user_id=user_id).order_by(
        Goal.week_start.desc()
    ).limit(20).all()
    if not goals:
        return _ok("No goals.")
    return _ok("\n".join(
        f"#{g.id} [{g.status.value}] {g.title} (week {g.week_start})" for g in goals
    ))


# ============================================================================
# REGISTRY
# ============================================================================

def _build_registry() -> dict[str, Tool]:
    return {
        # Write tools
        "create_task": Tool(
            "create_task", "Create a new task for the user.",
            CreateTaskIn.model_json_schema(), _create_task,
        ),
        "decompose_goal": Tool(
            "decompose_goal",
            "Attach subtasks to a goal (optionally wrapped in a parent task).",
            DecomposeGoalIn.model_json_schema(), _decompose_goal,
        ),
        "update_task": Tool(
            "update_task", "Update fields of a task.",
            UpdateTaskIn.model_json_schema(), _update_task,
        ),
        "mark_task_started": Tool(
            "mark_task_started", "Mark a task as active.",
            TaskIdIn.model_json_schema(), _mark_started,
        ),
        "complete_task": Tool(
            "complete_task", "Mark a task completed.",
            TaskIdIn.model_json_schema(), _complete_task,
        ),
        "postpone_task": Tool(
            "postpone_task", "Postpone a task.",
            TaskIdIn.model_json_schema(), _postpone_task,
        ),
        "suggest_and_apply_schedule": Tool(
            "suggest_and_apply_schedule",
            "Generate and persist a weekly schedule.",
            ScheduleIn.model_json_schema(), _suggest_and_apply,
        ),
        "set_reminder": Tool(
            "set_reminder", "Create a persisted reminder.",
            SetReminderIn.model_json_schema(), _set_reminder,
        ),
        "remember": Tool(
            "remember", "Persist a fact/preference about the user.",
            MemoryIn.model_json_schema(), _remember,
        ),
        "idea_to_task": Tool(
            "idea_to_task", "Convert a captured idea into a task.",
            IdeaToTaskIn.model_json_schema(), _idea_to_task,
        ),
        "log_mood": Tool(
            "log_mood", "Log the user's mood and energy (1-5).",
            LogMoodIn.model_json_schema(), _log_mood,
        ),
        "log_water": Tool(
            "log_water", "Log water intake.",
            LogWaterIn.model_json_schema(), _log_water,
        ),
        "log_food": Tool(
            "log_food", "Log a meal or snack.",
            LogFoodIn.model_json_schema(), _log_food,
        ),
        "log_focus": Tool(
            "log_focus", "Start a focus session.",
            LogFocusIn.model_json_schema(), _log_focus,
        ),
        # Read tools
        "get_status": Tool(
            "get_status", "Quick today status counts.",
            {}, _get_status,
        ),
        "get_today_context": Tool(
            "get_today_context",
            "Full snapshot of today: tasks, overdue, water, mood, food, focus.",
            {}, _get_today_context,
        ),
        "get_tracking_summary": Tool(
            "get_tracking_summary",
            "Summary of mood, energy, water, food over the last N days.",
            DaysIn.model_json_schema(), _get_tracking_summary,
        ),
        "list_tasks": Tool(
            "list_tasks", "List tasks, optionally filtered by status.",
            TaskListIn.model_json_schema(), _list_tasks,
        ),
        "get_ideas": Tool(
            "get_ideas", "List pending ideas.",
            {}, _get_ideas,
        ),
        "recall_memory": Tool(
            "recall_memory", "Recall stored user memory.",
            {}, _recall_memory,
        ),
        "list_goals": Tool(
            "list_goals", "List user goals.",
            {}, _list_goals,
        ),
                "record_blocker": Tool(
            "record_blocker",
            "Record WHY a task wasn't done: categorise (avoidance/too_big/unclear/"
            "low_energy/health/external/other), store the reason, propose a next action.",
            RecordBlockerIn.model_json_schema(), _record_blocker,
        ),
    }


TOOLS = _build_registry()


# ============================================================================
# SCHEMA MAP (must exist at module level — used by execute_tool)
# ============================================================================

_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    "create_task": CreateTaskIn,
    "decompose_goal": DecomposeGoalIn,
    "update_task": UpdateTaskIn,
    "mark_task_started": TaskIdIn,
    "complete_task": TaskIdIn,
    "postpone_task": TaskIdIn,
    "suggest_and_apply_schedule": ScheduleIn,
    "set_reminder": SetReminderIn,
    "remember": MemoryIn,
    "idea_to_task": IdeaToTaskIn,
    "log_mood": LogMoodIn,
    "log_water": LogWaterIn,
    "log_food": LogFoodIn,
    "log_focus": LogFocusIn,
    "get_status": EmptyInput,
    "get_today_context": EmptyInput,
    "get_tracking_summary": DaysIn,
    "list_tasks": TaskListIn,
    "get_ideas": EmptyInput,
    "recall_memory": EmptyInput,
    "list_goals": EmptyInput,
    "record_blocker": RecordBlockerIn,
}


# ============================================================================
# PUBLIC INTERFACE
# ============================================================================

def tool_definitions_for_llm() -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema or {"type": "object", "properties": {}},
        }
        for t in TOOLS.values()
    ]


def execute_tool(db: Session, user_id: int, name: str, raw_args: dict) -> str:
    tool = TOOLS.get(name)
    if not tool:
        return _err(f"unknown tool {name}")
    schema_cls = _SCHEMA_MAP.get(name)
    if schema_cls is None:
        return _err(f"no schema registered for tool {name}")
    try:
        args = schema_cls(**(raw_args or {}))
    except ValidationError as e:
        return _err(f"invalid args for {name}: {e.errors()[:2]}")
    try:
        return tool.fn(db, user_id, args)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        return _err(f"{name} failed: {type(e).__name__}: {e}")