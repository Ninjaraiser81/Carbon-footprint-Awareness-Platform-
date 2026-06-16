"""
Auth router — register, login, profile.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.schemas import UserCreate, UserLogin, UserResponse, Token
from app.services import auth_service
from app.dependencies import get_current_user
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(data: UserCreate, db: Session = Depends(get_db)) -> Token:
    """Create a new user account and return JWT access token."""
    if auth_service.get_user_by_username(db, data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    if auth_service.get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = auth_service.create_user(db, data)
    token = auth_service.create_access_token(user.id, user.username)
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Login and obtain JWT token",
)
def login(data: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Authenticate credentials and return JWT access token."""
    user = auth_service.authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_service.create_access_token(user.id, user.username)
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)
