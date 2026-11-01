import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.domain.enums import FacilityType, RoadOverrideType, TrafficLevel, TrafficMode
from fluxmed.infrastructure.models.city import (
    AddressModel,
    CityModel,
    DistrictModel,
    FacilityModel,
    IntersectionModel,
    RoadSegmentModel,
    StreetModel,
)
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.road_override import RoadOverrideModel
from fluxmed.optimization import TravelMatrix, TravelMetric
from fluxmed.routing import DirectedGraph, GraphEdge, GraphNode, NoRouteFoundError, RoutingEngine
from fluxmed.routing.traffic import TrafficModel

CITY_NAME = "Santa Aurora"


class OptimizationRoutingError(RuntimeError):
    pass


class RoutingMatrixBuilder:
    def __init__(self, session: Session) -> None:
        self._session = session

    def build(
        self,
        *,
        operation: OperationModel,
        delivery_addresses: dict[uuid.UUID, uuid.UUID],
    ) -> TravelMatrix:
        city = self._session.scalar(select(CityModel).where(CityModel.name == CITY_NAME))
        if city is None:
            raise OptimizationRoutingError("Santa Aurora ainda não foi gerada.")
        graph = self._graph(city.id)
        depot = self._depot_address(city.id)
        addresses = self._delivery_addresses(city.id, depot, delivery_addresses)
        closed_edges, traffic_overrides = self._effective_overrides(operation.id)
        departure_at = datetime.combine(operation.operation_date, operation.operation_start_time)
        metrics: dict[tuple[uuid.UUID | None, uuid.UUID | None], TravelMetric] = {}
        keys = list(addresses)
        for origin in keys:
            for destination in keys:
                if origin == destination:
                    continue
                distance_m, travel_seconds = self._travel(
                    graph=graph,
                    origin=addresses[origin],
                    destination=addresses[destination],
                    departure_at=departure_at,
                    traffic_mode=operation.traffic_mode,
                    closed_edges=closed_edges,
                    traffic_overrides=traffic_overrides,
                )
                metrics[(origin, destination)] = TravelMetric(
                    distance_km=Decimal(str(distance_m)) / Decimal("1000"),
                    travel_minutes=Decimal(str(travel_seconds)) / Decimal("60"),
                )
        return TravelMatrix(metrics)

    def build_route_geometry(
        self,
        *,
        operation: OperationModel,
        delivery_addresses: dict[uuid.UUID, uuid.UUID],
        delivery_ids: tuple[uuid.UUID, ...],
    ) -> dict[str, object]:
        city = self._session.scalar(select(CityModel).where(CityModel.name == CITY_NAME))
        if city is None:
            raise OptimizationRoutingError("Santa Aurora ainda não foi gerada.")
        graph = self._graph(city.id)
        depot = self._depot_address(city.id)
        addresses = self._delivery_addresses(city.id, depot, delivery_addresses)
        closed_edges, traffic_overrides = self._effective_overrides(operation.id)
        departure_at = datetime.combine(operation.operation_date, operation.operation_start_time)
        sequence: list[uuid.UUID | None] = [None, *delivery_ids, None]
        coordinates: list[list[float]] = []
        for origin_key, destination_key in zip(sequence, sequence[1:], strict=False):
            origin = addresses[origin_key]
            destination = addresses[destination_key]
            _distance, _travel_seconds, leg_coordinates = self._travel_with_geometry(
                graph=graph,
                origin=origin,
                destination=destination,
                departure_at=departure_at,
                traffic_mode=operation.traffic_mode,
                closed_edges=closed_edges,
                traffic_overrides=traffic_overrides,
            )
            self._append_coordinates(coordinates, leg_coordinates)
            # Match the fixed departure snapshot used to construct every matrix leg.
        return {"type": "LineString", "coordinates": coordinates}

    def _delivery_addresses(
        self,
        city_id: uuid.UUID,
        depot: AddressModel,
        delivery_addresses: dict[uuid.UUID, uuid.UUID],
    ) -> dict[uuid.UUID | None, AddressModel]:
        addresses: dict[uuid.UUID | None, AddressModel] = {None: depot}
        for delivery_id, address_id in delivery_addresses.items():
            address = self._session.get(AddressModel, address_id)
            if address is None or not address.active or address.city_id != city_id:
                raise OptimizationRoutingError(
                    f"A entrega {delivery_id} possui endereço não roteável."
                )
            addresses[delivery_id] = address
        return addresses

    def _travel(
        self,
        *,
        graph: DirectedGraph,
        origin: AddressModel,
        destination: AddressModel,
        departure_at: datetime,
        traffic_mode: TrafficMode,
        closed_edges: set[uuid.UUID],
        traffic_overrides: dict[uuid.UUID, TrafficLevel],
    ) -> tuple[float, float]:
        distance_m, travel_seconds, _coordinates = self._travel_with_geometry(
            graph=graph,
            origin=origin,
            destination=destination,
            departure_at=departure_at,
            traffic_mode=traffic_mode,
            closed_edges=closed_edges,
            traffic_overrides=traffic_overrides,
        )
        return distance_m, travel_seconds

    def _travel_with_geometry(
        self,
        *,
        graph: DirectedGraph,
        origin: AddressModel,
        destination: AddressModel,
        departure_at: datetime,
        traffic_mode: TrafficMode,
        closed_edges: set[uuid.UUID],
        traffic_overrides: dict[uuid.UUID, TrafficLevel],
    ) -> tuple[float, float, list[list[float]]]:
        if origin.id == destination.id:
            return 0.0, 0.0, []
        origin_edge = graph.edge(origin.road_segment_id)
        destination_edge = graph.edge(destination.road_segment_id)
        if origin_edge.id in closed_edges or destination_edge.id in closed_edges:
            raise OptimizationRoutingError("Uma entrega possui acesso viário interditado.")

        origin_node = graph.node(origin_edge.to_node_id)
        destination_node = graph.node(destination_edge.from_node_id)
        origin_fraction = max(0.0, 1.0 - origin.position_on_segment)
        destination_fraction = max(0.0, destination.position_on_segment)
        origin_seconds = self._access_seconds(
            edge=origin_edge,
            fraction=origin_fraction,
            entered_at=departure_at,
            traffic_mode=traffic_mode,
            district_slug=origin_node.district_slug,
            override_level=traffic_overrides.get(origin_edge.id),
        )
        core_departure = departure_at + timedelta(seconds=origin_seconds)
        try:
            core = RoutingEngine(graph).shortest_path(
                origin_node_id=origin_node.id,
                destination_node_id=destination_node.id,
                departure_at=core_departure,
                traffic_mode=traffic_mode,
                closed_edge_ids=closed_edges,
                traffic_overrides=traffic_overrides,
            )
        except NoRouteFoundError as exc:
            raise OptimizationRoutingError(
                f"Não existe caminho dirigido entre {origin.id} e {destination.id}."
            ) from exc
        destination_seconds = self._access_seconds(
            edge=destination_edge,
            fraction=destination_fraction,
            entered_at=core.arrival_at,
            traffic_mode=traffic_mode,
            district_slug=destination_node.district_slug,
            override_level=traffic_overrides.get(destination_edge.id),
        )
        distance_m = (
            origin_edge.length_m * origin_fraction
            + core.distance_m
            + destination_edge.length_m * destination_fraction
        )
        edge_ids = (origin_edge.id, *core.edge_ids, destination_edge.id)
        coordinates: list[list[float]] = []
        for edge_id in dict.fromkeys(edge_ids):
            edge = graph.edge(edge_id)
            self._append_coordinates(
                coordinates,
                [[longitude, latitude] for longitude, latitude in edge.coordinates],
            )
        return (
            distance_m,
            origin_seconds + core.travel_time_seconds + destination_seconds,
            coordinates,
        )

    @staticmethod
    def _append_coordinates(
        target: list[list[float]],
        source: list[list[float]],
    ) -> None:
        if not source:
            return
        if target and target[-1] == source[0]:
            target.extend(source[1:])
        else:
            target.extend(source)

    @staticmethod
    def _access_seconds(
        *,
        edge: GraphEdge,
        fraction: float,
        entered_at: datetime,
        traffic_mode: TrafficMode,
        district_slug: str,
        override_level: TrafficLevel | None,
    ) -> float:
        distance_m = edge.length_m * min(max(fraction, 0.0), 1.0)
        base_seconds = distance_m / (edge.speed_limit_kmh * 1000 / 3600)
        factor = TrafficModel.factor(
            mode=traffic_mode,
            entered_at=entered_at,
            road_class=edge.road_class,
            district_slug=district_slug,
            override_level=override_level,
        )
        return base_seconds * factor

    def _graph(self, city_id: uuid.UUID) -> DirectedGraph:
        node_rows = self._session.execute(
            select(
                IntersectionModel.id,
                DistrictModel.slug,
                func.ST_X(IntersectionModel.geometry),
                func.ST_Y(IntersectionModel.geometry),
            )
            .join(DistrictModel, DistrictModel.id == IntersectionModel.district_id)
            .where(IntersectionModel.city_id == city_id)
        ).all()
        nodes = [
            GraphNode(
                id=node_id,
                district_slug=district_slug,
                longitude=float(longitude),
                latitude=float(latitude),
            )
            for node_id, district_slug, longitude, latitude in node_rows
        ]
        edge_rows = self._session.execute(
            select(
                RoadSegmentModel,
                StreetModel.name,
                func.ST_AsGeoJSON(RoadSegmentModel.geometry),
            )
            .join(StreetModel, StreetModel.id == RoadSegmentModel.street_id)
            .where(RoadSegmentModel.city_id == city_id, RoadSegmentModel.active.is_(True))
        ).all()
        edges: list[GraphEdge] = []
        for segment, street_name, geometry_json in edge_rows:
            geometry = json.loads(geometry_json)
            coordinates = tuple(
                (float(point[0]), float(point[1])) for point in geometry.get("coordinates", [])
            )
            edges.append(
                GraphEdge(
                    id=segment.id,
                    from_node_id=segment.from_intersection_id,
                    to_node_id=segment.to_intersection_id,
                    length_m=float(segment.length_m),
                    speed_limit_kmh=segment.speed_limit_kmh,
                    road_class=segment.road_class,
                    street_name=street_name,
                    coordinates=coordinates,
                    is_bridge=segment.is_bridge,
                    bridge_name=segment.bridge_name,
                )
            )
        return DirectedGraph(nodes, edges)

    def _depot_address(self, city_id: uuid.UUID) -> AddressModel:
        address = self._session.scalar(
            select(AddressModel)
            .join(FacilityModel, FacilityModel.address_id == AddressModel.id)
            .where(
                FacilityModel.city_id == city_id,
                FacilityModel.facility_type == FacilityType.DEPOT,
                FacilityModel.active.is_(True),
                AddressModel.active.is_(True),
            )
            .limit(1)
        )
        if address is None:
            raise OptimizationRoutingError("O depósito não possui endereço roteável.")
        return address

    def _effective_overrides(
        self, operation_id: uuid.UUID
    ) -> tuple[set[uuid.UUID], dict[uuid.UUID, TrafficLevel]]:
        rows = list(
            self._session.scalars(
                select(RoadOverrideModel).where(RoadOverrideModel.operation_id == operation_id)
            )
        )
        closures = {
            item.road_segment_id for item in rows if item.override_type is RoadOverrideType.CLOSURE
        }
        traffic = {
            item.road_segment_id: item.traffic_level
            for item in rows
            if item.override_type is RoadOverrideType.TRAFFIC and item.traffic_level is not None
        }
        return closures, traffic
