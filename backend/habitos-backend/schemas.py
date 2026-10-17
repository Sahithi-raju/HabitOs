"""
schemas.py — Pydantic request / response models
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    email: Optional[str] = None
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ══════════════════════════════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════════════════════════════

class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    icon: str = Field(default="⭐", max_length=10)
    unit: str = Field(..., min_length=1, max_length=20)
    daily_limit: float = Field(..., gt=0)
    low_warn: bool = True
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")

class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=60)
    icon: Optional[str] = Field(None, max_length=10)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    daily_limit: Optional[float] = Field(None, gt=0)
    low_warn: Optional[bool] = None
    priority: Optional[str] = Field(None, pattern="^(high|medium|low)$")
    is_active: Optional[bool] = None

class TaskOut(BaseModel):
    id: int
    name: str
    icon: str
    unit: str
    daily_limit: float
    low_warn: bool
    priority: str
    is_default: bool
    is_active: bool
    created_at: str


# ══════════════════════════════════════════════════════════════════════════════
#  HABIT LOGS
# ══════════════════════════════════════════════════════════════════════════════

class HabitLogCreate(BaseModel):
    task_id: int
    log_date: str = Field(..., description="YYYY-MM-DD")
    value: float = Field(..., ge=0)
    note: Optional[str] = Field(None, max_length=200)

    @field_validator("log_date")
    @classmethod
    def validate_date(cls, v):
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("log_date must be YYYY-MM-DD")
        return v

class HabitLogUpdate(BaseModel):
    value: Optional[float] = Field(None, ge=0)
    note: Optional[str] = None

class HabitLogOut(BaseModel):
    id: int
    task_id: int
    task_name: str
    task_icon: str
    task_unit: str
    task_limit: float
    log_date: str
    value: float
    note: Optional[str]
    status: str          # "ok" | "over" | "under"
    created_at: str
    updated_at: str

class BulkLogEntry(BaseModel):
    task_id: int
    value: float = Field(..., ge=0)
    note: Optional[str] = None

class BulkLogCreate(BaseModel):
    log_date: str
    entries: List[BulkLogEntry]

class DayLogOut(BaseModel):
    log_date: str
    logs: List[HabitLogOut]
    productivity_score: int
    total_tasks: int
    completed_tasks: int


# ══════════════════════════════════════════════════════════════════════════════
#  REMINDERS
# ══════════════════════════════════════════════════════════════════════════════

class ReminderCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    icon: str = Field(default="🔔", max_length=10)
    time_hhmm: str = Field(..., description="HH:MM (24h)", pattern=r"^\d{2}:\d{2}$")
    repeat_days: List[int] = Field(default=[0,1,2,3,4,5,6], description="0=Sun … 6=Sat")
    category: str = Field(default="custom", pattern="^(health|water|work|sleep|custom)$")
    sound: str = Field(default="bell", pattern="^(bell|chime|ding|none)$")
    note: Optional[str] = Field(None, max_length=200)
    is_enabled: bool = True

    @field_validator("repeat_days")
    @classmethod
    def validate_days(cls, v):
        if not v:
            raise ValueError("At least one repeat day is required")
        for d in v:
            if d not in range(7):
                raise ValueError("Days must be integers 0–6")
        return sorted(set(v))

    @field_validator("time_hhmm")
    @classmethod
    def validate_time(cls, v):
        h, m = v.split(":")
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            raise ValueError("time_hhmm must be a valid HH:MM time")
        return v

class ReminderUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=10)
    time_hhmm: Optional[str] = None
    repeat_days: Optional[List[int]] = None
    category: Optional[str] = None
    sound: Optional[str] = None
    note: Optional[str] = None
    is_enabled: Optional[bool] = None

class ReminderOut(BaseModel):
    id: int
    label: str
    icon: str
    time_hhmm: str
    time_12h: str
    repeat_days: List[int]
    days_label: str
    category: str
    sound: str
    note: Optional[str]
    is_enabled: bool
    next_occurrence: Optional[str]
    created_at: str
    updated_at: str


# ══════════════════════════════════════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════════════════════════════════════

class WeeklyStatOut(BaseModel):
    week_start: str
    week_end: str
    days_logged: int
    avg_productivity: int
    streak: int
    best_day: Optional[str]
    worst_day: Optional[str]
    daily_scores: List[dict]

class TaskStatOut(BaseModel):
    task_id: int
    task_name: str
    task_icon: str
    avg_value: float
    days_logged: int
    days_on_target: int
    compliance_pct: int
    trend: str          # "improving" | "declining" | "stable"

class AISuggestionOut(BaseModel):
    type: str           # "warning" | "success" | "info"
    icon: str
    title: str
    message: str
    tomorrow_target: str
    task_id: Optional[int]
