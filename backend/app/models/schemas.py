"""
Pydantic v2 schemas for request/response validation.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.database.models import ActivityCategory


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)
    country: str = Field(default="Global", max_length=100)
    annual_goal_kg: float = Field(default=2000.0, ge=100, le=50000)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    country: str
    annual_goal_kg: float
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Activity Schemas ──────────────────────────────────────────────────────────

class ActivityCreate(BaseModel):
    category: ActivityCategory
    subcategory: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    quantity: float = Field(..., gt=0, le=100000)
    unit: str = Field(..., min_length=1, max_length=30)
    activity_date: datetime


class ActivityUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    quantity: Optional[float] = Field(None, gt=0, le=100000)
    activity_date: Optional[datetime] = None


class ActivityResponse(BaseModel):
    id: int
    category: ActivityCategory
    subcategory: str
    description: Optional[str]
    quantity: float
    unit: str
    co2e_kg: float
    logged_at: datetime
    activity_date: datetime

    model_config = {"from_attributes": True}


# ─── Dashboard Schemas ─────────────────────────────────────────────────────────

class DailyStat(BaseModel):
    date: str
    co2e_kg: float


class CategoryStat(BaseModel):
    category: str
    co2e_kg: float
    percentage: float


class BadgeResponse(BaseModel):
    name: str
    description: str
    icon: str
    earned_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    total_co2e_this_month: float
    total_co2e_this_year: float
    average_daily_co2e: float
    annual_goal_kg: float
    goal_progress_pct: float
    streak_days: int
    global_avg_monthly_kg: float
    national_avg_monthly_kg: float
    daily_trend: List[DailyStat]
    category_breakdown: List[CategoryStat]
    recent_activities: List[ActivityResponse]
    badges: List[BadgeResponse]
    carbon_score: int  # 0–100 eco score


# ─── Insights Schemas ─────────────────────────────────────────────────────────

class Recommendation(BaseModel):
    title: str
    description: str
    potential_saving_kg: float
    difficulty: str  # easy | medium | hard
    category: str
    icon: str


class InsightsResponse(BaseModel):
    eco_score: int
    score_label: str
    top_emission_category: str
    recommendations: List[Recommendation]
    tip_of_the_day: str
    comparison_global_pct: float   # how much above/below global avg (negative = better)
    comparison_national_pct: float
    monthly_trend_pct: float       # change vs prev month (negative = improvement)
