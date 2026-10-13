"""Add persisted LLM assistant telemetry without storing prompt or response content.

Revision ID: 20260916_0012
Revises: 20260915_0011
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260916_0012"
down_revision: str | None = "20260915_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "tool_calls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("tool_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_assistant_telemetry_request_id", "assistant_telemetry", ["request_id"])
    op.create_index("ix_assistant_telemetry_user_id", "assistant_telemetry", ["user_id"])
    op.create_index("ix_assistant_telemetry_operation_id", "assistant_telemetry", ["operation_id"])
    op.create_index("ix_assistant_telemetry_status", "assistant_telemetry", ["status"])


def downgrade() -> None:
    op.drop_index("ix_assistant_telemetry_status", table_name="assistant_telemetry")
    op.drop_index("ix_assistant_telemetry_operation_id", table_name="assistant_telemetry")
    op.drop_index("ix_assistant_telemetry_user_id", table_name="assistant_telemetry")
    op.drop_index("ix_assistant_telemetry_request_id", table_name="assistant_telemetry")
    op.drop_table("assistant_telemetry")
