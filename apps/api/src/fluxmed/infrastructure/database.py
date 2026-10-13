import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://fluxmed:fluxmed@localhost:5432/fluxmed",
    )


def get_database_connect_timeout_seconds() -> int:
    return max(1, int(os.getenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "3")))


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = database_url or get_database_url()
    if resolved_url.startswith("postgresql"):
        return create_engine(
            resolved_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": get_database_connect_timeout_seconds()},
        )
    return create_engine(resolved_url, pool_pre_ping=True)


engine = create_database_engine()
SessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def database_is_ready() -> bool:
    session = SessionFactory()
    try:
        session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
