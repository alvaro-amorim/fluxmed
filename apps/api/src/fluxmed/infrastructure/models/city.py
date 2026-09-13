import uuid
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.domain.enums import CitySourceType, RoadClass
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
