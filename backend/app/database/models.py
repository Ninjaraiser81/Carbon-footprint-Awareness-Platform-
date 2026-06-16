"""
Carbon Footprint Tracker — Database Models (SQLAlchemy 2.0)
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""
    pass


class ActivityCategory(str, enum.Enum):
    TRANSPORT = "transport"
    ENERGY = "energy"
    FOOD = "food"
    SHOPPING = "shopping"
    TRAVEL = "travel"
    WASTE = "waste"


class User(Base):
    """Represents an application user."""
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    username: str = Column(String(50), unique=True, index=True, nullable=False)
    email: str = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password: str = Column(String(255), nullable=False)
    full_name: Optional[str] = Column(String(100), nullable=True)
    country: str = Column(String(100), default="Global")
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    # Goal in kg CO2e per year (global avg ~4000 kg)
    annual_goal_kg: float = Column(Float, default=2000.0)

    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")


class Activity(Base):
    """Records a single carbon-emitting activity."""
    __tablename__ = "activities"

    id: int = Column(Integer, primary_key=True, index=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    category: ActivityCategory = Column(SAEnum(ActivityCategory), nullable=False)
    subcategory: str = Column(String(100), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)
    quantity: float = Column(Float, nullable=False)
    unit: str = Column(String(30), nullable=False)
    co2e_kg: float = Column(Float, nullable=False)  # Calculated emission
    logged_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    activity_date: datetime = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="activities")


class Badge(Base):
    """Defines available badges/achievements."""
    __tablename__ = "badges"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(100), unique=True, nullable=False)
    description: str = Column(Text, nullable=False)
    icon: str = Column(String(50), nullable=False)  # emoji or icon name
    condition_type: str = Column(String(50), nullable=False)  # e.g. 'streak', 'total_reduction'
    condition_value: float = Column(Float, nullable=False)

    earned_by = relationship("UserBadge", back_populates="badge")


class UserBadge(Base):
    """Junction table tracking which users earned which badges."""
    __tablename__ = "user_badges"

    id: int = Column(Integer, primary_key=True, index=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id: int = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="earned_by")
