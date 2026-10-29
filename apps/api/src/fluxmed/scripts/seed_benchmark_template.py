"""Restore the exact resource/time template used by the academic benchmark."""

import argparse
import json
import os
import uuid
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Numeric, Uuid, select
from sqlalchemy.orm import Session

from fluxmed.domain.enums import OperationStatus, TrafficMode
from fluxmed.infrastructure.database import SessionFactory
from fluxmed.infrastructure.models.city import CityModel
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
from fluxmed.infrastructure.models.road_override import RoadOverrideModel
from fluxmed.infrastructure.models.user import UserModel

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "benchmarks"
    / "fixtures"
    / "operation-OP-20260915-001.json"
)
RESOURCE_TABLES: tuple[tuple[str, type[Any]], ...] = (
    ("vehicles", VehicleModel),
    ("workers", WorkerModel),
    ("owned_profiles", OwnedVehicleCostProfileModel),
    ("maintenance_items", VehicleMaintenanceItemModel),
    ("aggregated_contracts", AggregatedVehicleContractModel),
)


def load_fixture(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    fixture: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if (
        fixture["operation"]["operation_code"] != "OP-20260915-001"
        or len(fixture["vehicles"]) != 7
        or len(fixture["workers"]) != 12
        or fixture["worker_availability"]
        or fixture["road_overrides"]
        or len(fixture["city"]) != 1
    ):
        raise ValueError("Academic template fixture does not match the archived experiment.")
    return fixture


def _model_values(model: type[Any], row: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in row.items():
        column = model.__table__.columns[key]
        if value is not None and isinstance(column.type, Uuid):
            value = uuid.UUID(value)
        elif value is not None and isinstance(column.type, Numeric):
            value = Decimal(value)
        elif value is not None and isinstance(column.type, SAEnum):
            enum_class = column.type.enum_class
            if enum_class is None:
                raise ValueError(f"Enum type missing for {model.__name__}.{key}.")
            value = enum_class(value)
        values[key] = value
    return values


def _verify_rows(session: Session, fixture: dict[str, Any]) -> None:
    for key, model in RESOURCE_TABLES:
        for row in fixture[key]:
            expected = _model_values(model, row)
            stored = session.get(model, expected["id"])
            if stored is None or any(
                getattr(stored, field) != value for field, value in expected.items()
            ):
                raise ValueError(f"Stored {key} differ from the academic fixture.")


def verify_template(session: Session, fixture: dict[str, Any]) -> None:
    city_data = fixture["city"][0]
    city = session.scalar(select(CityModel).where(CityModel.name == city_data["name"]))
    if city is None or any(
        str(getattr(city, key)) != str(value) for key, value in city_data.items()
    ):
        raise ValueError("Santa Aurora seed/version differs from the academic fixture.")

    operation_data = fixture["operation"]
    operation = session.scalar(
        select(OperationModel).where(
            OperationModel.operation_code == operation_data["operation_code"]
        )
    )
    if operation is None:
        raise ValueError("Academic template operation is absent.")
    if (
        operation.id != uuid.UUID(operation_data["id"])
        or operation.operation_date != date.fromisoformat(operation_data["operation_date"])
        or operation.operation_start_time
        != time.fromisoformat(operation_data["operation_start_time"])
        or operation.operation_end_time != time.fromisoformat(operation_data["operation_end_time"])
        or operation.traffic_mode != TrafficMode(operation_data["traffic_mode"])
    ):
        raise ValueError("Stored operation settings differ from the academic fixture.")
    vehicle_ids = set(
        session.scalars(
            select(OperationVehicleSelectionModel.vehicle_id).where(
                OperationVehicleSelectionModel.operation_id == operation.id
            )
        )
    )
    worker_ids = set(
        session.scalars(
            select(OperationWorkerSelectionModel.worker_id).where(
                OperationWorkerSelectionModel.operation_id == operation.id
            )
        )
    )
    if vehicle_ids != {uuid.UUID(row["id"]) for row in fixture["vehicles"]} or worker_ids != {
        uuid.UUID(row["id"]) for row in fixture["workers"]
    }:
        raise ValueError("Stored resource selection differs from the academic fixture.")
    if (
        session.scalar(
            select(RoadOverrideModel.id)
            .where(RoadOverrideModel.operation_id == operation.id)
            .limit(1)
        )
        is not None
    ):
        raise ValueError("Stored operation has road overrides absent from the academic fixture.")
    if (
        session.scalar(
            select(WorkerAvailabilityModel.id)
            .where(
                WorkerAvailabilityModel.worker_id.in_(worker_ids),
                WorkerAvailabilityModel.date == operation.operation_date,
            )
            .limit(1)
        )
        is not None
    ):
        raise ValueError("Stored worker availability differs from the academic fixture.")
    maintenance_ids = set(
        session.scalars(
            select(VehicleMaintenanceItemModel.id).where(
                VehicleMaintenanceItemModel.vehicle_id.in_(vehicle_ids)
            )
        )
    )
    if maintenance_ids != {uuid.UUID(row["id"]) for row in fixture["maintenance_items"]}:
        raise ValueError("Stored maintenance items differ from the academic fixture.")
    _verify_rows(session, fixture)


def seed_template(session: Session, fixture: dict[str, Any]) -> bool:
    """Insert only into an empty demo resource catalog; never replace existing rows."""
    operation_data = fixture["operation"]
    existing = session.scalar(
        select(OperationModel).where(
            OperationModel.operation_code == operation_data["operation_code"]
        )
    )
    if existing is not None:
        verify_template(session, fixture)
        return False

    if (
        session.scalar(select(VehicleModel.id).limit(1)) is not None
        or session.scalar(select(WorkerModel.id).limit(1)) is not None
    ):
        raise ValueError(
            "Seed requires a fresh demo resource catalog; existing rows were preserved."
        )

    demo_email = os.getenv("DEMO_PLANNER_EMAIL", "planner@fluxmed.demo").strip().lower()
    user = session.scalar(select(UserModel).where(UserModel.email == demo_email))
    if user is None:
        raise ValueError("Demo user is absent. Run the standard Docker init first.")

    for key, model in RESOURCE_TABLES:
        for row in fixture[key]:
            session.add(model(**_model_values(model, row)))
        session.flush()

    operation = OperationModel(
        id=uuid.UUID(operation_data["id"]),
        operation_code=operation_data["operation_code"],
        operation_date=date.fromisoformat(operation_data["operation_date"]),
        operation_start_time=time.fromisoformat(operation_data["operation_start_time"]),
        operation_end_time=time.fromisoformat(operation_data["operation_end_time"]),
        traffic_mode=TrafficMode(operation_data["traffic_mode"]),
        status=OperationStatus.DRAFT,
        current_revision_number=0,
        created_by_user_id=user.id,
    )
    session.add(operation)
    session.flush()
    session.add_all(
        OperationVehicleSelectionModel(operation_id=operation.id, vehicle_id=uuid.UUID(row["id"]))
        for row in fixture["vehicles"]
    )
    session.add_all(
        OperationWorkerSelectionModel(operation_id=operation.id, worker_id=uuid.UUID(row["id"]))
        for row in fixture["workers"]
    )
    session.flush()
    verify_template(session, fixture)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Insert the academic benchmark template into a fresh local demo database.",
    )
    args = parser.parse_args()
    fixture = load_fixture()
    if args.seed and os.getenv("APP_ENV", "development").strip().lower() == "production":
        parser.error("Academic fixture seeding is unavailable in production.")
    with SessionFactory.begin() as session:
        if args.seed:
            inserted = seed_template(session, fixture)
            print(
                "Academic benchmark template created." if inserted else "Template already matches."
            )
        else:
            verify_template(session, fixture)
            print("Academic benchmark template matches the stored operation.")


if __name__ == "__main__":
    main()
