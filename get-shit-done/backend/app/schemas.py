from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import CoachingStyle, GoalStatus, IdeaStatus, TaskStatus, TaskType


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Auth ----
class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: str


# ---- Prefs ----
class PrefsOut(ORM):
    coaching_style: CoachingStyle
    custom_instructions: str
    work_hours_start: str
    work_hours_end: str
    quiet_hours_start: str
    quiet_hours_end: str
    hydration_goal_ml: int
    motivational_prompts: bool
    intervention_frequency: str
    autonomy_level: str
    timezone: str
    theme: str = "paper"
    accent_color: str = ""
    bg_image: str = ""
    bg_opacity: int = 60


class PrefsUpdate(BaseModel):
    coaching_style: Optional[CoachingStyle] = None
    custom_instructions: Optional[str] = None
    work_hours_start: Optional[str] = None
    work_hours_end: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    hydration_goal_ml: Optional[int] = None
    motivational_prompts: Optional[bool] = None
    intervention_frequency: Optional[str] = None
    autonomy_level: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    accent_color: Optional[str] = None
    bg_image: Optional[str] = None
    bg_opacity: Optional[int] = None


# ---- Goals ----
class GoalCreate(BaseModel):
    title: str
    description: str = ""
    target_outcome: str = ""
    week_start: str
    priority: int = 3


class GoalOut(ORM):
    id: int
    title: str
    description: str
    target_outcome: str
    week_start: str
    priority: int
    status: GoalStatus


# ---- Tasks ----
class TaskCreate(BaseModel):
    title: str
    description: str = ""
    outcome: str = ""
    smallest_first_action: str = ""
    goal_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    priority: int = 3
    task_type: TaskType = TaskType.deep_work
    estimated_minutes: int = 30
    energy_required: int = 3
    deadline: Optional[datetime] = None
    completion_criteria: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    outcome: Optional[str] = None
    smallest_first_action: Optional[str] = None
    priority: Optional[int] = None
    task_type: Optional[TaskType] = None
    estimated_minutes: Optional[int] = None
    energy_required: Optional[int] = None
    deadline: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    blocker: Optional[str] = None
    completion_criteria: Optional[str] = None


class TaskOut(ORM):
    id: int
    goal_id: Optional[int]
    parent_task_id: Optional[int]
    title: str
    description: str
    outcome: str
    smallest_first_action: str
    priority: int
    task_type: TaskType
    estimated_minutes: int
    actual_minutes: int
    energy_required: int
    deadline: Optional[datetime]
    status: TaskStatus
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    postpone_count: int
    blocker: str
    completion_criteria: str
    subtask_progress: Optional[dict] = None   # ← add this


# ---- Availability / Commitments ----
class AvailabilityIn(BaseModel):
    date: str
    available_minutes: int


class CommitmentIn(BaseModel):
    title: str
    date: str
    start_time: str
    end_time: str


# ---- Tracking ----
class MoodEnergyIn(BaseModel):
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    energy: Optional[int] = Field(default=None, ge=1, le=5)
    notes: str = ""


class FoodIn(BaseModel):
    meal_type: str = "snack"
    description: str = ""
    notes: str = ""


class WaterIn(BaseModel):
    amount_ml: int = 250


class IdeaIn(BaseModel):
    content: str
    tags: str = ""


class IdeaOut(ORM):
    id: int
    content: str
    tags: str
    status: IdeaStatus
    created_at: datetime
    review_at: Optional[datetime]


# ---- Focus ----
class FocusStart(BaseModel):
    task_id: Optional[int] = None
    planned_minutes: int = 25


class FocusEnd(BaseModel):
    session_id: int
    notes: str = ""
    completed: bool = True


# ---- Agent ----
class ChatIn(BaseModel):
    message: str


class ChatOut(BaseModel):
    reply: str
    tool_calls: list[dict] = []


# ---- Dashboard ----
class DashboardOut(BaseModel):
    today_tasks: list[TaskOut]
    next_task: Optional[TaskOut]
    completed_today: int
    planned_today: int
    focus_minutes_today: int
    overdue_count: int
    blocked_count: int
    weekly_goal_progress: list[dict]
    hydration_ml_today: int
    hydration_goal_ml: int
    mood_energy: list[dict]
    agent_summary: str
    
# ---- Goal update ----
class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_outcome: Optional[str] = None
    week_start: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[GoalStatus] = None


# ---- Idea update ----
class IdeaUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[IdeaStatus] = None


# ---- Mood / food read + update ----
class MoodEnergyOut(ORM):
    id: int
    logged_at: datetime
    mood: Optional[int]
    energy: Optional[int]
    notes: str


class MoodEnergyUpdate(BaseModel):
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    energy: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None


class FoodOut(ORM):
    id: int
    logged_at: datetime
    meal_type: str
    description: str
    notes: str


class FoodUpdate(BaseModel):
    meal_type: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None