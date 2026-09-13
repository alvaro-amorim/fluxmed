import uuid
from datetime import date

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from fluxmed.domain.enums import OperationStatus
from fluxmed.infrastructure.models.operation import OperationModel


class OperationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, operation: OperationModel) -> None:
        self._session.add(operation)

    def get_by_id(self, operation_id: uuid.UUID) -> OperationModel | None:
        return self._session.get(OperationModel, operation_id)

    def next_operation_code(self, operation_date: date) -> str:
        prefix = f"OP-{operation_date:%Y%m%d}-"
        statement = (
            select(OperationModel.operation_code)
            .where(OperationModel.operation_code.like(f"{prefix}%"))
            .order_by(OperationModel.operation_code.desc())
            .limit(1)
        )
        latest = self._session.scalar(statement)
        sequence = int(latest.rsplit("-", 1)[1]) + 1 if latest else 1
        return f"{prefix}{sequence:03d}"

    def list_page(
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
    ) -> tuple[list[OperationModel], int]:
        filters: list[ColumnElement[bool]] = []
        if status is not None:
            filters.append(OperationModel.status == status)
        if date_from is not None:
            filters.append(OperationModel.operation_date >= date_from)
        if date_to is not None:
            filters.append(OperationModel.operation_date <= date_to)
        if q:
            filters.append(OperationModel.operation_code.ilike(f"%{q.strip()}%"))

        count_statement = select(func.count()).select_from(OperationModel).where(*filters)
        total = int(self._session.scalar(count_statement) or 0)

        sort_columns = {
            "created_at": OperationModel.created_at,
            "updated_at": OperationModel.updated_at,
            "operation_date": OperationModel.operation_date,
            "operation_code": OperationModel.operation_code,
        }
        sort_column = sort_columns.get(sort, OperationModel.updated_at)
        ordering = sort_column.asc() if order == "asc" else sort_column.desc()
        statement = (
            select(OperationModel)
            .where(*filters)
            .order_by(ordering, OperationModel.operation_code.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self._session.scalars(statement)), total
