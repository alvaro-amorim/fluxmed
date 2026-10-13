import logging
from datetime import timedelta

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

from fluxmed.api.dependencies import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_HOURS,
    CurrentUser,
    DbSession,
)
from fluxmed.api.errors import ApiError
from fluxmed.application.auth import (
    AuthenticatedUser,
    AuthService,
    InactiveUserError,
    InvalidCredentialsError,
)
from fluxmed.domain.enums import UserRole
from fluxmed.security.http import session_cookie_samesite, session_cookie_secure

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: UserRole


class LoginResponse(BaseModel):
    user: UserResponse


def _user_response(user: AuthenticatedUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, session: DbSession) -> LoginResponse:
    auth_service = AuthService(session, timedelta(hours=SESSION_TTL_HOURS))
    try:
        result = auth_service.login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        logger.warning("auth_login_failed reason=invalid_credentials")
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_CREDENTIALS",
            "E-mail ou senha inválidos.",
        ) from exc
    except InactiveUserError as exc:
        logger.warning("auth_login_failed reason=inactive_user")
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "USER_INACTIVE",
            "Este usuário está inativo.",
        ) from exc

    logger.info(
        "auth_login_succeeded user_id=%s role=%s",
        result.user.id,
        result.user.role.value,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=result.token,
        max_age=SESSION_TTL_HOURS * 60 * 60,
        httponly=True,
        secure=session_cookie_secure(),
        samesite=session_cookie_samesite(),
        path="/",
    )
    return LoginResponse(user=_user_response(result.user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: DbSession,
    current_user: CurrentUser,
) -> Response:
    auth_service = AuthService(session, timedelta(hours=SESSION_TTL_HOURS))
    auth_service.logout(request.cookies.get(SESSION_COOKIE_NAME))
    logger.info("auth_logout user_id=%s", current_user.id)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=session_cookie_secure(),
        httponly=True,
        samesite=session_cookie_samesite(),
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return _user_response(current_user)
