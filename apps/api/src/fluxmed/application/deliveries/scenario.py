import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from fluxmed.domain.enums import (
    CargoProfile,
    DeliveryPriority,
    FacilityType,
    HandlingRequirement,
    TemperatureClass,
    TimeWindowPolicy,
)
from fluxmed.infrastructure.repositories.delivery_repository import AddressContext


class ScenarioProfile(StrEnum):
    NORMAL = "NORMAL"
    BUSY = "BUSY"
    HIGH_PRESSURE = "HIGH_PRESSURE"
    EMERGENCY = "EMERGENCY"


@dataclass(frozen=True, slots=True)
class GeneratedDeliverySpec:
    invoice_number: str
    invoice_series: str
    issuer_document: str
    issuer_name: str
    destination_address_id: uuid.UUID
    recipient_name: str
    package_count: int
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    priority: DeliveryPriority
    time_window_start: datetime | None
    time_window_end: datetime | None
    time_window_policy: TimeWindowPolicy
    temperature_class: TemperatureClass
    handling_requirement: HandlingRequirement
    cargo_profile: CargoProfile
    notes: str


@dataclass(frozen=True, slots=True)
class ScenarioBatch:
    seed: int
    deliveries: list[GeneratedDeliverySpec]


@dataclass(frozen=True, slots=True)
class _ProfileConfig:
    critical_rate: float
    high_rate: float
    refrigerated_rate: float
    hard_window_rate: float
    no_window_rate: float
    min_window_minutes: int
    max_window_minutes: int
    heavy_cargo_rate: float


_CONFIG = {
    ScenarioProfile.NORMAL: _ProfileConfig(0.05, 0.18, 0.14, 0.22, 0.20, 120, 240, 0.10),
    ScenarioProfile.BUSY: _ProfileConfig(0.08, 0.25, 0.18, 0.34, 0.12, 90, 180, 0.16),
    ScenarioProfile.HIGH_PRESSURE: _ProfileConfig(0.13, 0.32, 0.24, 0.48, 0.06, 60, 150, 0.22),
    ScenarioProfile.EMERGENCY: _ProfileConfig(0.24, 0.34, 0.30, 0.62, 0.03, 45, 120, 0.18),
}


def _weighted_address_choice(
    rng: random.Random, available: list[AddressContext]
) -> AddressContext:
    weights: list[int] = []
    for context in available:
        if context.facility is None:
            weight = 2
        else:
            weight = {
                FacilityType.HOSPITAL: 8,
                FacilityType.CLINIC: 6,
                FacilityType.LABORATORY: 5,
                FacilityType.PHARMACY: 4,
                FacilityType.PUBLIC_FACILITY: 3,
                FacilityType.WAREHOUSE: 2,
                FacilityType.DEPOT: 0,
            }[context.facility.facility_type]
        weights.append(weight)
    if not any(weights):
        raise ValueError("Nenhum endereço elegível para cenário.")
    return rng.choices(available, weights=weights, k=1)[0]


def _priority(rng: random.Random, config: _ProfileConfig) -> DeliveryPriority:
    roll = rng.random()
    if roll < config.critical_rate:
        return DeliveryPriority.CRITICAL
    if roll < config.critical_rate + config.high_rate:
        return DeliveryPriority.HIGH
    if roll < 0.92:
        return DeliveryPriority.NORMAL
    return DeliveryPriority.LOW


def _cargo_profile(
    rng: random.Random,
    context: AddressContext,
    config: _ProfileConfig,
) -> CargoProfile:
    if context.facility is not None and context.facility.facility_type is FacilityType.LABORATORY:
        return CargoProfile.LAB_MATERIAL
    if rng.random() < config.refrigerated_rate:
        return CargoProfile.REFRIGERATED_MEDICATION
    if rng.random() < config.heavy_cargo_rate:
        return rng.choice([CargoProfile.BULK_CONSUMABLES, CargoProfile.MEDICAL_EQUIPMENT])
    if context.facility is not None and context.facility.facility_type is FacilityType.HOSPITAL:
        return rng.choice([CargoProfile.HOSPITAL_SUPPLIES, CargoProfile.MEDICATION_SMALL])
    return CargoProfile.MEDICATION_SMALL


def _cargo_values(
    rng: random.Random, profile: CargoProfile
) -> tuple[int, Decimal, Decimal, HandlingRequirement]:
    ranges = {
        CargoProfile.MEDICATION_SMALL: (1, 8, 2.0, 10.0, 0.015, 0.055),
        CargoProfile.REFRIGERATED_MEDICATION: (1, 10, 3.0, 12.0, 0.020, 0.060),
        CargoProfile.LAB_MATERIAL: (1, 7, 2.5, 9.0, 0.015, 0.045),
        CargoProfile.HOSPITAL_SUPPLIES: (4, 18, 6.0, 18.0, 0.045, 0.110),
        CargoProfile.BULK_CONSUMABLES: (8, 28, 8.0, 24.0, 0.080, 0.170),
        CargoProfile.MEDICAL_EQUIPMENT: (1, 6, 18.0, 55.0, 0.100, 0.350),
    }
    min_packages, max_packages, min_kg, max_kg, min_m3, max_m3 = ranges[profile]
    package_count = rng.randint(min_packages, max_packages)
    weight = Decimal(str(round(package_count * rng.uniform(min_kg, max_kg), 3)))
    volume = Decimal(str(round(package_count * rng.uniform(min_m3, max_m3), 4)))
    handling = (
        HandlingRequirement.TWO_PERSON
        if profile in {CargoProfile.BULK_CONSUMABLES, CargoProfile.MEDICAL_EQUIPMENT}
        and (weight >= Decimal("180") or volume >= Decimal("1.2"))
        else HandlingRequirement.STANDARD
    )
    return package_count, weight, volume, handling


def _window(
    rng: random.Random,
    *,
    operation_date: date,
    start_time: time,
    end_time: time,
    config: _ProfileConfig,
) -> tuple[datetime | None, datetime | None, TimeWindowPolicy]:
    if rng.random() < config.no_window_rate:
        return None, None, TimeWindowPolicy.SOFT

    timezone = ZoneInfo("America/Sao_Paulo")
    operation_start = datetime.combine(operation_date, start_time, timezone)
    operation_end = datetime.combine(operation_date, end_time, timezone)
    total_minutes = max(1, int((operation_end - operation_start).total_seconds() // 60))
    width = min(rng.randint(config.min_window_minutes, config.max_window_minutes), total_minutes)
    latest_offset = max(0, total_minutes - width)
    start_offset = rng.randint(0, latest_offset) if latest_offset else 0
    window_start = operation_start + timedelta(minutes=start_offset)
    window_end = min(window_start + timedelta(minutes=width), operation_end)
    policy = (
        TimeWindowPolicy.HARD if rng.random() < config.hard_window_rate else TimeWindowPolicy.SOFT
    )
    return window_start, window_end, policy


def generate_scenario(
    *,
    address_pool: list[AddressContext],
    operation_date: date,
    operation_start_time: time,
    operation_end_time: time,
    profile: ScenarioProfile,
    delivery_count: int,
    seed: int,
) -> ScenarioBatch:
    if delivery_count <= 0 or delivery_count > 100:
        raise ValueError("O cenário deve conter entre 1 e 100 entregas.")
    eligible = [
        context
        for context in address_pool
        if context.facility is None or context.facility.facility_type is not FacilityType.DEPOT
    ]
    if len(eligible) < delivery_count:
        raise ValueError("A cidade não possui endereços elegíveis suficientes.")

    rng = random.Random(seed)
    config = _CONFIG[profile]
    available = list(eligible)
    generated: list[GeneratedDeliverySpec] = []
    for index in range(delivery_count):
        context = _weighted_address_choice(rng, available)
        available.remove(context)
        cargo_profile = _cargo_profile(rng, context, config)
        package_count, weight, volume, handling = _cargo_values(rng, cargo_profile)
        priority = _priority(rng, config)
        window_start, window_end, window_policy = _window(
            rng,
            operation_date=operation_date,
            start_time=operation_start_time,
            end_time=operation_end_time,
            config=config,
        )
        facility_name = context.facility.name if context.facility is not None else None
        recipient = facility_name or f"Atendimento domiciliar {index + 1:02d}"
        temperature = (
            TemperatureClass.REFRIGERATED
            if cargo_profile is CargoProfile.REFRIGERATED_MEDICATION
            else TemperatureClass.AMBIENT
        )
        invoice_number = f"{seed % 100000:05d}{index + 1:03d}"
        generated.append(
            GeneratedDeliverySpec(
                invoice_number=invoice_number,
                invoice_series="1",
                issuer_document="12.345.678/0001-90",
                issuer_name="Distribuidora Médica Santa Aurora",
                destination_address_id=context.address.id,
                recipient_name=recipient,
                package_count=package_count,
                total_weight_kg=weight,
                total_volume_m3=volume,
                priority=priority,
                time_window_start=window_start,
                time_window_end=window_end,
                time_window_policy=window_policy,
                temperature_class=temperature,
                handling_requirement=handling,
                cargo_profile=cargo_profile,
                notes=f"Cenário sintético {profile.value} · seed {seed}",
            )
        )
    return ScenarioBatch(seed=seed, deliveries=generated)
