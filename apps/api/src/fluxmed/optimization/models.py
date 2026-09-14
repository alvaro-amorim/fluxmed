import uuid
from dataclasses import dataclass
from decimal import Decimal

LocationKey = uuid.UUID | None
FitnessKey = tuple[int, int, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, int]
ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class OptimizationDelivery:
    id: uuid.UUID
    weight_kg: Decimal
    volume_m3: Decimal
    service_minutes: int


@dataclass(frozen=True, slots=True)
class OptimizationVehicle:
    id: uuid.UUID
    max_payload_kg: Decimal
    max_volume_m3: Decimal
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


@dataclass(frozen=True, slots=True)
class DecodedSolution:
    routes: tuple[DecodedRoute, ...]
    unassigned_delivery_ids: tuple[uuid.UUID, ...] = ()


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
