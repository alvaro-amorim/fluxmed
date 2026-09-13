import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.domain.enums import UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.city import CityModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration


def test_city_endpoints_expose_generated_santa_aurora() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    email = f"city-api-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"
    with session_scope() as session:
        user = UserModel(
            email=email,
            display_name="City API Test",
            password_hash=hash_password(password),
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
        city = seed_santa_aurora(
            session,
            seed=20260913,
            dataset_version="api-test",
            replace=True,
        )
        city_id = city.id

    try:
        with TestClient(app) as client:
            login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200

            cities = client.get("/api/v1/cities")
            assert cities.status_code == 200
            assert len(cities.json()) == 1
            assert cities.json()[0]["name"] == "Santa Aurora"
            assert cities.json()[0]["district_count"] == 9
            assert cities.json()[0]["bridge_count"] == 3

            detail = client.get(f"/api/v1/cities/{city_id}")
            assert detail.status_code == 200
            assert detail.json()["generator_version"] == "santa-aurora-v1"

            districts = client.get(f"/api/v1/cities/{city_id}/districts")
            assert districts.status_code == 200
            assert len(districts.json()) == 9

            city_map = client.get(f"/api/v1/cities/{city_id}/map")
            assert city_map.status_code == 200
            assert city_map.json()["type"] == "FeatureCollection"
            feature_types = {
                feature["properties"]["feature_type"] for feature in city_map.json()["features"]
            }
            assert {"district", "road", "river", "depot", "city_boundary"} <= feature_types
    finally:
        with session_scope() as session:
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
            session.execute(delete(UserModel).where(UserModel.id == user_id))
            session.execute(delete(CityModel).where(CityModel.id == city_id))
            assert session.scalar(select(UserModel).where(UserModel.id == user_id)) is None
