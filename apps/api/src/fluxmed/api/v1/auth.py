import os
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
    AuthService,
    AuthenticatedUser,
    InactiveUserError,
    InvalidCredentialsError,
)
from fluxmed.domain.enums import UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
        raise ApiError(
            status.HTTP_401_UNAUTHORIZED,
            "AUTH_INVALID_CREDENTIALS",
            "E-mail ou senha inválidos.",
        ) from exc
    except InactiveUserError as exc:
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "USER_INACTIVE",
            "Este usuário está inativo.",
        ) from exc

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=result.token,
        max_age=SESSION_TTL_HOURS * 60 * 60,
        httponly=True,
        secure=_env_bool("SESSION_COOKIE_SECURE"),
        samesite="lax",
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
    del current_user
    auth_service = AuthService(session, timedelta(hours=SESSION_TTL_HOURS))
    auth_service.logout(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return _user_response(current_user)
