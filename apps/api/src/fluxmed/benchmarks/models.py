from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from fluxmed.optimization.models import (
    OptimizationDelivery,
    OptimizationVehicle,
    TravelMatrix,
)


class BenchmarkMethod(StrEnum):
    NEAREST_NEIGHBOR = "NEAREST_NEIGHBOR"
    BEST_INSERTION = "BEST_INSERTION"
    GA_BASIC = "GA_BASIC"
    GA_PRUNING = "GA_PRUNING"
    GA_PRUNING_REPAIR = "GA_PRUNING_REPAIR"


@dataclass(frozen=True, slots=True)
class BenchmarkProblem:
    scenario_name: str
    deliveries: list[OptimizationDelivery]
    vehicles: list[OptimizationVehicle]
    travel_matrix: TravelMatrix
    operation_start_at: datetime | None = None
    operation_end_at: datetime | None = None

    @property
    def delivery_count(self) -> int:
        return len(self.deliveries)


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    scenario_name: str
    delivery_count: int
    method: BenchmarkMethod
    seed: int | None
    runtime_seconds: float
    feasible: bool
    hard_violations: int
    service_penalty: float
    critical_risk: float
    cost_brl: float
    makespan_minutes: float
    travel_minutes: float
    distance_km: float
    vehicles_used: int
    pruning_counts: dict[str, int]
    generations_completed: int | None = None
    stop_reason: str | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkSummary:
    scenario_name: str
    delivery_count: int
    method: BenchmarkMethod
    runs: int
    feasible_runs: int
    feasible_rate: float
    best_cost_brl: float | None
    mean_cost_brl: float | None
    std_cost_brl: float | None
    worst_cost_brl: float | None
    mean_runtime_seconds: float
    best_makespan_minutes: float | None
    mean_makespan_minutes: float | None


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    runs: tuple[BenchmarkRun, ...]
    summaries: tuple[BenchmarkSummary, ...]
