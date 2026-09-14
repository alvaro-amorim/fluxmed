"""Create fleet, workforce and operation resource selection tables.

Revision ID: 20260914_0007
Revises: 20260913_0006
Create Date: 2026-09-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0007"
down_revision: str | None = "20260913_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VEHICLE_TYPES = ("MOTO", "VAN_COMPACT", "CARGO_VAN", "LIGHT_TRUCK")
VEHICLE_OWNERSHIP_TYPES = ("OWNED", "AGGREGATED")
VEHICLE_STATUSES = ("AVAILABLE", "UNAVAILABLE", "MAINTENANCE", "INACTIVE")
HELPER_POLICIES = ("FORBIDDEN", "OPTIONAL", "REQUIRED")
FUEL_TYPES = ("GASOLINE", "ETHANOL", "DIESEL", "FLEX", "OTHER")
AGGREGATED_PRICING_MODELS = ("PER_ROUTE",)
WORKER_ROLES = ("DRIVER", "HELPER", "MOTORCYCLE_COURIER")
WORKER_ENGAGEMENT_TYPES = ("EMPLOYEE", "DAY_WORKER", "AGGREGATED")
COMPENSATION_MODELS = (
    "HOURLY",
    "DAILY",
    "PER_ROUTE",
    "INCLUDED_IN_VEHICLE_CONTRACT",
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*VEHICLE_TYPES, name="vehicle_type").create(bind, checkfirst=True)
    postgresql.ENUM(*VEHICLE_OWNERSHIP_TYPES, name="vehicle_ownership_type").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*VEHICLE_STATUSES, name="vehicle_status").create(bind, checkfirst=True)
    postgresql.ENUM(*HELPER_POLICIES, name="helper_policy").create(bind, checkfirst=True)
    postgresql.ENUM(*FUEL_TYPES, name="fuel_type").create(bind, checkfirst=True)
    postgresql.ENUM(*AGGREGATED_PRICING_MODELS, name="aggregated_pricing_model").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*WORKER_ROLES, name="worker_role").create(bind, checkfirst=True)
    postgresql.ENUM(*WORKER_ENGAGEMENT_TYPES, name="worker_engagement_type").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*COMPENSATION_MODELS, name="compensation_model").create(
        bind, checkfirst=True
    )

    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate", sa.String(length=16), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(*VEHICLE_TYPES, name="vehicle_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "ownership_type",
            postgresql.ENUM(
                *VEHICLE_OWNERSHIP_TYPES,
                name="vehicle_ownership_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("max_payload_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("max_volume_m3", sa.Numeric(12, 4), nullable=False),
        sa.Column("max_range_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("refrigerated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "status",
            postgresql.ENUM(*VEHICLE_STATUSES, name="vehicle_status", create_type=False),
            nullable=False,
            server_default="AVAILABLE",
        ),
        sa.Column(
            "helper_policy",
            postgresql.ENUM(*HELPER_POLICIES, name="helper_policy", create_type=False),
            nullable=False,
            server_default="OPTIONAL",
        ),
        sa.Column(
            "fuel_type",
            postgresql.ENUM(*FUEL_TYPES, name="fuel_type", create_type=False),
            nullable=True,
        ),
        sa.Column("fuel_efficiency_km_per_l", sa.Numeric(10, 3), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("max_payload_kg > 0", name="ck_vehicles_positive_vehicle_payload"),
        sa.CheckConstraint("max_volume_m3 > 0", name="ck_vehicles_positive_vehicle_volume"),
        sa.CheckConstraint("max_range_km > 0", name="ck_vehicles_positive_vehicle_range"),
        sa.CheckConstraint(
            "fuel_efficiency_km_per_l IS NULL OR fuel_efficiency_km_per_l > 0",
            name="ck_vehicles_positive_vehicle_efficiency",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vehicles"),
        sa.UniqueConstraint("plate", name="uq_vehicles_plate"),
    )
    op.create_index("ix_vehicles_plate", "vehicles", ["plate"], unique=True)
    op.create_index("ix_vehicles_type", "vehicles", ["type"], unique=False)
    op.create_index("ix_vehicles_ownership_type", "vehicles", ["ownership_type"], unique=False)
    op.create_index("ix_vehicles_status", "vehicles", ["status"], unique=False)
    op.create_index("ix_vehicles_active", "vehicles", ["active"], unique=False)

    op.create_table(
        "owned_vehicle_cost_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("acquisition_value_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("residual_value_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("useful_life_km", sa.Numeric(14, 2), nullable=False),
        sa.Column("annual_ipva_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("annual_insurance_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("annual_fixed_costs_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("expected_productive_hours_per_year", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "acquisition_value_brl >= 0",
            name="ck_owned_vehicle_cost_profiles_nonnegative_acquisition_value",
        ),
        sa.CheckConstraint(
            "residual_value_brl >= 0",
            name="ck_owned_vehicle_cost_profiles_nonnegative_residual_value",
        ),
        sa.CheckConstraint(
            "residual_value_brl <= acquisition_value_brl",
            name="ck_owned_vehicle_cost_profiles_residual_not_above_acquisition",
        ),
        sa.CheckConstraint(
            "useful_life_km > 0",
            name="ck_owned_vehicle_cost_profiles_positive_useful_life",
        ),
        sa.CheckConstraint(
            "annual_ipva_brl >= 0",
            name="ck_owned_vehicle_cost_profiles_nonnegative_ipva",
        ),
        sa.CheckConstraint(
            "annual_insurance_brl >= 0",
            name="ck_owned_vehicle_cost_profiles_nonnegative_insurance",
        ),
        sa.CheckConstraint(
            "annual_fixed_costs_brl >= 0",
            name="ck_owned_vehicle_cost_profiles_nonnegative_fixed_costs",
        ),
        sa.CheckConstraint(
            "expected_productive_hours_per_year > 0",
            name="ck_owned_vehicle_cost_profiles_positive_productive_hours",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_owned_vehicle_cost_profiles_vehicle_id_vehicles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_owned_vehicle_cost_profiles"),
        sa.UniqueConstraint("vehicle_id", name="uq_owned_vehicle_cost_profiles_vehicle_id"),
    )
    op.create_index(
        "ix_owned_vehicle_cost_profiles_vehicle_id",
        "owned_vehicle_cost_profiles",
        ["vehicle_id"],
        unique=True,
    )

    op.create_table(
        "vehicle_maintenance_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("cost_brl", sa.Numeric(12, 2), nullable=False),
        sa.Column("interval_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "cost_brl >= 0", name="ck_vehicle_maintenance_items_nonnegative_maintenance_cost"
        ),
        sa.CheckConstraint(
            "interval_km > 0", name="ck_vehicle_maintenance_items_positive_maintenance_interval"
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_vehicle_maintenance_items_vehicle_id_vehicles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vehicle_maintenance_items"),
    )
    op.create_index(
        "ix_vehicle_maintenance_items_vehicle_id",
        "vehicle_maintenance_items",
        ["vehicle_id"],
        unique=False,
    )

    op.create_table(
        "aggregated_vehicle_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "pricing_model",
            postgresql.ENUM(
                *AGGREGATED_PRICING_MODELS,
                name="aggregated_pricing_model",
                create_type=False,
            ),
            nullable=False,
            server_default="PER_ROUTE",
        ),
        sa.Column("price_brl", sa.Numeric(12, 2), nullable=False),
        sa.Column("fuel_included", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("driver_included", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("helper_included", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "price_brl >= 0", name="ck_aggregated_vehicle_contracts_nonnegative_aggregated_price"
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_aggregated_vehicle_contracts_vehicle_id_vehicles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_aggregated_vehicle_contracts"),
        sa.UniqueConstraint("vehicle_id", name="uq_aggregated_vehicle_contracts_vehicle_id"),
    )
    op.create_index(
        "ix_aggregated_vehicle_contracts_vehicle_id",
        "aggregated_vehicle_contracts",
        ["vehicle_id"],
        unique=True,
    )

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(*WORKER_ROLES, name="worker_role", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "engagement_type",
            postgresql.ENUM(
                *WORKER_ENGAGEMENT_TYPES,
                name="worker_engagement_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "compensation_model",
            postgresql.ENUM(
                *COMPENSATION_MODELS,
                name="compensation_model",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("compensation_value_brl", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "compensation_value_brl >= 0",
            name="ck_workers_nonnegative_worker_compensation",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workers"),
    )
    op.create_index("ix_workers_name", "workers", ["name"], unique=False)
    op.create_index("ix_workers_role", "workers", ["role"], unique=False)
    op.create_index("ix_workers_active", "workers", ["active"], unique=False)

    op.create_table(
        "worker_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["workers.id"],
            name="fk_worker_availability_worker_id_workers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_worker_availability"),
        sa.UniqueConstraint(
            "worker_id", "date", name="uq_worker_availability_worker_date"
        ),
    )
    op.create_index(
        "ix_worker_availability_worker_id",
        "worker_availability",
        ["worker_id"],
        unique=False,
    )
    op.create_index(
        "ix_worker_availability_date",
        "worker_availability",
        ["date"],
        unique=False,
    )

    op.create_table(
        "operation_vehicle_selections",
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="fk_operation_vehicle_selections_operation_id_operations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_operation_vehicle_selections_vehicle_id_vehicles",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "operation_id", "vehicle_id", name="pk_operation_vehicle_selections"
        ),
    )

    op.create_table(
        "operation_worker_selections",
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="fk_operation_worker_selections_operation_id_operations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worker_id"],
            ["workers.id"],
            name="fk_operation_worker_selections_worker_id_workers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "operation_id", "worker_id", name="pk_operation_worker_selections"
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("operation_worker_selections")
    op.drop_table("operation_vehicle_selections")
    op.drop_table("worker_availability")
    op.drop_table("workers")
    op.drop_table("aggregated_vehicle_contracts")
    op.drop_table("vehicle_maintenance_items")
    op.drop_table("owned_vehicle_cost_profiles")
    op.drop_table("vehicles")

    postgresql.ENUM(*COMPENSATION_MODELS, name="compensation_model").drop(bind, checkfirst=True)
    postgresql.ENUM(*WORKER_ENGAGEMENT_TYPES, name="worker_engagement_type").drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(*WORKER_ROLES, name="worker_role").drop(bind, checkfirst=True)
    postgresql.ENUM(*AGGREGATED_PRICING_MODELS, name="aggregated_pricing_model").drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(*FUEL_TYPES, name="fuel_type").drop(bind, checkfirst=True)
    postgresql.ENUM(*HELPER_POLICIES, name="helper_policy").drop(bind, checkfirst=True)
    postgresql.ENUM(*VEHICLE_STATUSES, name="vehicle_status").drop(bind, checkfirst=True)
    postgresql.ENUM(*VEHICLE_OWNERSHIP_TYPES, name="vehicle_ownership_type").drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(*VEHICLE_TYPES, name="vehicle_type").drop(bind, checkfirst=True)
