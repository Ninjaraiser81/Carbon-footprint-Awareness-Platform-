"""
Activities router — CRUD for carbon activity logging.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Activity, ActivityCategory, User
from app.models.schemas import ActivityCreate, ActivityResponse, ActivityUpdate
from app.services.carbon_calculator import calculate_co2e, get_all_subcategories
from app.dependencies import get_current_user

router = APIRouter(prefix="/activities", tags=["Activities"])


@router.get(
    "/subcategories",
    summary="Get all available activity subcategories with emission factors",
)
def list_subcategories() -> dict:
    """Return all subcategories grouped by category (public endpoint)."""
    return get_all_subcategories()


@router.post(
    "/",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a new carbon activity",
)
def create_activity(
    data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityResponse:
    """
    Log a carbon-emitting activity. CO2e is calculated automatically
    from the subcategory emission factor.
    """
    try:
        co2e = calculate_co2e(data.subcategory, data.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    activity = Activity(
        user_id=current_user.id,
        category=data.category,
        subcategory=data.subcategory,
        description=data.description,
        quantity=data.quantity,
        unit=data.unit,
        co2e_kg=co2e,
        activity_date=data.activity_date,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return ActivityResponse.model_validate(activity)


@router.get(
    "/",
    response_model=List[ActivityResponse],
    summary="List user's activities with optional filters",
)
def list_activities(
    category: Optional[ActivityCategory] = Query(None, description="Filter by category"),
    start_date: Optional[datetime] = Query(None, description="Filter from date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter to date (ISO 8601)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ActivityResponse]:
    """Return activities for the current user, optionally filtered."""
    query = db.query(Activity).filter(Activity.user_id == current_user.id)
    if category:
        query = query.filter(Activity.category == category)
    if start_date:
        query = query.filter(Activity.activity_date >= start_date)
    if end_date:
        query = query.filter(Activity.activity_date <= end_date)
    activities = (
        query.order_by(Activity.activity_date.desc())
             .offset(offset)
             .limit(limit)
             .all()
    )
    return [ActivityResponse.model_validate(a) for a in activities]


@router.get(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Get a specific activity",
)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityResponse:
    """Retrieve a single activity by ID (must belong to current user)."""
    activity = (
        db.query(Activity)
        .filter(Activity.id == activity_id, Activity.user_id == current_user.id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return ActivityResponse.model_validate(activity)


@router.put(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Update an activity",
)
def update_activity(
    activity_id: int,
    data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityResponse:
    """Update description, quantity, or date of an existing activity."""
    activity = (
        db.query(Activity)
        .filter(Activity.id == activity_id, Activity.user_id == current_user.id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")

    if data.description is not None:
        activity.description = data.description
    if data.quantity is not None:
        activity.quantity = data.quantity
        activity.co2e_kg = calculate_co2e(activity.subcategory, data.quantity)
    if data.activity_date is not None:
        activity.activity_date = data.activity_date

    db.commit()
    db.refresh(activity)
    return ActivityResponse.model_validate(activity)


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an activity",
)
def delete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Permanently delete an activity belonging to the current user."""
    activity = (
        db.query(Activity)
        .filter(Activity.id == activity_id, Activity.user_id == current_user.id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    db.delete(activity)
    db.commit()
