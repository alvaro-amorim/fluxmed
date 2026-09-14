import heapq
import math
import uuid
from datetime import datetime, timedelta
from itertools import count

from fluxmed.domain.enums import RoutingAlgorithm, TrafficLevel, TrafficMode
from fluxmed.routing.graph import DirectedGraph, GraphEdge, RoutePath
from fluxmed.routing.traffic import TrafficModel, time_bucket

MAX_HEURISTIC_SPEED_KMH = 90.0


class NoRouteFoundError(LookupError):
    pass


class RoutingEngine:
    def __init__(self, graph: DirectedGraph) -> None:
        self._graph = graph

    def shortest_path(
        self,
        *,
        origin_node_id: uuid.UUID,
        destination_node_id: uuid.UUID,
        departure_at: datetime,
        traffic_mode: TrafficMode,
        algorithm: RoutingAlgorithm = RoutingAlgorithm.ASTAR,
        closed_edge_ids: set[uuid.UUID] | None = None,
        traffic_overrides: dict[uuid.UUID, TrafficLevel] | None = None,
    ) -> RoutePath:
        if origin_node_id == destination_node_id:
            bucket = time_bucket(departure_at)
            return RoutePath(
                origin_node_id=origin_node_id,
                destination_node_id=destination_node_id,
                node_ids=(origin_node_id,),
                edge_ids=(),
                distance_m=0.0,
                travel_time_seconds=0.0,
                departure_at=departure_at,
                arrival_at=departure_at,
                algorithm=algorithm,
                traffic_mode=traffic_mode,
                time_bucket=bucket.label,
                geometry={"type": "LineString", "coordinates": []},
            )

        self._graph.node(origin_node_id)
        self._graph.node(destination_node_id)
        closures = closed_edge_ids or set()
        overrides = traffic_overrides or {}

        best_seconds: dict[uuid.UUID, float] = {origin_node_id: 0.0}
        previous: dict[uuid.UUID, tuple[uuid.UUID, uuid.UUID]] = {}
        serial = count()
        queue: list[tuple[float, int, uuid.UUID]] = []
        heapq.heappush(
            queue,
            (
                self._heuristic_seconds(origin_node_id, destination_node_id, algorithm),
                next(serial),
                origin_node_id,
            ),
        )

        while queue:
            priority, _serial, current_id = heapq.heappop(queue)
            current_best = best_seconds.get(current_id)
            if current_best is None:
                continue

            expected_priority = current_best + self._heuristic_seconds(
                current_id, destination_node_id, algorithm
            )
            if priority > expected_priority + 1e-9:
                continue
            if current_id == destination_node_id:
                return self._build_path(
                    origin_node_id=origin_node_id,
                    destination_node_id=destination_node_id,
                    previous=previous,
                    travel_seconds=current_best,
                    departure_at=departure_at,
                    traffic_mode=traffic_mode,
                    algorithm=algorithm,
                )

            entered_at = departure_at + timedelta(seconds=current_best)
            current_node = self._graph.node(current_id)
            for edge in self._graph.outgoing(current_id):
                if edge.id in closures:
                    continue
                edge_seconds = self._edge_seconds(
                    edge=edge,
                    entered_at=entered_at,
                    traffic_mode=traffic_mode,
                    district_slug=current_node.district_slug,
                    override_level=overrides.get(edge.id),
                )
                candidate = current_best + edge_seconds
                if candidate + 1e-9 >= best_seconds.get(edge.to_node_id, math.inf):
                    continue
                best_seconds[edge.to_node_id] = candidate
                previous[edge.to_node_id] = (current_id, edge.id)
                heapq.heappush(
                    queue,
                    (
                        candidate
                        + self._heuristic_seconds(
                            edge.to_node_id, destination_node_id, algorithm
                        ),
                        next(serial),
                        edge.to_node_id,
                    ),
                )

        raise NoRouteFoundError(
            f"No directed route from {origin_node_id} to {destination_node_id}."
        )

    @staticmethod
    def _edge_seconds(
        *,
        edge: GraphEdge,
        entered_at: datetime,
        traffic_mode: TrafficMode,
        district_slug: str,
        override_level: TrafficLevel | None,
    ) -> float:
        base_seconds = edge.length_m / (edge.speed_limit_kmh * 1000 / 3600)
        factor = TrafficModel.factor(
            mode=traffic_mode,
            entered_at=entered_at,
            road_class=edge.road_class,
            district_slug=district_slug,
            override_level=override_level,
        )
        return base_seconds * factor

    def _heuristic_seconds(
        self,
        origin_node_id: uuid.UUID,
        destination_node_id: uuid.UUID,
        algorithm: RoutingAlgorithm,
    ) -> float:
        if algorithm is RoutingAlgorithm.DIJKSTRA:
            return 0.0
        origin = self._graph.node(origin_node_id)
        destination = self._graph.node(destination_node_id)
        distance_m = self._haversine_m(
            origin.latitude,
            origin.longitude,
            destination.latitude,
            destination.longitude,
        )
        return distance_m / (MAX_HEURISTIC_SPEED_KMH * 1000 / 3600)

    def _build_path(
        self,
        *,
        origin_node_id: uuid.UUID,
        destination_node_id: uuid.UUID,
        previous: dict[uuid.UUID, tuple[uuid.UUID, uuid.UUID]],
        travel_seconds: float,
        departure_at: datetime,
        traffic_mode: TrafficMode,
        algorithm: RoutingAlgorithm,
    ) -> RoutePath:
        node_ids: list[uuid.UUID] = [destination_node_id]
        edge_ids: list[uuid.UUID] = []
        cursor = destination_node_id
        while cursor != origin_node_id:
            try:
                parent, edge_id = previous[cursor]
            except KeyError as exc:
                raise NoRouteFoundError("Routing predecessor chain is incomplete.") from exc
            node_ids.append(parent)
            edge_ids.append(edge_id)
            cursor = parent

        node_ids.reverse()
        edge_ids.reverse()
        edges = [self._graph.edge(edge_id) for edge_id in edge_ids]
        distance_m = sum(edge.length_m for edge in edges)
        arrival_at = departure_at + timedelta(seconds=travel_seconds)
        bucket = time_bucket(departure_at)
        return RoutePath(
            origin_node_id=origin_node_id,
            destination_node_id=destination_node_id,
            node_ids=tuple(node_ids),
            edge_ids=tuple(edge_ids),
            distance_m=distance_m,
            travel_time_seconds=travel_seconds,
            departure_at=departure_at,
            arrival_at=arrival_at,
            algorithm=algorithm,
            traffic_mode=traffic_mode,
            time_bucket=bucket.label,
            geometry=self._route_geometry(edges),
        )

    @staticmethod
    def _route_geometry(edges: list[GraphEdge]) -> dict[str, object]:
        coordinates: list[list[float]] = []
        for edge in edges:
            edge_coordinates = [[longitude, latitude] for longitude, latitude in edge.coordinates]
            if not edge_coordinates:
                continue
            if coordinates and coordinates[-1] == edge_coordinates[0]:
                coordinates.extend(edge_coordinates[1:])
            else:
                coordinates.extend(edge_coordinates)
        return {"type": "LineString", "coordinates": coordinates}

    @staticmethod
    def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_m = 6_371_000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))
