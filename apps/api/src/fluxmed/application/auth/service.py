import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from fluxmed.domain.enums import UserRole
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.infrastructure.repositories import AuthSessionRepository, UserRepository
from fluxmed.security.passwords import hash_password, password_needs_rehash, verify_password
from fluxmed.security.session_tokens import create_session_token, hash_session_token


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: AuthenticatedUser
    token: str
    expires_at: datetime


class AuthService:
    def __init__(self, session: Session, session_ttl: timedelta) -> None:
        self._session = session
        self._session_ttl = session_ttl
        self._users = UserRepository(session)
        self._sessions = AuthSessionRepository(session)

    def login(self, email: str, password: str) -> LoginResult:
        user = self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError
        if not user.active:
            raise InactiveUserError

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        token = create_session_token()
        expires_at = datetime.now(UTC) + self._session_ttl
        self._sessions.add(
            AuthSessionModel(
                user_id=user.id,
                token_hash=hash_session_token(token),
                expires_at=expires_at,
            )
        )
        self._session.flush()
        return LoginResult(user=self._to_identity(user), token=token, expires_at=expires_at)

    def authenticate(self, token: str | None) -> AuthenticatedUser:
        if not token:
            raise InvalidSessionError
        user = self._sessions.get_user_for_token_hash(
            hash_session_token(token), datetime.now(UTC)
        )
        if user is None:
            raise InvalidSessionError
        if not user.active:
            raise InactiveUserError
        return self._to_identity(user)

    def logout(self, token: str | None) -> None:
        if token:
            self._sessions.delete_by_token_hash(hash_session_token(token))

    @staticmethod
    def _to_identity(user: UserModel) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
        )
