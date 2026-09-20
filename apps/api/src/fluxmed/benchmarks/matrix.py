import json
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.application.deliveries.scenario import ScenarioProfile, generate_scenario
from fluxmed.application.optimization.problem_inputs import (
    build_vehicle_input,
    operation_window,
)
from fluxmed.application.optimization.routing_matrix import RoutingMatrixBuilder
from fluxmed.application.resources import ResourceService
from fluxmed.benchmarks.models import (
    BenchmarkConvergencePoint,
    BenchmarkMethod,
    BenchmarkProblem,
    BenchmarkReport,
    BenchmarkRun,
    BenchmarkSummary,
)
from fluxmed.benchmarks.runner import OptimizerBenchmarkRunner
from fluxmed.domain.deliveries import ServiceTimeEstimator
from fluxmed.domain.enums import WorkerRole
from fluxmed.infrastructure.models.city import CityModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.repositories.delivery_repository import DeliveryRepository
from fluxmed.optimization import GeneticOptimizerConfig, OptimizationDelivery


@dataclass(frozen=True, slots=True)
class ScenarioMatrixCell:
    profile: ScenarioProfile
    delivery_count: int
    scenario_seed: int
    scenario_name: str


@dataclass(frozen=True, slots=True)
class ScenarioMatrixResult:
    template_operation_code: str
    cells: tuple[ScenarioMatrixCell, ...]
    report: BenchmarkReport


class SantaAuroraScenarioProblemFactory:
    def __init__(self, session: Session, *, template_operation_code: str) -> None:
        self._session = session
        operation = session.scalar(
            select(OperationModel).where(
                OperationModel.operation_code == template_operation_code.strip()
            )
        )
        if operation is None:
            raise LookupError(template_operation_code)
        self._operation: OperationModel = operation

        city = session.scalar(select(CityModel).where(CityModel.name == "Santa Aurora"))
        if city is None:
            raise ValueError("Santa Aurora ainda não foi gerada.")
        self._timezone = ZoneInfo(city.timezone)

        resources = ResourceService(session).get_operation_resources(self._operation.id)
        selected_vehicle_ids = set(resources.selected_vehicle_ids)
        selected_worker_ids = set(resources.selected_worker_ids)
        selected_workers = [
            worker for worker in resources.workers if worker.id in selected_worker_ids
        ]
        helper_available = any(worker.role is WorkerRole.HELPER for worker in selected_workers)
        selected_vehicles = [
            vehicle for vehicle in resources.vehicles if vehicle.id in selected_vehicle_ids
        ]
        self._vehicles = [
            build_vehicle_input(vehicle, helper_available=helper_available)
            for vehicle in selected_vehicles
        ]
        if not self._vehicles:
            raise ValueError("A operação-base não possui veículos selecionados.")

        self._address_pool = DeliveryRepository(session).scenario_address_pool(city_id=city.id)
        self._address_by_id = {context.address.id: context for context in self._address_pool}
        self._estimator = ServiceTimeEstimator()
        self._matrix_builder = RoutingMatrixBuilder(session)
        self._operation_start_at, self._operation_end_at = operation_window(
            operation_date=self._operation.operation_date,
            operation_start_time=self._operation.operation_start_time,
            operation_end_time=self._operation.operation_end_time,
            timezone=self._timezone,
        )

    @property
    def template_operation_code(self) -> str:
        return self._operation.operation_code

    def build(
        self,
        *,
        profile: ScenarioProfile,
        delivery_count: int,
        scenario_seed: int,
    ) -> BenchmarkProblem:
        batch = generate_scenario(
            address_pool=self._address_pool,
            operation_date=self._operation.operation_date,
            operation_start_time=self._operation.operation_start_time,
            operation_end_time=self._operation.operation_end_time,
            profile=profile,
            delivery_count=delivery_count,
            seed=scenario_seed,
        )
        namespace_label = (
            f"fluxmed-benchmark:{self._operation.id}:{profile.value}:"
            f"{delivery_count}:{scenario_seed}"
        )
        namespace = uuid.uuid5(uuid.NAMESPACE_URL, namespace_label)
        deliveries: list[OptimizationDelivery] = []
        delivery_addresses: dict[uuid.UUID, uuid.UUID] = {}
        for index, spec in enumerate(batch.deliveries, start=1):
            delivery_id = uuid.uuid5(namespace, str(index))
            context = self._address_by_id[spec.destination_address_id]
            estimate = self._estimator.estimate(
                building_type=context.building.building_type,
                package_count=spec.package_count,
                total_weight_kg=spec.total_weight_kg,
                total_volume_m3=spec.total_volume_m3,
                handling_requirement=spec.handling_requirement,
            )
            deliveries.append(
                OptimizationDelivery(
                    id=delivery_id,
                    weight_kg=spec.total_weight_kg,
                    volume_m3=spec.total_volume_m3,
                    service_minutes=estimate.selected_minutes,
                    priority=spec.priority,
                    temperature_class=spec.temperature_class,
                    handling_requirement=spec.handling_requirement,
                    time_window_start=spec.time_window_start,
                    time_window_end=spec.time_window_end,
                    time_window_policy=spec.time_window_policy,
                )
            )
            delivery_addresses[delivery_id] = spec.destination_address_id

        travel_matrix = self._matrix_builder.build(
            operation=self._operation,
            delivery_addresses=delivery_addresses,
        )
        scenario_name = f"{profile.value}-{delivery_count}-S{scenario_seed}"
        return BenchmarkProblem(
            scenario_name=scenario_name,
            deliveries=deliveries,
            vehicles=list(self._vehicles),
            travel_matrix=travel_matrix,
            operation_start_at=self._operation_start_at,
            operation_end_at=self._operation_end_at,
        )


class ScenarioMatrixBenchmarkRunner:
    def __init__(
        self,
        *,
        problem_factory: Callable[..., BenchmarkProblem],
        benchmark_runner: OptimizerBenchmarkRunner,
    ) -> None:
        self._problem_factory = problem_factory
        self._benchmark_runner = benchmark_runner

    def run(
        self,
        *,
        template_operation_code: str,
        profiles: tuple[ScenarioProfile, ...],
        sizes: tuple[int, ...],
        scenario_seeds: tuple[int, ...],
        ga_seeds: tuple[int, ...],
        on_cell_start: Callable[[ScenarioMatrixCell], None] | None = None,
    ) -> ScenarioMatrixResult:
        if not profiles or not sizes or not scenario_seeds or not ga_seeds:
            raise ValueError("Perfis, tamanhos e seeds do benchmark não podem ficar vazios.")
        invalid_sizes = [size for size in sizes if size <= 0 or size > 100]
        if invalid_sizes:
            raise ValueError("Os tamanhos do benchmark devem ficar entre 1 e 100 entregas.")

        all_runs: list[BenchmarkRun] = []
        all_summaries: list[BenchmarkSummary] = []
        all_convergence: list[BenchmarkConvergencePoint] = []
        cells: list[ScenarioMatrixCell] = []
        for profile in profiles:
            for size in sizes:
                for scenario_seed in scenario_seeds:
                    cell = ScenarioMatrixCell(
                        profile=profile,
                        delivery_count=size,
                        scenario_seed=scenario_seed,
                        scenario_name=f"{profile.value}-{size}-S{scenario_seed}",
                    )
                    if on_cell_start is not None:
                        on_cell_start(cell)
                    problem = self._problem_factory(
                        profile=profile,
                        delivery_count=size,
                        scenario_seed=scenario_seed,
                    )
                    report = self._benchmark_runner.run(problem, seeds=ga_seeds)
                    cells.append(cell)
                    all_runs.extend(report.runs)
                    all_summaries.extend(report.summaries)
                    all_convergence.extend(report.convergence)

        return ScenarioMatrixResult(
            template_operation_code=template_operation_code,
            cells=tuple(cells),
            report=BenchmarkReport(
                runs=tuple(all_runs),
                summaries=tuple(all_summaries),
                convergence=tuple(all_convergence),
            ),
        )


def write_matrix_manifest(
    result: ScenarioMatrixResult,
    output_dir: Path,
    *,
    ga_seeds: tuple[int, ...],
    quick: bool,
    ga_config: GeneticOptimizerConfig,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "matrix-manifest.json"
    payload = {
        "template_operation_code": result.template_operation_code,
        "quick": quick,
        "ga_seeds": list(ga_seeds),
        "ga_config": asdict(ga_config),
        "method_configurations": _method_configurations(ga_config),
        "cells": [
            {
                **asdict(cell),
                "profile": cell.profile.value,
            }
            for cell in result.cells
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def enrich_matrix_manifest(path: Path) -> Path:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ga_config = GeneticOptimizerConfig(**payload["ga_config"])
    payload["method_configurations"] = _method_configurations(ga_config)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _method_configurations(
    ga_config: GeneticOptimizerConfig,
) -> dict[str, object]:
    return {
        BenchmarkMethod.NEAREST_NEIGHBOR.value: {
            "kind": "deterministic_baseline",
            "runs_per_scenario": 1,
        },
        BenchmarkMethod.BEST_INSERTION.value: {
            "kind": "deterministic_baseline",
            "runs_per_scenario": 1,
        },
        BenchmarkMethod.GA_BASIC.value: asdict(
            replace(
                ga_config,
                advanced_pruning_enabled=False,
                repair_enabled=False,
            )
        ),
        BenchmarkMethod.GA_PRUNING.value: asdict(
            replace(
                ga_config,
                advanced_pruning_enabled=True,
                repair_enabled=False,
            )
        ),
        BenchmarkMethod.GA_PRUNING_REPAIR.value: asdict(
            replace(
                ga_config,
                advanced_pruning_enabled=True,
                repair_enabled=True,
            )
        ),
    }
