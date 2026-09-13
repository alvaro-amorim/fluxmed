import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, replace

from fluxmed.city.naming import StreetNameRequest, StreetNamingService
from fluxmed.domain.enums import BuildingType, FacilityType, LotStatus, RoadClass

DEFAULT_SEED = 20260913
DATASET_VERSION = "1.1.0"
GENERATOR_VERSION = "santa-aurora-v2"
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
class GeneratedLot:
    id: uuid.UUID
    district_slug: str
    road_segment_id: uuid.UUID
    position_on_segment: float
    status: LotStatus
    location: Coordinate


@dataclass(frozen=True)
class GeneratedBuilding:
    id: uuid.UUID
    lot_id: uuid.UUID
    district_slug: str
    building_type: BuildingType
    entrance_location: Coordinate


@dataclass(frozen=True)
class GeneratedAddress:
    id: uuid.UUID
    street_id: uuid.UUID
    district_slug: str
    building_id: uuid.UUID
    road_segment_id: uuid.UUID
    house_number: str
    house_number_numeric: int
    suffix: str | None
    complement: str | None
    position_on_segment: float
    location: Coordinate


@dataclass(frozen=True)
class GeneratedFacility:
    id: uuid.UUID
    address_id: uuid.UUID
    building_id: uuid.UUID
    name: str
    facility_type: FacilityType


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
    lots: tuple[GeneratedLot, ...]
    buildings: tuple[GeneratedBuilding, ...]
    addresses: tuple[GeneratedAddress, ...]
    facilities: tuple[GeneratedFacility, ...]


def _stable_id(dataset_version: str, seed: int, kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{dataset_version}:{seed}:{kind}:{key}")


def _stable_score(dataset_version: str, seed: int, kind: str, key: str) -> float:
    value = _stable_id(dataset_version, seed, kind, key).int & 0xFFFFFFFF
    return value / 0xFFFFFFFF


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
    if road_class == RoadClass.EXPRESSWAY:
        return 2
    if road_class == RoadClass.ARTERIAL:
        return 2
    return 1


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


def _road_class_for_local(orientation: str, index: int, district_slug: str) -> RoadClass:
    if orientation == "vertical":
        base = RoadClass.COLLECTOR if index % 5 == 0 else RoadClass.LOCAL
    else:
        base = RoadClass.COLLECTOR if index % 6 == 0 else RoadClass.LOCAL
    if district_slug in {"distrito-industrial", "distrito-logistico"} and base == RoadClass.LOCAL:
        return RoadClass.SERVICE
    return base


def _interpolate_offset(
    start: Coordinate,
    end: Coordinate,
    position: float,
    side: int,
    offset_degrees: float = 0.000055,
) -> Coordinate:
    lon = start[0] + (end[0] - start[0]) * position
    lat = start[1] + (end[1] - start[1]) * position
    delta_lon = end[0] - start[0]
    delta_lat = end[1] - start[1]
    norm = math.hypot(delta_lon, delta_lat) or 1.0
    lon += (-delta_lat / norm) * offset_degrees * side
    lat += (delta_lon / norm) * offset_degrees * side
    return (round(lon, 7), round(lat, 7))


def _building_type(district_slug: str, score: float) -> BuildingType:
    if district_slug == "distrito-logistico":
        return BuildingType.WAREHOUSE if score < 0.72 else BuildingType.COMMERCIAL
    if district_slug == "distrito-industrial":
        if score < 0.58:
            return BuildingType.WAREHOUSE
        if score < 0.90:
            return BuildingType.COMMERCIAL
        return BuildingType.OTHER
    if district_slug == "centro-historico":
        if score < 0.42:
            return BuildingType.APARTMENT_BUILDING
        if score < 0.78:
            return BuildingType.COMMERCIAL
        return BuildingType.HOUSE
    if district_slug == "santa-cecilia":
        if score < 0.35:
            return BuildingType.APARTMENT_BUILDING
        if score < 0.62:
            return BuildingType.COMMERCIAL
        return BuildingType.HOUSE
    if district_slug == "parque-universitario":
        if score < 0.28:
            return BuildingType.APARTMENT_BUILDING
        if score < 0.55:
            return BuildingType.COMMERCIAL
        if score < 0.68:
            return BuildingType.SCHOOL
        return BuildingType.HOUSE
    if district_slug == "nova-esperanca":
        if score < 0.20:
            return BuildingType.APARTMENT_BUILDING
        if score < 0.34:
            return BuildingType.COMMERCIAL
        return BuildingType.HOUSE
    if district_slug == "vale-verde":
        return BuildingType.HOUSE if score < 0.90 else BuildingType.OTHER
    if district_slug == "jardim-das-flores":
        return BuildingType.HOUSE if score < 0.88 else BuildingType.APARTMENT_BUILDING
    if district_slug == "vila-aurora":
        if score < 0.18:
            return BuildingType.COMMERCIAL
        if score < 0.28:
            return BuildingType.APARTMENT_BUILDING
        return BuildingType.HOUSE
    return BuildingType.OTHER


def _facility_building_type(facility_type: FacilityType) -> BuildingType:
    return {
        FacilityType.DEPOT: BuildingType.WAREHOUSE,
        FacilityType.HOSPITAL: BuildingType.HOSPITAL,
        FacilityType.CLINIC: BuildingType.CLINIC,
        FacilityType.LABORATORY: BuildingType.LABORATORY,
        FacilityType.PHARMACY: BuildingType.PHARMACY,
        FacilityType.WAREHOUSE: BuildingType.WAREHOUSE,
        FacilityType.PUBLIC_FACILITY: BuildingType.PUBLIC_BUILDING,
    }[facility_type]


def build_santa_aurora(
    *, seed: int = DEFAULT_SEED, dataset_version: str = DATASET_VERSION
) -> GeneratedCity:
    """Build the deterministic complete Santa Aurora city dataset in memory."""
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

    x_values = tuple(-0.052 + index * (0.104 / 23) for index in range(24))
    y_values = tuple(-0.040 + index * (0.080 / 31) for index in range(32))
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

    naming = StreetNamingService()
    global_names = {
        key: naming.reserve_global(key)
        for key in (
            "ring",
            "santa-aurora",
            "integracao",
            "republica",
            "central",
            "universidade",
            "logistica",
        )
    }
    streets: dict[str, GeneratedStreet] = {}
    district_name_ordinals: defaultdict[str, int] = defaultdict(int)

    def street(
        key: str,
        road_class: RoadClass,
        district_slug: str,
        *,
        global_key: str | None = None,
    ) -> GeneratedStreet:
        existing = streets.get(key)
        if existing is not None:
            return existing
        if global_key is not None:
            name = global_names[global_key]
        else:
            ordinal = district_name_ordinals[district_slug]
            name = naming.name(
                StreetNameRequest(
                    key=key,
                    district_slug=district_slug,
                    road_class=road_class,
                    ordinal=ordinal,
                )
            )
            district_name_ordinals[district_slug] += 1
        generated = GeneratedStreet(
            id=_stable_id(dataset_version, seed, "street", key),
            key=key,
            name=name,
            road_class=road_class,
        )
        streets[key] = generated
        return generated

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

    global_vertical = {
        6: ("republica", RoadClass.ARTERIAL),
        11: ("central", RoadClass.ARTERIAL),
        17: ("santa-aurora", RoadClass.ARTERIAL),
    }
    global_horizontal = {
        5: ("logistica", RoadClass.ARTERIAL),
        15: ("integracao", RoadClass.ARTERIAL),
        26: ("universidade", RoadClass.ARTERIAL),
    }
    bridge_names = {5: "Ponte Sul", 15: "Ponte Central", 26: "Ponte Norte"}

    for x_index, x in enumerate(x_values):
        for y_index in range(len(y_values) - 1):
            y_mid = (y_values[y_index] + y_values[y_index + 1]) / 2
            district_slug = _district_slug(x, y_mid)
            if x_index in {0, len(x_values) - 1}:
                road = street("ring", RoadClass.EXPRESSWAY, district_slug, global_key="ring")
            elif x_index in global_vertical:
                key, road_class = global_vertical[x_index]
                road = street(key, road_class, district_slug, global_key=key)
            else:
                band = 0 if y_index < 10 else 1 if y_index < 21 else 2
                key = f"vertical:{x_index}:{band}"
                road_class = _road_class_for_local("vertical", x_index, district_slug)
                road = street(key, road_class, district_slug)
            add_two_way(
                road=road,
                a=intersection_by_grid[(x_index, y_index)],
                b=intersection_by_grid[(x_index, y_index + 1)],
                key=f"vertical:{x_index}:{y_index}",
            )

    for y_index, y in enumerate(y_values):
        for x_index in range(len(x_values) - 1):
            crosses_river = x_index == 11
            if crosses_river and y_index not in bridge_names:
                continue
            x_mid = (x_values[x_index] + x_values[x_index + 1]) / 2
            district_slug = _district_slug(x_mid, y)
            if y_index in {0, len(y_values) - 1}:
                road = street("ring", RoadClass.EXPRESSWAY, district_slug, global_key="ring")
            elif y_index in global_horizontal:
                key, road_class = global_horizontal[y_index]
                road = street(key, road_class, district_slug, global_key=key)
            else:
                zone = 0 if x_index < 8 else 1 if x_index < 16 else 2
                key = f"horizontal:{y_index}:{zone}"
                road_class = _road_class_for_local("horizontal", y_index, district_slug)
                road = street(key, road_class, district_slug)
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

    lot_count_by_class = {
        RoadClass.EXPRESSWAY: 0,
        RoadClass.ARTERIAL: 14,
        RoadClass.COLLECTOR: 18,
        RoadClass.LOCAL: 22,
        RoadClass.SERVICE: 16,
    }
    vacancy_rate = {
        "centro-historico": 0.04,
        "santa-cecilia": 0.06,
        "parque-universitario": 0.08,
        "nova-esperanca": 0.10,
        "vila-aurora": 0.10,
        "jardim-das-flores": 0.12,
        "vale-verde": 0.22,
        "distrito-industrial": 0.30,
        "distrito-logistico": 0.38,
    }
    lots: list[GeneratedLot] = []
    buildings: list[GeneratedBuilding] = []
    addresses: list[GeneratedAddress] = []
    number_counters: defaultdict[tuple[uuid.UUID, int], int] = defaultdict(int)

    # add_two_way always emits forward then reverse. Addresses are generated only from
    # the forward edge so a physical road frontage is represented once.
    for segment in road_segments[::2]:
        if segment.is_bridge or segment.road_class == RoadClass.EXPRESSWAY:
            continue
        lot_count = lot_count_by_class[segment.road_class]
        for lot_index in range(lot_count):
            position = (lot_index + 1) / (lot_count + 1)
            side = -1 if lot_index % 2 == 0 else 1
            location = _interpolate_offset(
                segment.coordinates[0], segment.coordinates[1], position, side
            )
            district_slug = _district_slug(location[0] - CENTER_LON, location[1] - CENTER_LAT)
            lot_key = f"{segment.id}:{lot_index}"
            occupied_score = _stable_score(dataset_version, seed, "lot-occupancy", lot_key)
            status = (
                LotStatus.VACANT
                if occupied_score < vacancy_rate[district_slug]
                else LotStatus.OCCUPIED
            )
            lot_id = _stable_id(dataset_version, seed, "lot", lot_key)
            lots.append(
                GeneratedLot(
                    id=lot_id,
                    district_slug=district_slug,
                    road_segment_id=segment.id,
                    position_on_segment=position,
                    status=status,
                    location=location,
                )
            )

            counter_key = (segment.street_id, side)
            current = number_counters[counter_key]
            if current == 0:
                current = 1 if side == -1 else 2
            house_number_numeric = current
            gap_score = _stable_score(dataset_version, seed, "number-gap", lot_key)
            number_counters[counter_key] = current + (4 if gap_score < 0.08 else 2)
            if status == LotStatus.VACANT:
                continue

            building_id = _stable_id(dataset_version, seed, "building", lot_key)
            building_score = _stable_score(dataset_version, seed, "building-type", lot_key)
            building_type = _building_type(district_slug, building_score)
            buildings.append(
                GeneratedBuilding(
                    id=building_id,
                    lot_id=lot_id,
                    district_slug=district_slug,
                    building_type=building_type,
                    entrance_location=location,
                )
            )

            suffix_score = _stable_score(dataset_version, seed, "address-suffix", lot_key)
            suffix: str | None = None
            if suffix_score < 0.012:
                suffix = "A"
            elif suffix_score < 0.018:
                suffix = "B"
            house_number = f"{house_number_numeric}{suffix or ''}"
            complement: str | None = None
            if building_type == BuildingType.APARTMENT_BUILDING:
                complement = "Entrada principal"
            address_id = _stable_id(dataset_version, seed, "address", lot_key)
            addresses.append(
                GeneratedAddress(
                    id=address_id,
                    street_id=segment.street_id,
                    district_slug=district_slug,
                    building_id=building_id,
                    road_segment_id=segment.id,
                    house_number=house_number,
                    house_number_numeric=house_number_numeric,
                    suffix=suffix,
                    complement=complement,
                    position_on_segment=position,
                    location=location,
                )
            )

    district_by_address = {address.id: address.district_slug for address in addresses}
    address_by_id = {address.id: address for address in addresses}
    building_index = {building.id: index for index, building in enumerate(buildings)}
    used_address_ids: set[uuid.UUID] = set()
    facilities: list[GeneratedFacility] = []

    def pick_addresses(
        facility_type: FacilityType,
        count: int,
        preferred_districts: tuple[str, ...],
    ) -> list[GeneratedAddress]:
        candidates = [
            address
            for address in addresses
            if address.id not in used_address_ids
            and district_by_address[address.id] in preferred_districts
        ]
        candidates.sort(
            key=lambda address: _stable_score(
                dataset_version,
                seed,
                f"facility-{facility_type.value.lower()}",
                str(address.id),
            )
        )
        chosen = candidates[:count]
        if len(chosen) != count:
            raise RuntimeError(f"Not enough addresses for {facility_type.value}")
        used_address_ids.update(address.id for address in chosen)
        return chosen

    facility_specs = (
        (
            FacilityType.HOSPITAL,
            4,
            ("centro-historico", "parque-universitario", "santa-cecilia", "nova-esperanca"),
        ),
        (
            FacilityType.CLINIC,
            15,
            (
                "centro-historico",
                "parque-universitario",
                "santa-cecilia",
                "nova-esperanca",
                "vila-aurora",
            ),
        ),
        (
            FacilityType.LABORATORY,
            7,
            ("parque-universitario", "centro-historico", "santa-cecilia"),
        ),
        (
            FacilityType.PHARMACY,
            15,
            (
                "centro-historico",
                "parque-universitario",
                "santa-cecilia",
                "nova-esperanca",
                "vila-aurora",
                "jardim-das-flores",
                "vale-verde",
            ),
        ),
        (
            FacilityType.WAREHOUSE,
            4,
            ("distrito-industrial", "distrito-logistico"),
        ),
        (
            FacilityType.PUBLIC_FACILITY,
            3,
            ("centro-historico", "nova-esperanca", "vila-aurora"),
        ),
    )
    facility_names = {
        FacilityType.HOSPITAL: (
            "Hospital Central de Santa Aurora",
            "Hospital Universitário Aurora",
            "Hospital Regional Horizonte",
            "Hospital Nova Esperança",
        ),
        FacilityType.CLINIC: tuple(f"Clínica Aurora {index:02d}" for index in range(1, 16)),
        FacilityType.LABORATORY: tuple(
            f"Laboratório Santa Aurora {index:02d}" for index in range(1, 8)
        ),
        FacilityType.PHARMACY: tuple(f"Farmácia Vida {index:02d}" for index in range(1, 16)),
        FacilityType.WAREHOUSE: tuple(
            f"Centro Logístico Médico {index:02d}" for index in range(1, 5)
        ),
        FacilityType.PUBLIC_FACILITY: (
            "Unidade Municipal de Saúde Aurora",
            "Centro Público de Atendimento Esperança",
            "Unidade Integrada Vila Aurora",
        ),
    }

    def add_facility(
        address: GeneratedAddress, facility_type: FacilityType, name: str, key: str
    ) -> None:
        building_position = building_index[address.building_id]
        buildings[building_position] = replace(
            buildings[building_position],
            building_type=_facility_building_type(facility_type),
        )
        facilities.append(
            GeneratedFacility(
                id=_stable_id(dataset_version, seed, "facility", key),
                address_id=address.id,
                building_id=address.building_id,
                name=name,
                facility_type=facility_type,
            )
        )

    logistics_addresses = [
        address for address in addresses if address.district_slug == "distrito-logistico"
    ]
    if not logistics_addresses:
        raise RuntimeError("Santa Aurora must have a valid depot address")
    depot_seed_point = intersection_by_grid[(20, 4)].point
    depot_address = min(
        logistics_addresses,
        key=lambda address: _haversine_m(address.location, depot_seed_point),
    )
    used_address_ids.add(depot_address.id)
    add_facility(
        depot_address,
        FacilityType.DEPOT,
        "Centro de Distribuição FluxMed",
        "fluxmed-depot",
    )

    for facility_type, count, preferred_districts in facility_specs:
        chosen = pick_addresses(facility_type, count, preferred_districts)
        names = facility_names[facility_type]
        for index, address in enumerate(chosen):
            add_facility(
                address,
                facility_type,
                names[index],
                f"{facility_type.value.lower()}:{index + 1}",
            )

    # Keep references alive and make accidental orphan generation immediately visible.
    if any(facility.address_id not in address_by_id for facility in facilities):
        raise RuntimeError("Generated facility without address")

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
        depot_point=depot_address.location,
        districts=tuple(districts),
        intersections=tuple(intersections),
        streets=tuple(streets.values()),
        road_segments=tuple(road_segments),
        lots=tuple(lots),
        buildings=tuple(buildings),
        addresses=tuple(addresses),
        facilities=tuple(facilities),
    )
