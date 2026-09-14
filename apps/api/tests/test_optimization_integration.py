import os
import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import select

from fluxmed.application.optimization import OptimizationService
from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.domain.enums import (
    CompensationModel,
    DeliveryPriority,
    DeliveryStatus,
    FacilityType,
    HandlingRequirement,
    HelperPolicy,
    ServiceTimeSource,
    TemperatureClass,
    TimeWindowPolicy,
    TrafficMode,
    UserRole,
    VehicleOwnershipType,
    VehicleStatus,
    VehicleType,
    WorkerEngagementType,
    WorkerRole,
)
from fluxmed.infrastructure.database import SessionFactory
from fluxmed.infrastructure.models.city import AddressModel, FacilityModel
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.resource import (
    OperationVehicleSelectionModel,
    OperationWorkerSelectionModel,
    OwnedVehicleCostProfileModel,
    VehicleModel,
    WorkerModel,
)
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.optimization import GeneticOptimizerConfig

pytestmark = pytest.mark.integration


def test_operation_runs_ga_and_returns_valid_multi_vehicle_plan() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    session = SessionFactory()
    try:
        seed = int(uuid.uuid4().int % 1_000_000_000)
        city = seed_santa_aurora(
            session,
            seed=seed,
            dataset_version=f"optimizer-test-{seed}",
            replace=True,
        )
        depot_address_id = session.scalar(
            select(FacilityModel.address_id)
            .where(
                FacilityModel.city_id == city.id,
                FacilityModel.facility_type == FacilityType.DEPOT,
            )
            .limit(1)
        )
        assert depot_address_id is not None
        address_ids = list(
            session.scalars(
                select(AddressModel.id)
                .where(
                    AddressModel.city_id == city.id,
                    AddressModel.active.is_(True),
                    AddressModel.id != depot_address_id,
                )
                .order_by(AddressModel.house_number_numeric)
                .limit(5)
            )
        )
        assert len(address_ids) == 5

        user = UserModel(
            email=f"optimizer-{uuid.uuid4().hex}@example.test",
            display_name="Optimizer Test",
            password_hash="not-used-in-this-test",
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        operation = OperationModel(
            operation_code=f"OPT-{uuid.uuid4().hex[:10].upper()}",
            operation_date=date(2026, 9, 14),
            operation_start_time=time(7, 30),
            operation_end_time=time(18, 0),
            traffic_mode=TrafficMode.FREE,
            created_by_user_id=user.id,
        )
        session.add(operation)
        session.flush()

        deliveries: list[DeliveryModel] = []
        for index, address_id in enumerate(address_ids, start=1):
            delivery = DeliveryModel(
                delivery_code=f"DLV-OPT-{seed}-{index:03d}",
                operation_id=operation.id,
                invoice_number=f"NF{index}",
                invoice_series="1",
                issuer_document="00000000000100",
                destination_address_id=address_id,
                recipient_name=f"Destino {index}",
                package_count=1,
                total_weight_kg=Decimal("70"),
                total_volume_m3=Decimal("0.25"),
                priority=DeliveryPriority.NORMAL,
                time_window_start=None,
                time_window_end=None,
                time_window_policy=TimeWindowPolicy.SOFT,
                service_time_minutes=5,
                service_time_source=ServiceTimeSource.ESTIMATED,
                temperature_class=TemperatureClass.AMBIENT,
                handling_requirement=HandlingRequirement.STANDARD,
                status=DeliveryStatus.PENDING,
            )
            session.add(delivery)
            deliveries.append(delivery)

        vehicles: list[VehicleModel] = []
        for index in range(2):
            vehicle = VehicleModel(
                plate=f"OPT{seed % 1000:03d}{index}",
                type=VehicleType.CARGO_VAN,
                ownership_type=VehicleOwnershipType.OWNED,
                max_payload_kg=Decimal("220"),
                max_volume_m3=Decimal("1.20"),
                max_range_km=Decimal("500"),
                refrigerated=False,
                status=VehicleStatus.AVAILABLE,
                helper_policy=HelperPolicy.OPTIONAL,
                active=True,
            )
            session.add(vehicle)
            session.flush()
            session.add(
                OwnedVehicleCostProfileModel(
                    vehicle_id=vehicle.id,
                    acquisition_value_brl=Decimal("120000"),
                    residual_value_brl=Decimal("30000"),
                    useful_life_km=Decimal("240000"),
                    annual_ipva_brl=Decimal("2400"),
                    annual_insurance_brl=Decimal("3600"),
                    annual_fixed_costs_brl=Decimal("6000"),
                    expected_productive_hours_per_year=Decimal("2000"),
                )
            )
            session.add(
                OperationVehicleSelectionModel(
                    operation_id=operation.id,
                    vehicle_id=vehicle.id,
                )
            )
            vehicles.append(vehicle)

        for index in range(2):
            worker = WorkerModel(
                name=f"Motorista Teste {index + 1}",
                role=WorkerRole.DRIVER,
                engagement_type=WorkerEngagementType.EMPLOYEE,
                compensation_model=CompensationModel.HOURLY,
                compensation_value_brl=Decimal("25") + Decimal(index),
                active=True,
            )
            session.add(worker)
            session.flush()
            session.add(
                OperationWorkerSelectionModel(
                    operation_id=operation.id,
                    worker_id=worker.id,
                )
            )
        session.flush()

        result = OptimizationService(
            session,
            config=GeneticOptimizerConfig(
                population_size=16,
                max_generations=18,
                stagnation_generations=6,
            ),
        ).optimize_operation(operation.id, random_seed=582914)

        assigned = [
            delivery_id
            for route in result.result.best.solution.routes
            for delivery_id in route.delivery_ids
        ]
        assert result.validation.valid is True
        assert result.result.best.fitness.feasible is True
        assert set(assigned) == {delivery.id for delivery in deliveries}
        assert len(result.result.best.solution.routes) == 2
        assert all(route.returns_to_depot for route in result.result.best.solution.routes)
    finally:
        session.rollback()
        session.close()
