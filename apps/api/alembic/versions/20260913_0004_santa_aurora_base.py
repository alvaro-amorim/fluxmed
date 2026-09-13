"""Create Santa Aurora base city graph tables.

Revision ID: 20260913_0004
Revises: 20260913_0003
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0004"
down_revision: str | None = "20260913_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CITY_SOURCE_TYPES = ("SYNTHETIC",)
ROAD_CLASSES = ("EXPRESSWAY", "ARTERIAL", "COLLECTOR", "LOCAL", "SERVICE")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*CITY_SOURCE_TYPES, name="city_source_type").create(bind, checkfirst=True)
    postgresql.ENUM(*ROAD_CLASSES, name="road_class").create(bind, checkfirst=True)

    op.create_table(
        "cities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column(
            "source_type",
            postgresql.ENUM(*CITY_SOURCE_TYPES, name="city_source_type", create_type=False),
            nullable=False,
        ),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("generation_seed", sa.Integer(), nullable=False),
        sa.Column("generator_version", sa.String(length=64), nullable=False),
        sa.Column(
            "boundary",
            Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "river_geometry",
            Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("depot_name", sa.String(length=160), nullable=False),
        sa.Column(
            "depot_geometry",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cities"),
        sa.UniqueConstraint("name", name="uq_cities_name"),
    )
    op.create_index("ix_cities_name", "cities", ["name"], unique=False)

    op.create_table(
        "districts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column(
            "geometry",
            Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_districts_city_id_cities", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_districts"),
        sa.UniqueConstraint("city_id", "slug", name="uq_districts_city_slug"),
    )
    op.create_index("ix_districts_city_id", "districts", ["city_id"], unique=False)

    op.create_table(
        "intersections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("district_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column(
            "geometry",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_intersections_city_id_cities", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["districts.id"],
            name="fk_intersections_district_id_districts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_intersections"),
        sa.UniqueConstraint("city_id", "code", name="uq_intersections_city_code"),
    )
    op.create_index("ix_intersections_city_id", "intersections", ["city_id"], unique=False)
    op.create_index(
        "ix_intersections_district_id", "intersections", ["district_id"], unique=False
    )

    op.create_table(
        "streets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "road_class",
            postgresql.ENUM(*ROAD_CLASSES, name="road_class", create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_streets_city_id_cities", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_streets"),
        sa.UniqueConstraint("city_id", "key", name="uq_streets_city_key"),
        sa.UniqueConstraint("city_id", "name", name="uq_streets_city_name"),
    )
    op.create_index("ix_streets_city_id", "streets", ["city_id"], unique=False)

    op.create_table(
        "road_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("street_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_intersection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_intersection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "geometry",
            Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("speed_limit_kmh", sa.Integer(), nullable=False),
        sa.Column(
            "road_class",
            postgresql.ENUM(*ROAD_CLASSES, name="road_class", create_type=False),
            nullable=False,
        ),
        sa.Column("lanes", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_bridge", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("bridge_name", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_road_segments_city_id_cities", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["street_id"],
            ["streets.id"],
            name="fk_road_segments_street_id_streets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_intersection_id"],
            ["intersections.id"],
            name="fk_road_segments_from_intersection_id_intersections",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_intersection_id"],
            ["intersections.id"],
            name="fk_road_segments_to_intersection_id_intersections",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_road_segments"),
    )
    op.create_index("ix_road_segments_city_id", "road_segments", ["city_id"], unique=False)
    op.create_index("ix_road_segments_street_id", "road_segments", ["street_id"], unique=False)
    op.create_index(
        "ix_road_segments_from_intersection_id",
        "road_segments",
        ["from_intersection_id"],
        unique=False,
    )
    op.create_index(
        "ix_road_segments_to_intersection_id",
        "road_segments",
        ["to_intersection_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("road_segments")
    op.drop_table("streets")
    op.drop_table("intersections")
    op.drop_table("districts")
    op.drop_index("ix_cities_name", table_name="cities")
    op.drop_table("cities")
    postgresql.ENUM(*ROAD_CLASSES, name="road_class").drop(bind, checkfirst=True)
    postgresql.ENUM(*CITY_SOURCE_TYPES, name="city_source_type").drop(bind, checkfirst=True)
