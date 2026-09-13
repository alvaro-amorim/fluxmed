import os
from collections.abc import Callable, Iterator
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request, status
from sqlalchemy.orm import Session

from fluxmed.api.errors import ApiError
from fluxmed.application.auth import (
    AuthService,
    AuthenticatedUser,
    InactiveUserError,
    InvalidSessionError,
)
from fluxmed.domain.enums import UserRole
from fluxmed.infrastructure.database import SessionFactory

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "fluxmed_session")
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "8"))


def get_db_session() -> Iterator[Session]:
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db_session)]


def get_current_user(request: Request, session: DbSession) -> AuthenticatedUser:
    auth_service = AuthService(session, timedelta(hours=SESSION_TTL_HOURS))
    try:
        return auth_service.authenticate(request.cookies.get(SESSION_COOKIE_NAME))
    except InvalidSessionError as exc:
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_REQUIRED",
            "Autenticação necessária.",
        ) from exc
    except InactiveUserError as exc:
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "USER_INACTIVE",
            "Este usuário está inativo.",
        ) from exc


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def ensure_role(user: AuthenticatedUser, allowed_roles: set[UserRole]) -> None:
    if user.role not in allowed_roles:
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN_ACTION",
            "Você não tem permissão para realizar esta ação.",
        )


def require_roles(*roles: UserRole) -> Callable[..., AuthenticatedUser]:
    allowed_roles = set(roles)

    def dependency(current_user: CurrentUser) -> AuthenticatedUser:
        ensure_role(current_user, allowed_roles)
        return current_user

    return dependency
