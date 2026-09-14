import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from fluxmed.domain.enums import (
    AggregatedPricingModel,
    CompensationModel,
    FuelType,
    HelperPolicy,
    VehicleOwnershipType,
    VehicleStatus,
    VehicleType,
    WorkerEngagementType,
    WorkerRole,
)
from fluxmed.infrastructure.database import Base


class VehicleModel(Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("max_payload_kg > 0", name="positive_vehicle_payload"),
        CheckConstraint("max_volume_m3 > 0", name="positive_vehicle_volume"),
        CheckConstraint("max_range_km > 0", name="positive_vehicle_range"),
        CheckConstraint(
            "fuel_efficiency_km_per_l IS NULL OR fuel_efficiency_km_per_l > 0",
            name="positive_vehicle_efficiency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plate: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    type: Mapped[VehicleType] = mapped_column(
        SAEnum(VehicleType, name="vehicle_type"), nullable=False, index=True
    )
    ownership_type: Mapped[VehicleOwnershipType] = mapped_column(
        SAEnum(VehicleOwnershipType, name="vehicle_ownership_type"), nullable=False, index=True
    )
    max_payload_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    max_volume_m3: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    max_range_km: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    refrigerated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[VehicleStatus] = mapped_column(
        SAEnum(VehicleStatus, name="vehicle_status"),
        nullable=False,
        default=VehicleStatus.AVAILABLE,
        index=True,
    )
    helper_policy: Mapped[HelperPolicy] = mapped_column(
        SAEnum(HelperPolicy, name="helper_policy"), nullable=False, default=HelperPolicy.OPTIONAL
    )
    fuel_type: Mapped[FuelType | None] = mapped_column(
        SAEnum(FuelType, name="fuel_type"), nullable=True
    )
    fuel_efficiency_km_per_l: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OwnedVehicleCostProfileModel(Base):
    __tablename__ = "owned_vehicle_cost_profiles"
    __table_args__ = (
        CheckConstraint("acquisition_value_brl >= 0", name="nonnegative_acquisition_value"),
        CheckConstraint("residual_value_brl >= 0", name="nonnegative_residual_value"),
        CheckConstraint(
            "residual_value_brl <= acquisition_value_brl",
            name="residual_not_above_acquisition",
        ),
        CheckConstraint("useful_life_km > 0", name="positive_useful_life"),
        CheckConstraint("annual_ipva_brl >= 0", name="nonnegative_ipva"),
        CheckConstraint("annual_insurance_brl >= 0", name="nonnegative_insurance"),
        CheckConstraint("annual_fixed_costs_brl >= 0", name="nonnegative_fixed_costs"),
        CheckConstraint(
            "expected_productive_hours_per_year > 0",
            name="positive_productive_hours",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    acquisition_value_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    residual_value_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    useful_life_km: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    annual_ipva_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    annual_insurance_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    annual_fixed_costs_brl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expected_productive_hours_per_year: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class VehicleMaintenanceItemModel(Base):
    __tablename__ = "vehicle_maintenance_items"
    __table_args__ = (
        CheckConstraint("cost_brl >= 0", name="nonnegative_maintenance_cost"),
        CheckConstraint("interval_km > 0", name="positive_maintenance_interval"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    cost_brl: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    interval_km: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AggregatedVehicleContractModel(Base):
    __tablename__ = "aggregated_vehicle_contracts"
    __table_args__ = (CheckConstraint("price_brl >= 0", name="nonnegative_aggregated_price"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    pricing_model: Mapped[AggregatedPricingModel] = mapped_column(
        SAEnum(AggregatedPricingModel, name="aggregated_pricing_model"),
        nullable=False,
        default=AggregatedPricingModel.PER_ROUTE,
    )
    price_brl: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fuel_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    driver_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    helper_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WorkerModel(Base):
    __tablename__ = "workers"
    __table_args__ = (
        CheckConstraint("compensation_value_brl >= 0", name="nonnegative_worker_compensation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    role: Mapped[WorkerRole] = mapped_column(
        SAEnum(WorkerRole, name="worker_role"), nullable=False, index=True
    )
    engagement_type: Mapped[WorkerEngagementType] = mapped_column(
        SAEnum(WorkerEngagementType, name="worker_engagement_type"), nullable=False
    )
    compensation_model: Mapped[CompensationModel] = mapped_column(
        SAEnum(CompensationModel, name="compensation_model"), nullable=False
    )
    compensation_value_brl: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class WorkerAvailabilityModel(Base):
    __tablename__ = "worker_availability"
    __table_args__ = (
        UniqueConstraint("worker_id", "date", name="uq_worker_availability_worker_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class OperationVehicleSelectionModel(Base):
    __tablename__ = "operation_vehicle_selections"

    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), primary_key=True
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), primary_key=True
    )


class OperationWorkerSelectionModel(Base):
    __tablename__ = "operation_worker_selections"

    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("operations.id", ondelete="CASCADE"), primary_key=True
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workers.id", ondelete="RESTRICT"), primary_key=True
    )
