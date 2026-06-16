"""
Unit tests for the carbon calculator service.
Tests emission factor accuracy, edge cases, and eco scoring.
"""
import pytest
from app.services.carbon_calculator import (
    calculate_co2e,
    eco_score,
    get_factors_by_category,
    get_all_subcategories,
    get_national_avg,
    EMISSION_FACTORS,
    COUNTRY_AVERAGES,
)
from app.database.models import ActivityCategory


class TestCalculateCo2e:
    """Tests for the calculate_co2e function."""

    def test_petrol_car_emission(self):
        result = calculate_co2e("car_petrol", 100)
        assert result == pytest.approx(17.0, rel=1e-3)

    def test_electric_car_lower_than_petrol(self):
        petrol = calculate_co2e("car_petrol", 100)
        electric = calculate_co2e("car_electric", 100)
        assert electric < petrol

    def test_bicycle_zero_emission(self):
        assert calculate_co2e("bicycle", 50) == 0.0

    def test_walking_zero_emission(self):
        assert calculate_co2e("walking", 10) == 0.0

    def test_beef_high_emission(self):
        result = calculate_co2e("beef", 1)
        assert result == pytest.approx(27.0, rel=1e-3)

    def test_legumes_lower_than_beef(self):
        beef = calculate_co2e("beef", 1)
        legumes = calculate_co2e("legumes", 1)
        assert legumes < beef

    def test_flight_long_haul(self):
        result = calculate_co2e("flight_long_haul", 10000)
        assert result == pytest.approx(1950.0, rel=1e-3)

    def test_recycling_negative_emission(self):
        """Recycling should produce negative (avoided) emissions."""
        result = calculate_co2e("recycling_metal", 10)
        assert result < 0

    def test_composting_negative_emission(self):
        result = calculate_co2e("composting", 5)
        assert result < 0

    def test_unknown_subcategory_raises(self):
        with pytest.raises(ValueError, match="Unknown subcategory"):
            calculate_co2e("invalid_category_xyz", 10)

    def test_zero_quantity_returns_zero(self):
        result = calculate_co2e("car_petrol", 0)
        assert result == 0.0

    def test_negative_quantity_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_co2e("car_petrol", -1)

    def test_result_is_rounded_to_4_decimals(self):
        result = calculate_co2e("bus", 1)
        assert result == round(result, 4)

    def test_large_quantity(self):
        result = calculate_co2e("electricity_grid", 10000)
        assert result == pytest.approx(2330.0, rel=1e-3)


class TestEcoScore:
    """Tests for the eco_score function."""

    def test_net_zero_gets_perfect_score(self):
        score, label = eco_score(0)
        assert score == 100
        assert "Net Zero" in label

    def test_negative_is_also_perfect(self):
        score, label = eco_score(-10)
        assert score == 100

    def test_very_low_score_high_impact(self):
        score, label = eco_score(1500)
        assert score <= 15
        assert "High" in label

    def test_global_avg_is_mid_range(self):
        score, _ = eco_score(333)
        assert 50 <= score <= 75

    def test_score_decreases_with_higher_emissions(self):
        scores = [eco_score(kg)[0] for kg in [0, 100, 300, 600, 1000]]
        assert scores == sorted(scores, reverse=True)


class TestFactoryFunctions:
    """Tests for helper factory functions."""

    def test_get_factors_by_category_transport(self):
        factors = get_factors_by_category(ActivityCategory.TRANSPORT)
        assert len(factors) > 0
        subcats = [f.subcategory for f in factors]
        assert "car_petrol" in subcats
        assert "bicycle" in subcats

    def test_get_all_subcategories_has_all_categories(self):
        all_cats = get_all_subcategories()
        for cat in ActivityCategory:
            assert cat.value in all_cats

    def test_get_national_avg_known_country(self):
        avg = get_national_avg("United States")
        assert avg == COUNTRY_AVERAGES["United States"]

    def test_get_national_avg_unknown_defaults_to_global(self):
        avg = get_national_avg("Atlantis")
        assert avg == COUNTRY_AVERAGES["Global"]

    def test_all_emission_factors_positive_or_allowed_negative(self):
        """Negative factors only in WASTE category (avoided emissions)."""
        for cat, factors in EMISSION_FACTORS.items():
            for ef in factors:
                if cat != ActivityCategory.WASTE:
                    assert ef.kg_co2e_per_unit >= 0, (
                        f"{ef.subcategory} in {cat} should not be negative"
                    )
