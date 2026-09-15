"""Add optimization lifecycle state and persisted decision trace.

Revision ID: 20260914_0010
Revises: 20260914_0009
Create Date: 2026-09-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0010"
down_revision: str | None = "20260914_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "optimization_runs",
        "operation_revision_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "optimization_runs",
        "completed_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )
    op.add_column(
        "optimization_runs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "optimization_runs",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "optimization_runs",
        sa.Column("error_code", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "optimization_runs",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "optimization_runs",
        sa.Column("previous_operation_status", sa.String(length=24), nullable=True),
    )

    op.create_table(
        "optimization_trace_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("optimization_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=True),
        sa.Column("elapsed_ms", sa.Integer(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["optimization_run_id"], ["optimization_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "optimization_run_id",
            "sequence",
            name="uq_optimization_trace_run_sequence",
        ),
    )
    op.create_index(
        "ix_optimization_trace_events_optimization_run_id",
        "optimization_trace_events",
        ["optimization_run_id"],
    )
    op.create_index(
        "ix_optimization_trace_events_event_type",
        "optimization_trace_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_optimization_trace_events_event_type",
        table_name="optimization_trace_events",
    )
    op.drop_index(
        "ix_optimization_trace_events_optimization_run_id",
        table_name="optimization_trace_events",
    )
    op.drop_table("optimization_trace_events")
    op.drop_column("optimization_runs", "previous_operation_status")
    op.drop_column("optimization_runs", "error_message")
    op.drop_column("optimization_runs", "error_code")
    op.drop_column("optimization_runs", "cancel_requested_at")
    op.drop_column("optimization_runs", "started_at")
    op.alter_column(
        "optimization_runs",
        "completed_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    op.alter_column(
        "optimization_runs",
        "operation_revision_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
