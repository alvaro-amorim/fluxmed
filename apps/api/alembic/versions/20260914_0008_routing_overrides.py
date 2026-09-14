"""Create operation road overrides for routing.

Revision ID: 20260914_0008
Revises: 20260914_0007
Create Date: 2026-09-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0008"
down_revision: str | None = "20260914_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROAD_OVERRIDE_TYPES = ("CLOSURE", "TRAFFIC")
ROAD_OVERRIDE_DIRECTION_SCOPES = ("SEGMENT_DIRECTION",)
TRAFFIC_LEVELS = ("FREE", "LIGHT", "MODERATE", "HEAVY", "VERY_HEAVY")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*ROAD_OVERRIDE_TYPES, name="road_override_type").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(
        *ROAD_OVERRIDE_DIRECTION_SCOPES, name="road_override_direction_scope"
    ).create(bind, checkfirst=True)
    postgresql.ENUM(*TRAFFIC_LEVELS, name="traffic_level").create(bind, checkfirst=True)

    op.create_table(
        "road_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "override_type",
            postgresql.ENUM(*ROAD_OVERRIDE_TYPES, name="road_override_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "direction_scope",
            postgresql.ENUM(
                *ROAD_OVERRIDE_DIRECTION_SCOPES,
                name="road_override_direction_scope",
                create_type=False,
            ),
            nullable=False,
            server_default="SEGMENT_DIRECTION",
        ),
        sa.Column(
            "traffic_level",
            postgresql.ENUM(*TRAFFIC_LEVELS, name="traffic_level", create_type=False),
            nullable=True,
        ),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["operations.id"], ondelete="CASCADE", name="fk_road_overrides_operation_id_operations"
        ),
        sa.ForeignKeyConstraint(
            ["road_segment_id"],
            ["road_segments.id"],
            ondelete="RESTRICT",
            name="fk_road_overrides_road_segment_id_road_segments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_road_overrides"),
        sa.UniqueConstraint(
            "operation_id",
            "road_segment_id",
            "override_type",
            name="uq_road_overrides_operation_segment_type",
        ),
    )
    op.create_index(
        "ix_road_overrides_operation_id", "road_overrides", ["operation_id"], unique=False
    )
    op.create_index(
        "ix_road_overrides_road_segment_id",
        "road_overrides",
        ["road_segment_id"],
        unique=False,
    )
    op.create_index(
        "ix_road_overrides_override_type", "road_overrides", ["override_type"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_road_overrides_override_type", table_name="road_overrides")
    op.drop_index("ix_road_overrides_road_segment_id", table_name="road_overrides")
    op.drop_index("ix_road_overrides_operation_id", table_name="road_overrides")
    op.drop_table("road_overrides")

    bind = op.get_bind()
    postgresql.ENUM(*TRAFFIC_LEVELS, name="traffic_level").drop(bind, checkfirst=True)
    postgresql.ENUM(
        *ROAD_OVERRIDE_DIRECTION_SCOPES, name="road_override_direction_scope"
    ).drop(bind, checkfirst=True)
    postgresql.ENUM(*ROAD_OVERRIDE_TYPES, name="road_override_type").drop(bind, checkfirst=True)
