import uuid
from dataclasses import dataclass
from datetime import date, datetime, time

from fluxmed.domain.enums import OperationStatus, TrafficMode


class InvalidOperationSchedule(ValueError):
    pass


class ImmutableOperationError(ValueError):
    pass


class InvalidOperationTransition(ValueError):
    pass


_ALLOWED_TRANSITIONS: dict[OperationStatus, set[OperationStatus]] = {
    OperationStatus.DRAFT: {OperationStatus.READY},
    OperationStatus.READY: {OperationStatus.DRAFT, OperationStatus.OPTIMIZING},
    OperationStatus.OPTIMIZING: {OperationStatus.OPTIMIZED, OperationStatus.READY},
    OperationStatus.OPTIMIZED: {OperationStatus.OUTDATED, OperationStatus.APPROVED},
    OperationStatus.OUTDATED: {OperationStatus.OPTIMIZING, OperationStatus.DRAFT},
    OperationStatus.APPROVED: {OperationStatus.OUTDATED, OperationStatus.DISPATCHED},
    OperationStatus.DISPATCHED: set(),
}


def validate_operation_window(start_time: time, end_time: time) -> None:
    if end_time <= start_time:
        raise InvalidOperationSchedule("O horário final deve ser posterior ao horário inicial.")


@dataclass(frozen=True, slots=True)
class Operation:
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

    def __post_init__(self) -> None:
        validate_operation_window(self.operation_start_time, self.operation_end_time)
        if self.current_revision_number < 0:
            raise ValueError("current_revision_number cannot be negative")

    def assert_mutable(self) -> None:
        if self.status is OperationStatus.DISPATCHED:
            raise ImmutableOperationError("Operações despachadas são imutáveis.")

    def assert_transition(self, target: OperationStatus) -> None:
        self.assert_mutable()
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidOperationTransition(
                f"Transição inválida de {self.status.value} para {target.value}."
            )
