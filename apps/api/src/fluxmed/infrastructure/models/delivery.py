import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.domain.enums import (
    CargoProfile,
    DeliveryPriority,
    DeliveryStatus,
    HandlingRequirement,
    ServiceTimeSource,
    TemperatureClass,
    TimeWindowPolicy,
)
from fluxmed.infrastructure.database import Base


class DeliveryModel(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint("package_count > 0", name="positive_package_count"),
        CheckConstraint("total_weight_kg > 0", name="positive_weight"),
        CheckConstraint("total_volume_m3 > 0", name="positive_volume"),
        CheckConstraint("service_time_minutes > 0", name="positive_service_time"),
        CheckConstraint(
            "(time_window_start IS NULL AND time_window_end IS NULL) OR "
            "(time_window_start IS NOT NULL AND time_window_end > time_window_start)",
            name="valid_time_window",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    delivery_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    invoice_series: Mapped[str] = mapped_column(String(40), nullable=False)
    issuer_document: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    issuer_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    destination_address_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recipient_name: Mapped[str] = mapped_column(String(180), nullable=False)
    package_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    total_volume_m3: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    priority: Mapped[DeliveryPriority] = mapped_column(
        SAEnum(DeliveryPriority, name="delivery_priority"), nullable=False, index=True
    )
    time_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_window_policy: Mapped[TimeWindowPolicy] = mapped_column(
        SAEnum(TimeWindowPolicy, name="time_window_policy"), nullable=False
    )
    service_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    service_time_source: Mapped[ServiceTimeSource] = mapped_column(
        SAEnum(ServiceTimeSource, name="service_time_source"), nullable=False
    )
    temperature_class: Mapped[TemperatureClass] = mapped_column(
        SAEnum(TemperatureClass, name="temperature_class"), nullable=False, index=True
    )
    handling_requirement: Mapped[HandlingRequirement] = mapped_column(
        SAEnum(HandlingRequirement, name="handling_requirement"), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus, name="delivery_status"),
        nullable=False,
        default=DeliveryStatus.PENDING,
        index=True,
    )
    cargo_profile: Mapped[CargoProfile | None] = mapped_column(
        SAEnum(CargoProfile, name="cargo_profile"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DeliveryImportModel(Base):
    __tablename__ = "delivery_imports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="REVIEW", index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_json: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
