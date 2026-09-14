import os
import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fluxmed.domain.enums import (
    HelperPolicy,
    OperationStatus,
    RevisionStatus,
    TrafficMode,
    UserRole,
    VehicleOwnershipType,
    VehicleStatus,
    VehicleType,
)
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.operation_revision import OperationRevisionModel
from fluxmed.infrastructure.models.optimization_result import (
    OptimizationRunModel,
    RoutePlanModel,
    RouteTeamAssignmentModel,
)
from fluxmed.infrastructure.models.resource import VehicleModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration


def test_result_endpoints_return_persisted_plan_and_approve_it() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    email = f"result-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"
    operation_id: uuid.UUID
    run_id: uuid.UUID
    route_id: uuid.UUID
    vehicle_id: uuid.UUID
    user_id: uuid.UUID

    with session_scope() as session:
        user = UserModel(
            email=email,
            display_name="Optimization Result API Test",
            password_hash=hash_password(password),
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
        operation = OperationModel(
            operation_code=f"OP-RESULT-{uuid.uuid4().hex[:8]}",
            operation_date=date(2026, 9, 16),
            operation_start_time=time(7, 30),
            operation_end_time=time(18, 0),
            traffic_mode=TrafficMode.AUTOMATIC,
            status=OperationStatus.OPTIMIZED,
            current_revision_number=1,
            created_by_user_id=user_id,
        )
        session.add(operation)
        session.flush()
        operation_id = operation.id
        revision = OperationRevisionModel(
            operation_id=operation.id,
            revision_number=1,
            status=RevisionStatus.OPTIMIZED,
            operation_date=operation.operation_date,
            operation_start_time=operation.operation_start_time,
            operation_end_time=operation.operation_end_time,
            traffic_mode=operation.traffic_mode,
            created_by_user_id=user_id,
        )
        session.add(revision)
        vehicle = VehicleModel(
            plate=f"TST{uuid.uuid4().hex[:4].upper()}",
            type=VehicleType.CARGO_VAN,
            ownership_type=VehicleOwnershipType.OWNED,
            max_payload_kg=Decimal("1000"),
            max_volume_m3=Decimal("8"),
            max_range_km=Decimal("500"),
            refrigerated=False,
            status=VehicleStatus.AVAILABLE,
            helper_policy=HelperPolicy.OPTIONAL,
            active=True,
        )
        session.add(vehicle)
        session.flush()
        vehicle_id = vehicle.id
        run = OptimizationRunModel(
            operation_id=operation.id,
            operation_revision_id=revision.id,
            status="COMPLETED",
            random_seed=42,
            generations_completed=30,
            stop_reason="EARLY_STOPPING",
            validated=True,
            delivery_count=0,
            vehicles_used=1,
            total_cost_brl=Decimal("85.50"),
            distance_km=Decimal("20"),
            makespan_minutes=Decimal("120"),
            critical_delays=0,
            on_time_percentage=Decimal("100"),
            average_weight_utilization_pct=Decimal("10"),
            average_volume_utilization_pct=Decimal("12.5"),
            pruning_counts={"CAPACITY_EXCEEDED": 2},
        )
        session.add(run)
        session.flush()
        run_id = run.id
        route = RoutePlanModel(
            optimization_run_id=run.id,
            route_code="R-01",
            sequence=1,
            vehicle_id=vehicle.id,
            total_weight_kg=Decimal("100"),
            total_volume_m3=Decimal("1"),
            distance_km=Decimal("20"),
            duration_minutes=Decimal("120"),
            weight_utilization_pct=Decimal("10"),
            volume_utilization_pct=Decimal("12.5"),
            depreciation_brl=Decimal("10"),
            maintenance_brl=Decimal("4"),
            fixed_time_brl=Decimal("20"),
            fuel_brl=Decimal("12"),
            team_brl=Decimal("20"),
            contract_brl=Decimal("0"),
            total_cost_brl=Decimal("66"),
            geometry={"type": "LineString", "coordinates": []},
        )
        session.add(route)
        session.flush()
        route_id = route.id
        session.add(
            RouteTeamAssignmentModel(
                route_id=route.id,
                primary_role="DRIVER",
                primary_included=True,
                helper_included=False,
                team_cost_brl=Decimal("0"),
            )
        )

    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200

            response = client.get(f"/api/v1/optimization-runs/{run_id}/result")
            assert response.status_code == 200
            body = response.json()
            assert body["operation_id"] == str(operation_id)
            assert body["validated"] is True
            assert body["routes"][0]["route_code"] == "R-01"
            assert body["routes"][0]["vehicle"]["id"] == str(vehicle_id)
            assert body["routes"][0]["cost"]["total_brl"] == "66.00"

            route_response = client.get(f"/api/v1/routes/{route_id}")
            assert route_response.status_code == 200
            assert route_response.json()["route_code"] == "R-01"

            approval = client.post(f"/api/v1/optimization-runs/{run_id}/approve")
            assert approval.status_code == 200

        with session_scope() as session:
            operation = session.get(OperationModel, operation_id)
            revision = session.scalar(
                pytest.importorskip("sqlalchemy")
                .select(OperationRevisionModel)
                .where(
                    OperationRevisionModel.operation_id == operation_id,
                    OperationRevisionModel.revision_number == 1,
                )
            )
            assert operation is not None
            assert operation.status is OperationStatus.APPROVED
            assert revision is not None
            assert revision.status is RevisionStatus.APPROVED
    finally:
        with session_scope() as session:
            session.execute(delete(OperationModel).where(OperationModel.id == operation_id))
            session.execute(delete(VehicleModel).where(VehicleModel.id == vehicle_id))
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
            session.execute(delete(UserModel).where(UserModel.id == user_id))
