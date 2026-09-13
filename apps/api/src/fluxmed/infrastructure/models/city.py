import uuid
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.domain.enums import (
    BuildingType,
    CitySourceType,
    FacilityType,
    LotStatus,
    RoadClass,
)
from fluxmed.infrastructure.database import Base


class CityModel(Base):
    __tablename__ = "cities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[CitySourceType] = mapped_column(
        SAEnum(CitySourceType, name="city_source_type"), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    generation_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    generator_version: Mapped[str] = mapped_column(String(64), nullable=False)
    boundary: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False
    )
    river_geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False
    )
    depot_name: Mapped[str] = mapped_column(String(160), nullable=False)
    depot_geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )


class DistrictModel(Base):
    __tablename__ = "districts"
    __table_args__ = (UniqueConstraint("city_id", "slug", name="uq_districts_city_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False
    )


class IntersectionModel(Base):
    __tablename__ = "intersections"
    __table_args__ = (UniqueConstraint("city_id", "code", name="uq_intersections_city_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )


class StreetModel(Base):
    __tablename__ = "streets"
    __table_args__ = (
        UniqueConstraint("city_id", "key", name="uq_streets_city_key"),
        UniqueConstraint("city_id", "name", name="uq_streets_city_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    road_class: Mapped[RoadClass] = mapped_column(
        SAEnum(RoadClass, name="road_class"), nullable=False
    )


class RoadSegmentModel(Base):
    __tablename__ = "road_segments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    street_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("streets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    from_intersection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intersections.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_intersection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intersections.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False
    )
    length_m: Mapped[float] = mapped_column(Float, nullable=False)
    speed_limit_kmh: Mapped[int] = mapped_column(Integer, nullable=False)
    road_class: Mapped[RoadClass] = mapped_column(
        SAEnum(RoadClass, name="road_class"), nullable=False
    )
    lanes: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_bridge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bridge_name: Mapped[str | None] = mapped_column(String(120), nullable=True)


class LotModel(Base):
    __tablename__ = "lots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    road_segment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("road_segments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position_on_segment: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[LotStatus] = mapped_column(SAEnum(LotStatus, name="lot_status"), nullable=False)
    location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )


class BuildingModel(Base):
    __tablename__ = "buildings"
    __table_args__ = (UniqueConstraint("lot_id", name="uq_buildings_lot_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    building_type: Mapped[BuildingType] = mapped_column(
        SAEnum(BuildingType, name="building_type"), nullable=False
    )
    entrance_location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )


class AddressModel(Base):
    __tablename__ = "addresses"
    __table_args__ = (
        UniqueConstraint(
            "city_id", "street_id", "house_number", name="uq_addresses_city_street_number"
        ),
        UniqueConstraint("building_id", name="uq_addresses_building_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    street_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("streets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    road_segment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("road_segments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    house_number: Mapped[str] = mapped_column(String(16), nullable=False)
    house_number_numeric: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    suffix: Mapped[str | None] = mapped_column(String(4), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(80), nullable=True)
    position_on_segment: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class FacilityModel(Base):
    __tablename__ = "facilities"
    __table_args__ = (UniqueConstraint("address_id", name="uq_facilities_address_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    address_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    facility_type: Mapped[FacilityType] = mapped_column(
        SAEnum(FacilityType, name="facility_type"), nullable=False, index=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
