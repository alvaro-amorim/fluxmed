import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.domain.enums import OperationStatus, TrafficMode
from fluxmed.infrastructure.database import Base


class OperationModel(Base):
    __tablename__ = "operations"
    __table_args__ = (
        CheckConstraint(
            "operation_end_time > operation_start_time",
            name="end_after_start",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    operation_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    operation_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    traffic_mode: Mapped[TrafficMode] = mapped_column(
        SAEnum(TrafficMode, name="traffic_mode"),
        nullable=False,
        default=TrafficMode.AUTOMATIC,
    )
    status: Mapped[OperationStatus] = mapped_column(
        SAEnum(OperationStatus, name="operation_status"),
        nullable=False,
        default=OperationStatus.DRAFT,
    )
    current_revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
