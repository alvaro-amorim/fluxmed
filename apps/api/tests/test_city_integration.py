import os
import uuid

import pytest
from sqlalchemy import delete, func, select

from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.city.service import CityService
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.city import (
    AddressModel,
    CityModel,
    DistrictModel,
    RoadSegmentModel,
    StreetModel,
)

pytestmark = pytest.mark.integration


def test_city_persists_valid_geometry_and_serves_address_search() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    seed = int(uuid.uuid4().int % 1_000_000_000)
    with session_scope() as session:
        city = seed_santa_aurora(session, seed=seed, dataset_version=f"test-{seed}", replace=True)
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
            first_address = session.execute(
                select(AddressModel, StreetModel.name)
                .join(StreetModel, StreetModel.id == AddressModel.street_id)
                .where(AddressModel.city_id == city_id)
                .order_by(StreetModel.name, AddressModel.house_number_numeric)
                .limit(1)
            ).one()
            address, street_name = first_address
            service = CityService(session)
            exact_search = service.search_addresses(
                city_id, f"{street_name}, {address.house_number}"
            )
            fuzzy_search = service.search_addresses(city_id, street_name[:-1])
            missing_number = service.search_addresses(city_id, f"{street_name}, 999999")
            facilities = service.facilities(city_id)

        assert boundary_valid is True
        assert districts_valid is True
        assert segments_valid is True
        assert summary.district_count == 9
        assert 140 <= summary.street_count <= 170
        assert 700 <= summary.intersection_count <= 900
        assert 20_000 <= summary.address_count <= 40_000
        assert 40 <= summary.facility_count <= 60
        assert summary.bridge_count == 3
        assert exact_search.matches
        assert exact_search.matches[0].id == address.id
        assert fuzzy_search.matches
        assert fuzzy_search.street_suggestion == street_name
        assert not missing_number.matches
        assert missing_number.number_suggestions
        assert len(facilities) == summary.facility_count
        assert geojson["type"] == "FeatureCollection"
        assert any(
            feature["properties"]["feature_type"] == "depot" for feature in geojson["features"]
        )
        assert any(
            feature["properties"]["feature_type"] == "river" for feature in geojson["features"]
        )
        assert any(
            feature["properties"]["feature_type"] == "facility"
            for feature in geojson["features"]
        )
    finally:
        with session_scope() as session:
            session.execute(delete(CityModel).where(CityModel.id == city_id))
