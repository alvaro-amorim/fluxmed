import os
import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fluxmed.domain.enums import OperationStatus, TrafficMode, UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.resource import (
    AggregatedVehicleContractModel,
    OperationVehicleSelectionModel,
    OperationWorkerSelectionModel,
    OwnedVehicleCostProfileModel,
    VehicleMaintenanceItemModel,
    VehicleModel,
    WorkerAvailabilityModel,
    WorkerModel,
)
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration


def test_resource_crud_costs_availability_and_operation_selection() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    email = f"resources-api-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"
    operation_id: uuid.UUID
    user_id: uuid.UUID

    with session_scope() as session:
        user = UserModel(
            email=email,
            display_name="Resources API Test",
            password_hash=hash_password(password),
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
        operation = OperationModel(
            operation_code=f"OP-RES-{uuid.uuid4().hex[:8]}",
            operation_date=date(2026, 9, 15),
            operation_start_time=time(7, 30),
            operation_end_time=time(18, 0),
            traffic_mode=TrafficMode.AUTOMATIC,
            status=OperationStatus.DRAFT,
            current_revision_number=0,
            created_by_user_id=user_id,
        )
        session.add(operation)
        session.flush()
        operation_id = operation.id

    vehicle_ids: list[uuid.UUID] = []
    worker_ids: list[uuid.UUID] = []
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200

            owned = client.post(
                "/api/v1/vehicles",
                json={
                    "plate": "ABC1D23",
                    "type": "CARGO_VAN",
                    "ownership_type": "OWNED",
                    "max_payload_kg": "1500",
                    "max_volume_m3": "8.5",
                    "max_range_km": "450",
                    "refrigerated": True,
                    "helper_policy": "OPTIONAL",
                    "fuel_type": "DIESEL",
                    "fuel_efficiency_km_per_l": "10",
                    "owned_cost": {
                        "acquisition_value_brl": "120000",
                        "residual_value_brl": "20000",
                        "useful_life_km": "200000",
                        "annual_ipva_brl": "2400",
                        "annual_insurance_brl": "3600",
                        "annual_fixed_costs_brl": "6000",
                        "expected_productive_hours_per_year": "2000",
                        "maintenance_items": [
                            {
                                "name": "Revisão preventiva",
                                "cost_brl": "1200",
                                "interval_km": "10000",
                            }
                        ],
                    },
                },
            )
            assert owned.status_code == 201
            owned_body = owned.json()
            owned_id = uuid.UUID(owned_body["id"])
            vehicle_ids.append(owned_id)
            assert owned_body["cost"]["depreciation_per_km"] == "0.5"
            assert owned_body["cost"]["maintenance_per_km"] == "0.12"
            assert owned_body["cost"]["fixed_cost_per_hour"] == "6"

            aggregated = client.post(
                "/api/v1/vehicles",
                json={
                    "plate": "XYZ9A87",
                    "type": "VAN_COMPACT",
                    "ownership_type": "AGGREGATED",
                    "max_payload_kg": "900",
                    "max_volume_m3": "5",
                    "max_range_km": "350",
                    "aggregated_contract": {
                        "price_brl": "480",
                        "fuel_included": True,
                        "driver_included": True,
                        "helper_included": False,
                    },
                },
            )
            assert aggregated.status_code == 201
            aggregated_body = aggregated.json()
            aggregated_id = uuid.UUID(aggregated_body["id"])
            vehicle_ids.append(aggregated_id)
            assert aggregated_body["cost"]["contract_price_brl"] == "480"
            assert aggregated_body["cost"]["fuel_included"] is True
            assert aggregated_body["cost"]["driver_included"] is True

            driver = client.post(
                "/api/v1/workers",
                json={
                    "name": "Carlos Almeida",
                    "role": "DRIVER",
                    "engagement_type": "EMPLOYEE",
                    "compensation_model": "HOURLY",
                    "compensation_value_brl": "28.50",
                },
            )
            assert driver.status_code == 201
            driver_id = uuid.UUID(driver.json()["id"])
            worker_ids.append(driver_id)

            helper = client.post(
                "/api/v1/workers",
                json={
                    "name": "Marina Souza",
                    "role": "HELPER",
                    "engagement_type": "DAY_WORKER",
                    "compensation_model": "DAILY",
                    "compensation_value_brl": "180",
                },
            )
            assert helper.status_code == 201
            helper_id = uuid.UUID(helper.json()["id"])
            worker_ids.append(helper_id)

            availability = client.put(
                f"/api/v1/workers/{helper_id}/availability",
                json={
                    "date": "2026-09-15",
                    "available": False,
                    "notes": "Folga programada",
                },
            )
            assert availability.status_code == 200
            assert availability.json()["available"] is False

            blocked = client.put(
                f"/api/v1/operations/{operation_id}/resources",
                json={
                    "vehicle_ids": [str(owned_id)],
                    "worker_ids": [str(driver_id), str(helper_id)],
                },
            )
            assert blocked.status_code == 422
            assert blocked.json()["error"]["code"] == "INVALID_RESOURCE"

            selected = client.put(
                f"/api/v1/operations/{operation_id}/resources",
                json={
                    "vehicle_ids": [str(owned_id), str(aggregated_id)],
                    "worker_ids": [str(driver_id)],
                },
            )
            assert selected.status_code == 200
            selected_body = selected.json()
            assert set(selected_body["selected_vehicle_ids"]) == {
                str(owned_id),
                str(aggregated_id),
            }
            assert selected_body["selected_worker_ids"] == [str(driver_id)]
            assert str(helper_id) in selected_body["unavailable_worker_ids"]

            deactivated = client.post(f"/api/v1/vehicles/{aggregated_id}/deactivate")
            assert deactivated.status_code == 200
            assert deactivated.json()["active"] is False
            assert deactivated.json()["status"] == "INACTIVE"

            selection_after_deactivation = client.get(
                f"/api/v1/operations/{operation_id}/resources"
            )
            assert selection_after_deactivation.status_code == 200
            assert str(aggregated_id) in selection_after_deactivation.json()["selected_vehicle_ids"]
    finally:
        with session_scope() as session:
            session.execute(
                delete(OperationVehicleSelectionModel).where(
                    OperationVehicleSelectionModel.operation_id == operation_id
                )
            )
            session.execute(
                delete(OperationWorkerSelectionModel).where(
                    OperationWorkerSelectionModel.operation_id == operation_id
                )
            )
            if worker_ids:
                session.execute(
                    delete(WorkerAvailabilityModel).where(
                        WorkerAvailabilityModel.worker_id.in_(worker_ids)
                    )
                )
                session.execute(delete(WorkerModel).where(WorkerModel.id.in_(worker_ids)))
            if vehicle_ids:
                session.execute(
                    delete(VehicleMaintenanceItemModel).where(
                        VehicleMaintenanceItemModel.vehicle_id.in_(vehicle_ids)
                    )
                )
                session.execute(
                    delete(OwnedVehicleCostProfileModel).where(
                        OwnedVehicleCostProfileModel.vehicle_id.in_(vehicle_ids)
                    )
                )
                session.execute(
                    delete(AggregatedVehicleContractModel).where(
                        AggregatedVehicleContractModel.vehicle_id.in_(vehicle_ids)
                    )
                )
                session.execute(delete(VehicleModel).where(VehicleModel.id.in_(vehicle_ids)))
            session.execute(delete(OperationModel).where(OperationModel.id == operation_id))
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
            session.execute(delete(UserModel).where(UserModel.id == user_id))
