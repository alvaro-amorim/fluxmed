import os
import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fluxmed.application.optimization.trace import OptimizationTraceService
from fluxmed.domain.enums import (
    OperationStatus,
    OptimizationRunStatus,
    TrafficMode,
    UserRole,
)
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.optimization_result import OptimizationRunModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration
ZERO = Decimal("0")


def _run(operation: OperationModel, *, status: OptimizationRunStatus) -> OptimizationRunModel:
    return OptimizationRunModel(
        operation_id=operation.id,
        operation_revision_id=None,
        status=status.value,
        random_seed=42,
        generations_completed=0,
        stop_reason=status.value,
        validated=False,
        delivery_count=0,
        vehicles_used=0,
        total_cost_brl=ZERO,
        distance_km=ZERO,
        makespan_minutes=ZERO,
        critical_delays=0,
        on_time_percentage=ZERO,
        average_weight_utilization_pct=ZERO,
        average_volume_utilization_pct=ZERO,
        pruning_counts={},
        previous_operation_status=OperationStatus.READY.value,
        completed_at=None,
    )


def test_trace_events_are_ordered_and_running_jobs_recover_as_interrupted() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    user_id: uuid.UUID
    operation_id: uuid.UUID
    with session_scope() as session:
        user = UserModel(
            email=f"trace-{uuid.uuid4().hex}@example.test",
            display_name="Trace Test",
            password_hash="unused",
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
        operation = OperationModel(
            operation_code=f"OP-TRACE-{uuid.uuid4().hex[:8]}",
            operation_date=date(2026, 9, 17),
            operation_start_time=time(7, 30),
            operation_end_time=time(18, 0),
            traffic_mode=TrafficMode.FREE,
            status=OperationStatus.OPTIMIZING,
            created_by_user_id=user.id,
        )
        session.add(operation)
        session.flush()
        operation_id = operation.id
        run = _run(operation, status=OptimizationRunStatus.RUNNING)
        session.add(run)
        session.flush()
        trace = OptimizationTraceService(session)
        trace.append_event(run.id, "optimization_started", payload={"random_seed": 42})
        trace.append_event(
            run.id,
            "generation_snapshot",
            generation=0,
            payload={"cost_brl": "100"},
        )
        trace.append_event(
            run.id,
            "best_solution_updated",
            generation=1,
            payload={"cost_brl": "90"},
        )

        events = trace.events(run.id)
        assert [event.sequence for event in events] == [1, 2, 3]
        assert [event.sequence for event in trace.events(run.id, after_sequence=1)] == [2, 3]

        recovered = trace.recover_interrupted_runs()
        assert recovered == 1
        assert trace.get_run(run.id).status == OptimizationRunStatus.INTERRUPTED.value
        assert trace.events(run.id)[-1].event_type == "optimization_failed"
        assert trace.events(run.id)[-1].payload["error_code"] == "PROCESS_INTERRUPTED"
        assert operation.status is OperationStatus.READY

    with session_scope() as session:
        session.execute(delete(OperationModel).where(OperationModel.id == operation_id))
        session.execute(delete(UserModel).where(UserModel.id == user_id))


def test_trace_api_replays_persisted_events_and_resumes_from_last_event_id() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    email = f"trace-api-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"
    user_id: uuid.UUID
    operation_id: uuid.UUID
    run_id: uuid.UUID

    with session_scope() as session:
        user = UserModel(
            email=email,
            display_name="Trace API Test",
            password_hash=hash_password(password),
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
        operation = OperationModel(
            operation_code=f"OP-TRACE-API-{uuid.uuid4().hex[:8]}",
            operation_date=date(2026, 9, 17),
            operation_start_time=time(7, 30),
            operation_end_time=time(18, 0),
            traffic_mode=TrafficMode.FREE,
            status=OperationStatus.READY,
            created_by_user_id=user.id,
        )
        session.add(operation)
        session.flush()
        operation_id = operation.id
        run = _run(operation, status=OptimizationRunStatus.COMPLETED)
        run.completed_at = None
        session.add(run)
        session.flush()
        run_id = run.id
        trace = OptimizationTraceService(session)
        trace.append_event(run.id, "optimization_started", payload={"random_seed": 42})
        trace.append_event(
            run.id,
            "generation_snapshot",
            generation=0,
            payload={"cost_brl": "100"},
        )
        trace.append_event(
            run.id,
            "optimization_completed",
            generation=1,
            payload={"status": OptimizationRunStatus.COMPLETED.value},
        )

    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200

            replay = client.get(f"/api/v1/optimization-runs/{run_id}/trace")
            assert replay.status_code == 200
            assert [event["sequence"] for event in replay.json()] == [1, 2, 3]

            stream = client.get(
                f"/api/v1/optimization-runs/{run_id}/events",
                headers={"Last-Event-ID": "1"},
            )
            assert stream.status_code == 200
            assert "event: optimization_started" not in stream.text
            assert "id: 2" in stream.text
            assert "event: generation_snapshot" in stream.text
            assert "id: 3" in stream.text
            assert "event: optimization_completed" in stream.text
    finally:
        with session_scope() as session:
            session.execute(delete(OperationModel).where(OperationModel.id == operation_id))
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
            session.execute(delete(UserModel).where(UserModel.id == user_id))
