import os
import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fluxmed.domain.enums import OperationStatus, TrafficMode, UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration


def test_preflight_endpoint_blocks_incomplete_operation() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    email = f"preflight-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"
    operation_id: uuid.UUID
    user_id: uuid.UUID

    with session_scope() as session:
        user = UserModel(
            email=email,
            display_name="Preflight API Test",
            password_hash=hash_password(password),
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
        operation = OperationModel(
            operation_code=f"OP-PREF-{uuid.uuid4().hex[:8]}",
            operation_date=date(2026, 9, 16),
            operation_start_time=time(7, 30),
            operation_end_time=time(18, 0),
            traffic_mode=TrafficMode.AUTOMATIC,
            status=OperationStatus.DRAFT,
            current_revision_number=0,
            created_by_user_id=user_id,
        )
        session.add(operation)
        session.flush()
        operation_id = operation.id

    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200

            response = client.post(f"/api/v1/operations/{operation_id}/validate")
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "INVALID"
            assert {item["code"] for item in body["blocking_errors"]} == {
                "NO_DELIVERIES",
                "NO_VEHICLES",
            }
            assert body["summary"]["delivery_count"] == 0
            assert body["summary"]["vehicle_count"] == 0
            assert body["summary"]["operation_window_minutes"] == 630
    finally:
        with session_scope() as session:
            session.execute(delete(OperationModel).where(OperationModel.id == operation_id))
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
            session.execute(delete(UserModel).where(UserModel.id == user_id))
