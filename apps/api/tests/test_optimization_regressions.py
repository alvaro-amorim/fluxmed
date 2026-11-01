import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from fluxmed.domain.enums import DeliveryPriority, TimeWindowPolicy
from fluxmed.optimization import (
    DecodedSolution,
    FitnessEvaluator,
    GeneticOptimizer,
    GeneticOptimizerConfig,
    OptimizationDelivery,
    OptimizationVehicle,
    RouteDecoder,
    SolutionValidator,
    TravelMatrix,
    TravelMetric,
)

D = Decimal
START = datetime(2026, 10, 31, 8, tzinfo=UTC)


def problem():
    deliveries = [OptimizationDelivery(uuid.UUID(int=i), D("10"), D("0.1"), 5) for i in (1, 2)]
    vehicle = OptimizationVehicle(uuid.UUID(int=101), D("100"), D("1"), cost_per_hour_brl=D("60"))
    locations = [None, *(d.id for d in deliveries)]
    matrix = TravelMatrix(
        {(a, b): TravelMetric(D("1"), D("10")) for a in locations for b in locations if a != b}
    )
    return deliveries, vehicle, matrix


def decode(deliveries, vehicle, matrix, order=None):
    return RouteDecoder(
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=matrix,
        operation_start_at=START,
        operation_end_at=START + timedelta(hours=8),
    ).decode(order or tuple(d.id for d in deliveries))


@pytest.mark.parametrize(
    "higher,lower",
    [
        (DeliveryPriority.CRITICAL, DeliveryPriority.HIGH),
        (DeliveryPriority.HIGH, DeliveryPriority.NORMAL),
        (DeliveryPriority.NORMAL, DeliveryPriority.LOW),
    ],
)
def test_priority_changes_preferred_order_with_other_inputs_identical(higher, lower):
    deliveries, vehicle, matrix = problem()
    a, b = (d.id for d in deliveries)
    evaluator = FitnessEvaluator()
    for first_priority, second_priority, expected in [
        (higher, lower, (a, b)),
        (lower, higher, (b, a)),
    ]:
        inputs = [
            replace(deliveries[0], priority=first_priority),
            replace(deliveries[1], priority=second_priority),
        ]
        choices = {
            order: evaluator.evaluate(decode(inputs, vehicle, matrix, order)).sort_key()
            for order in [(a, b), (b, a)]
        }
        assert min(choices, key=choices.get) == expected
        assert choices[(a, b)] != choices[(b, a)]


def test_waiting_is_part_of_elapsed_duration_makespan_and_hourly_cost():
    deliveries, vehicle, matrix = problem()
    delivery = replace(
        deliveries[0], service_minutes=0, time_window_start=START + timedelta(hours=1)
    )
    solution = decode([delivery], vehicle, matrix)
    route = solution.routes[0]
    assert route.stops[0].arrival_at == START + timedelta(minutes=10)
    assert route.stops[0].departure_at == START + timedelta(minutes=60)
    assert route.total_duration_minutes == D("70")
    assert route.total_cost_brl.quantize(D("0.01")) == D("70")
    assert FitnessEvaluator().evaluate(solution).makespan_minutes == D("70")


def test_ga_changes_order_when_only_delivery_priority_is_swapped():
    deliveries, vehicle, matrix = problem()
    optimizer = GeneticOptimizer(
        GeneticOptimizerConfig(
            population_size=8,
            max_generations=3,
            stagnation_generations=2,
        )
    )
    for index in (0, 1):
        inputs = [
            replace(d, priority=DeliveryPriority.HIGH if i == index else DeliveryPriority.NORMAL)
            for i, d in enumerate(deliveries)
        ]
        result = optimizer.optimize(
            deliveries=inputs,
            vehicles=[vehicle],
            travel_matrix=matrix,
            random_seed=101,
            operation_start_at=START,
        )
        assert result.best.solution.routes[0].delivery_ids[0] == deliveries[index].id


def test_changing_priority_does_not_require_a_different_route_without_an_alternative():
    deliveries, vehicle, matrix = problem()
    solutions = [
        decode([replace(deliveries[0], priority=p)], vehicle, matrix) for p in DeliveryPriority
    ]
    assert all(s.routes[0].delivery_ids == (deliveries[0].id,) for s in solutions)


@pytest.mark.parametrize("corruption", ["load", "volume", "distance", "stops", "clock", "duration"])
def test_final_validator_rejects_inconsistent_declared_route(corruption):
    deliveries, vehicle, matrix = problem()
    solution = decode(deliveries, vehicle, matrix)
    route = solution.routes[0]
    changes = {
        "load": {"total_weight_kg": D("1")},
        "volume": {"total_volume_m3": D("0.01")},
        "distance": {"distance_km": D("0.01")},
        "stops": {"stops": tuple(reversed(route.stops))},
        "clock": {"stops": (replace(route.stops[0], arrival_at=START), *route.stops[1:])},
        "duration": {"total_duration_minutes": D("1")},
    }
    result = SolutionValidator().validate(
        solution=replace(solution, routes=(replace(route, **changes[corruption]),)),
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=matrix,
        operation_start_at=START,
        operation_end_at=START + timedelta(hours=8),
    )
    assert not result.valid


def test_final_validator_rejects_hidden_hard_window_violation():
    deliveries, vehicle, matrix = problem()
    deliveries = [
        replace(
            deliveries[0],
            time_window_end=START + timedelta(minutes=5),
            time_window_policy=TimeWindowPolicy.HARD,
        )
    ]
    solution = RouteDecoder(
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=matrix,
        operation_start_at=START,
        advanced_pruning_enabled=False,
    ).decode((deliveries[0].id,))
    solution = replace(solution, routes=(replace(solution.routes[0], hard_violations=()),))
    result = SolutionValidator().validate(
        solution=solution,
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=matrix,
        operation_start_at=START,
    )
    assert "HARD_TIME_WINDOW_IMPOSSIBLE" in {issue.code for issue in result.issues}


def test_final_validator_rejects_vehicle_in_two_routes():
    deliveries, vehicle, matrix = problem()
    routes = tuple(decode([delivery], vehicle, matrix).routes[0] for delivery in deliveries)
    result = SolutionValidator().validate(
        solution=DecodedSolution(routes=routes),
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=matrix,
        operation_start_at=START,
    )
    assert "VEHICLE_REUSED" in {issue.code for issue in result.issues}


def test_priority_weights_late_service_but_does_not_invent_an_order_for_equal_priorities():
    deliveries, vehicle, matrix = problem()
    deliveries = [replace(d, time_window_end=START + timedelta(minutes=15)) for d in deliveries]
    a, b = (d.id for d in deliveries)
    evaluator = FitnessEvaluator()
    equal = [
        evaluator.evaluate(decode(deliveries, vehicle, matrix, order)) for order in [(a, b), (b, a)]
    ]
    assert equal[0].sort_key() == equal[1].sort_key()
    penalties = []
    for priority in [
        DeliveryPriority.LOW,
        DeliveryPriority.NORMAL,
        DeliveryPriority.HIGH,
        DeliveryPriority.CRITICAL,
    ]:
        inputs = [deliveries[0], replace(deliveries[1], priority=priority)]
        penalties.append(evaluator.evaluate(decode(inputs, vehicle, matrix)).service_penalty)
    assert penalties == sorted(set(penalties))


@pytest.mark.parametrize("rule", ["capacity", "volume", "range", "shift", "return", "missing_stop"])
def test_final_validator_recomputes_limits_without_decoder_warnings(rule):
    deliveries, vehicle, matrix = problem()
    solution = decode(deliveries, vehicle, matrix)
    route = solution.routes[0]
    codes = {
        "capacity": "CAPACITY_EXCEEDED",
        "volume": "VOLUME_EXCEEDED",
        "range": "RANGE_IMPOSSIBLE",
        "shift": "END_OF_SHIFT_IMPOSSIBLE",
        "return": "ROUTE_DISCONNECTED",
        "missing_stop": "STOP_SEQUENCE_MISMATCH",
    }
    if rule == "capacity":
        deliveries = [replace(d, weight_kg=D("100")) for d in deliveries]
    if rule == "volume":
        deliveries = [replace(d, volume_m3=D("1")) for d in deliveries]
    if rule == "range":
        vehicle = replace(vehicle, max_range_km=D("1"))
    if rule == "return":
        matrix = TravelMatrix(
            {
                key: value
                for key, value in matrix._metrics.items()
                if key != (deliveries[-1].id, None)
            }
        )
    if rule == "missing_stop":
        solution = replace(solution, routes=(replace(route, stops=route.stops[:-1]),))
    validation = SolutionValidator().validate(
        solution=solution,
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=matrix,
        operation_start_at=START,
        operation_end_at=START + timedelta(minutes=5 if rule == "shift" else 480),
    )
    assert codes[rule] in {issue.code for issue in validation.issues}


def test_independent_validator_accepts_waiting_fractional_travel_and_timezones():
    deliveries, vehicle, matrix = problem()
    deliveries = [
        replace(
            deliveries[0],
            time_window_start=START + timedelta(hours=1),
            time_window_end=START + timedelta(hours=2),
            time_window_policy=TimeWindowPolicy.HARD,
        )
    ]
    matrix = TravelMatrix(
        {
            key: TravelMetric(value.distance_km, D("1.23456789"))
            for key, value in matrix._metrics.items()
        }
    )
    solution = decode(deliveries, vehicle, matrix)
    validation = SolutionValidator().validate(
        solution=solution,
        deliveries=deliveries,
        vehicles=[vehicle],
        travel_matrix=matrix,
        operation_start_at=START,
        operation_end_at=START + timedelta(hours=8),
    )
    assert validation.valid, validation.issues
