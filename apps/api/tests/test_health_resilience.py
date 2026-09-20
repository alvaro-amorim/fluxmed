import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from fluxmed.api.errors import database_error_handler
from fluxmed.infrastructure import database


def test_database_readiness_returns_true_when_probe_succeeds(monkeypatch) -> None:
    class HealthySession:
        def execute(self, _statement: object) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(database, "SessionFactory", HealthySession)

    assert database.database_is_ready() is True


def test_database_readiness_returns_false_when_probe_fails(monkeypatch) -> None:
    class BrokenSession:
        def execute(self, _statement: object) -> None:
            raise SQLAlchemyError("sensitive database detail")

        def close(self) -> None:
            return None

    monkeypatch.setattr(database, "SessionFactory", BrokenSession)

    assert database.database_is_ready() is False


def test_database_error_handler_returns_sanitized_service_unavailable() -> None:
    test_app = FastAPI()
    test_app.add_exception_handler(SQLAlchemyError, database_error_handler)

    @test_app.get("/boom")
    def boom() -> None:
        raise SQLAlchemyError("password=super-secret")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "super-secret" not in json.dumps(payload)


def test_database_error_handler_can_be_called_directly() -> None:
    response = asyncio.run(
        database_error_handler(
            object(),  # type: ignore[arg-type]
            SQLAlchemyError("sensitive detail"),
        )
    )

    assert response.status_code == 503
