import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.domain.enums import FacilityType, UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.city import AddressModel, CityModel, FacilityModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.operation_revision import OperationRevisionModel
from fluxmed.infrastructure.models.road_override import RoadOverrideModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration


@dataclass(frozen=True, slots=True)
class RoutingFixture:
    client: TestClient
    operation_id: uuid.UUID
    city_id: uuid.UUID
    destination_address_id: uuid.UUID


@pytest.fixture
def routing_fixture() -> Iterator[RoutingFixture]:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    seed = int(uuid.uuid4().int % 1_000_000_000)
    user_id = uuid.uuid4()
    email = f"routing-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"

    with session_scope() as session:
        city = seed_santa_aurora(
            session,
            seed=seed,
            dataset_version=f"routing-test-{seed}",
            replace=True,
        )
        city_id = city.id
        depot_address_id = session.scalar(
            select(AddressModel.id)
            .join(FacilityModel, FacilityModel.address_id == AddressModel.id)
            .where(
                FacilityModel.city_id == city_id,
                FacilityModel.facility_type == FacilityType.DEPOT,
            )
        )
        assert depot_address_id is not None
        destination_address_id = session.scalar(
            select(AddressModel.id)
            .where(
                AddressModel.city_id == city_id,
                AddressModel.active.is_(True),
                AddressModel.id != depot_address_id,
            )
            .order_by(AddressModel.house_number_numeric.desc())
            .limit(1)
        )
        assert destination_address_id is not None
        session.add(
            UserModel(
                id=user_id,
                email=email,
                display_name="Routing Test User",
                password_hash=hash_password(password),
                role=UserRole.PLANNER,
                active=True,
            )
        )

    operation_id: uuid.UUID | None = None
    try:
        with TestClient(app) as client:
            login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200
            created = client.post(
                "/api/v1/operations",
                json={
                    "operation_date": "2026-09-14",
                    "operation_start_time": "07:30:00",
                    "operation_end_time": "18:00:00",
                    "traffic_mode": "FREE",
                },
            )
            assert created.status_code == 201
            operation_id = uuid.UUID(created.json()["id"])
            yield RoutingFixture(
                client=client,
                operation_id=operation_id,
                city_id=city_id,
                destination_address_id=destination_address_id,
            )
    finally:
        with session_scope() as session:
            if operation_id is not None:
                session.execute(
                    delete(RoadOverrideModel).where(
                        RoadOverrideModel.operation_id == operation_id
                    )
                )
                session.execute(
                    delete(OperationRevisionModel).where(
                        OperationRevisionModel.operation_id == operation_id
                    )
                )
                session.execute(delete(OperationModel).where(OperationModel.id == operation_id))
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
            session.execute(delete(UserModel).where(UserModel.id == user_id))
            session.execute(delete(CityModel).where(CityModel.id == city_id))


def _preview(fixture: RoutingFixture) -> dict[str, object]:
    response = fixture.client.post(
        f"/api/v1/operations/{fixture.operation_id}/route-preview",
        json={
            "destination_address_id": str(fixture.destination_address_id),
            "algorithm": "ASTAR",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_route_preview_returns_real_geometry_and_cache_hit(
    routing_fixture: RoutingFixture,
) -> None:
    first = _preview(routing_fixture)
    second = _preview(routing_fixture)

    assert first["distance_m"] > 0
    assert first["travel_time_seconds"] > 0
    assert first["edge_ids"]
    assert first["geometry"]["type"] == "LineString"
    assert len(first["geometry"]["coordinates"]) >= 2
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["edge_ids"] == first["edge_ids"]


def test_closure_changes_route_or_reports_no_path(routing_fixture: RoutingFixture) -> None:
    initial = _preview(routing_fixture)
    edge_ids = initial["edge_ids"]
    assert isinstance(edge_ids, list) and edge_ids
    blocked_edge_id = edge_ids[len(edge_ids) // 2]

    created = routing_fixture.client.post(
        f"/api/v1/operations/{routing_fixture.operation_id}/road-overrides",
        json={
            "road_segment_id": blocked_edge_id,
            "override_type": "CLOSURE",
            "direction_scope": "SEGMENT_DIRECTION",
            "reason": "ROADWORK",
            "notes": "Interdição simulada no teste de roteamento.",
        },
    )
    assert created.status_code == 201, created.text
    override_id = created.json()["id"]

    rerouted = routing_fixture.client.post(
        f"/api/v1/operations/{routing_fixture.operation_id}/route-preview",
        json={"destination_address_id": str(routing_fixture.destination_address_id)},
    )
    if rerouted.status_code == 200:
        assert blocked_edge_id not in rerouted.json()["edge_ids"]
        assert rerouted.json()["cache_hit"] is False
    else:
        assert rerouted.status_code == 422
        assert rerouted.json()["error"]["code"] == "ROUTE_NOT_AVAILABLE"

    removed = routing_fixture.client.delete(
        f"/api/v1/operations/{routing_fixture.operation_id}/road-overrides/{override_id}"
    )
    assert removed.status_code == 204


def test_traffic_override_never_makes_free_flow_route_faster(
    routing_fixture: RoutingFixture,
) -> None:
    initial = _preview(routing_fixture)
    edge_ids = initial["edge_ids"]
    assert isinstance(edge_ids, list) and edge_ids
    congested_edge_id = edge_ids[len(edge_ids) // 2]

    created = routing_fixture.client.post(
        f"/api/v1/operations/{routing_fixture.operation_id}/road-overrides",
        json={
            "road_segment_id": congested_edge_id,
            "override_type": "TRAFFIC",
            "direction_scope": "SEGMENT_DIRECTION",
            "traffic_level": "VERY_HEAVY",
            "reason": "EVENT",
        },
    )
    assert created.status_code == 201, created.text

    rerouted = _preview(routing_fixture)
    assert rerouted["travel_time_seconds"] >= initial["travel_time_seconds"]

    listed = routing_fixture.client.get(
        f"/api/v1/operations/{routing_fixture.operation_id}/road-overrides"
    )
    assert listed.status_code == 200
    assert any(item["road_segment_id"] == congested_edge_id for item in listed.json())
