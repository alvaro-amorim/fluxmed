from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.user import UserModel


class AuthSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, auth_session: AuthSessionModel) -> None:
        self._session.add(auth_session)

    def get_user_for_token_hash(self, token_hash: str, now: datetime) -> UserModel | None:
        statement = (
            select(UserModel)
            .join(AuthSessionModel, AuthSessionModel.user_id == UserModel.id)
            .where(
                AuthSessionModel.token_hash == token_hash,
                AuthSessionModel.expires_at > now,
            )
        )
        return self._session.scalar(statement)

    def delete_by_token_hash(self, token_hash: str) -> None:
        statement = select(AuthSessionModel).where(AuthSessionModel.token_hash == token_hash)
        auth_session = self._session.scalar(statement)
        if auth_session is not None:
            self._session.delete(auth_session)
