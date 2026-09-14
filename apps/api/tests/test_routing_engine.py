import uuid
from datetime import datetime, time

import pytest

from fluxmed.domain.enums import RoadClass, RoutingAlgorithm, TrafficLevel, TrafficMode
from fluxmed.routing import (
    DirectedGraph,
    GraphEdge,
    GraphNode,
    NoRouteFoundError,
    RoutingEngine,
    time_bucket,
)


def _id(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def _graph() -> tuple[DirectedGraph, dict[str, uuid.UUID]]:
    ids = {
        "a": _id(1),
        "b": _id(2),
        "c": _id(3),
        "d": _id(4),
        "ab": _id(11),
        "bc": _id(12),
        "ad": _id(13),
        "dc": _id(14),
        "ca": _id(15),
    }
    nodes = [
        GraphNode(ids["a"], -46.6200, -22.4000, "centro-historico"),
        GraphNode(ids["b"], -46.6199, -22.4000, "centro-historico"),
        GraphNode(ids["c"], -46.6198, -22.4000, "centro-historico"),
        GraphNode(ids["d"], -46.6200, -22.3999, "vale-verde"),
    ]
    edges = [
        GraphEdge(
            ids["ab"],
            ids["a"],
            ids["b"],
            100,
            60,
            RoadClass.ARTERIAL,
            "A-B",
            ((-46.6200, -22.4000), (-46.6199, -22.4000)),
        ),
        GraphEdge(
            ids["bc"],
            ids["b"],
            ids["c"],
            100,
            60,
            RoadClass.ARTERIAL,
            "B-C",
            ((-46.6199, -22.4000), (-46.6198, -22.4000)),
            True,
            "Ponte Teste",
        ),
        GraphEdge(
            ids["ad"],
            ids["a"],
            ids["d"],
            160,
            60,
            RoadClass.COLLECTOR,
            "A-D",
            ((-46.6200, -22.4000), (-46.6200, -22.3999)),
        ),
        GraphEdge(
            ids["dc"],
            ids["d"],
            ids["c"],
            160,
            60,
            RoadClass.COLLECTOR,
            "D-C",
            ((-46.6200, -22.3999), (-46.6198, -22.4000)),
        ),
        GraphEdge(
            ids["ca"],
            ids["c"],
            ids["a"],
            100,
            60,
            RoadClass.ARTERIAL,
            "C-A",
            ((-46.6198, -22.4000), (-46.6200, -22.4000)),
        ),
    ]
    return DirectedGraph(nodes, edges), ids


def test_astar_respects_one_way_and_can_return_by_another_edge() -> None:
    graph, ids = _graph()
    engine = RoutingEngine(graph)
    route = engine.shortest_path(
        origin_node_id=ids["b"],
        destination_node_id=ids["a"],
        departure_at=datetime(2026, 9, 14, 3, 0),
        traffic_mode=TrafficMode.FREE,
        algorithm=RoutingAlgorithm.ASTAR,
    )

    assert route.edge_ids == (ids["bc"], ids["ca"])
    assert ids["ab"] not in route.edge_ids


def test_closure_and_bridge_closure_force_detour() -> None:
    graph, ids = _graph()
    engine = RoutingEngine(graph)
    route = engine.shortest_path(
        origin_node_id=ids["a"],
        destination_node_id=ids["c"],
        departure_at=datetime(2026, 9, 14, 3, 0),
        traffic_mode=TrafficMode.FREE,
        closed_edge_ids={ids["bc"]},
    )

    assert route.edge_ids == (ids["ad"], ids["dc"])
    assert route.distance_m == 320


def test_traffic_override_can_change_best_path() -> None:
    graph, ids = _graph()
    engine = RoutingEngine(graph)
    baseline = engine.shortest_path(
        origin_node_id=ids["a"],
        destination_node_id=ids["c"],
        departure_at=datetime(2026, 9, 14, 3, 0),
        traffic_mode=TrafficMode.FREE,
    )
    congested = engine.shortest_path(
        origin_node_id=ids["a"],
        destination_node_id=ids["c"],
        departure_at=datetime(2026, 9, 14, 3, 0),
        traffic_mode=TrafficMode.FREE,
        traffic_overrides={
            ids["ab"]: TrafficLevel.VERY_HEAVY,
            ids["bc"]: TrafficLevel.VERY_HEAVY,
        },
    )

    assert baseline.edge_ids == (ids["ab"], ids["bc"])
    assert congested.edge_ids == (ids["ad"], ids["dc"])


def test_automatic_peak_traffic_increases_travel_time() -> None:
    graph, ids = _graph()
    engine = RoutingEngine(graph)
    free_flow = engine.shortest_path(
        origin_node_id=ids["c"],
        destination_node_id=ids["a"],
        departure_at=datetime(2026, 9, 14, 3, 0),
        traffic_mode=TrafficMode.AUTOMATIC,
    )
    peak = engine.shortest_path(
        origin_node_id=ids["c"],
        destination_node_id=ids["a"],
        departure_at=datetime(2026, 9, 14, 8, 0),
        traffic_mode=TrafficMode.AUTOMATIC,
    )

    assert peak.travel_time_seconds > free_flow.travel_time_seconds


def test_time_bucket_uses_fifteen_minute_windows() -> None:
    assert time_bucket(time(7, 8)).label == "07:00-07:15"
    assert time_bucket(time(7, 29)).label == "07:15-07:30"


def test_no_path_is_explicit() -> None:
    graph, ids = _graph()
    engine = RoutingEngine(graph)

    with pytest.raises(NoRouteFoundError):
        engine.shortest_path(
            origin_node_id=ids["a"],
            destination_node_id=ids["c"],
            departure_at=datetime(2026, 9, 14, 3, 0),
            traffic_mode=TrafficMode.FREE,
            closed_edge_ids={ids["bc"], ids["ad"]},
        )


def test_dijkstra_route_return_is_supported() -> None:
    graph, ids = _graph()
    route = RoutingEngine(graph).shortest_path(
        origin_node_id=ids["c"],
        destination_node_id=ids["a"],
        departure_at=datetime(2026, 9, 14, 3, 0),
        traffic_mode=TrafficMode.FREE,
        algorithm=RoutingAlgorithm.DIJKSTRA,
    )

    assert route.edge_ids == (ids["ca"],)
    assert route.geometry["type"] == "LineString"
    assert route.distance_m == 100
