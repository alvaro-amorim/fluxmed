import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from fluxmed.infrastructure.database import SessionFactory
from fluxmed.infrastructure.models.assistant_telemetry import AssistantTelemetryModel


@dataclass(frozen=True, slots=True)
class AssistantTelemetryInput:
    request_id: uuid.UUID
    user_id: uuid.UUID
    operation_id: uuid.UUID | None
    provider: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    tool_calls: tuple[dict[str, str], ...]
    tool_failures: int
    status: str
    fallback_used: bool = False
    error_code: str | None = None


class AssistantTelemetryRecorder:
    """Persists metadata only; prompts, tool payloads and assistant text are never stored."""

    @staticmethod
    def count_since(user_id: uuid.UUID, since: datetime) -> int | None:
        session = SessionFactory()
        try:
            value = session.scalar(
                select(func.count())
                .select_from(AssistantTelemetryModel)
                .where(
                    AssistantTelemetryModel.user_id == user_id,
                    AssistantTelemetryModel.created_at >= since,
                )
            )
            return int(value or 0)
        except SQLAlchemyError:
            session.rollback()
            return None
        finally:
            session.close()

    @staticmethod
    def record(payload: AssistantTelemetryInput) -> bool:
        session = SessionFactory()
        try:
            session.add(
                AssistantTelemetryModel(
                    request_id=payload.request_id,
                    user_id=payload.user_id,
                    operation_id=payload.operation_id,
                    provider=payload.provider,
                    model=payload.model,
                    latency_ms=max(payload.latency_ms, 0),
                    input_tokens=max(payload.input_tokens, 0),
                    output_tokens=max(payload.output_tokens, 0),
                    tool_calls=list(payload.tool_calls),
                    tool_failures=max(payload.tool_failures, 0),
                    status=payload.status,
                    fallback_used=payload.fallback_used,
                    error_code=payload.error_code,
                )
            )
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            return False
        finally:
            session.close()
        return True
