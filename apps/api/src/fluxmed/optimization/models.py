import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from fluxmed.domain.enums import DeliveryPriority, TemperatureClass, TimeWindowPolicy

LocationKey = uuid.UUID | None
FitnessKey = tuple[int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, int]
ZERO = Decimal("0")
UNBOUNDED_RANGE_KM = Decimal("999999999")


class PruningReason(StrEnum):
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    VOLUME_EXCEEDED = "VOLUME_EXCEEDED"
    HARD_TIME_WINDOW_IMPOSSIBLE = "HARD_TIME_WINDOW_IMPOSSIBLE"
    RANGE_IMPOSSIBLE = "RANGE_IMPOSSIBLE"
    REFRIGERATION_INCOMPATIBLE = "REFRIGERATION_INCOMPATIBLE"
    TEAM_INFEASIBLE = "TEAM_INFEASIBLE"
    ROAD_ACCESS_IMPOSSIBLE = "ROAD_ACCESS_IMPOSSIBLE"
    END_OF_SHIFT_IMPOSSIBLE = "END_OF_SHIFT_IMPOSSIBLE"
    FUTURE_INFEASIBILITY = "FUTURE_INFEASIBILITY"
    DOMINATED_STATE = "DOMINATED_STATE"
    LOWER_BOUND = "LOWER_BOUND"


@dataclass(frozen=True, slots=True)
class OptimizationContext:
    operation_start_at: datetime
    operation_end_at: datetime
    range_safety_factor: Decimal = Decimal("0.90")

    def validate(self) -> None:
        if self.operation_end_at <= self.operation_start_at:
            raise ValueError("operation_end_at must be after operation_start_at.")
        if not Decimal("0") < self.range_safety_factor <= Decimal("1"):
            raise ValueError("range_safety_factor must be between zero and one.")


@dataclass(frozen=True, slots=True)
class OptimizationDelivery:
    id: uuid.UUID
    weight_kg: Decimal
    volume_m3: Decimal
    service_minutes: int
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    temperature_class: TemperatureClass = TemperatureClass.AMBIENT
    time_window_policy: TimeWindowPolicy = TimeWindowPolicy.SOFT
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None


@dataclass(frozen=True, slots=True)
class OptimizationVehicle:
    id: uuid.UUID
    max_payload_kg: Decimal
    max_volume_m3: Decimal
    max_range_km: Decimal = UNBOUNDED_RANGE_KM
    refrigerated: bool = False
    fixed_route_cost_brl: Decimal = ZERO
    cost_per_km_brl: Decimal = ZERO
    cost_per_hour_brl: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class TravelMetric:
    distance_km: Decimal
    travel_minutes: Decimal


TravelMetricProvider = Callable[[LocationKey, LocationKey, datetime], TravelMetric]


class TravelMatrix:
    def __init__(
        self,
        metrics: dict[tuple[LocationKey, LocationKey], TravelMetric],
        *,
        timed_provider: TravelMetricProvider | None = None,
    ) -> None:
        self._metrics = dict(metrics)
        self._timed_provider = timed_provider

    def metric(
        self,
        origin: LocationKey,
        destination: LocationKey,
        departure_at: datetime | None = None,
    ) -> TravelMetric:
        if origin == destination:
            return TravelMetric(distance_km=ZERO, travel_minutes=ZERO)
        if departure_at is not None and self._timed_provider is not None:
            return self._timed_provider(origin, destination, departure_at)
        try:
            return self._metrics[(origin, destination)]
        except KeyError as exc:
            raise KeyError(f"Missing travel metric for {origin!s} -> {destination!s}.") from exc


@dataclass(frozen=True, slots=True)
class DecodedStop:
    delivery_id: uuid.UUID
    arrival_at: datetime | None = None
    service_start_at: datetime | None = None
    departure_at: datetime | None = None
    lateness_minutes: Decimal = ZERO
    slack_minutes: Decimal | None = None
    service_penalty: Decimal = ZERO
    critical_risk: Decimal = ZERO


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
    starts_at_depot: bool = True
    returns_to_depot: bool = True
    stops: tuple[DecodedStop, ...] = ()
    return_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DecodedSolution:
    routes: tuple[DecodedRoute, ...]
    unassigned_delivery_ids: tuple[uuid.UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class PruningSummary:
    total_pruned: int = 0
    pruned_by_reason: dict[str, int] = field(default_factory=dict)
    avoided_full_evaluations: int = 0

    @property
    def pruning_rate(self) -> Decimal:
        denominator = self.total_pruned + self.avoided_full_evaluations
        if denominator == 0:
            return ZERO
        return Decimal(self.total_pruned) / Decimal(denominator)


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

    def sort_key(self) -> FitnessKey:
        return (
            0 if self.feasible else 1,
            self.hard_violations,
            self.service_penalty,
            self.critical_risk,
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
    pruning: PruningSummary = field(default_factory=PruningSummary)
    repairs_applied: int = 0
    diversity_history: tuple[float, ...] = ()
    mutation_rate_history: tuple[float, ...] = ()
    elapsed_seconds: float = 0.0


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
