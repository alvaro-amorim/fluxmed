import uuid
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status
from pydantic import BaseModel, Field

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.application.deliveries import (
    DeliveryAddressNotFoundError,
    DeliveryImportNotFoundError,
    DeliveryImportValidationError,
    DeliveryImportView,
    DeliveryInput,
    DeliveryMutationBlockedError,
    DeliveryNotFoundError,
    DeliveryPage,
    DeliveryService,
    DeliveryView,
    ScenarioProfile,
    UnsupportedImportFormatError,
)
from fluxmed.domain.deliveries import DeliveryValidationError
from fluxmed.security.http import delivery_import_max_bytes
from fluxmed.domain.enums import (
    CargoProfile,
    DeliveryPriority,
    DeliveryStatus,
    HandlingRequirement,
    ServiceTimeSource,
    TemperatureClass,
    TimeWindowPolicy,
)

router = APIRouter(tags=["deliveries"])

IMPORT_READ_CHUNK_BYTES = 64 * 1024
MAX_IMPORT_FILENAME_CHARS = 180


def _safe_import_filename(filename: str | None) -> str:
    if filename is None:
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "IMPORT_FILENAME_INVALID",
            "Nome do arquivo é obrigatório.",
        )
    cleaned = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not cleaned or len(cleaned) > MAX_IMPORT_FILENAME_CHARS:
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "IMPORT_FILENAME_INVALID",
            "Nome do arquivo de importação inválido.",
        )
    return cleaned


async def _read_import_upload(file: UploadFile) -> bytes:
    limit = delivery_import_max_bytes()
    content = bytearray()
    while True:
        chunk = await file.read(IMPORT_READ_CHUNK_BYTES)
        if not chunk:
            return bytes(content)
        content.extend(chunk)
        if len(content) > limit:
            raise ApiError(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "IMPORT_FILE_TOO_LARGE",
                "Arquivo de importação excede o limite permitido.",
            )


class DeliveryCreateRequest(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=80)
    invoice_series: str = Field(min_length=1, max_length=40)
    issuer_document: str = Field(min_length=1, max_length=40)
    issuer_name: str | None = Field(default=None, max_length=180)
    external_reference: str | None = Field(default=None, max_length=120)
    recipient_name: str = Field(min_length=1, max_length=180)
    destination_address_id: uuid.UUID
    package_count: int = Field(gt=0)
    total_weight_kg: Decimal = Field(gt=0)
    total_volume_m3: Decimal = Field(gt=0)
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    time_window_policy: TimeWindowPolicy = TimeWindowPolicy.SOFT
    temperature_class: TemperatureClass = TemperatureClass.AMBIENT
    handling_requirement: HandlingRequirement = HandlingRequirement.STANDARD
    service_time_minutes: int | None = Field(default=None, gt=0)
    cargo_profile: CargoProfile | None = None
    notes: str | None = Field(default=None, max_length=1000)


class DeliveryUpdateRequest(BaseModel):
    invoice_number: str | None = Field(default=None, min_length=1, max_length=80)
    invoice_series: str | None = Field(default=None, min_length=1, max_length=40)
    issuer_document: str | None = Field(default=None, min_length=1, max_length=40)
    issuer_name: str | None = Field(default=None, max_length=180)
    external_reference: str | None = Field(default=None, max_length=120)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=180)
    destination_address_id: uuid.UUID | None = None
    package_count: int | None = Field(default=None, gt=0)
    total_weight_kg: Decimal | None = Field(default=None, gt=0)
    total_volume_m3: Decimal | None = Field(default=None, gt=0)
    priority: DeliveryPriority | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    time_window_policy: TimeWindowPolicy | None = None
    temperature_class: TemperatureClass | None = None
    handling_requirement: HandlingRequirement | None = None
    service_time_minutes: int | None = Field(default=None, gt=0)
    cargo_profile: CargoProfile | None = None
    notes: str | None = Field(default=None, max_length=1000)


class DeliveryResponse(BaseModel):
    id: uuid.UUID
    delivery_code: str
    operation_id: uuid.UUID
    invoice_number: str
    invoice_series: str
    issuer_document: str
    issuer_name: str | None
    external_reference: str | None
    destination_address_id: uuid.UUID
    destination_address: str
    district_name: str
    recipient_name: str
    package_count: int
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    priority: DeliveryPriority
    time_window_start: datetime | None
    time_window_end: datetime | None
    time_window_policy: TimeWindowPolicy
    service_time_minutes: int
    service_time_source: ServiceTimeSource
    temperature_class: TemperatureClass
    handling_requirement: HandlingRequirement
    status: DeliveryStatus
    cargo_profile: CargoProfile | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DeliveryListResponse(BaseModel):
    items: list[DeliveryResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class ScenarioRequest(BaseModel):
    profile: ScenarioProfile = ScenarioProfile.NORMAL
    delivery_count: int = Field(default=20, ge=1, le=100)
    random_seed: int | None = Field(default=None, ge=0, le=2_147_483_647)


class ScenarioSummaryResponse(BaseModel):
    generated_count: int
    critical_count: int
    refrigerated_count: int
    hard_window_count: int
    total_weight_kg: Decimal
    total_volume_m3: Decimal


class ScenarioResponse(BaseModel):
    seed: int
    summary: ScenarioSummaryResponse
    validation: dict[str, str]
    deliveries: list[DeliveryResponse]


class DeliveryImportResponse(BaseModel):
    id: uuid.UUID
    operation_id: uuid.UUID
    filename: str
    file_type: str
    status: str
    summary: dict[str, int]
    rows: list[dict[str, object]]
    created_at: datetime
    confirmed_at: datetime | None


def _delivery_response(view: DeliveryView) -> DeliveryResponse:
    return DeliveryResponse(**asdict(view))


def _page_response(page: DeliveryPage) -> DeliveryListResponse:
    return DeliveryListResponse(
        items=[_delivery_response(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        total_pages=page.total_pages,
    )


def _import_response(view: DeliveryImportView) -> DeliveryImportResponse:
    return DeliveryImportResponse(
        id=view.id,
        operation_id=view.operation_id,
        filename=view.filename,
        file_type=view.file_type,
        status=view.status,
        summary={
            "total_rows": view.total_rows,
            "valid_rows": view.valid_rows,
            "warning_rows": view.warning_rows,
            "error_rows": view.error_rows,
        },
        rows=view.rows,
        created_at=view.created_at,
        confirmed_at=view.confirmed_at,
    )


def _input(payload: DeliveryCreateRequest) -> DeliveryInput:
    return DeliveryInput(**payload.model_dump())


def _raise_delivery_error(exc: Exception) -> None:
    if isinstance(exc, DeliveryAddressNotFoundError):
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ADDRESS_NOT_FOUND",
            "O endereço informado não existe no dataset ativo.",
        ) from exc
    if isinstance(exc, DeliveryImportNotFoundError):
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "DELIVERY_IMPORT_NOT_FOUND",
            "Importação não encontrada.",
        ) from exc
    if isinstance(exc, DeliveryNotFoundError):
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "DELIVERY_NOT_FOUND",
            "Entrega ou operação não encontrada.",
        ) from exc
    if isinstance(exc, DeliveryMutationBlockedError):
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "INVALID_OPERATION_STATE",
            str(exc),
        ) from exc
    if isinstance(exc, DeliveryImportValidationError):
        raise ApiError(
            status.HTTP_409_CONFLICT,
            "IMPORT_VALIDATION_FAILED",
            str(exc),
        ) from exc
    if isinstance(exc, UnsupportedImportFormatError):
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "IMPORT_FORMAT_INVALID",
            str(exc),
        ) from exc
    if isinstance(exc, DeliveryValidationError | ValueError):
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_DELIVERY",
            str(exc),
        ) from exc
    raise exc


@router.get("/deliveries", response_model=DeliveryListResponse)
def list_deliveries(
    session: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    operation_id: uuid.UUID | None = None,
    priority: DeliveryPriority | None = None,
    temperature_class: TemperatureClass | None = None,
    delivery_status: Annotated[DeliveryStatus | None, Query(alias="status")] = None,
    district_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> DeliveryListResponse:
    del current_user
    result = DeliveryService(session).list(
        page=page,
        page_size=page_size,
        operation_id=operation_id,
        priority=priority,
        temperature_class=temperature_class,
        status=delivery_status,
        district_id=district_id,
        q=q,
    )
    return _page_response(result)


@router.get("/deliveries/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(
    delivery_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> DeliveryResponse:
    del current_user
    try:
        return _delivery_response(DeliveryService(session).get(delivery_id))
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.get("/operations/{operation_id}/deliveries", response_model=DeliveryListResponse)
def list_operation_deliveries(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
) -> DeliveryListResponse:
    del current_user
    try:
        result = DeliveryService(session).list_for_operation(
            operation_id,
            page=page,
            page_size=page_size,
        )
        return _page_response(result)
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.post(
    "/operations/{operation_id}/deliveries",
    response_model=DeliveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery(
    operation_id: uuid.UUID,
    payload: DeliveryCreateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> DeliveryResponse:
    del current_user
    try:
        return _delivery_response(DeliveryService(session).create(operation_id, _input(payload)))
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.patch(
    "/operations/{operation_id}/deliveries/{delivery_id}",
    response_model=DeliveryResponse,
)
def update_delivery(
    operation_id: uuid.UUID,
    delivery_id: uuid.UUID,
    payload: DeliveryUpdateRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> DeliveryResponse:
    del current_user
    try:
        changes = payload.model_dump(exclude_unset=True)
        return _delivery_response(
            DeliveryService(session).update(
                operation_id,
                delivery_id,
                changes,
            )
        )
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.delete(
    "/operations/{operation_id}/deliveries/{delivery_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_delivery(
    operation_id: uuid.UUID,
    delivery_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> None:
    del current_user
    try:
        DeliveryService(session).delete(operation_id, delivery_id)
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.post(
    "/operations/{operation_id}/generate-scenario",
    response_model=ScenarioResponse,
)
def generate_operation_scenario(
    operation_id: uuid.UUID,
    payload: ScenarioRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ScenarioResponse:
    del current_user
    try:
        result = DeliveryService(session).generate_scenario(
            operation_id,
            profile=payload.profile,
            delivery_count=payload.delivery_count,
            random_seed=payload.random_seed,
        )
        return ScenarioResponse(
            seed=result.seed,
            summary=ScenarioSummaryResponse(**asdict(result.summary)),
            validation={
                "status": "PENDING_RESOURCES",
                "message": ("Endereços validados; capacidade de frota será avaliada no preflight."),
            },
            deliveries=[_delivery_response(item) for item in result.deliveries],
        )
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.post(
    "/operations/{operation_id}/delivery-imports",
    response_model=DeliveryImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_delivery_import(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
) -> DeliveryImportResponse:
    try:
        filename = _safe_import_filename(file.filename)
        content = await _read_import_upload(file)
        view = DeliveryService(session).create_import_preview(
            operation_id,
            created_by_user_id=current_user.id,
            filename=filename,
            content=content,
        )
        return _import_response(view)
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.get(
    "/delivery-imports/{import_id}",
    response_model=DeliveryImportResponse,
)
def get_delivery_import(
    import_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> DeliveryImportResponse:
    del current_user
    try:
        return _import_response(DeliveryService(session).get_import(import_id))
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.post(
    "/delivery-imports/{import_id}/confirm",
    response_model=DeliveryImportResponse,
)
def confirm_delivery_import(
    import_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> DeliveryImportResponse:
    del current_user
    try:
        return _import_response(DeliveryService(session).confirm_import(import_id))
    except Exception as exc:
        _raise_delivery_error(exc)
        raise


@router.delete(
    "/delivery-imports/{import_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_delivery_import(
    import_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> None:
    del current_user
    try:
        DeliveryService(session).delete_import(import_id)
    except Exception as exc:
        _raise_delivery_error(exc)
        raise
