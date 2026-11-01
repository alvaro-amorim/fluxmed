import uuid
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from fluxmed.application.optimization.routing_matrix import RoutingMatrixBuilder
from fluxmed.domain.enums import RoadClass, TrafficMode
from fluxmed.routing import DirectedGraph, GraphEdge, GraphNode, RoutingEngine


def test_geometry_uses_the_same_traffic_snapshot_as_matrix(monkeypatch):
    nodes = [GraphNode(uuid.UUID(int=i + 1), 0, 0, "test") for i in range(4)]
    specs = [
        (0, 1, 1000, RoadClass.LOCAL),
        (1, 2, 1000, RoadClass.SERVICE),
        (1, 3, 560, RoadClass.EXPRESSWAY),
        (3, 2, 560, RoadClass.EXPRESSWAY),
        (2, 0, 1000, RoadClass.LOCAL),
    ]
    edges = [
        GraphEdge(
            uuid.UUID(int=100 + i),
            nodes[a].id,
            nodes[b].id,
            length,
            60,
            kind,
            str(i),
            ((float(a), 0), (float(b), 0)),
        )
        for i, (a, b, length, kind) in enumerate(specs)
    ]
    graph = DirectedGraph(nodes, edges)
    engine = RoutingEngine(graph)
    start = datetime(2026, 10, 31, 5, 59, 50)
    early = engine.shortest_path(
        origin_node_id=nodes[1].id,
        destination_node_id=nodes[2].id,
        departure_at=start,
        traffic_mode=TrafficMode.AUTOMATIC,
    )
    late = engine.shortest_path(
        origin_node_id=nodes[1].id,
        destination_node_id=nodes[2].id,
        departure_at=start + timedelta(minutes=2),
        traffic_mode=TrafficMode.AUTOMATIC,
    )
    assert early.edge_ids != late.edge_ids  # A real path change across the traffic boundary.
    session = Mock()
    session.scalar.return_value = SimpleNamespace(id=uuid.UUID(int=900))
    builder = RoutingMatrixBuilder(session)
    a, b = uuid.UUID(int=501), uuid.UUID(int=502)
    addresses = {None: nodes[0], a: nodes[1], b: nodes[2]}
    monkeypatch.setattr(builder, "_graph", lambda _: graph)
    monkeypatch.setattr(builder, "_depot_address", lambda _: nodes[0])
    monkeypatch.setattr(builder, "_delivery_addresses", lambda *_: addresses)
    monkeypatch.setattr(builder, "_effective_overrides", lambda _: (set(), {}))

    def travel(**kwargs):
        path = engine.shortest_path(
            origin_node_id=kwargs["origin"].id,
            destination_node_id=kwargs["destination"].id,
            departure_at=kwargs["departure_at"],
            traffic_mode=kwargs["traffic_mode"],
        )
        return path.distance_m, path.travel_time_seconds, path.geometry["coordinates"]

    monkeypatch.setattr(builder, "_travel_with_geometry", travel)
    operation = SimpleNamespace(
        id=uuid.UUID(int=901),
        operation_date=date(2026, 10, 31),
        operation_start_time=time(5, 59, 50),
        traffic_mode=TrafficMode.AUTOMATIC,
    )
    matrix = builder.build(operation=operation, delivery_addresses={a: a, b: b})
    expected = []
    for origin, destination in [(None, a), (a, b), (b, None)]:
        distance, _, coordinates = travel(
            origin=addresses[origin],
            destination=addresses[destination],
            departure_at=start,
            traffic_mode=TrafficMode.AUTOMATIC,
        )
        assert float(matrix.metric(origin, destination).distance_km) == distance / 1000
        builder._append_coordinates(expected, coordinates)
    actual = builder.build_route_geometry(
        operation=operation, delivery_addresses={a: a, b: b}, delivery_ids=(a, b)
    )
    assert actual["coordinates"] == expected
