"""SQLAlchemy persistence models.

Importing this package registers the current models in Base.metadata for Alembic.
"""

from fluxmed.infrastructure.models.assistant_telemetry import AssistantTelemetryModel
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.city import (
    AddressModel,
    BuildingModel,
    CityModel,
    DistrictModel,
    FacilityModel,
    IntersectionModel,
    LotModel,
    RoadSegmentModel,
    StreetModel,
)
from fluxmed.infrastructure.models.delivery import DeliveryImportModel, DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.operation_revision import OperationRevisionModel
from fluxmed.infrastructure.models.optimization_result import (
    OptimizationRunModel,
    OptimizationTraceEventModel,
    RoutePlanModel,
    RouteStopModel,
    RouteTeamAssignmentModel,
)
from fluxmed.infrastructure.models.report import ReportModel
from fluxmed.infrastructure.models.resource import (
    AggregatedVehicleContractModel,
    OperationVehicleSelectionModel,
    OperationWorkerSelectionModel,
    OwnedVehicleCostProfileModel,
    VehicleMaintenanceItemModel,
    VehicleModel,
    WorkerAvailabilityModel,
    WorkerModel,
)
from fluxmed.infrastructure.models.road_override import RoadOverrideModel
from fluxmed.infrastructure.models.user import UserModel

__all__ = [
    "AddressModel",
    "AggregatedVehicleContractModel",
    "AssistantTelemetryModel",
    "AuthSessionModel",
    "BuildingModel",
    "CityModel",
    "DeliveryImportModel",
    "DeliveryModel",
    "DistrictModel",
    "FacilityModel",
    "IntersectionModel",
    "LotModel",
    "OperationModel",
    "OperationRevisionModel",
    "OperationVehicleSelectionModel",
    "OperationWorkerSelectionModel",
    "OptimizationRunModel",
    "OptimizationTraceEventModel",
    "OwnedVehicleCostProfileModel",
    "ReportModel",
    "RoadOverrideModel",
    "RoadSegmentModel",
    "RoutePlanModel",
    "RouteStopModel",
    "RouteTeamAssignmentModel",
    "StreetModel",
    "UserModel",
    "VehicleMaintenanceItemModel",
    "VehicleModel",
    "WorkerAvailabilityModel",
    "WorkerModel",
]
