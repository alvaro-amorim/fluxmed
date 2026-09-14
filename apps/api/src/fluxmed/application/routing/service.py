import json
import uuid
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from threading import RLock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.domain.enums import (
    FacilityType,
    OperationStatus,
    RoadOverrideDirectionScope,
    RoadOverrideType,
    RoutingAlgorithm,
    TrafficLevel,
    TrafficMode,
)
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
from fluxmed.routing import DirectedGraph, GraphEdge, GraphNode, NoRouteFoundError, RoutingEngine
from fluxmed.routing.traffic import TrafficModel, time_bucket

CITY_NAME = "Santa Aurora"
MAX_ROUTE_CACHE_ENTRIES = 2048


class RoutingOperationNotFoundError(LookupError):
    pass


class RoutingAddressNotFoundError(LookupError):
    pass


class RoutingUnavailableError(LookupError):
    pass


class RoadOverrideNotFoundError(LookupError):
    pass


class RoadOverrideConflictError(ValueError):
    pass


class InvalidRoadOverrideError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RoadOverrideView:
    id: uuid.UUID
    operation_id: uuid.UUID
    road_segment_id: uuid.UUID
    street_name: str
    override_type: RoadOverrideType
    direction_scope: RoadOverrideDirectionScope
    traffic_level: TrafficLevel | None
    reason: str
    notes: str | None
    is_bridge: bool
    bridge_name: str | None


@dataclass(frozen=True, slots=True)
class RoutePreview:
    operation_id: uuid.UUID
    destination_address_id: uuid.UUID
    algorithm: RoutingAlgorithm
    traffic_mode: TrafficMode
    departure_at: datetime
    arrival_at: datetime
    distance_m: float
    travel_time_seconds: float
    time_bucket: str
    edge_ids: tuple[uuid.UUID, ...]
    geometry: dict[str, object]
    cache_hit: bool = False


_graph_cache: dict[tuple[uuid.UUID, str, str], DirectedGraph] = {}
_route_cache: OrderedDict[tuple[object, ...], RoutePreview] = OrderedDict()
_cache_lock = RLock()


def clear_routing_caches() -> None:
    with _cache_lock:
        _graph_cache.clear()
        _route_cache.clear()


class RoutingService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def preview_depot_to_address(
        self,
        *,
        operation_id: uuid.UUID,
        destination_address_id: uuid.UUID,
        departure_time: time | None = None,
        algorithm: RoutingAlgorithm = RoutingAlgorithm.ASTAR,
    ) -> RoutePreview:
        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise RoutingOperationNotFoundError(operation_id)
        city = self._require_city()
        destination = self._require_address(city.id, destination_address_id)
        depot = self._depot_address(city.id)

        departure_at = datetime.combine(
            operation.operation_date,
            departure_time or operation.operation_start_time,
        )
        graph = self._graph(city)
        depot_edge = graph.edge(depot.road_segment_id)
        destination_edge = graph.edge(destination.road_segment_id)
        closed_edges, traffic_overrides, override_fingerprint = self._effective_overrides(
            operation_id
        )

        if depot_edge.id in closed_edges:
            raise RoutingUnavailableError("O acesso viário do depósito está interditado.")
        if destination_edge.id in closed_edges:
            raise RoutingUnavailableError("O acesso viário do destino está interditado.")

        origin_node = graph.node(depot_edge.to_node_id)
        destination_node = graph.node(destination_edge.from_node_id)
        bucket = time_bucket(departure_at)
        cache_key = (
            city.id,
            city.dataset_version,
            city.generator_version,
            operation_id,
            destination.id,
            algorithm.value,
            operation.traffic_mode.value,
            departure_at.replace(second=0, microsecond=0).isoformat(),
            bucket.label,
            override_fingerprint,
        )
        cached = self._cache_get(cache_key)
        if cached is not None:
            return replace(cached, cache_hit=True)

        origin_access_seconds = self._access_seconds(
            edge=depot_edge,
            fraction=max(0.0, 1.0 - depot.position_on_segment),
            entered_at=departure_at,
            traffic_mode=operation.traffic_mode,
            district_slug=origin_node.district_slug,
            override_level=traffic_overrides.get(depot_edge.id),
        )
        origin_access_m = depot_edge.length_m * max(0.0, 1.0 - depot.position_on_segment)
        core_departure = departure_at + timedelta(seconds=origin_access_seconds)

        try:
            core = RoutingEngine(graph).shortest_path(
                origin_node_id=origin_node.id,
                destination_node_id=destination_node.id,
                departure_at=core_departure,
                traffic_mode=operation.traffic_mode,
                algorithm=algorithm,
                closed_edge_ids=closed_edges,
                traffic_overrides=traffic_overrides,
            )
        except NoRouteFoundError as exc:
            raise RoutingUnavailableError(
                "Não existe caminho viário para o destino selecionado."
            ) from exc

        destination_access_seconds = self._access_seconds(
            edge=destination_edge,
            fraction=max(0.0, destination.position_on_segment),
            entered_at=core.arrival_at,
            traffic_mode=operation.traffic_mode,
            district_slug=destination_node.district_slug,
            override_level=traffic_overrides.get(destination_edge.id),
        )
        destination_access_m = destination_edge.length_m * max(0.0, destination.position_on_segment)
        total_seconds = (
            origin_access_seconds + core.travel_time_seconds + destination_access_seconds
        )
        total_distance = origin_access_m + core.distance_m + destination_access_m
        geometry = self._preview_geometry(city, destination, core.geometry)

        edge_ids = tuple(dict.fromkeys((depot_edge.id, *core.edge_ids, destination_edge.id)))
        result = RoutePreview(
            operation_id=operation.id,
            destination_address_id=destination.id,
            algorithm=algorithm,
            traffic_mode=operation.traffic_mode,
            departure_at=departure_at,
            arrival_at=departure_at + timedelta(seconds=total_seconds),
            distance_m=total_distance,
            travel_time_seconds=total_seconds,
            time_bucket=bucket.label,
            edge_ids=edge_ids,
            geometry=geometry,
        )
        self._cache_put(cache_key, result)
        return result

    def _require_city(self) -> CityModel:
        city = self._session.scalar(select(CityModel).where(CityModel.name == CITY_NAME))
        if city is None:
            raise RoutingUnavailableError("Santa Aurora ainda não foi gerada.")
        return city

    def _require_address(self, city_id: uuid.UUID, address_id: uuid.UUID) -> AddressModel:
        address = self._session.get(AddressModel, address_id)
        if address is None or not address.active or address.city_id != city_id:
            raise RoutingAddressNotFoundError(address_id)
        return address

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
            raise RoutingUnavailableError("O depósito não possui endereço roteável.")
        return address

    def _graph(self, city: CityModel) -> DirectedGraph:
        key = (city.id, city.dataset_version, city.generator_version)
        with _cache_lock:
            cached = _graph_cache.get(key)
        if cached is not None:
            return cached

        node_rows = self._session.execute(
            select(
                IntersectionModel.id,
                DistrictModel.slug,
                func.ST_X(IntersectionModel.geometry),
                func.ST_Y(IntersectionModel.geometry),
            )
            .join(DistrictModel, DistrictModel.id == IntersectionModel.district_id)
            .where(IntersectionModel.city_id == city.id)
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
            .where(RoadSegmentModel.city_id == city.id, RoadSegmentModel.active.is_(True))
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
        graph = DirectedGraph(nodes, edges)
        with _cache_lock:
            _graph_cache[key] = graph
        return graph

    def _effective_overrides(
        self, operation_id: uuid.UUID
    ) -> tuple[set[uuid.UUID], dict[uuid.UUID, TrafficLevel], tuple[tuple[str, str, str], ...]]:
        rows = list(
            self._session.scalars(
                select(RoadOverrideModel)
                .where(RoadOverrideModel.operation_id == operation_id)
                .order_by(RoadOverrideModel.road_segment_id, RoadOverrideModel.override_type)
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
        fingerprint = tuple(
            (
                str(item.road_segment_id),
                item.override_type.value,
                item.traffic_level.value if item.traffic_level is not None else "",
            )
            for item in rows
        )
        return closures, traffic, fingerprint

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

    def _preview_geometry(
        self,
        city: CityModel,
        destination: AddressModel,
        core_geometry: dict[str, object],
    ) -> dict[str, object]:
        depot_lng, depot_lat, destination_lng, destination_lat = self._session.execute(
            select(
                func.ST_X(CityModel.depot_geometry),
                func.ST_Y(CityModel.depot_geometry),
                func.ST_X(AddressModel.location),
                func.ST_Y(AddressModel.location),
            )
            .select_from(CityModel)
            .join(AddressModel, AddressModel.id == destination.id)
            .where(CityModel.id == city.id)
        ).one()

        core_coordinates = core_geometry.get("coordinates", [])
        coordinates: list[list[float]] = [[float(depot_lng), float(depot_lat)]]
        if isinstance(core_coordinates, list):
            for item in core_coordinates:
                if isinstance(item, list) and len(item) >= 2:
                    point = [float(item[0]), float(item[1])]
                    if coordinates[-1] != point:
                        coordinates.append(point)
        destination_point = [float(destination_lng), float(destination_lat)]
        if coordinates[-1] != destination_point:
            coordinates.append(destination_point)
        return {"type": "LineString", "coordinates": coordinates}

    @staticmethod
    def _cache_get(key: tuple[object, ...]) -> RoutePreview | None:
        with _cache_lock:
            value = _route_cache.get(key)
            if value is None:
                return None
            _route_cache.move_to_end(key)
            return value

    @staticmethod
    def _cache_put(key: tuple[object, ...], value: RoutePreview) -> None:
        with _cache_lock:
            _route_cache[key] = value
            _route_cache.move_to_end(key)
            while len(_route_cache) > MAX_ROUTE_CACHE_ENTRIES:
                _route_cache.popitem(last=False)


class RoadOverrideService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, operation_id: uuid.UUID) -> list[RoadOverrideView]:
        self._require_operation(operation_id)
        rows = self._session.execute(
            select(RoadOverrideModel, RoadSegmentModel, StreetModel.name)
            .join(RoadSegmentModel, RoadSegmentModel.id == RoadOverrideModel.road_segment_id)
            .join(StreetModel, StreetModel.id == RoadSegmentModel.street_id)
            .where(RoadOverrideModel.operation_id == operation_id)
            .order_by(StreetModel.name, RoadOverrideModel.created_at)
        ).all()
        return [self._view(model, segment, street_name) for model, segment, street_name in rows]

    def create(
        self,
        *,
        operation_id: uuid.UUID,
        road_segment_id: uuid.UUID,
        override_type: RoadOverrideType,
        direction_scope: RoadOverrideDirectionScope,
        traffic_level: TrafficLevel | None,
        reason: str,
        notes: str | None,
    ) -> RoadOverrideView:
        operation = self._require_operation(operation_id)
        self._assert_mutable(operation)
        segment = self._require_segment(road_segment_id)
        self._validate_override(override_type, traffic_level)
        existing = self._session.scalar(
            select(RoadOverrideModel).where(
                RoadOverrideModel.operation_id == operation_id,
                RoadOverrideModel.road_segment_id == road_segment_id,
                RoadOverrideModel.override_type == override_type,
            )
        )
        if existing is not None:
            raise RoadOverrideConflictError(
                "Já existe um override deste tipo para o segmento selecionado."
            )
        model = RoadOverrideModel(
            operation_id=operation_id,
            road_segment_id=road_segment_id,
            override_type=override_type,
            direction_scope=direction_scope,
            traffic_level=traffic_level,
            reason=reason.strip(),
            notes=notes.strip() if notes else None,
        )
        if not model.reason:
            raise InvalidRoadOverrideError("Informe o motivo do override.")
        self._session.add(model)
        self._mark_operation_changed(operation)
        self._session.flush()
        street_name = self._session.scalar(
            select(StreetModel.name).where(StreetModel.id == segment.street_id)
        )
        self._invalidate_operation_cache(operation_id)
        return self._view(model, segment, street_name or "Via sem nome")

    def update(
        self,
        *,
        operation_id: uuid.UUID,
        override_id: uuid.UUID,
        traffic_level: TrafficLevel | None,
        reason: str | None,
        notes: str | None,
    ) -> RoadOverrideView:
        operation = self._require_operation(operation_id)
        self._assert_mutable(operation)
        model = self._require_override(operation_id, override_id)
        if traffic_level is not None:
            if model.override_type is not RoadOverrideType.TRAFFIC:
                raise InvalidRoadOverrideError("Closure não aceita nível de trânsito.")
            model.traffic_level = traffic_level
        if reason is not None:
            cleaned = reason.strip()
            if not cleaned:
                raise InvalidRoadOverrideError("Informe o motivo do override.")
            model.reason = cleaned
        if notes is not None:
            model.notes = notes.strip() or None
        self._validate_override(model.override_type, model.traffic_level)
        self._mark_operation_changed(operation)
        self._session.flush()
        segment = self._require_segment(model.road_segment_id)
        street_name = self._session.scalar(
            select(StreetModel.name).where(StreetModel.id == segment.street_id)
        )
        self._invalidate_operation_cache(operation_id)
        return self._view(model, segment, street_name or "Via sem nome")

    def delete(self, operation_id: uuid.UUID, override_id: uuid.UUID) -> None:
        operation = self._require_operation(operation_id)
        self._assert_mutable(operation)
        model = self._require_override(operation_id, override_id)
        self._session.delete(model)
        self._mark_operation_changed(operation)
        self._session.flush()
        self._invalidate_operation_cache(operation_id)

    def _require_operation(self, operation_id: uuid.UUID) -> OperationModel:
        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise RoutingOperationNotFoundError(operation_id)
        return operation

    def _require_segment(self, road_segment_id: uuid.UUID) -> RoadSegmentModel:
        segment = self._session.get(RoadSegmentModel, road_segment_id)
        if segment is None or not segment.active:
            raise InvalidRoadOverrideError("Segmento viário não encontrado ou inativo.")
        city_id = self._session.scalar(select(CityModel.id).where(CityModel.name == CITY_NAME))
        if city_id is None or segment.city_id != city_id:
            raise InvalidRoadOverrideError("Segmento não pertence à cidade da operação.")
        return segment

    def _require_override(
        self, operation_id: uuid.UUID, override_id: uuid.UUID
    ) -> RoadOverrideModel:
        model = self._session.scalar(
            select(RoadOverrideModel).where(
                RoadOverrideModel.id == override_id,
                RoadOverrideModel.operation_id == operation_id,
            )
        )
        if model is None:
            raise RoadOverrideNotFoundError(override_id)
        return model

    @staticmethod
    def _validate_override(
        override_type: RoadOverrideType, traffic_level: TrafficLevel | None
    ) -> None:
        if override_type is RoadOverrideType.TRAFFIC and traffic_level is None:
            raise InvalidRoadOverrideError("Traffic override exige traffic_level.")
        if override_type is RoadOverrideType.CLOSURE and traffic_level is not None:
            raise InvalidRoadOverrideError("Closure não aceita traffic_level.")

    @staticmethod
    def _assert_mutable(operation: OperationModel) -> None:
        if operation.status is OperationStatus.DISPATCHED:
            raise InvalidRoadOverrideError("Operação despachada não aceita alterações viárias.")

    @staticmethod
    def _mark_operation_changed(operation: OperationModel) -> None:
        if operation.status in {OperationStatus.OPTIMIZED, OperationStatus.APPROVED}:
            operation.status = OperationStatus.OUTDATED
        elif operation.status is OperationStatus.READY:
            operation.status = OperationStatus.DRAFT

    @staticmethod
    def _view(
        model: RoadOverrideModel,
        segment: RoadSegmentModel,
        street_name: str,
    ) -> RoadOverrideView:
        return RoadOverrideView(
            id=model.id,
            operation_id=model.operation_id,
            road_segment_id=model.road_segment_id,
            street_name=street_name,
            override_type=model.override_type,
            direction_scope=model.direction_scope,
            traffic_level=model.traffic_level,
            reason=model.reason,
            notes=model.notes,
            is_bridge=segment.is_bridge,
            bridge_name=segment.bridge_name,
        )

    @staticmethod
    def _invalidate_operation_cache(operation_id: uuid.UUID) -> None:
        with _cache_lock:
            keys = [key for key in _route_cache if operation_id in key]
            for key in keys:
                _route_cache.pop(key, None)
