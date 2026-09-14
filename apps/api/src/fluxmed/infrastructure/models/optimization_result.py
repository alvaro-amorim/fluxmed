import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.infrastructure.database import Base


class OptimizationRunModel(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operation_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="COMPLETED", index=True)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    generations_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_reason: Mapped[str] = mapped_column(String(60), nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivery_count: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicles_used: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    distance_km: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    makespan_minutes: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    critical_delays: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    on_time_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    average_weight_utilization_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    average_volume_utilization_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    pruning_counts: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    previous_operation_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OptimizationTraceEventModel(Base):
    __tablename__ = "optimization_trace_events"
    __table_args__ = (
        UniqueConstraint(
            "optimization_run_id",
            "sequence",
            name="uq_optimization_trace_run_sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RoutePlanModel(Base):
    __tablename__ = "route_plans"
    __table_args__ = (
        UniqueConstraint("optimization_run_id", "route_code", name="uq_route_plans_run_code"),
        UniqueConstraint("optimization_run_id", "vehicle_id", name="uq_route_plans_run_vehicle"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    optimization_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("optimization_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    route_code: Mapped[str] = mapped_column(String(24), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    total_volume_m3: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    distance_km: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    duration_minutes: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    weight_utilization_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    volume_utilization_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    depreciation_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    maintenance_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fixed_time_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fuel_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    team_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    contract_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_cost_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    geometry: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class RouteStopModel(Base):
    __tablename__ = "route_stops"
    __table_args__ = (
        UniqueConstraint("route_id", "sequence", name="uq_route_stops_route_sequence"),
        UniqueConstraint("route_id", "delivery_id", name="uq_route_stops_route_delivery"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    route_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("route_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deliveries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lateness_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)


class RouteTeamAssignmentModel(Base):
    __tablename__ = "route_team_assignments"

    route_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("route_plans.id", ondelete="CASCADE"), primary_key=True
    )
    primary_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_worker_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    helper_worker_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    primary_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    helper_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    team_cost_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
