import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    HelperPolicy,
    TemperatureClass,
    TimeWindowPolicy,
)

LocationKey = uuid.UUID | None
ZERO = Decimal("0")
# Ordinal service weights: every higher priority has one additional unit of urgency.
PRIORITY_WEIGHTS = {
    DeliveryPriority.LOW: 1,
    DeliveryPriority.NORMAL: 2,
    DeliveryPriority.HIGH: 3,
    DeliveryPriority.CRITICAL: 4,
}


@dataclass(frozen=True, slots=True)
class OptimizationDelivery:
    id: uuid.UUID
    weight_kg: Decimal
    volume_m3: Decimal
    service_minutes: int
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    temperature_class: TemperatureClass = TemperatureClass.AMBIENT
    handling_requirement: HandlingRequirement = HandlingRequirement.STANDARD
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    time_window_policy: TimeWindowPolicy = TimeWindowPolicy.SOFT


@dataclass(frozen=True, slots=True)
class OptimizationVehicle:
    id: uuid.UUID
    max_payload_kg: Decimal
    max_volume_m3: Decimal
    max_range_km: Decimal = Decimal("999999")
    refrigerated: bool = False
    helper_policy: HelperPolicy = HelperPolicy.OPTIONAL
    helper_available: bool = True
    fixed_route_cost_brl: Decimal = ZERO
    cost_per_km_brl: Decimal = ZERO
    cost_per_hour_brl: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class TravelMetric:
    distance_km: Decimal
    travel_minutes: Decimal


class TravelMatrix:
    def __init__(self, metrics: dict[tuple[LocationKey, LocationKey], TravelMetric]) -> None:
        self._metrics = dict(metrics)

    def metric(self, origin: LocationKey, destination: LocationKey) -> TravelMetric:
        if origin == destination:
            return TravelMetric(distance_km=ZERO, travel_minutes=ZERO)
        try:
            return self._metrics[(origin, destination)]
        except KeyError as exc:
            raise KeyError(f"Missing travel metric for {origin!s} -> {destination!s}.") from exc


@dataclass(frozen=True, slots=True)
class DecodedStop:
    delivery_id: uuid.UUID
    arrival_at: datetime
    service_start_at: datetime
    departure_at: datetime
    lateness_minutes: Decimal = ZERO
    priority: DeliveryPriority = DeliveryPriority.NORMAL


@dataclass(frozen=True, slots=True)
class DecodedRoute:
    vehicle_id: uuid.UUID
    delivery_ids: tuple[uuid.UUID, ...]
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    distance_km: Decimal
    travel_minutes: Decimal
    service_minutes: int
    total_duration_minutes: Decimal
    total_cost_brl: Decimal
    stops: tuple[DecodedStop, ...] = ()
    hard_violations: tuple[str, ...] = ()
    soft_lateness_minutes: Decimal = ZERO
    critical_risk: Decimal = ZERO
    starts_at_depot: bool = True
    returns_to_depot: bool = True
    waiting_minutes: Decimal = ZERO
    weighted_lateness_minutes: Decimal | None = None


@dataclass(frozen=True, slots=True)
class DecodedSolution:
    routes: tuple[DecodedRoute, ...]
    unassigned_delivery_ids: tuple[uuid.UUID, ...] = ()
    pruning_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FitnessVector:
    feasible: bool
    hard_violations: int
    service_penalty: Decimal
    critical_risk: Decimal
    total_cost_brl: Decimal
    makespan_minutes: Decimal
    travel_minutes: Decimal
    distance_km: Decimal
    vehicles_used: int
    priority_inversion_minutes: Decimal = ZERO
    team_feasible: bool = True

    def sort_key(self) -> tuple[object, ...]:
        return (
            0 if self.feasible else 1,
            self.hard_violations,
            self.service_penalty,
            self.critical_risk,
            self.priority_inversion_minutes,
            self.total_cost_brl,
            self.makespan_minutes,
            self.travel_minutes,
            self.distance_km,
            self.vehicles_used,
        )


@dataclass(frozen=True, slots=True)
class EvaluatedIndividual:
    chromosome: tuple[uuid.UUID, ...]
    solution: DecodedSolution
    fitness: FitnessVector


@dataclass(frozen=True, slots=True)
class OptimizationProgress:
    generation: int
    best: EvaluatedIndividual
    improved: bool
    diversity_ratio: float
    effective_mutation_rate: float
    immigrants_added: int
    pruning_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class BaselineResult:
    name: str
    chromosome: tuple[uuid.UUID, ...]
    solution: DecodedSolution
    fitness: FitnessVector


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    random_seed: int
    generations_completed: int
    stop_reason: str
    best: EvaluatedIndividual
    baselines: tuple[BaselineResult, ...]
    diversity_ratio: float = 1.0
    effective_mutation_rate: float = 0.0
    immigrants_added: int = 0
    pruning_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    delivery_id: uuid.UUID | None = None
    vehicle_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...]
