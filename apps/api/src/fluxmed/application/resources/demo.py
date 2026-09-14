import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from fluxmed.application.resources.service import (
    AggregatedContractInput,
    MaintenanceInput,
    OperationResourcesView,
    OwnedCostInput,
    ResourceService,
    VehicleInput,
    WorkerInput,
)
from fluxmed.domain.enums import (
    CompensationModel,
    FuelType,
    HelperPolicy,
    VehicleOwnershipType,
    VehicleStatus,
    VehicleType,
    WorkerEngagementType,
    WorkerRole,
)


def _owned_cost(
    *,
    acquisition: str,
    residual: str,
    useful_life_km: str,
    annual_fixed_costs: str,
    maintenance_cost: str,
    maintenance_interval_km: str,
) -> OwnedCostInput:
    return OwnedCostInput(
        acquisition_value_brl=Decimal(acquisition),
        residual_value_brl=Decimal(residual),
        useful_life_km=Decimal(useful_life_km),
        annual_ipva_brl=Decimal("3200"),
        annual_insurance_brl=Decimal("4800"),
        annual_fixed_costs_brl=Decimal(annual_fixed_costs),
        expected_productive_hours_per_year=Decimal("2200"),
        maintenance_items=[
            MaintenanceInput(
                name="Revisão preventiva demo",
                cost_brl=Decimal(maintenance_cost),
                interval_km=Decimal(maintenance_interval_km),
            )
        ],
    )


def _demo_vehicle_inputs() -> tuple[VehicleInput, ...]:
    return (
        VehicleInput(
            plate="FMD1A01",
            type=VehicleType.CARGO_VAN,
            ownership_type=VehicleOwnershipType.OWNED,
            max_payload_kg=Decimal("1800"),
            max_volume_m3=Decimal("10"),
            max_range_km=Decimal("520"),
            refrigerated=True,
            helper_policy=HelperPolicy.OPTIONAL,
            fuel_type=FuelType.DIESEL,
            fuel_efficiency_km_per_l=Decimal("9.5"),
            owned_cost=_owned_cost(
                acquisition="210000",
                residual="60000",
                useful_life_km="320000",
                annual_fixed_costs="4200",
                maintenance_cost="1800",
                maintenance_interval_km="12000",
            ),
        ),
        VehicleInput(
            plate="FMD1A02",
            type=VehicleType.CARGO_VAN,
            ownership_type=VehicleOwnershipType.OWNED,
            max_payload_kg=Decimal("1600"),
            max_volume_m3=Decimal("9"),
            max_range_km=Decimal("500"),
            refrigerated=False,
            helper_policy=HelperPolicy.OPTIONAL,
            fuel_type=FuelType.DIESEL,
            fuel_efficiency_km_per_l=Decimal("10"),
            owned_cost=_owned_cost(
                acquisition="190000",
                residual="50000",
                useful_life_km="320000",
                annual_fixed_costs="3900",
                maintenance_cost="1650",
                maintenance_interval_km="12000",
            ),
        ),
        VehicleInput(
            plate="FMD1A03",
            type=VehicleType.VAN_COMPACT,
            ownership_type=VehicleOwnershipType.OWNED,
            max_payload_kg=Decimal("900"),
            max_volume_m3=Decimal("5"),
            max_range_km=Decimal("430"),
            refrigerated=True,
            helper_policy=HelperPolicy.OPTIONAL,
            fuel_type=FuelType.DIESEL,
            fuel_efficiency_km_per_l=Decimal("11"),
            owned_cost=_owned_cost(
                acquisition="155000",
                residual="42000",
                useful_life_km="280000",
                annual_fixed_costs="3400",
                maintenance_cost="1350",
                maintenance_interval_km="12000",
            ),
        ),
        VehicleInput(
            plate="FMD1A04",
            type=VehicleType.VAN_COMPACT,
            ownership_type=VehicleOwnershipType.OWNED,
            max_payload_kg=Decimal("850"),
            max_volume_m3=Decimal("4.8"),
            max_range_km=Decimal("430"),
            refrigerated=False,
            helper_policy=HelperPolicy.OPTIONAL,
            fuel_type=FuelType.DIESEL,
            fuel_efficiency_km_per_l=Decimal("11.5"),
            owned_cost=_owned_cost(
                acquisition="145000",
                residual="38000",
                useful_life_km="280000",
                annual_fixed_costs="3200",
                maintenance_cost="1250",
                maintenance_interval_km="12000",
            ),
        ),
        VehicleInput(
            plate="FMD1A05",
            type=VehicleType.LIGHT_TRUCK,
            ownership_type=VehicleOwnershipType.OWNED,
            max_payload_kg=Decimal("4500"),
            max_volume_m3=Decimal("24"),
            max_range_km=Decimal("650"),
            refrigerated=True,
            helper_policy=HelperPolicy.OPTIONAL,
            fuel_type=FuelType.DIESEL,
            fuel_efficiency_km_per_l=Decimal("6.5"),
            owned_cost=_owned_cost(
                acquisition="360000",
                residual="110000",
                useful_life_km="420000",
                annual_fixed_costs="7200",
                maintenance_cost="3200",
                maintenance_interval_km="15000",
            ),
        ),
        VehicleInput(
            plate="FMD1A06",
            type=VehicleType.MOTO,
            ownership_type=VehicleOwnershipType.OWNED,
            max_payload_kg=Decimal("40"),
            max_volume_m3=Decimal("0.15"),
            max_range_km=Decimal("250"),
            refrigerated=False,
            helper_policy=HelperPolicy.FORBIDDEN,
            fuel_type=FuelType.GASOLINE,
            fuel_efficiency_km_per_l=Decimal("32"),
            owned_cost=_owned_cost(
                acquisition="26000",
                residual="7000",
                useful_life_km="120000",
                annual_fixed_costs="1200",
                maintenance_cost="350",
                maintenance_interval_km="5000",
            ),
        ),
        VehicleInput(
            plate="FMD1A07",
            type=VehicleType.CARGO_VAN,
            ownership_type=VehicleOwnershipType.AGGREGATED,
            max_payload_kg=Decimal("2200"),
            max_volume_m3=Decimal("12"),
            max_range_km=Decimal("550"),
            refrigerated=True,
            helper_policy=HelperPolicy.OPTIONAL,
            fuel_type=FuelType.DIESEL,
            fuel_efficiency_km_per_l=Decimal("9"),
            aggregated_contract=AggregatedContractInput(
                price_brl=Decimal("420"),
                fuel_included=True,
                driver_included=True,
                helper_included=True,
            ),
        ),
    )


def _demo_worker_inputs() -> tuple[WorkerInput, ...]:
    workers: list[WorkerInput] = []
    for index, hourly_rate in enumerate(("28.50", "29.50", "30.00", "31.00", "33.00"), 1):
        workers.append(
            WorkerInput(
                name=f"Motorista Demo {index}",
                role=WorkerRole.DRIVER,
                engagement_type=WorkerEngagementType.EMPLOYEE,
                compensation_model=CompensationModel.HOURLY,
                compensation_value_brl=Decimal(hourly_rate),
            )
        )
    for index, hourly_rate in enumerate(("19.00", "19.50", "20.00", "21.00", "22.00"), 1):
        workers.append(
            WorkerInput(
                name=f"Ajudante Demo {index}",
                role=WorkerRole.HELPER,
                engagement_type=WorkerEngagementType.EMPLOYEE,
                compensation_model=CompensationModel.HOURLY,
                compensation_value_brl=Decimal(hourly_rate),
            )
        )
    for index, hourly_rate in enumerate(("26.00", "27.00"), 1):
        workers.append(
            WorkerInput(
                name=f"Motociclista Demo {index}",
                role=WorkerRole.MOTORCYCLE_COURIER,
                engagement_type=WorkerEngagementType.EMPLOYEE,
                compensation_model=CompensationModel.HOURLY,
                compensation_value_brl=Decimal(hourly_rate),
            )
        )
    return tuple(workers)


def ensure_demo_operation_resources(
    session: Session,
    operation_id: uuid.UUID,
) -> OperationResourcesView:
    service = ResourceService(session)

    existing_vehicles = {item.plate: item for item in service.list_vehicles(active=None)}
    selected_vehicle_ids: list[uuid.UUID] = []
    for vehicle_payload in _demo_vehicle_inputs():
        vehicle = existing_vehicles.get(vehicle_payload.plate)
        if vehicle is None:
            vehicle = service.create_vehicle(vehicle_payload)
        if vehicle.active and vehicle.status is VehicleStatus.AVAILABLE:
            selected_vehicle_ids.append(vehicle.id)

    existing_workers = {item.name: item for item in service.list_workers(active=None)}
    selected_worker_ids: list[uuid.UUID] = []
    for worker_payload in _demo_worker_inputs():
        worker = existing_workers.get(worker_payload.name)
        if worker is None:
            worker = service.create_worker(worker_payload)
        if worker.active:
            selected_worker_ids.append(worker.id)

    return service.update_operation_resources(
        operation_id,
        vehicle_ids=selected_vehicle_ids,
        worker_ids=selected_worker_ids,
    )
