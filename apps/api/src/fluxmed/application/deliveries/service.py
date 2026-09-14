import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from fluxmed.application.deliveries.importer import ParsedImportRow, parse_delivery_file
from fluxmed.application.deliveries.scenario import ScenarioProfile, generate_scenario
from fluxmed.domain.deliveries import (
    DeliveryValidationError,
    ServiceTimeEstimator,
    validate_delivery_values,
)
from fluxmed.domain.enums import (
    CargoProfile,
    DeliveryPriority,
    DeliveryStatus,
    HandlingRequirement,
    OperationStatus,
    ServiceTimeSource,
    TemperatureClass,
    TimeWindowPolicy,
)
from fluxmed.infrastructure.models.delivery import DeliveryImportModel, DeliveryModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.repositories.delivery_repository import (
    AddressContext,
    DeliveryRepository,
)


class DeliveryNotFoundError(LookupError):
    pass


class DeliveryAddressNotFoundError(LookupError):
    pass


class DeliveryImportNotFoundError(LookupError):
    pass


class DeliveryImportValidationError(ValueError):
    pass


class DeliveryMutationBlockedError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeliveryInput:
    invoice_number: str
    invoice_series: str
    issuer_document: str
    recipient_name: str
    destination_address_id: uuid.UUID
    package_count: int
    total_weight_kg: Decimal
    total_volume_m3: Decimal
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    issuer_name: str | None = None
    external_reference: str | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    time_window_policy: TimeWindowPolicy = TimeWindowPolicy.SOFT
    temperature_class: TemperatureClass = TemperatureClass.AMBIENT
    handling_requirement: HandlingRequirement = HandlingRequirement.STANDARD
    service_time_minutes: int | None = None
    cargo_profile: CargoProfile | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryView:
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


@dataclass(frozen=True, slots=True)
class DeliveryPage:
    items: list[DeliveryView]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    generated_count: int
    critical_count: int
    refrigerated_count: int
    hard_window_count: int
    total_weight_kg: Decimal
    total_volume_m3: Decimal


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    seed: int
    summary: ScenarioSummary
    deliveries: list[DeliveryView]


@dataclass(frozen=True, slots=True)
class DeliveryImportView:
    id: uuid.UUID
    operation_id: uuid.UUID
    filename: str
    file_type: str
    status: str
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    rows: list[dict[str, object]]
    created_at: datetime
    confirmed_at: datetime | None


class DeliveryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._deliveries = DeliveryRepository(session)
        self._estimator = ServiceTimeEstimator()

    def create(self, operation_id: uuid.UUID, payload: DeliveryInput) -> DeliveryView:
        operation = self._require_mutable_operation(operation_id)
        context = self._require_address(payload.destination_address_id)
        model = self._create_model(
            operation_id=operation_id,
            payload=payload,
            context=context,
            explicit_source=ServiceTimeSource.MANUAL,
        )
        self._touch_operation(operation)
        self._session.flush()
        return self._view(model, context)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        operation_id: uuid.UUID | None = None,
        priority: DeliveryPriority | None = None,
        temperature_class: TemperatureClass | None = None,
        status: DeliveryStatus | None = None,
        district_id: uuid.UUID | None = None,
        q: str | None = None,
    ) -> DeliveryPage:
        rows, total = self._deliveries.list_page(
            page=page,
            page_size=page_size,
            operation_id=operation_id,
            priority=priority,
            temperature_class=temperature_class,
            status=status,
            district_id=district_id,
            q=q,
        )
        items: list[DeliveryView] = []
        for model, street_name, district_name in rows:
            context = self._deliveries.address_context(model.destination_address_id)
            if context is None:
                raise DeliveryAddressNotFoundError(model.destination_address_id)
            items.append(self._view(model, context, street_name, district_name))
        return DeliveryPage(items=items, page=page, page_size=page_size, total=total)

    def list_for_operation(
        self,
        operation_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
    ) -> DeliveryPage:
        self._require_operation(operation_id)
        return self.list(page=page, page_size=page_size, operation_id=operation_id)

    def get(self, delivery_id: uuid.UUID) -> DeliveryView:
        model = self._require_delivery(delivery_id)
        context = self._require_address(model.destination_address_id)
        return self._view(model, context)

    def update(
        self,
        operation_id: uuid.UUID,
        delivery_id: uuid.UUID,
        changes: dict[str, Any],
    ) -> DeliveryView:
        operation = self._require_mutable_operation(operation_id)
        model = self._require_delivery(delivery_id)
        if model.operation_id != operation_id:
            raise DeliveryNotFoundError(delivery_id)

        editable = {
            "invoice_number",
            "invoice_series",
            "issuer_document",
            "issuer_name",
            "external_reference",
            "destination_address_id",
            "recipient_name",
            "package_count",
            "total_weight_kg",
            "total_volume_m3",
            "priority",
            "time_window_start",
            "time_window_end",
            "time_window_policy",
            "temperature_class",
            "handling_requirement",
            "service_time_minutes",
            "cargo_profile",
            "notes",
        }
        unknown = set(changes) - editable
        if unknown:
            raise DeliveryValidationError(f"Campos não editáveis: {', '.join(sorted(unknown))}.")

        required_fields = {
            "invoice_number",
            "invoice_series",
            "issuer_document",
            "destination_address_id",
            "recipient_name",
            "package_count",
            "total_weight_kg",
            "total_volume_m3",
            "priority",
            "time_window_policy",
            "temperature_class",
            "handling_requirement",
        }
        null_required = sorted(
            field for field in required_fields if field in changes and changes[field] is None
        )
        if null_required:
            raise DeliveryValidationError(
                f"Campos obrigatórios não podem ser nulos: {', '.join(null_required)}."
            )

        address_value = changes.get(
            "destination_address_id",
            model.destination_address_id,
        )
        context = self._require_address(address_value)
        package_count = int(str(changes.get("package_count", model.package_count)))
        total_weight_kg = Decimal(str(changes.get("total_weight_kg", model.total_weight_kg)))
        total_volume_m3 = Decimal(str(changes.get("total_volume_m3", model.total_volume_m3)))
        time_window_start = changes.get("time_window_start", model.time_window_start)
        time_window_end = changes.get("time_window_end", model.time_window_end)
        handling_value = changes.get(
            "handling_requirement",
            model.handling_requirement,
        )
        handling_requirement = (
            handling_value
            if isinstance(handling_value, HandlingRequirement)
            else HandlingRequirement(str(handling_value))
        )

        reset_service_time = (
            "service_time_minutes" in changes and changes["service_time_minutes"] is None
        )
        if reset_service_time:
            estimate = self._estimator.estimate(
                building_type=context.building.building_type,
                package_count=package_count,
                total_weight_kg=total_weight_kg,
                total_volume_m3=total_volume_m3,
                handling_requirement=handling_requirement,
            )
            service_time_minutes = estimate.selected_minutes
            service_time_source = ServiceTimeSource.ESTIMATED
        elif "service_time_minutes" in changes:
            service_time_minutes = int(str(changes["service_time_minutes"]))
            service_time_source = ServiceTimeSource.MANUAL
        else:
            service_time_minutes = model.service_time_minutes
            service_time_source = model.service_time_source

        if time_window_start is not None and not isinstance(time_window_start, datetime):
            raise DeliveryValidationError("Início da janela inválido.")
        if time_window_end is not None and not isinstance(time_window_end, datetime):
            raise DeliveryValidationError("Fim da janela inválido.")
        validate_delivery_values(
            package_count=package_count,
            total_weight_kg=total_weight_kg,
            total_volume_m3=total_volume_m3,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            service_time_minutes=service_time_minutes,
        )

        for field, value in changes.items():
            if field == "service_time_minutes" and value is None:
                continue
            setattr(model, field, value)
        model.service_time_minutes = service_time_minutes
        model.service_time_source = service_time_source
        self._touch_operation(operation)
        self._session.flush()
        return self._view(model, context)

    def delete(self, operation_id: uuid.UUID, delivery_id: uuid.UUID) -> None:
        operation = self._require_mutable_operation(operation_id)
        model = self._require_delivery(delivery_id)
        if model.operation_id != operation_id:
            raise DeliveryNotFoundError(delivery_id)
        self._deliveries.delete(model)
        self._touch_operation(operation)
        self._session.flush()

    def generate_scenario(
        self,
        operation_id: uuid.UUID,
        *,
        profile: ScenarioProfile,
        delivery_count: int,
        random_seed: int | None,
    ) -> ScenarioResult:
        operation = self._require_mutable_operation(operation_id)
        seed = random_seed if random_seed is not None else secrets.randbelow(2_000_000_000)
        batch = generate_scenario(
            address_pool=self._deliveries.scenario_address_pool(),
            operation_date=operation.operation_date,
            operation_start_time=operation.operation_start_time,
            operation_end_time=operation.operation_end_time,
            profile=profile,
            delivery_count=delivery_count,
            seed=seed,
        )
        created: list[DeliveryView] = []
        for spec in batch.deliveries:
            payload = DeliveryInput(
                invoice_number=spec.invoice_number,
                invoice_series=spec.invoice_series,
                issuer_document=spec.issuer_document,
                issuer_name=spec.issuer_name,
                recipient_name=spec.recipient_name,
                destination_address_id=spec.destination_address_id,
                package_count=spec.package_count,
                total_weight_kg=spec.total_weight_kg,
                total_volume_m3=spec.total_volume_m3,
                priority=spec.priority,
                time_window_start=spec.time_window_start,
                time_window_end=spec.time_window_end,
                time_window_policy=spec.time_window_policy,
                temperature_class=spec.temperature_class,
                handling_requirement=spec.handling_requirement,
                cargo_profile=spec.cargo_profile,
                notes=spec.notes,
            )
            context = self._require_address(spec.destination_address_id)
            model = self._create_model(
                operation_id=operation_id,
                payload=payload,
                context=context,
                explicit_source=ServiceTimeSource.ESTIMATED,
            )
            self._session.flush()
            created.append(self._view(model, context))

        self._touch_operation(operation)
        self._session.flush()
        summary = ScenarioSummary(
            generated_count=len(created),
            critical_count=sum(item.priority is DeliveryPriority.CRITICAL for item in created),
            refrigerated_count=sum(
                item.temperature_class is TemperatureClass.REFRIGERATED for item in created
            ),
            hard_window_count=sum(
                item.time_window_policy is TimeWindowPolicy.HARD for item in created
            ),
            total_weight_kg=sum(
                (item.total_weight_kg for item in created),
                Decimal("0"),
            ),
            total_volume_m3=sum(
                (item.total_volume_m3 for item in created),
                Decimal("0"),
            ),
        )
        return ScenarioResult(seed=batch.seed, summary=summary, deliveries=created)

    def create_import_preview(
        self,
        operation_id: uuid.UUID,
        *,
        created_by_user_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> DeliveryImportView:
        operation = self._require_mutable_operation(operation_id)
        rows = parse_delivery_file(
            filename=filename,
            content=content,
            operation_date=operation.operation_date,
            resolve_address=self._deliveries.find_exact_address,
        )
        serializable_rows = [self._import_row_dict(row) for row in rows]
        model = DeliveryImportModel(
            operation_id=operation_id,
            created_by_user_id=created_by_user_id,
            filename=filename,
            file_type=filename.rsplit(".", 1)[-1].lower(),
            status="REVIEW",
            total_rows=len(rows),
            valid_rows=sum(row.status == "VALID" for row in rows),
            warning_rows=sum(row.status == "WARNING" for row in rows),
            error_rows=sum(row.status == "ERROR" for row in rows),
            rows_json=serializable_rows,
        )
        self._session.add(model)
        self._session.flush()
        return self._import_view(model)

    def get_import(self, import_id: uuid.UUID) -> DeliveryImportView:
        return self._import_view(self._require_import(import_id))

    def confirm_import(self, import_id: uuid.UUID) -> DeliveryImportView:
        model = self._require_import(import_id)
        if model.status == "CONFIRMED":
            return self._import_view(model)
        if model.error_rows:
            raise DeliveryImportValidationError(
                "A importação possui erros bloqueantes e não pode ser confirmada."
            )
        operation = self._require_mutable_operation(model.operation_id)
        for row in model.rows_json:
            if row.get("status") == "ERROR":
                continue
            normalized = row.get("normalized")
            if not isinstance(normalized, dict):
                raise DeliveryImportValidationError("Linha normalizada inválida na importação.")
            self._create_imported_delivery(model.operation_id, normalized)

        model.status = "CONFIRMED"
        model.confirmed_at = datetime.now(UTC)
        self._touch_operation(operation)
        self._session.flush()
        return self._import_view(model)

    def delete_import(self, import_id: uuid.UUID) -> None:
        model = self._require_import(import_id)
        if model.status == "CONFIRMED":
            raise DeliveryImportValidationError(
                "Uma importação já confirmada não pode ser removida."
            )
        self._session.delete(model)
        self._session.flush()

    def _create_imported_delivery(
        self,
        operation_id: uuid.UUID,
        normalized: dict[str, object],
    ) -> DeliveryModel:
        address_id = uuid.UUID(str(normalized["destination_address_id"]))
        context = self._require_address(address_id)
        service_raw = normalized.get("service_time_minutes")
        payload = DeliveryInput(
            invoice_number=str(normalized["invoice_number"]),
            invoice_series=str(normalized["invoice_series"]),
            issuer_document=str(normalized["issuer_document"]),
            issuer_name=self._optional_text(normalized.get("issuer_name")),
            external_reference=self._optional_text(normalized.get("external_reference")),
            recipient_name=str(normalized["recipient_name"]),
            destination_address_id=address_id,
            package_count=int(str(normalized["package_count"])),
            total_weight_kg=Decimal(str(normalized["total_weight_kg"])),
            total_volume_m3=Decimal(str(normalized["total_volume_m3"])),
            priority=DeliveryPriority(str(normalized["priority"])),
            time_window_start=self._optional_datetime(normalized.get("time_window_start")),
            time_window_end=self._optional_datetime(normalized.get("time_window_end")),
            time_window_policy=TimeWindowPolicy(str(normalized["time_window_policy"])),
            temperature_class=TemperatureClass(str(normalized["temperature_class"])),
            handling_requirement=HandlingRequirement(str(normalized["handling_requirement"])),
            service_time_minutes=(int(str(service_raw)) if service_raw is not None else None),
            notes=self._optional_text(normalized.get("notes")),
        )
        source = (
            ServiceTimeSource.IMPORTED if service_raw is not None else ServiceTimeSource.ESTIMATED
        )
        return self._create_model(
            operation_id=operation_id,
            payload=payload,
            context=context,
            explicit_source=source,
        )

    def _create_model(
        self,
        *,
        operation_id: uuid.UUID,
        payload: DeliveryInput,
        context: AddressContext,
        explicit_source: ServiceTimeSource,
    ) -> DeliveryModel:
        if not payload.invoice_number.strip():
            raise DeliveryValidationError("Número da NF é obrigatório.")
        if not payload.invoice_series.strip():
            raise DeliveryValidationError("Série da NF é obrigatória.")
        if not payload.issuer_document.strip():
            raise DeliveryValidationError("Documento do emissor é obrigatório.")
        if not payload.recipient_name.strip():
            raise DeliveryValidationError("Destinatário é obrigatório.")

        if payload.service_time_minutes is None:
            estimate = self._estimator.estimate(
                building_type=context.building.building_type,
                package_count=payload.package_count,
                total_weight_kg=payload.total_weight_kg,
                total_volume_m3=payload.total_volume_m3,
                handling_requirement=payload.handling_requirement,
            )
            service_time_minutes = estimate.selected_minutes
            service_time_source = ServiceTimeSource.ESTIMATED
        else:
            service_time_minutes = payload.service_time_minutes
            service_time_source = explicit_source

        validate_delivery_values(
            package_count=payload.package_count,
            total_weight_kg=payload.total_weight_kg,
            total_volume_m3=payload.total_volume_m3,
            time_window_start=payload.time_window_start,
            time_window_end=payload.time_window_end,
            service_time_minutes=service_time_minutes,
        )
        model = DeliveryModel(
            delivery_code=self._deliveries.next_delivery_code(payload.invoice_number),
            operation_id=operation_id,
            invoice_number=payload.invoice_number.strip(),
            invoice_series=payload.invoice_series.strip(),
            issuer_document=payload.issuer_document.strip(),
            issuer_name=self._clean_optional(payload.issuer_name),
            external_reference=self._clean_optional(payload.external_reference),
            destination_address_id=payload.destination_address_id,
            recipient_name=payload.recipient_name.strip(),
            package_count=payload.package_count,
            total_weight_kg=payload.total_weight_kg,
            total_volume_m3=payload.total_volume_m3,
            priority=payload.priority,
            time_window_start=payload.time_window_start,
            time_window_end=payload.time_window_end,
            time_window_policy=payload.time_window_policy,
            service_time_minutes=service_time_minutes,
            service_time_source=service_time_source,
            temperature_class=payload.temperature_class,
            handling_requirement=payload.handling_requirement,
            status=DeliveryStatus.PENDING,
            cargo_profile=payload.cargo_profile,
            notes=self._clean_optional(payload.notes),
        )
        self._deliveries.add(model)
        return model

    def _require_operation(self, operation_id: uuid.UUID) -> OperationModel:
        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise DeliveryNotFoundError(operation_id)
        return operation

    def _require_mutable_operation(self, operation_id: uuid.UUID) -> OperationModel:
        operation = self._require_operation(operation_id)
        if operation.status is OperationStatus.DISPATCHED:
            raise DeliveryMutationBlockedError("Uma operação despachada é imutável.")
        if operation.status is OperationStatus.OPTIMIZING:
            raise DeliveryMutationBlockedError(
                "Não altere entregas enquanto a otimização está em execução."
            )
        return operation

    @staticmethod
    def _touch_operation(operation: OperationModel) -> None:
        if operation.status in {
            OperationStatus.OPTIMIZED,
            OperationStatus.APPROVED,
        }:
            operation.status = OperationStatus.OUTDATED
        elif operation.status is OperationStatus.READY:
            operation.status = OperationStatus.DRAFT

    def _require_delivery(self, delivery_id: uuid.UUID) -> DeliveryModel:
        model = self._deliveries.get_by_id(delivery_id)
        if model is None:
            raise DeliveryNotFoundError(delivery_id)
        return model

    def _require_address(self, address_id: object) -> AddressContext:
        try:
            parsed_id = (
                address_id if isinstance(address_id, uuid.UUID) else uuid.UUID(str(address_id))
            )
        except (TypeError, ValueError) as exc:
            raise DeliveryAddressNotFoundError(address_id) from exc
        context = self._deliveries.address_context(parsed_id)
        if context is None:
            raise DeliveryAddressNotFoundError(parsed_id)
        return context

    def _require_import(self, import_id: uuid.UUID) -> DeliveryImportModel:
        model = self._session.get(DeliveryImportModel, import_id)
        if model is None:
            raise DeliveryImportNotFoundError(import_id)
        return model

    @staticmethod
    def _view(
        model: DeliveryModel,
        context: AddressContext,
        street_name: str | None = None,
        district_name: str | None = None,
    ) -> DeliveryView:
        destination = (
            f"{street_name}, {context.address.house_number} — {district_name}"
            if street_name is not None and district_name is not None
            else context.formatted
        )
        return DeliveryView(
            id=model.id,
            delivery_code=model.delivery_code,
            operation_id=model.operation_id,
            invoice_number=model.invoice_number,
            invoice_series=model.invoice_series,
            issuer_document=model.issuer_document,
            issuer_name=model.issuer_name,
            external_reference=model.external_reference,
            destination_address_id=model.destination_address_id,
            destination_address=destination,
            district_name=district_name or context.district_name,
            recipient_name=model.recipient_name,
            package_count=model.package_count,
            total_weight_kg=model.total_weight_kg,
            total_volume_m3=model.total_volume_m3,
            priority=model.priority,
            time_window_start=model.time_window_start,
            time_window_end=model.time_window_end,
            time_window_policy=model.time_window_policy,
            service_time_minutes=model.service_time_minutes,
            service_time_source=model.service_time_source,
            temperature_class=model.temperature_class,
            handling_requirement=model.handling_requirement,
            status=model.status,
            cargo_profile=model.cargo_profile,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _import_row_dict(row: ParsedImportRow) -> dict[str, object]:
        return {
            "row_number": row.row_number,
            "status": row.status,
            "normalized": row.normalized,
            "errors": row.errors,
            "warnings": row.warnings,
        }

    @staticmethod
    def _import_view(model: DeliveryImportModel) -> DeliveryImportView:
        return DeliveryImportView(
            id=model.id,
            operation_id=model.operation_id,
            filename=model.filename,
            file_type=model.file_type,
            status=model.status,
            total_rows=model.total_rows,
            valid_rows=model.valid_rows,
            warning_rows=model.warning_rows,
            error_rows=model.error_rows,
            rows=model.rows_json,
            created_at=model.created_at,
            confirmed_at=model.confirmed_at,
        )

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_datetime(value: object) -> datetime | None:
        if value is None or value == "":
            return None
        return datetime.fromisoformat(str(value))
