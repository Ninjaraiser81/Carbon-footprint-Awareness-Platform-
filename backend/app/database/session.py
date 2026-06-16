"""
Database session management and initialization.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.database.models import Base, Badge

DATABASE_URL = "sqlite:///./carbon_tracker.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable WAL mode for better SQLite concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all tables and seed initial data."""
    Base.metadata.create_all(bind=engine)
    _seed_badges()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_badges() -> None:
    """Insert default badges if they don't exist."""
    db = SessionLocal()
    try:
        if db.query(Badge).count() > 0:
            return
        badges = [
            Badge(name="First Step", description="Log your first activity", icon="🌱", condition_type="activity_count", condition_value=1),
            Badge(name="Week Warrior", description="Log activities for 7 consecutive days", icon="🔥", condition_type="streak_days", condition_value=7),
            Badge(name="Carbon Cutter", description="Reduce emissions by 10% vs last month", icon="✂️", condition_type="monthly_reduction_pct", condition_value=10),
            Badge(name="Green Champion", description="Stay under your annual goal for a month", icon="🏆", condition_type="monthly_goal_met", condition_value=1),
            Badge(name="Eco Warrior", description="Reduce emissions by 50% vs baseline", icon="⚡", condition_type="total_reduction_pct", condition_value=50),
            Badge(name="Plant Based Hero", description="Log 30 plant-based meals", icon="🥗", condition_type="plant_meals_count", condition_value=30),
            Badge(name="No Drive November", description="Zero transport emissions for a week", icon="🚶", condition_type="zero_transport_days", condition_value=7),
            Badge(name="Solar Powered", description="Log renewable energy use 10 times", icon="☀️", condition_type="renewable_logs", condition_value=10),
        ]
        db.add_all(badges)
        db.commit()
    finally:
        db.close()
