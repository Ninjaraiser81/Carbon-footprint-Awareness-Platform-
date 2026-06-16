"""
Integration tests for Auth and Activities API endpoints.
"""
import pytest
from datetime import datetime, timezone


class TestAuth:
    """Integration tests for /api/v1/auth endpoints."""

    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass1",
            "country": "India",
            "annual_goal_kg": 1500.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "newuser"
        assert data["user"]["country"] == "India"

    def test_register_duplicate_username(self, client, registered_user):
        resp = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "OtherPass1",
        })
        assert resp.status_code == 409

    def test_register_duplicate_email(self, client, registered_user):
        resp = client.post("/api/v1/auth/register", json={
            "username": "differentuser",
            "email": "test@example.com",
            "password": "DiffPass1",
        })
        assert resp.status_code == 409

    def test_register_weak_password_no_uppercase(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "nouppercase1",
        })
        assert resp.status_code == 422

    def test_register_weak_password_no_digit(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "weakuser2",
            "email": "weak2@example.com",
            "password": "NoDigitPass",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "username": "badmail",
            "email": "not-an-email",
            "password": "ValidPass1",
        })
        assert resp.status_code == 422

    def test_login_success(self, client, registered_user):
        resp = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "TestPass1",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "WrongPass1",
        })
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "username": "nobody",
            "password": "TestPass1",
        })
        assert resp.status_code == 401

    def test_get_me_authenticated(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_get_me_no_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 403

    def test_get_me_invalid_token(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer faketoken"})
        assert resp.status_code == 401


class TestActivities:
    """Integration tests for /api/v1/activities endpoints."""

    SAMPLE_ACTIVITY = {
        "category": "transport",
        "subcategory": "car_petrol",
        "description": "Daily commute",
        "quantity": 20.0,
        "unit": "km",
        "activity_date": "2024-06-01T08:00:00Z",
    }

    def test_create_activity_success(self, client, auth_headers):
        resp = client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["subcategory"] == "car_petrol"
        assert data["co2e_kg"] == pytest.approx(3.4, rel=1e-2)
        assert data["category"] == "transport"

    def test_create_activity_auto_calculates_co2e(self, client, auth_headers):
        """CO2e should be calculated server-side, not provided by client."""
        resp = client.post("/api/v1/activities/", json={
            **self.SAMPLE_ACTIVITY,
            "subcategory": "beef",
            "unit": "kg",
            "quantity": 2.0,
            "category": "food",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["co2e_kg"] == pytest.approx(54.0, rel=1e-2)

    def test_create_activity_invalid_subcategory(self, client, auth_headers):
        resp = client.post("/api/v1/activities/", json={
            **self.SAMPLE_ACTIVITY,
            "subcategory": "invalid_xyz",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_activity_negative_quantity(self, client, auth_headers):
        resp = client.post("/api/v1/activities/", json={
            **self.SAMPLE_ACTIVITY,
            "quantity": -5,
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_activity_requires_auth(self, client):
        resp = client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY)
        assert resp.status_code == 403

    def test_list_activities(self, client, auth_headers):
        client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        resp = client.get("/api/v1/activities/", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 2

    def test_list_activities_filter_by_category(self, client, auth_headers):
        client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        resp = client.get("/api/v1/activities/?category=transport", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json():
            assert item["category"] == "transport"

    def test_get_activity_by_id(self, client, auth_headers):
        created = client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        activity_id = created.json()["id"]
        resp = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == activity_id

    def test_get_activity_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/activities/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_activity(self, client, auth_headers):
        created = client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        activity_id = created.json()["id"]
        resp = client.put(
            f"/api/v1/activities/{activity_id}",
            json={"quantity": 40.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 40.0
        assert resp.json()["co2e_kg"] == pytest.approx(6.8, rel=1e-2)

    def test_delete_activity(self, client, auth_headers):
        created = client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        activity_id = created.json()["id"]
        resp = client.delete(f"/api/v1/activities/{activity_id}", headers=auth_headers)
        assert resp.status_code == 204
        # Confirm it's gone
        get_resp = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_list_subcategories_public(self, client):
        """Subcategories endpoint should be publicly accessible."""
        resp = client.get("/api/v1/activities/subcategories")
        assert resp.status_code == 200
        data = resp.json()
        assert "transport" in data
        assert "food" in data
        assert "energy" in data

    def test_pagination_limit(self, client, auth_headers):
        for _ in range(5):
            client.post("/api/v1/activities/", json=self.SAMPLE_ACTIVITY, headers=auth_headers)
        resp = client.get("/api/v1/activities/?limit=2", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


class TestDashboard:
    """Integration tests for /api/v1/dashboard."""

    def test_dashboard_empty_user(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_co2e_this_month"] == 0.0
        assert "carbon_score" in data
        assert "badges" in data
        assert "daily_trend" in data

    def test_dashboard_after_logging(self, client, auth_headers):
        client.post("/api/v1/activities/", json={
            "category": "food",
            "subcategory": "beef",
            "quantity": 1.0,
            "unit": "kg",
            "activity_date": datetime.now(timezone.utc).isoformat(),
        }, headers=auth_headers)
        resp = client.get("/api/v1/dashboard/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total_co2e_this_month"] > 0


class TestInsights:
    """Integration tests for /api/v1/insights."""

    def test_insights_no_data(self, client, auth_headers):
        resp = client.get("/api/v1/insights/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "eco_score" in data
        assert "recommendations" in data
        assert "tip_of_the_day" in data
        assert isinstance(data["recommendations"], list)

    def test_insights_with_high_transport(self, client, auth_headers):
        for _ in range(5):
            client.post("/api/v1/activities/", json={
                "category": "transport",
                "subcategory": "car_petrol",
                "quantity": 500.0,
                "unit": "km",
                "activity_date": datetime.now(timezone.utc).isoformat(),
            }, headers=auth_headers)
        resp = client.get("/api/v1/insights/", headers=auth_headers)
        data = resp.json()
        assert data["top_emission_category"] == "transport"
        # Check there's a transport-related recommendation
        rec_cats = [r["category"] for r in data["recommendations"]]
        assert "transport" in rec_cats


class TestHealthCheck:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Carbon Footprint Tracker" in resp.json()["message"]
