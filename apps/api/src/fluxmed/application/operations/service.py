import uuid
from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy.orm import Session

from fluxmed.domain.enums import OperationStatus, TrafficMode
from fluxmed.domain.operations import ImmutableOperationError, Operation, validate_operation_window
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.repositories.operation_repository import OperationRepository


class OperationNotFoundError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class OperationView:
    id: uuid.UUID
    operation_code: str
    operation_date: date
    operation_start_time: time
    operation_end_time: time
    traffic_mode: TrafficMode
    status: OperationStatus
    current_revision_number: int
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class OperationPage:
    items: list[OperationView]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


@dataclass(frozen=True, slots=True)
class OperationUpdate:
    operation_date: date | None = None
    operation_start_time: time | None = None
    operation_end_time: time | None = None
    traffic_mode: TrafficMode | None = None


class OperationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._operations = OperationRepository(session)

    def create(
        self,
        *,
        created_by_user_id: uuid.UUID,
        operation_date: date,
        operation_start_time: time,
        operation_end_time: time,
        traffic_mode: TrafficMode,
    ) -> OperationView:
        validate_operation_window(operation_start_time, operation_end_time)
        operation = OperationModel(
            operation_code=self._operations.next_operation_code(operation_date),
            operation_date=operation_date,
            operation_start_time=operation_start_time,
            operation_end_time=operation_end_time,
            traffic_mode=traffic_mode,
            status=OperationStatus.DRAFT,
            current_revision_number=0,
            created_by_user_id=created_by_user_id,
        )
        self._operations.add(operation)
        self._session.flush()
        return self._view(operation)

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: OperationStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        q: str | None = None,
        sort: str = "updated_at",
        order: str = "desc",
    ) -> OperationPage:
        items, total = self._operations.list_page(
            page=page,
            page_size=page_size,
            status=status,
            date_from=date_from,
            date_to=date_to,
            q=q,
            sort=sort,
            order=order,
        )
        return OperationPage(
            items=[self._view(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get(self, operation_id: uuid.UUID) -> OperationView:
        return self._view(self._require(operation_id))

    def update(self, operation_id: uuid.UUID, changes: OperationUpdate) -> OperationView:
        model = self._require(operation_id)
        current = self._entity(model)
        current.assert_mutable()

        operation_date = changes.operation_date or model.operation_date
        start_time = changes.operation_start_time or model.operation_start_time
        end_time = changes.operation_end_time or model.operation_end_time
        traffic_mode = changes.traffic_mode or model.traffic_mode
        validate_operation_window(start_time, end_time)

        changed = any(
            (
                operation_date != model.operation_date,
                start_time != model.operation_start_time,
                end_time != model.operation_end_time,
                traffic_mode != model.traffic_mode,
            )
        )
        if changed and model.status in {OperationStatus.OPTIMIZED, OperationStatus.APPROVED}:
            model.status = OperationStatus.OUTDATED
        elif changed and model.status is OperationStatus.READY:
            model.status = OperationStatus.DRAFT

        model.operation_date = operation_date
        model.operation_start_time = start_time
        model.operation_end_time = end_time
        model.traffic_mode = traffic_mode
        self._session.flush()
        return self._view(model)

    def _require(self, operation_id: uuid.UUID) -> OperationModel:
        model = self._operations.get_by_id(operation_id)
        if model is None:
            raise OperationNotFoundError(operation_id)
        return model

    @staticmethod
    def _entity(model: OperationModel) -> Operation:
        return Operation(
            id=model.id,
            operation_code=model.operation_code,
            operation_date=model.operation_date,
            operation_start_time=model.operation_start_time,
            operation_end_time=model.operation_end_time,
            traffic_mode=model.traffic_mode,
            status=model.status,
            current_revision_number=model.current_revision_number,
            created_by_user_id=model.created_by_user_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _view(model: OperationModel) -> OperationView:
        entity = OperationService._entity(model)
        return OperationView(
            id=entity.id,
            operation_code=entity.operation_code,
            operation_date=entity.operation_date,
            operation_start_time=entity.operation_start_time,
            operation_end_time=entity.operation_end_time,
            traffic_mode=entity.traffic_mode,
            status=entity.status,
            current_revision_number=entity.current_revision_number,
            created_by_user_id=entity.created_by_user_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


__all__ = [
    "ImmutableOperationError",
    "OperationNotFoundError",
    "OperationPage",
    "OperationService",
    "OperationUpdate",
    "OperationView",
]
