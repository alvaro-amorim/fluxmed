import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.domain.enums import (
    RoadOverrideDirectionScope,
    RoadOverrideType,
    TrafficLevel,
)
from fluxmed.infrastructure.database import Base


class RoadOverrideModel(Base):
    __tablename__ = "road_overrides"
    __table_args__ = (
        UniqueConstraint(
            "operation_id",
            "road_segment_id",
            "override_type",
            name="uq_road_overrides_operation_segment_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    road_segment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("road_segments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    override_type: Mapped[RoadOverrideType] = mapped_column(
        SAEnum(RoadOverrideType, name="road_override_type"), nullable=False, index=True
    )
    direction_scope: Mapped[RoadOverrideDirectionScope] = mapped_column(
        SAEnum(RoadOverrideDirectionScope, name="road_override_direction_scope"),
        nullable=False,
        default=RoadOverrideDirectionScope.SEGMENT_DIRECTION,
    )
    traffic_level: Mapped[TrafficLevel | None] = mapped_column(
        SAEnum(TrafficLevel, name="traffic_level"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
