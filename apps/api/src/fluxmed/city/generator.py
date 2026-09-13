import math
import uuid
from dataclasses import dataclass

from fluxmed.domain.enums import RoadClass

DEFAULT_SEED = 20260913
DATASET_VERSION = "1.0.0"
GENERATOR_VERSION = "santa-aurora-v1"
CENTER_LON = -46.6200
CENTER_LAT = -22.4000
_NAMESPACE = uuid.UUID("b168c345-7c0b-4d2c-a1f2-936f0a1f67a0")

Coordinate = tuple[float, float]


@dataclass(frozen=True)
class GeneratedDistrict:
    id: uuid.UUID
    name: str
    slug: str
    polygon: tuple[Coordinate, ...]


@dataclass(frozen=True)
class GeneratedIntersection:
    id: uuid.UUID
    code: str
    district_slug: str
    point: Coordinate


@dataclass(frozen=True)
class GeneratedStreet:
    id: uuid.UUID
    key: str
    name: str
    road_class: RoadClass


@dataclass(frozen=True)
class GeneratedRoadSegment:
    id: uuid.UUID
    street_id: uuid.UUID
    from_intersection_id: uuid.UUID
    to_intersection_id: uuid.UUID
    coordinates: tuple[Coordinate, Coordinate]
    length_m: float
    speed_limit_kmh: int
    road_class: RoadClass
    lanes: int
    is_bridge: bool
    bridge_name: str | None


@dataclass(frozen=True)
class GeneratedCity:
    id: uuid.UUID
    name: str
    country: str
    source_type: str
    timezone: str
    dataset_version: str
    generation_seed: int
    generator_version: str
    boundary: tuple[Coordinate, ...]
    river: tuple[Coordinate, ...]
    depot_name: str
    depot_point: Coordinate
    districts: tuple[GeneratedDistrict, ...]
    intersections: tuple[GeneratedIntersection, ...]
    streets: tuple[GeneratedStreet, ...]
    road_segments: tuple[GeneratedRoadSegment, ...]


def _stable_id(dataset_version: str, seed: int, kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{dataset_version}:{seed}:{kind}:{key}")


def _absolute(point: Coordinate) -> Coordinate:
    return (round(CENTER_LON + point[0], 7), round(CENTER_LAT + point[1], 7))


def _haversine_m(a: Coordinate, b: Coordinate) -> float:
    radius_m = 6_371_000.0
    lat1 = math.radians(a[1])
    lat2 = math.radians(b[1])
    delta_lat = math.radians(b[1] - a[1])
    delta_lon = math.radians(b[0] - a[0])
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return round(radius_m * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value)), 2)


def _speed_for(road_class: RoadClass) -> int:
    return {
        RoadClass.EXPRESSWAY: 80,
        RoadClass.ARTERIAL: 60,
        RoadClass.COLLECTOR: 40,
        RoadClass.LOCAL: 30,
        RoadClass.SERVICE: 20,
    }[road_class]


def _lanes_for(road_class: RoadClass) -> int:
    return 2 if road_class in {RoadClass.EXPRESSWAY, RoadClass.ARTERIAL} else 1


def _district_slug(x: float, y: float) -> str:
    if y >= 0.014:
        if x < -0.018:
            return "vale-verde"
        if x <= 0.018:
            return "parque-universitario"
        return "nova-esperanca"
    if y >= -0.014:
        if x < -0.018:
            return "vila-aurora"
        if x <= 0.018:
            return "centro-historico"
        return "santa-cecilia"
    if x < -0.018:
        return "jardim-das-flores"
    if x <= 0.018:
        return "distrito-industrial"
    return "distrito-logistico"


def build_santa_aurora(
    *, seed: int = DEFAULT_SEED, dataset_version: str = DATASET_VERSION
) -> GeneratedCity:
    """Build the deterministic Phase 5 Santa Aurora road graph in memory."""
    city_id = _stable_id(dataset_version, seed, "city", "santa-aurora")
    district_specs = (
        ("Vale Verde", "vale-verde", -0.055, -0.018, 0.014, 0.042),
        ("Parque Universitário", "parque-universitario", -0.018, 0.018, 0.014, 0.042),
        ("Nova Esperança", "nova-esperanca", 0.018, 0.055, 0.014, 0.042),
        ("Vila Aurora", "vila-aurora", -0.055, -0.018, -0.014, 0.014),
        ("Centro Histórico", "centro-historico", -0.018, 0.018, -0.014, 0.014),
        ("Santa Cecília", "santa-cecilia", 0.018, 0.055, -0.014, 0.014),
        ("Jardim das Flores", "jardim-das-flores", -0.055, -0.018, -0.042, -0.014),
        ("Distrito Industrial", "distrito-industrial", -0.018, 0.018, -0.042, -0.014),
        ("Distrito Logístico", "distrito-logistico", 0.018, 0.055, -0.042, -0.014),
    )
    districts: list[GeneratedDistrict] = []
    for name, slug, xmin, xmax, ymin, ymax in district_specs:
        polygon = tuple(
            _absolute(point)
            for point in ((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin))
        )
        districts.append(
            GeneratedDistrict(
                id=_stable_id(dataset_version, seed, "district", slug),
                name=name,
                slug=slug,
                polygon=polygon,
            )
        )

    x_values = (-0.050, -0.034, -0.018, -0.006, 0.006, 0.018, 0.034, 0.050)
    y_values = (-0.036, -0.024, -0.012, 0.000, 0.012, 0.024, 0.036)
    intersections: list[GeneratedIntersection] = []
    intersection_by_grid: dict[tuple[int, int], GeneratedIntersection] = {}
    for y_index, y in enumerate(y_values):
        for x_index, x in enumerate(x_values):
            code = f"INT-{y_index + 1:02d}-{x_index + 1:02d}"
            intersection = GeneratedIntersection(
                id=_stable_id(dataset_version, seed, "intersection", code),
                code=code,
                district_slug=_district_slug(x, y),
                point=_absolute((x, y)),
            )
            intersections.append(intersection)
            intersection_by_grid[(x_index, y_index)] = intersection

    streets: dict[str, GeneratedStreet] = {}

    def street(key: str, name: str, road_class: RoadClass) -> GeneratedStreet:
        if key not in streets:
            streets[key] = GeneratedStreet(
                id=_stable_id(dataset_version, seed, "street", key),
                key=key,
                name=name,
                road_class=road_class,
            )
        return streets[key]

    ring = street("ring", "Anel Viário de Santa Aurora", RoadClass.EXPRESSWAY)
    vertical_specs = {
        1: ("oeste", "Avenida Horizonte", RoadClass.COLLECTOR),
        2: ("republica", "Avenida República", RoadClass.ARTERIAL),
        3: ("mercado", "Rua do Mercado", RoadClass.COLLECTOR),
        4: ("santa-aurora", "Avenida Santa Aurora", RoadClass.ARTERIAL),
        5: ("central", "Avenida Central", RoadClass.ARTERIAL),
        6: ("progresso", "Avenida Progresso", RoadClass.COLLECTOR),
    }
    horizontal_left = {
        1: ("flores", "Rua das Flores", RoadClass.LOCAL),
        2: ("aurora-oeste", "Rua Aurora Oeste", RoadClass.COLLECTOR),
        4: ("universidade-oeste", "Avenida do Conhecimento", RoadClass.COLLECTOR),
        5: ("vale", "Rua do Vale", RoadClass.LOCAL),
    }
    horizontal_right = {
        1: ("logistica", "Avenida da Logística", RoadClass.COLLECTOR),
        2: ("cecilia", "Rua Santa Cecília", RoadClass.COLLECTOR),
        4: ("esperanca", "Avenida Nova Esperança", RoadClass.COLLECTOR),
        5: ("universidade-leste", "Rua dos Laboratórios", RoadClass.LOCAL),
    }
    integration = street("integracao", "Avenida da Integração", RoadClass.ARTERIAL)

    road_segments: list[GeneratedRoadSegment] = []

    def add_directed(
        *,
        road: GeneratedStreet,
        start: GeneratedIntersection,
        end: GeneratedIntersection,
        key: str,
        bridge_name: str | None = None,
    ) -> None:
        road_segments.append(
            GeneratedRoadSegment(
                id=_stable_id(dataset_version, seed, "segment", key),
                street_id=road.id,
                from_intersection_id=start.id,
                to_intersection_id=end.id,
                coordinates=(start.point, end.point),
                length_m=_haversine_m(start.point, end.point),
                speed_limit_kmh=_speed_for(road.road_class),
                road_class=road.road_class,
                lanes=_lanes_for(road.road_class),
                is_bridge=bridge_name is not None,
                bridge_name=bridge_name,
            )
        )

    def add_two_way(
        *,
        road: GeneratedStreet,
        a: GeneratedIntersection,
        b: GeneratedIntersection,
        key: str,
        bridge_name: str | None = None,
    ) -> None:
        add_directed(road=road, start=a, end=b, key=f"{key}:forward", bridge_name=bridge_name)
        add_directed(road=road, start=b, end=a, key=f"{key}:reverse", bridge_name=bridge_name)

    for x_index in range(len(x_values)):
        if x_index in {0, len(x_values) - 1}:
            road = ring
        else:
            key, name, road_class = vertical_specs[x_index]
            road = street(key, name, road_class)
        for y_index in range(len(y_values) - 1):
            add_two_way(
                road=road,
                a=intersection_by_grid[(x_index, y_index)],
                b=intersection_by_grid[(x_index, y_index + 1)],
                key=f"vertical:{x_index}:{y_index}",
            )

    bridge_names = {0: "Ponte Sul", 3: "Ponte Central", 6: "Ponte Norte"}
    for y_index in range(len(y_values)):
        for x_index in range(len(x_values) - 1):
            crosses_river = x_index == 3
            if crosses_river and y_index not in bridge_names:
                continue
            if y_index in {0, len(y_values) - 1}:
                road = ring
            elif y_index == 3:
                road = integration
            elif x_index < 3:
                key, name, road_class = horizontal_left[y_index]
                road = street(key, name, road_class)
            else:
                key, name, road_class = horizontal_right[y_index]
                road = street(key, name, road_class)
            add_two_way(
                road=road,
                a=intersection_by_grid[(x_index, y_index)],
                b=intersection_by_grid[(x_index + 1, y_index)],
                key=f"horizontal:{y_index}:{x_index}",
                bridge_name=bridge_names.get(y_index) if crosses_river else None,
            )

    boundary = tuple(
        _absolute(point)
        for point in (
            (-0.055, -0.042),
            (0.055, -0.042),
            (0.055, 0.042),
            (-0.055, 0.042),
            (-0.055, -0.042),
        )
    )
    river = tuple(
        _absolute(point)
        for point in (
            (-0.0010, -0.042),
            (0.0010, -0.021),
            (-0.0005, 0.000),
            (0.0015, 0.021),
            (0.0000, 0.042),
        )
    )
    depot_point = intersection_by_grid[(6, 1)].point

    return GeneratedCity(
        id=city_id,
        name="Santa Aurora",
        country="Brazil",
        source_type="SYNTHETIC",
        timezone="America/Sao_Paulo",
        dataset_version=dataset_version,
        generation_seed=seed,
        generator_version=GENERATOR_VERSION,
        boundary=boundary,
        river=river,
        depot_name="Centro de Distribuição FluxMed",
        depot_point=depot_point,
        districts=tuple(districts),
        intersections=tuple(intersections),
        streets=tuple(streets.values()),
        road_segments=tuple(road_segments),
    )
