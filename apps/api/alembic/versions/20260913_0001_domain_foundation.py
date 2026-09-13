"""Create domain foundation tables and enable PostGIS.

Revision ID: 20260913_0001
Revises:
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLES = ("ADMIN", "PLANNER")
OPERATION_STATUSES = (
    "DRAFT",
    "READY",
    "OPTIMIZING",
    "OPTIMIZED",
    "OUTDATED",
    "APPROVED",
    "DISPATCHED",
)
TRAFFIC_MODES = ("AUTOMATIC", "FREE", "CUSTOM")


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    postgresql.ENUM(*USER_ROLES, name="user_role").create(bind, checkfirst=True)
    postgresql.ENUM(*OPERATION_STATUSES, name="operation_status").create(bind, checkfirst=True)
    postgresql.ENUM(*TRAFFIC_MODES, name="traffic_mode").create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(*USER_ROLES, name="user_role", create_type=False),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_code", sa.String(length=40), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("operation_start_time", sa.Time(), nullable=False),
        sa.Column("operation_end_time", sa.Time(), nullable=False),
        sa.Column(
            "traffic_mode",
            postgresql.ENUM(*TRAFFIC_MODES, name="traffic_mode", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(*OPERATION_STATUSES, name="operation_status", create_type=False),
            nullable=False,
        ),
        sa.Column("current_revision_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "operation_end_time > operation_start_time",
            name="ck_operations_end_after_start",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_operations_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operations"),
        sa.UniqueConstraint("operation_code", name="uq_operations_operation_code"),
    )
    op.create_index("ix_operations_operation_code", "operations", ["operation_code"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_operations_operation_code", table_name="operations")
    op.drop_table("operations")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    postgresql.ENUM(*TRAFFIC_MODES, name="traffic_mode").drop(bind, checkfirst=True)
    postgresql.ENUM(*OPERATION_STATUSES, name="operation_status").drop(bind, checkfirst=True)
    postgresql.ENUM(*USER_ROLES, name="user_role").drop(bind, checkfirst=True)
