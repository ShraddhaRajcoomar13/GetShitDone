import enum
from datetime import datetime
from .timeutils import now_local

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from .database import Base


class TaskStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    completed = "completed"
    postponed = "postponed"
    blocked = "blocked"
    dropped = "dropped"
    overdue = "overdue"


class GoalStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"


class CoachingStyle(str, enum.Enum):
    gentle = "gentle"
    supportive_firm = "supportive_firm"
    strict = "strict"
    drill_sergeant = "drill_sergeant"
    analytical = "analytical"
    custom = "custom"


class TaskType(str, enum.Enum):
    deep_work = "deep_work"
    admin = "admin"
    errands = "errands"
    personal = "personal"


class IdeaStatus(str, enum.Enum):
    inbox = "inbox"
    archived = "archived"
    scheduled = "scheduled"
    converted = "converted"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    prefs = relationship("UserPreferences", uselist=False, cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    coaching_style = Column(Enum(CoachingStyle), default=CoachingStyle.supportive_firm)
    custom_instructions = Column(Text, default="")
    work_hours_start = Column(String(5), default="09:00")
    work_hours_end = Column(String(5), default="18:00")
    quiet_hours_start = Column(String(5), default="22:00")
    quiet_hours_end = Column(String(5), default="07:00")
    hydration_goal_ml = Column(Integer, default=2000)
    motivational_prompts = Column(Boolean, default=True)
    intervention_frequency = Column(String(20), default="normal")  # low|normal|high
    autonomy_level = Column(String(20), default="confirm")  # read|confirm|autonomous
    timezone = Column(String(64), default="UTC")
    theme = Column(String(32), default="paper")
    accent_color = Column(String(16), default="")
    bg_image = Column(Text, default="")
    bg_opacity = Column(Integer, default=60)


class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    target_outcome = Column(Text, default="")
    week_start = Column(String(10), nullable=False)  # YYYY-MM-DD (Monday)
    priority = Column(Integer, default=3)
    status = Column(Enum(GoalStatus), default=GoalStatus.draft)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    outcome = Column(Text, default="")
    smallest_first_action = Column(Text, default="")
    priority = Column(Integer, default=3)
    task_type = Column(Enum(TaskType), default=TaskType.deep_work)
    estimated_minutes = Column(Integer, default=30)
    actual_minutes = Column(Integer, default=0)
    energy_required = Column(Integer, default=3)  # 1..5
    deadline = Column(DateTime, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.planned, index=True)
    scheduled_start = Column(DateTime, nullable=True, index=True)
    scheduled_end = Column(DateTime, nullable=True)
    original_scheduled_start = Column(DateTime, nullable=True)
    postpone_count = Column(Integer, default=0)
    blocker = Column(Text, default="")
    completion_criteria = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="tasks")
    goal = relationship("Goal", back_populates="tasks")
    #subtasks = relationship("Task", cascade="all, delete-orphan", backref="parent", remote_side=[id])
    parent = relationship(
    "Task",
    back_populates="subtasks",
    remote_side=[id],
    foreign_keys=[parent_task_id],
    )
    subtasks = relationship(
        "Task",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys=[parent_task_id],
    )

class DailyAvailability(Base):
    __tablename__ = "daily_availability"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False)
    available_minutes = Column(Integer, default=240)


class FixedCommitment(Base):
    __tablename__ = "fixed_commitments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)


class FocusSession(Base):
    __tablename__ = "focus_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    #started_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, default=now_local)
    ended_at = Column(DateTime, nullable=True)
    planned_minutes = Column(Integer, default=25)
    notes = Column(Text, default="")
    completed = Column(Boolean, default=False)


class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    kind = Column(String(32), nullable=False)  # task_start | check_in | break | hydration | shutdown
    remind_at = Column(DateTime, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    message = Column(Text, default="")


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user | assistant | tool
    content = Column(Text, default="")
    tool_name = Column(String(64), nullable=True)
    tool_input = Column(Text, nullable=True)
    tool_output = Column(Text, nullable=True)
    #created_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=now_local, index=True)


class AgentMemory(Base):
    __tablename__ = "agent_memory"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_mem_user_key"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String(64), nullable=False)
    value = Column(Text, default="")
    #updated_at = Column(DateTime, onupdate=func.now(), default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=now_local, default=now_local)


class MoodEnergyLog(Base):
    __tablename__ = "mood_energy"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    #logged_at = Column(DateTime, default=datetime.utcnow, index=True)
    logged_at = Column(DateTime, default=now_local, index=True)
    mood = Column(Integer, nullable=True)  # 1..5
    energy = Column(Integer, nullable=True)  # 1..5
    notes = Column(Text, default="")


class FoodEntry(Base):
    __tablename__ = "food_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    #logged_at = Column(DateTime, default=datetime.utcnow, index=True)
    logged_at = Column(DateTime, default=now_local, index=True)
    meal_type = Column(String(32), default="snack")
    description = Column(Text, default="")
    notes = Column(Text, default="")


class WaterEntry(Base):
    __tablename__ = "water_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    #logged_at = Column(DateTime, default=datetime.utcnow, index=True)
    logged_at = Column(DateTime, default=now_local, index=True)
    amount_ml = Column(Integer, default=250)


class Idea(Base):
    __tablename__ = "ideas"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    tags = Column(String(255), default="")
    status = Column(Enum(IdeaStatus), default=IdeaStatus.inbox)
    #created_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=now_local, index=True)
    review_at = Column(DateTime, nullable=True)