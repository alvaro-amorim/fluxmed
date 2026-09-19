from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.application.resources import VehicleView
from fluxmed.domain.enums import VehicleOwnershipType
from fluxmed.infrastructure.models.city import AddressModel, CityModel
from fluxmed.infrastructure.models.delivery import DeliveryModel
from fluxmed.optimization import OptimizationDelivery, OptimizationVehicle

ZERO = Decimal("0")


def build_delivery_inputs(delivery_models: list[DeliveryModel]) -> list[OptimizationDelivery]:
    return [
        OptimizationDelivery(
            id=delivery.id,
            weight_kg=delivery.total_weight_kg,
            volume_m3=delivery.total_volume_m3,
            service_minutes=delivery.service_time_minutes,
            priority=delivery.priority,
            temperature_class=delivery.temperature_class,
            handling_requirement=delivery.handling_requirement,
            time_window_start=delivery.time_window_start,
            time_window_end=delivery.time_window_end,
            time_window_policy=delivery.time_window_policy,
        )
        for delivery in delivery_models
    ]


def build_vehicle_input(
    vehicle: VehicleView,
    *,
    helper_available: bool,
) -> OptimizationVehicle:
    if vehicle.ownership_type is VehicleOwnershipType.OWNED:
        cost_per_km = (vehicle.cost.depreciation_per_km or ZERO) + (
            vehicle.cost.maintenance_per_km or ZERO
        )
        cost_per_hour = vehicle.cost.fixed_cost_per_hour or ZERO
        fixed_route_cost = ZERO
    else:
        cost_per_km = ZERO
        cost_per_hour = ZERO
        fixed_route_cost = vehicle.cost.contract_price_brl or ZERO
    return OptimizationVehicle(
        id=vehicle.id,
        max_payload_kg=vehicle.max_payload_kg,
        max_volume_m3=vehicle.max_volume_m3,
        max_range_km=vehicle.max_range_km,
        refrigerated=vehicle.refrigerated,
        helper_policy=vehicle.helper_policy,
        helper_available=vehicle.cost.helper_included or helper_available,
        fixed_route_cost_brl=fixed_route_cost,
        cost_per_km_brl=cost_per_km,
        cost_per_hour_brl=cost_per_hour,
    )


def resolve_operation_timezone(
    session: Session,
    delivery_models: list[DeliveryModel],
) -> ZoneInfo:
    address_ids = {delivery.destination_address_id for delivery in delivery_models}
    timezone_names = set(
        session.scalars(
            select(CityModel.timezone)
            .join(AddressModel, AddressModel.city_id == CityModel.id)
            .where(AddressModel.id.in_(address_ids))
        )
    )
    if not timezone_names:
        raise ValueError("Não foi possível determinar o fuso horário da operação.")
    if len(timezone_names) != 1:
        raise ValueError(
            "Uma operação não pode combinar entregas de cidades com fusos horários diferentes."
        )
    timezone_name = next(iter(timezone_names))
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Fuso horário da cidade não reconhecido: {timezone_name}.") from exc


def operation_window(
    *,
    operation_date: datetime.date,
    operation_start_time: datetime.time,
    operation_end_time: datetime.time,
    timezone: ZoneInfo,
) -> tuple[datetime, datetime]:
    return (
        datetime.combine(operation_date, operation_start_time, tzinfo=timezone),
        datetime.combine(operation_date, operation_end_time, tzinfo=timezone),
    )
