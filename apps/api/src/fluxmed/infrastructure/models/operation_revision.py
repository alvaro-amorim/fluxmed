import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.domain.enums import RevisionStatus, TrafficMode
from fluxmed.infrastructure.database import Base


class OperationRevisionModel(Base):
    __tablename__ = "operation_revisions"
    __table_args__ = (
        UniqueConstraint("operation_id", "revision_number", name="operation_revision_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RevisionStatus] = mapped_column(
        SAEnum(RevisionStatus, name="revision_status"), nullable=False
    )
    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    operation_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    operation_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    traffic_mode: Mapped[TrafficMode] = mapped_column(
        SAEnum(TrafficMode, name="traffic_mode", create_type=False), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    optimized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
