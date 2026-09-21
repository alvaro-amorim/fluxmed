import asyncio
import json
import logging
import re
from types import SimpleNamespace

from fastapi.testclient import TestClient

from fluxmed.api.errors import unhandled_error_handler
from fluxmed.main import app


def test_request_observability_adds_request_id_without_logging_query_secrets(
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="fluxmed.main")

    with TestClient(app) as client:
        response = client.get("/health/live?token=super-secret")

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)

    application_logs = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "fluxmed.main"
    )
    assert "request_complete" in application_logs
    assert "path=/health/live" in application_logs
    assert "super-secret" not in application_logs
    assert "token=" not in application_logs


def test_unhandled_error_response_is_sanitized() -> None:
    request = SimpleNamespace(state=SimpleNamespace(request_id="request-123"))

    response = asyncio.run(
        unhandled_error_handler(
            request,  # type: ignore[arg-type]
            RuntimeError("password=super-secret"),
        )
    )

    assert response.status_code == 500
    payload = json.loads(response.body)
    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert payload["error"]["details"]["request_id"] == "request-123"
    assert "super-secret" not in json.dumps(payload)
