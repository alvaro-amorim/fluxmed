import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fluxmed.domain.enums import OperationStatus, RevisionStatus, UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.operation_revision import OperationRevisionModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client() -> Iterator[TestClient]:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    user_id = uuid.uuid4()
    email = f"operations-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"
    with session_scope() as session:
        session.add(
            UserModel(
                id=user_id,
                email=email,
                display_name="Operations Test User",
                password_hash=hash_password(password),
                role=UserRole.PLANNER,
                active=True,
            )
        )

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        yield client

    with session_scope() as session:
        operation_ids = list(
            session.scalars(
                OperationModel.__table__.select()
                .with_only_columns(OperationModel.id)
                .where(OperationModel.created_by_user_id == user_id)
            )
        )
        if operation_ids:
            session.execute(
                delete(OperationRevisionModel).where(
                    OperationRevisionModel.operation_id.in_(operation_ids)
                )
            )
            session.execute(delete(OperationModel).where(OperationModel.id.in_(operation_ids)))
        session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
        session.execute(delete(UserModel).where(UserModel.id == user_id))


def _payload() -> dict[str, str]:
    return {
        "operation_date": "2026-09-14",
        "operation_start_time": "07:30:00",
        "operation_end_time": "18:00:00",
        "traffic_mode": "AUTOMATIC",
    }


def test_create_list_detail_and_update_operation(authenticated_client: TestClient) -> None:
    created = authenticated_client.post("/api/v1/operations", json=_payload())
    assert created.status_code == 201
    body = created.json()
    assert body["operation_code"].startswith("OP-20260914-")
    assert body["status"] == "DRAFT"
    assert body["city_name"] == "Santa Aurora"

    operation_id = body["id"]
    listed = authenticated_client.get("/api/v1/operations?q=OP-20260914")
    assert listed.status_code == 200
    assert any(item["id"] == operation_id for item in listed.json()["items"])

    detail = authenticated_client.get(f"/api/v1/operations/{operation_id}")
    assert detail.status_code == 200
    assert detail.json()["operation_start_time"] == "07:30:00"

    updated = authenticated_client.patch(
        f"/api/v1/operations/{operation_id}",
        json={"operation_start_time": "08:00:00", "traffic_mode": "FREE"},
    )
    assert updated.status_code == 200
    assert updated.json()["operation_start_time"] == "08:00:00"
    assert updated.json()["traffic_mode"] == "FREE"


def test_rejects_invalid_operation_end_time(authenticated_client: TestClient) -> None:
    payload = _payload()
    payload["operation_end_time"] = "06:00:00"

    response = authenticated_client.post("/api/v1/operations", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OPERATION_SCHEDULE"


def test_dispatches_only_approved_operation(authenticated_client: TestClient) -> None:
    created = authenticated_client.post("/api/v1/operations", json=_payload())
    assert created.status_code == 201
    operation_id = uuid.UUID(created.json()["id"])

    with session_scope() as session:
        operation = session.get(OperationModel, operation_id)
        assert operation is not None
        operation.status = OperationStatus.APPROVED
        operation.current_revision_number = 1
        session.add(
            OperationRevisionModel(
                operation_id=operation.id,
                revision_number=1,
                status=RevisionStatus.APPROVED,
                operation_date=operation.operation_date,
                operation_start_time=operation.operation_start_time,
                operation_end_time=operation.operation_end_time,
                traffic_mode=operation.traffic_mode,
                created_by_user_id=operation.created_by_user_id,
            )
        )

    dispatched = authenticated_client.post(f"/api/v1/operations/{operation_id}/dispatch")
    assert dispatched.status_code == 200
    assert dispatched.json()["status"] == "DISPATCHED"

    with session_scope() as session:
        operation = session.get(OperationModel, operation_id)
        assert operation is not None
        assert operation.status is OperationStatus.DISPATCHED
        revision = (
            session.query(OperationRevisionModel)
            .filter_by(
                operation_id=operation_id,
                revision_number=1,
            )
            .one()
        )
        assert revision.status is RevisionStatus.DISPATCHED
        assert revision.dispatched_at is not None


def test_dispatch_rejects_non_approved_operation(authenticated_client: TestClient) -> None:
    created = authenticated_client.post("/api/v1/operations", json=_payload())
    assert created.status_code == 201
    operation_id = created.json()["id"]

    response = authenticated_client.post(f"/api/v1/operations/{operation_id}/dispatch")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OPERATION_DISPATCH_BLOCKED"


def test_dispatched_operation_is_immutable(authenticated_client: TestClient) -> None:
    created = authenticated_client.post("/api/v1/operations", json=_payload())
    assert created.status_code == 201
    operation_id = uuid.UUID(created.json()["id"])

    with session_scope() as session:
        operation = session.get(OperationModel, operation_id)
        assert operation is not None
        operation.status = OperationStatus.DISPATCHED

    response = authenticated_client.patch(
        f"/api/v1/operations/{operation_id}", json={"traffic_mode": "FREE"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OPERATION_ALREADY_DISPATCHED"
