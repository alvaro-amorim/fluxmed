import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.infrastructure.models.user import UserModel


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> UserModel | None:
        normalized_email = email.strip().lower()
        statement = select(UserModel).where(UserModel.email == normalized_email)
        return self._session.scalar(statement)

    def get_by_id(self, user_id: uuid.UUID) -> UserModel | None:
        return self._session.get(UserModel, user_id)

    def add(self, user: UserModel) -> None:
        self._session.add(user)
