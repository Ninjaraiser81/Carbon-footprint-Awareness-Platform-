"""
Carbon Footprint Calculator Service.

Emission factors sourced from:
- IPCC AR6 (2021) — transport, energy, food
- EPA (2023) — household & shopping
- DEFRA (2023) — travel, waste

All values in kg CO2e per unit.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
from app.database.models import ActivityCategory


@dataclass(frozen=True)
class EmissionFactor:
    """Represents an emission factor with metadata."""
    subcategory: str
    unit: str
    kg_co2e_per_unit: float
    description: str
    source: str = "IPCC AR6 / EPA 2023"


# ─── Emission Factor Registry ──────────────────────────────────────────────────

EMISSION_FACTORS: Dict[ActivityCategory, List[EmissionFactor]] = {

    ActivityCategory.TRANSPORT: [
        EmissionFactor("car_petrol",        "km",    0.170,  "Petrol car (avg)"),
        EmissionFactor("car_diesel",        "km",    0.168,  "Diesel car (avg)"),
        EmissionFactor("car_hybrid",        "km",    0.106,  "Hybrid car (avg)"),
        EmissionFactor("car_electric",      "km",    0.053,  "Electric car (UK grid)"),
        EmissionFactor("car_suv_petrol",    "km",    0.238,  "SUV petrol (avg)"),
        EmissionFactor("motorcycle",        "km",    0.114,  "Motorcycle (avg)"),
        EmissionFactor("bus",               "km",    0.089,  "Local bus"),
        EmissionFactor("metro_subway",      "km",    0.028,  "Metro / Subway"),
        EmissionFactor("train_national",    "km",    0.041,  "National rail (avg)"),
        EmissionFactor("train_high_speed",  "km",    0.014,  "High-speed rail"),
        EmissionFactor("taxi_rideshare",    "km",    0.189,  "Taxi / Rideshare"),
        EmissionFactor("bicycle",           "km",    0.0,    "Bicycle (zero emission)"),
        EmissionFactor("walking",           "km",    0.0,    "Walking (zero emission)"),
        EmissionFactor("e_scooter",         "km",    0.020,  "E-scooter (shared)"),
        EmissionFactor("ferry",             "km",    0.113,  "Ferry (avg)"),
    ],

    ActivityCategory.ENERGY: [
        EmissionFactor("electricity_grid",   "kWh",  0.233,  "Grid electricity (world avg)"),
        EmissionFactor("electricity_coal",   "kWh",  0.820,  "Coal-heavy grid electricity"),
        EmissionFactor("electricity_gas",    "kWh",  0.490,  "Gas-heavy grid electricity"),
        EmissionFactor("electricity_renew",  "kWh",  0.020,  "Renewable electricity"),
        EmissionFactor("natural_gas_home",   "kWh",  0.203,  "Natural gas (home heating)"),
        EmissionFactor("heating_oil",        "litre",2.520,  "Heating oil"),
        EmissionFactor("lpg",                "litre",1.555,  "LPG (home use)"),
        EmissionFactor("wood_pellets",       "kg",   0.039,  "Wood pellets (sustainable)"),
        EmissionFactor("coal_home",          "kg",   2.419,  "Coal (home heating)"),
        EmissionFactor("solar_panels",       "kWh",  0.041,  "Solar PV (lifecycle)"),
    ],

    ActivityCategory.FOOD: [
        EmissionFactor("beef",           "kg",  27.0,  "Beef (avg, incl. land use)"),
        EmissionFactor("lamb",           "kg",  39.2,  "Lamb / Mutton"),
        EmissionFactor("pork",           "kg",   7.6,  "Pork"),
        EmissionFactor("chicken",        "kg",   6.9,  "Chicken"),
        EmissionFactor("fish_farmed",    "kg",  13.6,  "Fish (farmed, avg)"),
        EmissionFactor("fish_wild",      "kg",   3.0,  "Fish (wild caught)"),
        EmissionFactor("dairy_milk",     "litre",3.2,  "Cow's milk"),
        EmissionFactor("cheese",         "kg",  21.0,  "Cheese"),
        EmissionFactor("eggs",           "unit", 0.18, "Eggs (per egg)"),
        EmissionFactor("tofu",           "kg",   2.0,  "Tofu"),
        EmissionFactor("vegetables",     "kg",   2.0,  "Mixed vegetables (avg)"),
        EmissionFactor("fruits",         "kg",   1.1,  "Mixed fruits (avg)"),
        EmissionFactor("legumes",        "kg",   0.9,  "Legumes / Pulses"),
        EmissionFactor("nuts",           "kg",   2.5,  "Nuts (avg)"),
        EmissionFactor("rice",           "kg",   4.0,  "Rice"),
        EmissionFactor("wheat_bread",    "kg",   1.6,  "Wheat / Bread"),
        EmissionFactor("coffee",         "cup",  0.21, "Coffee (1 cup)"),
        EmissionFactor("tea",            "cup",  0.03, "Tea (1 cup)"),
        EmissionFactor("alcohol_beer",   "pint", 0.74, "Beer (1 pint)"),
        EmissionFactor("food_waste",     "kg",   2.5,  "Food waste to landfill"),
    ],

    ActivityCategory.SHOPPING: [
        EmissionFactor("clothing_new",      "item",  10.0,   "New clothing item (avg)"),
        EmissionFactor("clothing_secondhand","item",  0.5,   "Second-hand clothing"),
        EmissionFactor("electronics_phone", "item",  70.0,   "New smartphone"),
        EmissionFactor("electronics_laptop","item",  300.0,  "New laptop"),
        EmissionFactor("electronics_tv",    "item",  400.0,  "New TV (55 inch)"),
        EmissionFactor("furniture",         "item",  100.0,  "Furniture item (avg)"),
        EmissionFactor("paper_books",       "item",  1.0,    "New book"),
        EmissionFactor("online_delivery",   "parcel",0.5,   "Online delivery (avg)"),
        EmissionFactor("streaming",         "hour",  0.036,  "Video streaming"),
        EmissionFactor("banking_savings",   "£1000", 1.4,   "Savings/investment (£1000)"),
    ],

    ActivityCategory.TRAVEL: [
        EmissionFactor("flight_domestic",    "km",  0.255,  "Domestic flight"),
        EmissionFactor("flight_short_haul",  "km",  0.195,  "Short-haul flight (<3h)"),
        EmissionFactor("flight_long_haul",   "km",  0.195,  "Long-haul flight economy"),
        EmissionFactor("flight_business",    "km",  0.429,  "Long-haul business class"),
        EmissionFactor("flight_first",       "km",  0.751,  "Long-haul first class"),
        EmissionFactor("cruise",             "day",  163.0, "Cruise ship (per day)"),
        EmissionFactor("hotel_stay",         "night",15.0,  "Hotel night (avg)"),
        EmissionFactor("hostel_stay",        "night",5.0,   "Hostel / budget stay"),
        EmissionFactor("camping",            "night",2.0,   "Camping"),
    ],

    ActivityCategory.WASTE: [
        EmissionFactor("landfill_general",   "kg",  0.47,   "General waste to landfill"),
        EmissionFactor("recycling_paper",    "kg", -0.90,   "Paper recycled (avoided)"),
        EmissionFactor("recycling_plastic",  "kg", -0.34,   "Plastic recycled (avoided)"),
        EmissionFactor("recycling_metal",    "kg", -9.10,   "Metal recycled (avoided)"),
        EmissionFactor("composting",         "kg", -0.31,   "Food composted (avoided)"),
        EmissionFactor("incineration",       "kg",  0.30,   "Waste incineration"),
    ],
}

# Flat lookup: subcategory -> EmissionFactor
_LOOKUP: Dict[str, EmissionFactor] = {
    ef.subcategory: ef
    for factors in EMISSION_FACTORS.values()
    for ef in factors
}


def calculate_co2e(subcategory: str, quantity: float) -> float:
    """
    Calculate CO2e emissions for an activity.

    Args:
        subcategory: The subcategory identifier (e.g. 'car_petrol').
        quantity: The quantity in the factor's unit.

    Returns:
        CO2e in kg, rounded to 4 decimal places. Negative for avoided emissions.

    Raises:
        ValueError: If subcategory is not found.
    """
    if subcategory not in _LOOKUP:
        raise ValueError(f"Unknown subcategory: '{subcategory}'. "
                         f"Valid options: {sorted(_LOOKUP.keys())}")
    if quantity < 0:
        raise ValueError(f"Quantity must be non-negative, got {quantity}")

    factor = _LOOKUP[subcategory]
    return round(factor.kg_co2e_per_unit * quantity, 4)


def get_factors_by_category(category: ActivityCategory) -> List[EmissionFactor]:
    """Return all emission factors for a given category."""
    return EMISSION_FACTORS.get(category, [])


def get_all_subcategories() -> Dict[str, Dict]:
    """Return all subcategories with their metadata, grouped by category."""
    result: Dict[str, Dict] = {}
    for category, factors in EMISSION_FACTORS.items():
        result[category.value] = [
            {
                "subcategory": ef.subcategory,
                "unit": ef.unit,
                "kg_co2e_per_unit": ef.kg_co2e_per_unit,
                "description": ef.description,
            }
            for ef in factors
        ]
    return result


def eco_score(monthly_co2e_kg: float) -> Tuple[int, str]:
    """
    Calculate an eco score (0–100) from monthly CO2e.

    Global average monthly = ~333 kg (4000/12).
    Score of 100 = net-zero or negative.
    Score of 0 = > 1000 kg/month.

    Returns:
        Tuple of (score int 0-100, label string).
    """
    if monthly_co2e_kg <= 0:
        return 100, "Net Zero Hero"
    if monthly_co2e_kg <= 100:
        return 95, "Carbon Champion"
    if monthly_co2e_kg <= 200:
        return 85, "Eco Warrior"
    if monthly_co2e_kg <= 333:
        return 70, "Green Minded"
    if monthly_co2e_kg <= 500:
        return 55, "Aware & Improving"
    if monthly_co2e_kg <= 700:
        return 35, "Room to Grow"
    if monthly_co2e_kg <= 1000:
        return 15, "High Impact"
    return 5, "Very High Impact"


# Country average monthly CO2e in kg (IEA 2023)
COUNTRY_AVERAGES: Dict[str, float] = {
    "Global":         333.0,
    "United States":  1375.0,
    "Australia":      1175.0,
    "Canada":         1292.0,
    "United Kingdom": 475.0,
    "Germany":        633.0,
    "China":          583.0,
    "India":          175.0,
    "Brazil":         200.0,
    "France":         433.0,
    "Japan":          708.0,
}


def get_national_avg(country: str) -> float:
    """Return monthly kg CO2e average for a country (defaults to Global)."""
    return COUNTRY_AVERAGES.get(country, COUNTRY_AVERAGES["Global"])
