"""Create operation revision snapshots.

Revision ID: 20260913_0003
Revises: 20260913_0002
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0003"
down_revision: str | None = "20260913_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVISION_STATUSES = ("DRAFT", "OPTIMIZED", "OUTDATED", "APPROVED", "DISPATCHED")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*REVISION_STATUSES, name="revision_status").create(bind, checkfirst=True)

    op.create_table(
        "operation_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(*REVISION_STATUSES, name="revision_status", create_type=False),
            nullable=False,
        ),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("operation_start_time", sa.Time(), nullable=False),
        sa.Column("operation_end_time", sa.Time(), nullable=False),
        sa.Column(
            "traffic_mode",
            postgresql.ENUM("AUTOMATIC", "FREE", "CUSTOM", name="traffic_mode", create_type=False),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("optimized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="fk_operation_revisions_operation_id_operations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_operation_revisions_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operation_revisions"),
        sa.UniqueConstraint(
            "operation_id", "revision_number", name="uq_operation_revisions_operation_revision_number"
        ),
    )
    op.create_index(
        "ix_operation_revisions_operation_id", "operation_revisions", ["operation_id"], unique=False
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_operation_revisions_operation_id", table_name="operation_revisions")
    op.drop_table("operation_revisions")
    postgresql.ENUM(*REVISION_STATUSES, name="revision_status").drop(bind, checkfirst=True)
