import os
import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fluxmed.domain.enums import UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration

UserFactory = Callable[..., tuple[str, str]]


@pytest.fixture
def user_factory() -> Iterator[UserFactory]:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    created_emails: list[str] = []

    def create_user(*, active: bool = True, role: UserRole = UserRole.PLANNER) -> tuple[str, str]:
        email = f"auth-{uuid.uuid4().hex}@example.test"
        password = "TestPassword2026!"
        with session_scope() as session:
            session.add(
                UserModel(
                    email=email,
                    display_name="Auth Test User",
                    password_hash=hash_password(password),
                    role=role,
                    active=active,
                )
            )
        created_emails.append(email)
        return email, password

    yield create_user

    with session_scope() as session:
        user_ids = list(
            session.scalars(UserModel.__table__.select().with_only_columns(UserModel.id).where(
                UserModel.email.in_(created_emails)
            ))
        ) if created_emails else []
        if user_ids:
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id.in_(user_ids)))
        if created_emails:
            session.execute(delete(UserModel).where(UserModel.email.in_(created_emails)))


def test_login_me_and_logout_use_real_server_side_session(user_factory: UserFactory) -> None:
    email, password = user_factory()

    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        assert login_response.json()["user"]["email"] == email
        assert login_response.json()["user"]["role"] == "PLANNER"
        assert "HttpOnly" in login_response.headers["set-cookie"]

        me_response = client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email

        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 204

        after_logout = client.get("/api/v1/auth/me")
        assert after_logout.status_code == 401
        assert after_logout.json()["error"]["code"] == "AUTH_REQUIRED"


def test_login_rejects_wrong_password(user_factory: UserFactory) -> None:
    email, _ = user_factory()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "WrongPassword2026!"}
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_login_rejects_inactive_user(user_factory: UserFactory) -> None:
    email, password = user_factory(active=False)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_INACTIVE"


def test_login_returns_admin_role(user_factory: UserFactory) -> None:
    email, password = user_factory(role=UserRole.ADMIN)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"
