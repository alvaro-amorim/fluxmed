"""Create delivery and delivery import tables.

Revision ID: 20260913_0006
Revises: 20260913_0005
Create Date: 2026-09-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0006"
down_revision: str | None = "20260913_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DELIVERY_PRIORITIES = ("CRITICAL", "HIGH", "NORMAL", "LOW")
TIME_WINDOW_POLICIES = ("HARD", "SOFT")
SERVICE_TIME_SOURCES = ("ESTIMATED", "MANUAL", "IMPORTED")
TEMPERATURE_CLASSES = ("AMBIENT", "REFRIGERATED")
HANDLING_REQUIREMENTS = ("STANDARD", "TWO_PERSON")
DELIVERY_STATUSES = (
    "PENDING",
    "PLANNED",
    "LOADED",
    "DISPATCHED",
    "IN_TRANSIT",
    "DELIVERED",
    "FAILED",
)
CARGO_PROFILES = (
    "MEDICATION_SMALL",
    "REFRIGERATED_MEDICATION",
    "LAB_MATERIAL",
    "HOSPITAL_SUPPLIES",
    "BULK_CONSUMABLES",
    "MEDICAL_EQUIPMENT",
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*DELIVERY_PRIORITIES, name="delivery_priority").create(bind, checkfirst=True)
    postgresql.ENUM(*TIME_WINDOW_POLICIES, name="time_window_policy").create(bind, checkfirst=True)
    postgresql.ENUM(*SERVICE_TIME_SOURCES, name="service_time_source").create(bind, checkfirst=True)
    postgresql.ENUM(*TEMPERATURE_CLASSES, name="temperature_class").create(bind, checkfirst=True)
    postgresql.ENUM(*HANDLING_REQUIREMENTS, name="handling_requirement").create(bind, checkfirst=True)
    postgresql.ENUM(*DELIVERY_STATUSES, name="delivery_status").create(bind, checkfirst=True)
    postgresql.ENUM(*CARGO_PROFILES, name="cargo_profile").create(bind, checkfirst=True)

    op.create_table(
        "deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_code", sa.String(length=64), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(length=80), nullable=False),
        sa.Column("invoice_series", sa.String(length=40), nullable=False),
        sa.Column("issuer_document", sa.String(length=40), nullable=False),
        sa.Column("issuer_name", sa.String(length=180), nullable=True),
        sa.Column("external_reference", sa.String(length=120), nullable=True),
        sa.Column("destination_address_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_name", sa.String(length=180), nullable=False),
        sa.Column("package_count", sa.Integer(), nullable=False),
        sa.Column("total_weight_kg", sa.Numeric(12, 3), nullable=False),
        sa.Column("total_volume_m3", sa.Numeric(12, 4), nullable=False),
        sa.Column(
            "priority",
            postgresql.ENUM(*DELIVERY_PRIORITIES, name="delivery_priority", create_type=False),
            nullable=False,
        ),
        sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "time_window_policy",
            postgresql.ENUM(*TIME_WINDOW_POLICIES, name="time_window_policy", create_type=False),
            nullable=False,
        ),
        sa.Column("service_time_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "service_time_source",
            postgresql.ENUM(*SERVICE_TIME_SOURCES, name="service_time_source", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "temperature_class",
            postgresql.ENUM(*TEMPERATURE_CLASSES, name="temperature_class", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "handling_requirement",
            postgresql.ENUM(*HANDLING_REQUIREMENTS, name="handling_requirement", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(*DELIVERY_STATUSES, name="delivery_status", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "cargo_profile",
            postgresql.ENUM(*CARGO_PROFILES, name="cargo_profile", create_type=False),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("package_count > 0", name="ck_deliveries_positive_package_count"),
        sa.CheckConstraint("total_weight_kg > 0", name="ck_deliveries_positive_weight"),
        sa.CheckConstraint("total_volume_m3 > 0", name="ck_deliveries_positive_volume"),
        sa.CheckConstraint("service_time_minutes > 0", name="ck_deliveries_positive_service_time"),
        sa.CheckConstraint(
            "(time_window_start IS NULL AND time_window_end IS NULL) OR "
            "(time_window_start IS NOT NULL AND time_window_end > time_window_start)",
            name="ck_deliveries_valid_time_window",
        ),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["operations.id"], name="fk_deliveries_operation_id_operations", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["destination_address_id"],
            ["addresses.id"],
            name="fk_deliveries_destination_address_id_addresses",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deliveries"),
        sa.UniqueConstraint("delivery_code", name="uq_deliveries_delivery_code"),
    )
    op.create_index("ix_deliveries_delivery_code", "deliveries", ["delivery_code"], unique=True)
    op.create_index("ix_deliveries_operation_id", "deliveries", ["operation_id"], unique=False)
    op.create_index("ix_deliveries_invoice_number", "deliveries", ["invoice_number"], unique=False)
    op.create_index("ix_deliveries_issuer_document", "deliveries", ["issuer_document"], unique=False)
    op.create_index(
        "ix_deliveries_destination_address_id", "deliveries", ["destination_address_id"], unique=False
    )
    op.create_index("ix_deliveries_priority", "deliveries", ["priority"], unique=False)
    op.create_index("ix_deliveries_temperature_class", "deliveries", ["temperature_class"], unique=False)
    op.create_index("ix_deliveries_status", "deliveries", ["status"], unique=False)

    op.create_table(
        "delivery_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="REVIEW"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["operation_id"],
            ["operations.id"],
            name="fk_delivery_imports_operation_id_operations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_delivery_imports_created_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_delivery_imports"),
    )
    op.create_index("ix_delivery_imports_operation_id", "delivery_imports", ["operation_id"], unique=False)
    op.create_index("ix_delivery_imports_status", "delivery_imports", ["status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("delivery_imports")
    op.drop_table("deliveries")
    postgresql.ENUM(*CARGO_PROFILES, name="cargo_profile").drop(bind, checkfirst=True)
    postgresql.ENUM(*DELIVERY_STATUSES, name="delivery_status").drop(bind, checkfirst=True)
    postgresql.ENUM(*HANDLING_REQUIREMENTS, name="handling_requirement").drop(bind, checkfirst=True)
    postgresql.ENUM(*TEMPERATURE_CLASSES, name="temperature_class").drop(bind, checkfirst=True)
    postgresql.ENUM(*SERVICE_TIME_SOURCES, name="service_time_source").drop(bind, checkfirst=True)
    postgresql.ENUM(*TIME_WINDOW_POLICIES, name="time_window_policy").drop(bind, checkfirst=True)
    postgresql.ENUM(*DELIVERY_PRIORITIES, name="delivery_priority").drop(bind, checkfirst=True)
