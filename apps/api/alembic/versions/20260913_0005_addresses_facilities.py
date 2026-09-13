"""Create address, building, lot and facility tables.

Revision ID: 20260913_0005
Revises: 20260913_0004
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op
from geoalchemy2 import Geometry
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0005"
down_revision: str | None = "20260913_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOT_STATUSES = ("OCCUPIED", "VACANT")
BUILDING_TYPES = (
    "HOUSE",
    "APARTMENT_BUILDING",
    "COMMERCIAL",
    "CLINIC",
    "HOSPITAL",
    "PHARMACY",
    "LABORATORY",
    "WAREHOUSE",
    "SCHOOL",
    "PUBLIC_BUILDING",
    "OTHER",
)
FACILITY_TYPES = (
    "DEPOT",
    "HOSPITAL",
    "CLINIC",
    "LABORATORY",
    "PHARMACY",
    "WAREHOUSE",
    "PUBLIC_FACILITY",
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*LOT_STATUSES, name="lot_status").create(bind, checkfirst=True)
    postgresql.ENUM(*BUILDING_TYPES, name="building_type").create(bind, checkfirst=True)
    postgresql.ENUM(*FACILITY_TYPES, name="facility_type").create(bind, checkfirst=True)

    op.create_table(
        "lots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("district_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_on_segment", sa.Float(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(*LOT_STATUSES, name="lot_status", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_lots_city_id_cities", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["districts.id"],
            name="fk_lots_district_id_districts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["road_segment_id"],
            ["road_segments.id"],
            name="fk_lots_road_segment_id_road_segments",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lots"),
    )
    op.create_index("ix_lots_city_id", "lots", ["city_id"], unique=False)
    op.create_index("ix_lots_district_id", "lots", ["district_id"], unique=False)
    op.create_index("ix_lots_road_segment_id", "lots", ["road_segment_id"], unique=False)

    op.create_table(
        "buildings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("district_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "building_type",
            postgresql.ENUM(*BUILDING_TYPES, name="building_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "entrance_location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_buildings_city_id_cities", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["districts.id"],
            name="fk_buildings_district_id_districts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"], ["lots.id"], name="fk_buildings_lot_id_lots", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_buildings"),
        sa.UniqueConstraint("lot_id", name="uq_buildings_lot_id"),
    )
    op.create_index("ix_buildings_city_id", "buildings", ["city_id"], unique=False)
    op.create_index("ix_buildings_district_id", "buildings", ["district_id"], unique=False)
    op.create_index("ix_buildings_lot_id", "buildings", ["lot_id"], unique=True)

    op.create_table(
        "addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("street_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("district_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("house_number", sa.String(length=16), nullable=False),
        sa.Column("house_number_numeric", sa.Integer(), nullable=False),
        sa.Column("suffix", sa.String(length=4), nullable=True),
        sa.Column("complement", sa.String(length=80), nullable=True),
        sa.Column("position_on_segment", sa.Float(), nullable=False),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_addresses_city_id_cities", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["street_id"],
            ["streets.id"],
            name="fk_addresses_street_id_streets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["districts.id"],
            name="fk_addresses_district_id_districts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name="fk_addresses_building_id_buildings",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["road_segment_id"],
            ["road_segments.id"],
            name="fk_addresses_road_segment_id_road_segments",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_addresses"),
        sa.UniqueConstraint(
            "city_id", "street_id", "house_number", name="uq_addresses_city_street_number"
        ),
        sa.UniqueConstraint("building_id", name="uq_addresses_building_id"),
    )
    op.create_index("ix_addresses_city_id", "addresses", ["city_id"], unique=False)
    op.create_index("ix_addresses_street_id", "addresses", ["street_id"], unique=False)
    op.create_index("ix_addresses_district_id", "addresses", ["district_id"], unique=False)
    op.create_index("ix_addresses_building_id", "addresses", ["building_id"], unique=True)
    op.create_index(
        "ix_addresses_road_segment_id", "addresses", ["road_segment_id"], unique=False
    )
    op.create_index(
        "ix_addresses_house_number_numeric", "addresses", ["house_number_numeric"], unique=False
    )
    op.create_index("ix_addresses_active", "addresses", ["active"], unique=False)

    op.create_table(
        "facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("address_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column(
            "facility_type",
            postgresql.ENUM(*FACILITY_TYPES, name="facility_type", create_type=False),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["city_id"], ["cities.id"], name="fk_facilities_city_id_cities", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["address_id"],
            ["addresses.id"],
            name="fk_facilities_address_id_addresses",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name="fk_facilities_building_id_buildings",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_facilities"),
        sa.UniqueConstraint("address_id", name="uq_facilities_address_id"),
    )
    op.create_index("ix_facilities_city_id", "facilities", ["city_id"], unique=False)
    op.create_index("ix_facilities_address_id", "facilities", ["address_id"], unique=True)
    op.create_index("ix_facilities_building_id", "facilities", ["building_id"], unique=False)
    op.create_index("ix_facilities_facility_type", "facilities", ["facility_type"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("facilities")
    op.drop_table("addresses")
    op.drop_table("buildings")
    op.drop_table("lots")
    postgresql.ENUM(*FACILITY_TYPES, name="facility_type").drop(bind, checkfirst=True)
    postgresql.ENUM(*BUILDING_TYPES, name="building_type").drop(bind, checkfirst=True)
    postgresql.ENUM(*LOT_STATUSES, name="lot_status").drop(bind, checkfirst=True)
