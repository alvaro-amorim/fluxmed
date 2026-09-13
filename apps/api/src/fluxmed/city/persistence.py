import uuid
from collections.abc import Iterable

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from fluxmed.city.generator import DATASET_VERSION, DEFAULT_SEED, Coordinate
from fluxmed.city.provider import SantaAuroraProvider
from fluxmed.domain.enums import CitySourceType
from fluxmed.infrastructure.models.city import (
    AddressModel,
    BuildingModel,
    CityModel,
    DistrictModel,
    FacilityModel,
    IntersectionModel,
    LotModel,
    RoadSegmentModel,
    StreetModel,
)


def _point_wkt(point: Coordinate) -> WKTElement:
    return WKTElement(f"POINT({point[0]} {point[1]})", srid=4326)


def _line_wkt(points: Iterable[Coordinate]) -> WKTElement:
    coordinates = ", ".join(f"{lon} {lat}" for lon, lat in points)
    return WKTElement(f"LINESTRING({coordinates})", srid=4326)


def _polygon_wkt(points: Iterable[Coordinate]) -> WKTElement:
    coordinates = ", ".join(f"{lon} {lat}" for lon, lat in points)
    return WKTElement(f"POLYGON(({coordinates}))", srid=4326)


def seed_santa_aurora(
    session: Session,
    *,
    seed: int = DEFAULT_SEED,
    dataset_version: str = DATASET_VERSION,
    replace: bool = False,
) -> CityModel:
    generated = SantaAuroraProvider(seed=seed, dataset_version=dataset_version).generate()
    existing = session.scalar(select(CityModel).where(CityModel.name == generated.name))
    if existing is not None:
        same_dataset = (
            existing.dataset_version == generated.dataset_version
            and existing.generation_seed == generated.generation_seed
            and existing.generator_version == generated.generator_version
        )
        if same_dataset and not replace:
            return existing
        if not replace:
            raise RuntimeError(
                "Santa Aurora already exists with another seed/version. "
                "Use replace=True explicitly."
            )
        session.execute(delete(CityModel).where(CityModel.id == existing.id))
        session.flush()

    city = CityModel(
        id=generated.id,
        name=generated.name,
        country=generated.country,
        source_type=CitySourceType.SYNTHETIC,
        timezone=generated.timezone,
        dataset_version=generated.dataset_version,
        generation_seed=generated.generation_seed,
        generator_version=generated.generator_version,
        boundary=_polygon_wkt(generated.boundary),
        river_geometry=_line_wkt(generated.river),
        depot_name=generated.depot_name,
        depot_geometry=_point_wkt(generated.depot_point),
    )
    session.add(city)
    session.flush()

    district_ids: dict[str, uuid.UUID] = {
        district.slug: district.id for district in generated.districts
    }
    session.execute(
        insert(DistrictModel),
        [
            {
                "id": district.id,
                "city_id": city.id,
                "name": district.name,
                "slug": district.slug,
                "geometry": _polygon_wkt(district.polygon),
            }
            for district in generated.districts
        ],
    )
    session.execute(
        insert(IntersectionModel),
        [
            {
                "id": intersection.id,
                "city_id": city.id,
                "district_id": district_ids[intersection.district_slug],
                "code": intersection.code,
                "geometry": _point_wkt(intersection.point),
            }
            for intersection in generated.intersections
        ],
    )
    session.execute(
        insert(StreetModel),
        [
            {
                "id": street.id,
                "city_id": city.id,
                "key": street.key,
                "name": street.name,
                "road_class": street.road_class,
            }
            for street in generated.streets
        ],
    )
    session.execute(
        insert(RoadSegmentModel),
        [
            {
                "id": segment.id,
                "city_id": city.id,
                "street_id": segment.street_id,
                "from_intersection_id": segment.from_intersection_id,
                "to_intersection_id": segment.to_intersection_id,
                "geometry": _line_wkt(segment.coordinates),
                "length_m": segment.length_m,
                "speed_limit_kmh": segment.speed_limit_kmh,
                "road_class": segment.road_class,
                "lanes": segment.lanes,
                "active": True,
                "is_bridge": segment.is_bridge,
                "bridge_name": segment.bridge_name,
            }
            for segment in generated.road_segments
        ],
    )
    session.execute(
        insert(LotModel),
        [
            {
                "id": lot.id,
                "city_id": city.id,
                "district_id": district_ids[lot.district_slug],
                "road_segment_id": lot.road_segment_id,
                "position_on_segment": lot.position_on_segment,
                "status": lot.status,
                "location": _point_wkt(lot.location),
            }
            for lot in generated.lots
        ],
    )
    session.execute(
        insert(BuildingModel),
        [
            {
                "id": building.id,
                "city_id": city.id,
                "district_id": district_ids[building.district_slug],
                "lot_id": building.lot_id,
                "building_type": building.building_type,
                "entrance_location": _point_wkt(building.entrance_location),
            }
            for building in generated.buildings
        ],
    )
    session.execute(
        insert(AddressModel),
        [
            {
                "id": address.id,
                "city_id": city.id,
                "street_id": address.street_id,
                "district_id": district_ids[address.district_slug],
                "building_id": address.building_id,
                "road_segment_id": address.road_segment_id,
                "house_number": address.house_number,
                "house_number_numeric": address.house_number_numeric,
                "suffix": address.suffix,
                "complement": address.complement,
                "position_on_segment": address.position_on_segment,
                "location": _point_wkt(address.location),
                "active": True,
            }
            for address in generated.addresses
        ],
    )
    session.execute(
        insert(FacilityModel),
        [
            {
                "id": facility.id,
                "city_id": city.id,
                "address_id": facility.address_id,
                "building_id": facility.building_id,
                "name": facility.name,
                "facility_type": facility.facility_type,
                "active": True,
            }
            for facility in generated.facilities
        ],
    )
    session.flush()
    return city
