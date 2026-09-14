import uuid
from dataclasses import dataclass
from datetime import datetime

from fluxmed.domain.enums import RoadClass, RoutingAlgorithm, TrafficMode

Coordinate = tuple[float, float]


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: uuid.UUID
    longitude: float
    latitude: float
    district_slug: str


@dataclass(frozen=True, slots=True)
class GraphEdge:
    id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    length_m: float
    speed_limit_kmh: int
    road_class: RoadClass
    street_name: str
    coordinates: tuple[Coordinate, ...]
    is_bridge: bool = False
    bridge_name: str | None = None


@dataclass(frozen=True, slots=True)
class RoutePath:
    origin_node_id: uuid.UUID
    destination_node_id: uuid.UUID
    node_ids: tuple[uuid.UUID, ...]
    edge_ids: tuple[uuid.UUID, ...]
    distance_m: float
    travel_time_seconds: float
    departure_at: datetime
    arrival_at: datetime
    algorithm: RoutingAlgorithm
    traffic_mode: TrafficMode
    time_bucket: str
    geometry: dict[str, object]


class DirectedGraph:
    def __init__(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        self.nodes = {node.id: node for node in nodes}
        self.edges = {edge.id: edge for edge in edges}
        self.adjacency: dict[uuid.UUID, list[GraphEdge]] = {node.id: [] for node in nodes}

        for edge in edges:
            if edge.from_node_id not in self.nodes or edge.to_node_id not in self.nodes:
                raise ValueError("Routing edge references an unknown graph node.")
            if edge.length_m <= 0:
                raise ValueError("Routing edge length must be positive.")
            if edge.speed_limit_kmh <= 0:
                raise ValueError("Routing edge speed must be positive.")
            self.adjacency[edge.from_node_id].append(edge)

        for outgoing in self.adjacency.values():
            outgoing.sort(key=lambda item: str(item.id))

    def outgoing(self, node_id: uuid.UUID) -> tuple[GraphEdge, ...]:
        return tuple(self.adjacency.get(node_id, ()))

    def node(self, node_id: uuid.UUID) -> GraphNode:
        try:
            return self.nodes[node_id]
        except KeyError as exc:
            raise KeyError(f"Unknown routing node: {node_id}") from exc

    def edge(self, edge_id: uuid.UUID) -> GraphEdge:
        try:
            return self.edges[edge_id]
        except KeyError as exc:
            raise KeyError(f"Unknown routing edge: {edge_id}") from exc
