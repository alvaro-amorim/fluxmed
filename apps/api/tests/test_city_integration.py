import os
import uuid

import pytest
from sqlalchemy import delete, func, select

from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.city.service import CityService
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.city import CityModel, DistrictModel, RoadSegmentModel

pytestmark = pytest.mark.integration


def test_city_persists_valid_geometry_and_serves_geojson() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    seed = int(uuid.uuid4().int % 1_000_000_000)
    with session_scope() as session:
        city = seed_santa_aurora(
            session, seed=seed, dataset_version=f"test-{seed}", replace=True
        )
        city_id = city.id

    try:
        with session_scope() as session:
            boundary_valid = session.scalar(
                select(func.ST_IsValid(CityModel.boundary)).where(CityModel.id == city_id)
            )
            districts_valid = session.scalar(
                select(func.bool_and(func.ST_IsValid(DistrictModel.geometry))).where(
                    DistrictModel.city_id == city_id
                )
            )
            segments_valid = session.scalar(
                select(func.bool_and(func.ST_IsValid(RoadSegmentModel.geometry))).where(
                    RoadSegmentModel.city_id == city_id
                )
            )
            summary = CityService(session).get(city_id)
            geojson = CityService(session).map_geojson(city_id)

        assert boundary_valid is True
        assert districts_valid is True
        assert segments_valid is True
        assert summary.district_count == 9
        assert summary.intersection_count == 56
        assert summary.bridge_count == 3
        assert geojson["type"] == "FeatureCollection"
        assert any(
            feature["properties"]["feature_type"] == "depot"
            for feature in geojson["features"]
        )
        assert any(
            feature["properties"]["feature_type"] == "river"
            for feature in geojson["features"]
        )
    finally:
        with session_scope() as session:
            session.execute(delete(CityModel).where(CityModel.id == city_id))
