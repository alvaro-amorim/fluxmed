import uuid
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.resources import (
    AggregatedContractInput,
    MaintenanceInput,
    OwnedCostInput,
    ResourceConflictError,
    ResourceSelectionError,
    ResourceService,
    VehicleInput,
    VehicleNotFoundError,
    VehicleView,
    WorkerAvailabilityView,
    WorkerInput,
    WorkerNotFoundError,
    WorkerView,
)
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
from fluxmed.domain.resources import ResourceValidationError

router = APIRouter(tags=["resources"])


class MaintenanceItemRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    cost_brl: Decimal = Field(ge=0)
    interval_km: Decimal = Field(gt=0)
    active: bool = True


class OwnedVehicleCostRequest(BaseModel):
    acquisition_value_brl: Decimal = Field(ge=0)
    residual_value_brl: Decimal = Field(ge=0)
    useful_life_km: Decimal = Field(gt=0)
    annual_ipva_brl: Decimal = Field(ge=0)
    annual_insurance_brl: Decimal = Field(ge=0)
    annual_fixed_costs_brl: Decimal = Field(ge=0)
    expected_productive_hours_per_year: Decimal = Field(gt=0)
    maintenance_items: list[MaintenanceItemRequest] = Field(default_factory=list)


class AggregatedVehicleContractRequest(BaseModel):
    price_brl: Decimal = Field(ge=0)
    pricing_model: AggregatedPricingModel = AggregatedPricingModel.PER_ROUTE
    fuel_included: bool = False
    driver_included: bool = False
    helper_included: bool = False


class VehicleCreateRequest(BaseModel):
    plate: str = Field(min_length=7, max_length=16)
    type: VehicleType
    ownership_type: VehicleOwnershipType
    max_payload_kg: Decimal = Field(gt=0)
    max_volume_m3: Decimal = Field(gt=0)
    max_range_km: Decimal = Field(gt=0)
    refrigerated: bool = False
    status: VehicleStatus = VehicleStatus.AVAILABLE
    helper_policy: HelperPolicy = HelperPolicy.OPTIONAL
    fuel_type: FuelType | None = None
    fuel_efficiency_km_per_l: Decimal | None = Field(default=None, gt=0)
    owned_cost: OwnedVehicleCostRequest | None = None
    aggregated_contract: AggregatedVehicleContractRequest | None = None


class VehicleUpdateRequest(BaseModel):
    plate: str | None = Field(default=None, min_length=7, max_length=16)
    type: VehicleType | None = None
    max_payload_kg: Decimal | None = Field(default=None, gt=0)
    max_volume_m3: Decimal | None = Field(default=None, gt=0)
    max_range_km: Decimal | None = Field(default=None, gt=0)
    refrigerated: bool | None = None
    status: VehicleStatus | None = None
    helper_policy: HelperPolicy | None = None
    fuel_type: FuelType | None = None
    fuel_efficiency_km_per_l: Decimal | None = Field(default=None, gt=0)


class VehicleCostUpdateRequest(BaseModel):
    owned_cost: OwnedVehicleCostRequest | None = None
    aggregated_contract: AggregatedVehicleContractRequest | None = None


class MaintenanceItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    cost_brl: Decimal
    interval_km: Decimal
    active: bool
    cost_per_km: Decimal


class VehicleCostResponse(BaseModel):
    ownership_type: VehicleOwnershipType
    depreciation_per_km: Decimal | None
    maintenance_per_km: Decimal | None
    fixed_cost_per_hour: Decimal | None
    contract_price_brl: Decimal | None
    pricing_model: AggregatedPricingModel | None
    fuel_included: bool
    driver_included: bool
    helper_included: bool
    maintenance_items: list[MaintenanceItemResponse]


class VehicleResponse(BaseModel):
    id: uuid.UUID
    plate: str
    type: VehicleType
    ownership_type: VehicleOwnershipType
    max_payload_kg: Decimal
    max_volume_m3: Decimal
    max_range_km: Decimal
    refrigerated: bool
    status: VehicleStatus
    helper_policy: HelperPolicy
    fuel_type: FuelType | None
    fuel_efficiency_km_per_l: Decimal | None
    active: bool
    cost: VehicleCostResponse
    created_at: datetime
    updated_at: datetime


class WorkerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    role: WorkerRole
    engagement_type: WorkerEngagementType
    compensation_model: CompensationModel
    compensation_value_brl: Decimal = Field(ge=0)


class WorkerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    role: WorkerRole | None = None
    engagement_type: WorkerEngagementType | None = None
    compensation_model: CompensationModel | None = None
    compensation_value_brl: Decimal | None = Field(default=None, ge=0)


class WorkerResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: WorkerRole
    engagement_type: WorkerEngagementType
    compensation_model: CompensationModel
    compensation_value_brl: Decimal
    active: bool
    created_at: datetime
    updated_at: datetime


class WorkerAvailabilityRequest(BaseModel):
    date: date
    available: bool
    notes: str | None = Field(default=None, max_length=500)


class WorkerAvailabilityResponse(BaseModel):
    worker_id: uuid.UUID
    date: date
    available: bool
    notes: str | None


class OperationResourceSelectionRequest(BaseModel):
    vehicle_ids: list[uuid.UUID] = Field(default_factory=list)
    worker_ids: list[uuid.UUID] = Field(default_factory=list)


class OperationResourcesResponse(BaseModel):
    operation_id: uuid.UUID
    operation_date: date
    selected_vehicle_ids: list[uuid.UUID]
    selected_worker_ids: list[uuid.UUID]
    unavailable_worker_ids: list[uuid.UUID]
    vehicles: list[VehicleResponse]
    workers: list[WorkerResponse]


def _maintenance_input(payload: MaintenanceItemRequest) -> MaintenanceInput:
    return MaintenanceInput(**payload.model_dump())


def _owned_input(payload: OwnedVehicleCostRequest | None) -> OwnedCostInput | None:
    if payload is None:
        return None
    values = payload.model_dump(exclude={"maintenance_items"})
    return OwnedCostInput(
        **values,
        maintenance_items=[_maintenance_input(item) for item in payload.maintenance_items],
    )


def _contract_input(
    payload: AggregatedVehicleContractRequest | None,
) -> AggregatedContractInput | None:
    return AggregatedContractInput(**payload.model_dump()) if payload is not None else None


def _vehicle_input(payload: VehicleCreateRequest) -> VehicleInput:
    values = payload.model_dump(exclude={"owned_cost", "aggregated_contract"})
    return VehicleInput(
        **values,
        owned_cost=_owned_input(payload.owned_cost),
        aggregated_contract=_contract_input(payload.aggregated_contract),
    )


def _vehicle_response(view: VehicleView) -> VehicleResponse:
    return VehicleResponse(**asdict(view))


def _worker_response(view: WorkerView) -> WorkerResponse:
    return WorkerResponse(**asdict(view))


def _availability_response(view: WorkerAvailabilityView) -> WorkerAvailabilityResponse:
    return WorkerAvailabilityResponse(**asdict(view))


def _resource_error(exc: Exception) -> None:
    if isinstance(exc, VehicleNotFoundError):
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "VEHICLE_NOT_FOUND",
            "Veículo não encontrado.",
        ) from exc
    if isinstance(exc, WorkerNotFoundError):
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "WORKER_NOT_FOUND",
            "Worker não encontrado.",
        ) from exc
    if isinstance(exc, ResourceConflictError):
        raise ApiError(status.HTTP_409_CONFLICT, "RESOURCE_CONFLICT", str(exc)) from exc
    if isinstance(exc, (ResourceValidationError, ResourceSelectionError, ValueError)):
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_RESOURCE",
            str(exc),
        ) from exc
    raise exc


@router.get("/vehicles", response_model=list[VehicleResponse])
def list_vehicles(
    session: DbSession,
    current_user: CurrentUser,
    active: bool | None = None,
    vehicle_status: Annotated[VehicleStatus | None, Query(alias="status")] = None,
    refrigerated: bool | None = None,
    q: Annotated[str | None, Query(max_length=60)] = None,
) -> list[VehicleResponse]:
    del current_user
    views = ResourceService(session).list_vehicles(
        active=active,
        status=vehicle_status,
        refrigerated=refrigerated,
        q=q,
    )
    return [_vehicle_response(item) for item in views]


@router.post(
    "/vehicles",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    payload: VehicleCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> VehicleResponse:
    del current_user
    try:
        return _vehicle_response(ResourceService(session).create_vehicle(_vehicle_input(payload)))
    except Exception as exc:
        _resource_error(exc)
        raise


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> VehicleResponse:
    del current_user
    try:
        return _vehicle_response(ResourceService(session).get_vehicle(vehicle_id))
    except Exception as exc:
        _resource_error(exc)
        raise


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> VehicleResponse:
    del current_user
    try:
        changes = payload.model_dump(exclude_unset=True)
        return _vehicle_response(ResourceService(session).update_vehicle(vehicle_id, changes))
    except Exception as exc:
        _resource_error(exc)
        raise


@router.put("/vehicles/{vehicle_id}/cost-profile", response_model=VehicleResponse)
def update_vehicle_cost_profile(
    vehicle_id: uuid.UUID,
    payload: VehicleCostUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> VehicleResponse:
    del current_user
    try:
        view = ResourceService(session).update_vehicle_cost(
            vehicle_id,
            owned_cost=_owned_input(payload.owned_cost),
            aggregated_contract=_contract_input(payload.aggregated_contract),
        )
        return _vehicle_response(view)
    except Exception as exc:
        _resource_error(exc)
        raise


@router.post("/vehicles/{vehicle_id}/deactivate", response_model=VehicleResponse)
def deactivate_vehicle(
    vehicle_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> VehicleResponse:
    del current_user
    try:
        return _vehicle_response(ResourceService(session).deactivate_vehicle(vehicle_id))
    except Exception as exc:
        _resource_error(exc)
        raise


@router.get("/workers", response_model=list[WorkerResponse])
def list_workers(
    session: DbSession,
    current_user: CurrentUser,
    active: bool | None = None,
    role: WorkerRole | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> list[WorkerResponse]:
    del current_user
    views = ResourceService(session).list_workers(active=active, role=role, q=q)
    return [_worker_response(item) for item in views]


@router.post(
    "/workers",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_worker(
    payload: WorkerCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> WorkerResponse:
    del current_user
    try:
        return _worker_response(
            ResourceService(session).create_worker(WorkerInput(**payload.model_dump()))
        )
    except Exception as exc:
        _resource_error(exc)
        raise


@router.get("/workers/{worker_id}", response_model=WorkerResponse)
def get_worker(
    worker_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> WorkerResponse:
    del current_user
    try:
        return _worker_response(ResourceService(session).get_worker(worker_id))
    except Exception as exc:
        _resource_error(exc)
        raise


@router.patch("/workers/{worker_id}", response_model=WorkerResponse)
def update_worker(
    worker_id: uuid.UUID,
    payload: WorkerUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> WorkerResponse:
    del current_user
    try:
        changes = payload.model_dump(exclude_unset=True)
        return _worker_response(ResourceService(session).update_worker(worker_id, changes))
    except Exception as exc:
        _resource_error(exc)
        raise


@router.post("/workers/{worker_id}/deactivate", response_model=WorkerResponse)
def deactivate_worker(
    worker_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> WorkerResponse:
    del current_user
    try:
        return _worker_response(ResourceService(session).deactivate_worker(worker_id))
    except Exception as exc:
        _resource_error(exc)
        raise


@router.get(
    "/workers/{worker_id}/availability",
    response_model=WorkerAvailabilityResponse,
)
def get_worker_availability(
    worker_id: uuid.UUID,
    target_date: Annotated[date, Query(alias="date")],
    session: DbSession,
    current_user: CurrentUser,
) -> WorkerAvailabilityResponse:
    del current_user
    try:
        view = ResourceService(session).get_worker_availability(worker_id, target_date)
        return _availability_response(view)
    except Exception as exc:
        _resource_error(exc)
        raise


@router.put(
    "/workers/{worker_id}/availability",
    response_model=WorkerAvailabilityResponse,
)
def set_worker_availability(
    worker_id: uuid.UUID,
    payload: WorkerAvailabilityRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> WorkerAvailabilityResponse:
    del current_user
    try:
        view = ResourceService(session).set_worker_availability(
            worker_id,
            payload.date,
            available=payload.available,
            notes=payload.notes,
        )
        return _availability_response(view)
    except Exception as exc:
        _resource_error(exc)
        raise


@router.get(
    "/operations/{operation_id}/resources",
    response_model=OperationResourcesResponse,
)
def get_operation_resources(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OperationResourcesResponse:
    del current_user
    try:
        view = ResourceService(session).get_operation_resources(operation_id)
        return OperationResourcesResponse(
            operation_id=view.operation_id,
            operation_date=view.operation_date,
            selected_vehicle_ids=view.selected_vehicle_ids,
            selected_worker_ids=view.selected_worker_ids,
            unavailable_worker_ids=view.unavailable_worker_ids,
            vehicles=[_vehicle_response(item) for item in view.vehicles],
            workers=[_worker_response(item) for item in view.workers],
        )
    except Exception as exc:
        _resource_error(exc)
        raise


@router.put(
    "/operations/{operation_id}/resources",
    response_model=OperationResourcesResponse,
)
def update_operation_resources(
    operation_id: uuid.UUID,
    payload: OperationResourceSelectionRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> OperationResourcesResponse:
    del current_user
    try:
        view = ResourceService(session).update_operation_resources(
            operation_id,
            vehicle_ids=payload.vehicle_ids,
            worker_ids=payload.worker_ids,
        )
        return OperationResourcesResponse(
            operation_id=view.operation_id,
            operation_date=view.operation_date,
            selected_vehicle_ids=view.selected_vehicle_ids,
            selected_worker_ids=view.selected_worker_ids,
            unavailable_worker_ids=view.unavailable_worker_ids,
            vehicles=[_vehicle_response(item) for item in view.vehicles],
            workers=[_worker_response(item) for item in view.workers],
        )
    except Exception as exc:
        _resource_error(exc)
        raise
