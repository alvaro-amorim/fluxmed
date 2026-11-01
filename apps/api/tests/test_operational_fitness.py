from dataclasses import replace
from datetime import timedelta
from functools import partial

import pytest

from fluxmed.application.optimization.cost_engine import FinalCostEngine
from fluxmed.application.optimization.evaluation import OperationalFitnessEvaluator
from fluxmed.application.optimization.problem_inputs import build_vehicle_input
from fluxmed.application.optimization.team_assignment import TeamAssignmentSolver
from fluxmed.benchmarks import BenchmarkProblem, OptimizerBenchmarkRunner
from fluxmed.domain.enums import (
    CompensationModel,
    HandlingRequirement,
    HelperPolicy,
    VehicleOwnershipType,
    VehicleType,
    WorkerRole,
)
from fluxmed.optimization import (
    DecodedSolution,
    GeneticOptimizer,
    GeneticOptimizerConfig,
    OptimizationDelivery,
    RouteDecoder,
    TravelMatrix,
    TravelMetric,
)
from test_optimization_regressions import START, D, problem
from test_team_assignment_results import _id, _route, _vehicle, _worker


@pytest.mark.parametrize("compensation", list(CompensationModel))
def test_fitness_cost_is_the_final_cost_with_fuel_team_and_waiting(compensation):
    deliveries, _, matrix = problem()
    deliveries = [
        replace(
            deliveries[0],
            service_minutes=0,
            time_window_start=START + timedelta(hours=1),
            handling_requirement=HandlingRequirement.TWO_PERSON,
        )
    ]
    vehicle = _vehicle(101)
    workers = [
        replace(_worker(201, WorkerRole.DRIVER, "12"), compensation_model=compensation),
        _worker(202, WorkerRole.HELPER, "6"),
    ]
    solution = RouteDecoder(
        deliveries=deliveries,
        vehicles=[build_vehicle_input(vehicle, helper_available=True)],
        travel_matrix=matrix,
        operation_start_at=START,
    ).decode((deliveries[0].id,))
    evaluator = OperationalFitnessEvaluator(
        deliveries=deliveries, vehicles=[vehicle], workers=workers
    )
    fitness = evaluator.evaluate(solution)
    team = (
        TeamAssignmentSolver()
        .solve(routes=solution.routes, deliveries=deliveries, vehicles=[vehicle], workers=workers)
        .assignments[0]
    )
    expected = FinalCostEngine().calculate(route=solution.routes[0], vehicle=vehicle, team=team)
    assert fitness.feasible
    assert fitness.total_cost_brl == expected.total_brl
    assert expected.fuel_brl > 0
    assert expected.team_brl > 0
    assert fitness.makespan_minutes == D("70")


def test_contract_included_fuel_and_team_are_not_charged_twice():
    deliveries, _, _ = problem()
    vehicle = _vehicle(
        101,
        ownership=VehicleOwnershipType.AGGREGATED,
        driver_included=True,
        helper_included=True,
        helper_policy=HelperPolicy.REQUIRED,
    )
    vehicle = replace(vehicle, cost=replace(vehicle.cost, fuel_included=True))
    solution = DecodedSolution(routes=(_route(vehicle.id, "120", (deliveries[0].id,)),))
    fitness = OperationalFitnessEvaluator(
        deliveries=deliveries, vehicles=[vehicle], workers=[]
    ).evaluate(solution)
    assert fitness.feasible
    assert fitness.total_cost_brl == vehicle.cost.contract_price_brl


@pytest.mark.parametrize("missing", ["driver", "courier", "helper", "inactive"])
def test_global_team_unavailability_makes_candidate_infeasible(missing):
    deliveries, _, _ = problem()
    if missing == "helper":
        deliveries = [
            replace(d, handling_requirement=HandlingRequirement.TWO_PERSON) for d in deliveries
        ]
    kind = VehicleType.MOTO if missing == "courier" else VehicleType.CARGO_VAN
    vehicles = [_vehicle(101, vehicle_type=kind), _vehicle(102, vehicle_type=kind)]
    routes = tuple(_route(v.id, "60", (d.id,)) for v, d in zip(vehicles, deliveries, strict=True))
    workers = [_worker(201, WorkerRole.DRIVER, "10")]
    if missing == "helper":
        workers += [_worker(202, WorkerRole.DRIVER, "20"), _worker(203, WorkerRole.HELPER, "5")]
    if missing == "inactive":
        workers += [replace(_worker(202, WorkerRole.DRIVER, "20"), active=False)]
    fitness = OperationalFitnessEvaluator(
        deliveries=deliveries, vehicles=vehicles, workers=workers
    ).evaluate(DecodedSolution(routes=routes))
    assert not fitness.feasible
    assert not fitness.team_feasible
    assert fitness.hard_violations > 0


def _fuel_problem():
    deliveries = [OptimizationDelivery(_id(i), D("10"), D("0.1"), 0) for i in (1, 2)]
    vehicles = [_vehicle(101), _vehicle(102)]
    vehicles = [
        replace(
            v,
            max_payload_kg=D("10"),
            fuel_efficiency_km_per_l=efficiency,
            cost=replace(
                v.cost,
                depreciation_per_km=D("0"),
                maintenance_per_km=D("0"),
                fixed_cost_per_hour=D("0"),
            ),
        )
        for v, efficiency in zip(vehicles, [D("100"), D("1")], strict=True)
    ]
    locations = {None: D("0"), deliveries[0].id: D("1"), deliveries[1].id: D("10")}
    matrix = TravelMatrix(
        {
            (a, b): TravelMetric(abs(x - y), abs(x - y) * 2)
            for a, x in locations.items()
            for b, y in locations.items()
            if a != b
        }
    )
    return deliveries, vehicles, matrix


@pytest.mark.parametrize("criterion", ["fuel", "team"])
def test_ga_selects_cheaper_operational_assignment_from_real_alternatives(criterion):
    deliveries, vehicles, matrix = _fuel_problem()
    workers = [_worker(201, WorkerRole.DRIVER, "10"), _worker(202, WorkerRole.DRIVER, "10")]
    if criterion == "team":
        vehicles = [
            replace(vehicles[0], type=VehicleType.MOTO, fuel_efficiency_km_per_l=D("10")),
            replace(vehicles[1], fuel_efficiency_km_per_l=D("10")),
        ]
        workers = [
            _worker(201, WorkerRole.MOTORCYCLE_COURIER, "10"),
            _worker(202, WorkerRole.DRIVER, "50"),
        ]
    inputs = [build_vehicle_input(v, helper_available=False) for v in vehicles]
    evaluator = OperationalFitnessEvaluator(
        deliveries=deliveries, vehicles=vehicles, workers=workers
    )
    result = GeneticOptimizer(
        GeneticOptimizerConfig(
            population_size=8,
            max_generations=3,
            stagnation_generations=2,
        )
    ).optimize(
        deliveries=deliveries,
        vehicles=inputs,
        travel_matrix=matrix,
        random_seed=11,
        operation_start_at=START,
        fitness_evaluator=evaluator,
    )
    assert result.best.fitness.feasible
    efficient_route = next(r for r in result.best.solution.routes if r.vehicle_id == vehicles[0].id)
    assert efficient_route.delivery_ids == (deliveries[1].id,)
    baseline = next(b for b in result.baselines if b.name == "NEAREST_NEIGHBOR")
    assert result.best.fitness.total_cost_brl < baseline.fitness.total_cost_brl


def test_every_benchmark_method_uses_operational_cost_and_team_feasibility():
    deliveries, vehicles, matrix = _fuel_problem()
    inputs = [build_vehicle_input(v, helper_available=False) for v in vehicles]
    worker = _worker(201, WorkerRole.DRIVER, "10")
    config = GeneticOptimizerConfig(population_size=8, max_generations=3, stagnation_generations=2)
    for workers, feasible in [([worker], False), ([worker, replace(worker, id=_id(202))], True)]:
        factory = partial(
            OperationalFitnessEvaluator, deliveries=deliveries, vehicles=vehicles, workers=workers
        )
        benchmark_problem = BenchmarkProblem(
            "COST-UNIT",
            deliveries,
            inputs,
            matrix,
            operation_start_at=START,
            fitness_evaluator_factory=factory,
        )
        report = OptimizerBenchmarkRunner(config).run(benchmark_problem, seeds=(11,))
        assert len(report.runs) == 5
        assert all(run.feasible is feasible for run in report.runs)
        if not feasible:
            assert all(
                run.route_hard_violation_counts["TEAM_INFEASIBLE"] == 1 for run in report.runs
            )
        else:
            assert all(run.cost_brl > 0 for run in report.runs)
            nearest = report.runs[0]
            solution = RouteDecoder(
                deliveries=deliveries,
                vehicles=inputs,
                travel_matrix=matrix,
                operation_start_at=START,
            ).decode(tuple(d.id for d in deliveries))
            assert nearest.cost_brl == float(factory().evaluate(solution).total_cost_brl)


def test_cost_cache_reuses_only_equivalent_cost_inputs(monkeypatch):
    deliveries, vehicles, _ = _fuel_problem()
    workers = [_worker(201, WorkerRole.DRIVER, "10"), _worker(202, WorkerRole.DRIVER, "20")]
    evaluator = OperationalFitnessEvaluator(
        deliveries=deliveries, vehicles=vehicles, workers=workers
    )
    solution = DecodedSolution(
        routes=tuple(_route(v.id, "60", (d.id,)) for v, d in zip(vehicles, deliveries, strict=True))
    )
    calls = []
    original = evaluator._teams.solve

    def solve(**kwargs):
        calls.append(1)
        return original(**kwargs)

    monkeypatch.setattr(evaluator._teams, "solve", solve)
    first = evaluator.evaluate(solution)
    repeated = evaluator.evaluate(replace(solution, routes=tuple(reversed(solution.routes))))
    assert first == repeated
    assert len(calls) == 1
    changed = replace(
        solution,
        routes=(replace(solution.routes[0], total_duration_minutes=D("120")), solution.routes[1]),
    )
    assert evaluator.evaluate(changed).total_cost_brl > first.total_cost_brl
    assert len(calls) == 2
    assert evaluator.cache_hits == 1


def test_cost_cache_keeps_helper_requirement_and_operation_resources_separate():
    deliveries, vehicles, _ = _fuel_problem()
    deliveries = [
        deliveries[0],
        replace(deliveries[1], handling_requirement=HandlingRequirement.TWO_PERSON),
    ]
    workers = [_worker(201, WorkerRole.DRIVER, "10")]
    evaluator = OperationalFitnessEvaluator(
        deliveries=deliveries, vehicles=vehicles, workers=workers
    )
    regular = DecodedSolution(routes=(_route(vehicles[0].id, "60", (deliveries[0].id,)),))
    helper = DecodedSolution(routes=(_route(vehicles[0].id, "60", (deliveries[1].id,)),))
    assert evaluator.evaluate(regular).team_feasible
    assert not evaluator.evaluate(helper).team_feasible
    with_helper = OperationalFitnessEvaluator(
        deliveries=deliveries,
        vehicles=vehicles,
        workers=[*workers, _worker(202, WorkerRole.HELPER, "5")],
    )
    assert with_helper.evaluate(helper).team_feasible
