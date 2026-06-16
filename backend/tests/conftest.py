"""
Pytest configuration and shared fixtures for the Carbon Footprint Tracker test suite.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.models import Base
from app.database.session import get_db

# Use in-memory SQLite for tests (isolated from production DB)
TEST_DATABASE_URL = "sqlite:///./test_carbon.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session():
    """Provide a fresh database session per test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI test client with DB override."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    """Register and return a test user with auth token."""
    resp = client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass1",
        "country": "United Kingdom",
        "annual_goal_kg": 2000.0,
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def auth_headers(registered_user):
    """Return Authorization headers for the test user."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}
