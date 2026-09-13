import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from fluxmed.domain.enums import (
    BuildingType,
    CargoProfile,
    DeliveryPriority,
    DeliveryStatus,
    HandlingRequirement,
    ServiceTimeSource,
    TemperatureClass,
    TimeWindowPolicy,
)


class DeliveryValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Delivery:
    id: uuid.UUID
    delivery_code: str
    operation_id: uuid.UUID
    invoice_number: str
    invoice_series: str
    issuer_document: str
    issuer_name: str | None
    external_reference: str | None
    destination_address_id: uuid.UUID
    recipient_name: str
    package_count: int
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    priority: DeliveryPriority
    time_window_start: datetime | None
    time_window_end: datetime | None
    time_window_policy: TimeWindowPolicy
    service_time_minutes: int
    service_time_source: ServiceTimeSource
    temperature_class: TemperatureClass
    handling_requirement: HandlingRequirement
    status: DeliveryStatus
    cargo_profile: CargoProfile | None
    notes: str | None

    def validate(self) -> None:
        validate_delivery_values(
            package_count=self.package_count,
            total_weight_kg=self.total_weight_kg,
            total_volume_m3=self.total_volume_m3,
            time_window_start=self.time_window_start,
            time_window_end=self.time_window_end,
            service_time_minutes=self.service_time_minutes,
        )


@dataclass(frozen=True, slots=True)
class ServiceTimeEstimate:
    solo_minutes: int
    with_helper_minutes: int
    selected_minutes: int


class ServiceTimeEstimator:
    """Deterministic stop-time estimator used when no explicit service time is supplied."""

    _BASE_MINUTES = {
        BuildingType.HOSPITAL: 14,
        BuildingType.CLINIC: 10,
        BuildingType.LABORATORY: 9,
        BuildingType.PHARMACY: 7,
        BuildingType.WAREHOUSE: 18,
        BuildingType.PUBLIC_BUILDING: 11,
        BuildingType.COMMERCIAL: 9,
        BuildingType.APARTMENT_BUILDING: 8,
        BuildingType.HOUSE: 6,
        BuildingType.SCHOOL: 9,
        BuildingType.OTHER: 8,
    }

    def estimate(
        self,
        *,
        building_type: BuildingType,
        package_count: int,
        total_weight_kg: Decimal,
        total_volume_m3: Decimal,
        handling_requirement: HandlingRequirement,
    ) -> ServiceTimeEstimate:
        if package_count <= 0 or total_weight_kg <= 0 or total_volume_m3 <= 0:
            raise DeliveryValidationError(
                "Carga deve possuir volumes, peso e volume cúbico positivos."
            )

        base = self._BASE_MINUTES[building_type]
        package_minutes = min(12, math.ceil(package_count / 5) * 2)
        weight_minutes = min(8, math.ceil(float(total_weight_kg) / 120) * 2)
        volume_minutes = min(8, math.ceil(float(total_volume_m3) / 1.5) * 2)
        solo = max(5, base + package_minutes + weight_minutes + volume_minutes)
        with_helper = max(5, math.ceil(solo * 0.72))
        selected = (
            with_helper
            if handling_requirement is HandlingRequirement.TWO_PERSON
            else solo
        )
        return ServiceTimeEstimate(
            solo_minutes=solo,
            with_helper_minutes=with_helper,
            selected_minutes=selected,
        )


def validate_delivery_values(
    *,
    package_count: int,
    total_weight_kg: Decimal,
    total_volume_m3: Decimal,
    time_window_start: datetime | None,
    time_window_end: datetime | None,
    service_time_minutes: int,
) -> None:
    if package_count <= 0:
        raise DeliveryValidationError("A quantidade de volumes deve ser maior que zero.")
    if total_weight_kg <= 0:
        raise DeliveryValidationError("O peso total deve ser maior que zero.")
    if total_volume_m3 <= 0:
        raise DeliveryValidationError("O volume total deve ser maior que zero.")
    if service_time_minutes <= 0:
        raise DeliveryValidationError("O tempo de atendimento deve ser maior que zero.")
    if (time_window_start is None) != (time_window_end is None):
        raise DeliveryValidationError(
            "A janela deve possuir início e fim, ou ambos devem ficar vazios."
        )
    if (
        time_window_start is not None
        and time_window_end is not None
        and time_window_end <= time_window_start
    ):
        raise DeliveryValidationError("O fim da janela deve ocorrer depois do início.")
