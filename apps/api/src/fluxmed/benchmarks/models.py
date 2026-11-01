from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from fluxmed.optimization.fitness import FitnessEvaluator
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
    fitness_evaluator_factory: Callable[[], FitnessEvaluator] | None = None

    @property
    def delivery_count(self) -> int:
        return len(self.deliveries)


@dataclass(frozen=True, slots=True)
class BenchmarkConvergencePoint:
    scenario_name: str
    delivery_count: int
    method: BenchmarkMethod
    seed: int
    generation: int
    elapsed_seconds: float
    improved: bool
    feasible: bool
    hard_violations: int
    service_penalty: float
    cost_brl: float
    makespan_minutes: float
    distance_km: float
    vehicles_used: int
    diversity_ratio: float
    effective_mutation_rate: float
    immigrants_added: int
    pruning_counts: dict[str, int]
    priority_inversion_minutes: float | None = None
    team_feasible: bool | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    scenario_name: str
    delivery_count: int
    method: BenchmarkMethod
    seed: int | None
    runtime_seconds: float
    feasible: bool
    hard_violations: int
    unassigned_delivery_count: int
    route_hard_violation_counts: dict[str, int]
    candidate_evaluations: int | None
    best_generation: int | None
    time_to_best_seconds: float | None
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
    priority_inversion_minutes: float | None = None
    team_feasible: bool | None = None
    solution_evidence: dict[str, object] | None = None


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
    mean_candidate_evaluations: float | None
    mean_time_to_best_seconds: float | None
    best_makespan_minutes: float | None
    mean_makespan_minutes: float | None


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    runs: tuple[BenchmarkRun, ...]
    summaries: tuple[BenchmarkSummary, ...]
    convergence: tuple[BenchmarkConvergencePoint, ...]
