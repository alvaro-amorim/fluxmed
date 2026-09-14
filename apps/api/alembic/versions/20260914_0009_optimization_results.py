"""Create persisted optimization runs, routes, stops and team assignments.

Revision ID: 20260914_0009
Revises: 20260914_0008
Create Date: 2026-09-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0009"
down_revision: str | None = "20260914_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "optimization_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="COMPLETED"),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("generations_completed", sa.Integer(), nullable=False),
        sa.Column("stop_reason", sa.String(length=60), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivery_count", sa.Integer(), nullable=False),
        sa.Column("vehicles_used", sa.Integer(), nullable=False),
        sa.Column("total_cost_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("distance_km", sa.Numeric(14, 3), nullable=False),
        sa.Column("makespan_minutes", sa.Numeric(14, 2), nullable=False),
        sa.Column("critical_delays", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("on_time_percentage", sa.Numeric(6, 2), nullable=False),
        sa.Column("average_weight_utilization_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column("average_volume_utilization_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column(
            "pruning_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["operations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["operation_revision_id"], ["operation_revisions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_optimization_runs_operation_id", "optimization_runs", ["operation_id"])
    op.create_index(
        "ix_optimization_runs_operation_revision_id",
        "optimization_runs",
        ["operation_revision_id"],
    )
    op.create_index("ix_optimization_runs_status", "optimization_runs", ["status"])

    op.create_table(
        "route_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("optimization_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_code", sa.String(length=24), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_weight_kg", sa.Numeric(14, 3), nullable=False),
        sa.Column("total_volume_m3", sa.Numeric(14, 4), nullable=False),
        sa.Column("distance_km", sa.Numeric(14, 3), nullable=False),
        sa.Column("duration_minutes", sa.Numeric(14, 2), nullable=False),
        sa.Column("weight_utilization_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column("volume_utilization_pct", sa.Numeric(6, 2), nullable=False),
        sa.Column("depreciation_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("maintenance_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("fixed_time_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("fuel_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("team_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("contract_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_cost_brl", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.ForeignKeyConstraint(
            ["optimization_run_id"], ["optimization_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("optimization_run_id", "route_code", name="uq_route_plans_run_code"),
        sa.UniqueConstraint("optimization_run_id", "vehicle_id", name="uq_route_plans_run_vehicle"),
    )
    op.create_index("ix_route_plans_optimization_run_id", "route_plans", ["optimization_run_id"])
    op.create_index("ix_route_plans_vehicle_id", "route_plans", ["vehicle_id"])

    op.create_table(
        "route_stops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("planned_arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lateness_minutes", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["route_id"], ["route_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_id", "sequence", name="uq_route_stops_route_sequence"),
        sa.UniqueConstraint("route_id", "delivery_id", name="uq_route_stops_route_delivery"),
    )
    op.create_index("ix_route_stops_route_id", "route_stops", ["route_id"])
    op.create_index("ix_route_stops_delivery_id", "route_stops", ["delivery_id"])

    op.create_table(
        "route_team_assignments",
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("primary_role", sa.String(length=32), nullable=True),
        sa.Column("primary_worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("helper_worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_included", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("helper_included", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("team_cost_brl", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["route_id"], ["route_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_worker_id"], ["workers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["helper_worker_id"], ["workers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("route_id"),
    )
    op.create_index(
        "ix_route_team_assignments_primary_worker_id",
        "route_team_assignments",
        ["primary_worker_id"],
    )
    op.create_index(
        "ix_route_team_assignments_helper_worker_id",
        "route_team_assignments",
        ["helper_worker_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_route_team_assignments_helper_worker_id", table_name="route_team_assignments"
    )
    op.drop_index(
        "ix_route_team_assignments_primary_worker_id", table_name="route_team_assignments"
    )
    op.drop_table("route_team_assignments")
    op.drop_index("ix_route_stops_delivery_id", table_name="route_stops")
    op.drop_index("ix_route_stops_route_id", table_name="route_stops")
    op.drop_table("route_stops")
    op.drop_index("ix_route_plans_vehicle_id", table_name="route_plans")
    op.drop_index("ix_route_plans_optimization_run_id", table_name="route_plans")
    op.drop_table("route_plans")
    op.drop_index("ix_optimization_runs_status", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_operation_revision_id", table_name="optimization_runs")
    op.drop_index("ix_optimization_runs_operation_id", table_name="optimization_runs")
    op.drop_table("optimization_runs")
