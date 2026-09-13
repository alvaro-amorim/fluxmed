import uuid

import pytest

from fluxmed.api.dependencies import ensure_role
from fluxmed.api.errors import ApiError
from fluxmed.application.auth import AuthenticatedUser
from fluxmed.domain.enums import UserRole


def _user(role: UserRole) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid.uuid4(),
        email="user@example.test",
        display_name="Test User",
        role=role,
    )


def test_admin_role_is_allowed_for_admin_action() -> None:
    ensure_role(_user(UserRole.ADMIN), {UserRole.ADMIN})


def test_planner_role_is_rejected_for_admin_action() -> None:
    with pytest.raises(ApiError) as exc_info:
        ensure_role(_user(UserRole.PLANNER), {UserRole.ADMIN})

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN_ACTION"
