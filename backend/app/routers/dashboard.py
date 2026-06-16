"""
Dashboard & Insights routers — aggregated stats and AI-like recommendations.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import Activity, User, UserBadge, Badge
from app.models.schemas import (
    DashboardResponse, DailyStat, CategoryStat, BadgeResponse,
    InsightsResponse, Recommendation,
)
from app.services.carbon_calculator import eco_score, get_national_avg
from app.dependencies import get_current_user

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
insights_router = APIRouter(prefix="/insights", tags=["Insights"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_monthly_activities(db: Session, user_id: int, months_ago: int = 0) -> List[Activity]:
    now = datetime.now(timezone.utc)
    start = (now.replace(day=1) - timedelta(days=30 * months_ago)).replace(day=1, hour=0, minute=0, second=0)
    end = now if months_ago == 0 else (start + timedelta(days=31)).replace(day=1)
    return (
        db.query(Activity)
        .filter(Activity.user_id == user_id, Activity.activity_date >= start, Activity.activity_date < end)
        .all()
    )


def _calculate_streak(db: Session, user_id: int) -> int:
    """Count consecutive days with at least one logged activity."""
    activities = (
        db.query(Activity)
        .filter(Activity.user_id == user_id)
        .order_by(Activity.activity_date.desc())
        .all()
    )
    if not activities:
        return 0

    logged_dates = {a.activity_date.date() for a in activities}
    today = datetime.now(timezone.utc).date()
    streak = 0
    current = today
    while current in logged_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def _check_and_award_badges(db: Session, user: User) -> None:
    """Award eligible badges to user based on their activity history."""
    all_activities = db.query(Activity).filter(Activity.user_id == user.id).all()
    earned_ids = {ub.badge_id for ub in db.query(UserBadge).filter(UserBadge.user_id == user.id).all()}
    all_badges = db.query(Badge).all()

    count = len(all_activities)
    streak = _calculate_streak(db, user.id)
    plant_meals = sum(
        1 for a in all_activities
        if a.subcategory in {"tofu", "vegetables", "fruits", "legumes"}
    )
    renewable_logs = sum(1 for a in all_activities if a.subcategory == "electricity_renew")
    zero_transport_days: set = set()

    transport_days = defaultdict(float)
    for a in all_activities:
        if a.category.value == "transport":
            transport_days[a.activity_date.date()] += a.co2e_kg
    zero_transport_days = {d for d, v in transport_days.items() if v == 0}

    conditions = {
        "activity_count": count,
        "streak_days": streak,
        "plant_meals_count": plant_meals,
        "renewable_logs": renewable_logs,
        "zero_transport_days": len(zero_transport_days),
    }

    for badge in all_badges:
        if badge.id in earned_ids:
            continue
        value = conditions.get(badge.condition_type, 0)
        if value >= badge.condition_value:
            db.add(UserBadge(user_id=user.id, badge_id=badge.id))

    db.commit()


# ─── Dashboard ────────────────────────────────────────────────────────────────

@dashboard_router.get(
    "/",
    response_model=DashboardResponse,
    summary="Get aggregated dashboard data for current user",
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    """Return comprehensive dashboard data including stats, trends, badges."""
    _check_and_award_badges(db, current_user)

    now = datetime.now(timezone.utc)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0)

    this_month = _get_monthly_activities(db, current_user.id, months_ago=0)
    all_year = (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id, Activity.activity_date >= year_start)
        .all()
    )

    total_month = sum(a.co2e_kg for a in this_month)
    total_year = sum(a.co2e_kg for a in all_year)
    days_in_month = (now - month_start).days + 1
    avg_daily = total_month / max(days_in_month, 1)

    goal_progress = min((total_year / max(current_user.annual_goal_kg, 1)) * 100, 200)

    # Daily trend (last 30 days)
    daily: dict = defaultdict(float)
    for a in this_month:
        daily[a.activity_date.strftime("%Y-%m-%d")] += a.co2e_kg
    daily_trend = [
        DailyStat(date=d, co2e_kg=round(v, 3))
        for d, v in sorted(daily.items())
    ]

    # Category breakdown
    cat_totals: dict = defaultdict(float)
    for a in this_month:
        cat_totals[a.category.value] += a.co2e_kg
    total_for_pct = max(sum(cat_totals.values()), 0.001)
    category_breakdown = [
        CategoryStat(
            category=cat,
            co2e_kg=round(val, 3),
            percentage=round((val / total_for_pct) * 100, 1),
        )
        for cat, val in sorted(cat_totals.items(), key=lambda x: -x[1])
    ]

    # Badges
    user_badges = (
        db.query(UserBadge, Badge)
        .join(Badge)
        .filter(UserBadge.user_id == current_user.id)
        .all()
    )
    badges = [
        BadgeResponse(
            name=b.name,
            description=b.description,
            icon=b.icon,
            earned_at=ub.earned_at,
        )
        for ub, b in user_badges
    ]

    score, _ = eco_score(total_month)
    global_avg = get_national_avg("Global")
    national_avg = get_national_avg(current_user.country)

    # Recent activities (last 10)
    from app.models.schemas import ActivityResponse
    recent = (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id)
        .order_by(Activity.activity_date.desc())
        .limit(10)
        .all()
    )

    return DashboardResponse(
        total_co2e_this_month=round(total_month, 3),
        total_co2e_this_year=round(total_year, 3),
        average_daily_co2e=round(avg_daily, 3),
        annual_goal_kg=current_user.annual_goal_kg,
        goal_progress_pct=round(goal_progress, 1),
        streak_days=_calculate_streak(db, current_user.id),
        global_avg_monthly_kg=global_avg,
        national_avg_monthly_kg=national_avg,
        daily_trend=daily_trend,
        category_breakdown=category_breakdown,
        recent_activities=[ActivityResponse.model_validate(a) for a in recent],
        badges=badges,
        carbon_score=score,
    )


# ─── Insights ────────────────────────────────────────────────────────────────

TIPS = [
    "Switch to a plant-based meal today — it can save up to 3 kg CO2e!",
    "Try cycling or walking for short trips under 3 km.",
    "Lowering your thermostat by 1°C can cut heating emissions by 10%.",
    "Washing clothes at 30°C instead of 60°C uses 40% less energy.",
    "Opt for a reusable water bottle to reduce plastic waste.",
    "Taking a train instead of a short-haul flight can reduce emissions by 85%.",
    "Eating seasonal and local produce cuts food transport emissions.",
    "Unplugging devices on standby can save 10% of household energy.",
    "Choose economy class — business class has 3x the carbon footprint.",
    "Composting food scraps diverts methane from landfill.",
    "Video calls instead of business travel saves 1+ tonnes CO2e per trip.",
    "Buy second-hand clothes — manufacturing new clothes is very carbon intensive.",
]


def _generate_recommendations(
    category_breakdown: list[CategoryStat],
    total_month: float,
    global_avg: float,
) -> list[Recommendation]:
    """Rule-based recommendation engine based on top emission categories."""
    recs: list[Recommendation] = []
    cat_map = {c.category: c for c in category_breakdown}

    if "transport" in cat_map and cat_map["transport"].co2e_kg > 50:
        recs.append(Recommendation(
            title="Switch to Electric or Public Transport",
            description="Your transport emissions are high. Consider taking the bus, train, or cycling for daily commutes. An EV can cut transport emissions by 60%.",
            potential_saving_kg=round(cat_map["transport"].co2e_kg * 0.40, 1),
            difficulty="medium",
            category="transport",
            icon="🚌",
        ))

    if "food" in cat_map and cat_map["food"].co2e_kg > 80:
        recs.append(Recommendation(
            title="Reduce Red Meat Consumption",
            description="Beef and lamb are the biggest food emission drivers. Replacing 2 beef meals per week with chicken or plant-based options saves ~20 kg CO2e/month.",
            potential_saving_kg=round(cat_map["food"].co2e_kg * 0.35, 1),
            difficulty="easy",
            category="food",
            icon="🥗",
        ))

    if "energy" in cat_map and cat_map["energy"].co2e_kg > 60:
        recs.append(Recommendation(
            title="Switch to Renewable Energy",
            description="Your energy usage is significant. Switching to a green energy tariff or installing solar panels could eliminate most of these emissions.",
            potential_saving_kg=round(cat_map["energy"].co2e_kg * 0.70, 1),
            difficulty="medium",
            category="energy",
            icon="☀️",
        ))

    if "travel" in cat_map and cat_map["travel"].co2e_kg > 100:
        recs.append(Recommendation(
            title="Replace Short-Haul Flights with Train",
            description="Flying is one of the most carbon-intensive activities. Trains produce 85% less CO2e than planes for the same journey.",
            potential_saving_kg=round(cat_map["travel"].co2e_kg * 0.60, 1),
            difficulty="hard",
            category="travel",
            icon="🚂",
        ))

    if "shopping" in cat_map and cat_map["shopping"].co2e_kg > 30:
        recs.append(Recommendation(
            title="Buy Second-Hand & Repair",
            description="Manufacturing new electronics and clothing is very carbon intensive. Choose second-hand, repair items, and reduce new purchases.",
            potential_saving_kg=round(cat_map["shopping"].co2e_kg * 0.50, 1),
            difficulty="easy",
            category="shopping",
            icon="♻️",
        ))

    # Generic if no specific
    if not recs:
        recs.append(Recommendation(
            title="Keep Logging Your Activities",
            description="Your emissions are low! Continue tracking to spot patterns and opportunities for further reduction.",
            potential_saving_kg=0.0,
            difficulty="easy",
            category="general",
            icon="🌱",
        ))

    return recs[:5]


@insights_router.get(
    "/",
    response_model=InsightsResponse,
    summary="Get personalized carbon insights and recommendations",
)
def get_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InsightsResponse:
    """Generate personalized recommendations and comparative analysis."""
    import random
    this_month = _get_monthly_activities(db, current_user.id, months_ago=0)
    prev_month = _get_monthly_activities(db, current_user.id, months_ago=1)

    total_this = sum(a.co2e_kg for a in this_month)
    total_prev = sum(a.co2e_kg for a in prev_month)

    cat_totals: dict = defaultdict(float)
    for a in this_month:
        cat_totals[a.category.value] += a.co2e_kg

    total_for_pct = max(sum(cat_totals.values()), 0.001)
    category_breakdown = [
        CategoryStat(
            category=cat,
            co2e_kg=round(val, 3),
            percentage=round((val / total_for_pct) * 100, 1),
        )
        for cat, val in sorted(cat_totals.items(), key=lambda x: -x[1])
    ]

    global_avg = get_national_avg("Global")
    national_avg = get_national_avg(current_user.country)
    score, label = eco_score(total_this)

    top_cat = category_breakdown[0].category if category_breakdown else "general"
    recs = _generate_recommendations(category_breakdown, total_this, global_avg)

    monthly_trend_pct = 0.0
    if total_prev > 0:
        monthly_trend_pct = round(((total_this - total_prev) / total_prev) * 100, 1)

    comparison_global = round(((total_this - global_avg) / global_avg) * 100, 1) if global_avg else 0
    comparison_national = round(((total_this - national_avg) / national_avg) * 100, 1) if national_avg else 0

    return InsightsResponse(
        eco_score=score,
        score_label=label,
        top_emission_category=top_cat,
        recommendations=recs,
        tip_of_the_day=random.choice(TIPS),
        comparison_global_pct=comparison_global,
        comparison_national_pct=comparison_national,
        monthly_trend_pct=monthly_trend_pct,
    )
