import asyncio
import io

import pytest
from fastapi import UploadFile

from fluxmed.api.errors import ApiError
from fluxmed.api.v1.deliveries import _read_import_upload, _safe_import_filename
from fluxmed.security.http import (
    DEFAULT_DELIVERY_IMPORT_MAX_BYTES,
    delivery_import_max_bytes,
    session_cookie_samesite,
    session_cookie_secure,
)


def test_production_forces_secure_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    assert session_cookie_secure() is True


def test_development_can_use_insecure_cookie_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    assert session_cookie_secure() is False


def test_cross_site_cookie_mode_is_rejected_without_csrf_design(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "none")

    with pytest.raises(ValueError, match="lax.*strict"):
        session_cookie_samesite()


def test_delivery_import_limit_has_safe_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DELIVERY_IMPORT_MAX_BYTES", raising=False)

    assert delivery_import_max_bytes() == DEFAULT_DELIVERY_IMPORT_MAX_BYTES


def test_import_filename_drops_client_path_components() -> None:
    assert _safe_import_filename(r"C:\fakepath\entregas.csv") == "entregas.csv"
    assert _safe_import_filename("../../entregas.xlsx") == "entregas.xlsx"


def test_import_upload_rejects_content_over_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DELIVERY_IMPORT_MAX_BYTES", "1024")
    upload = UploadFile(filename="entregas.csv", file=io.BytesIO(b"x" * 1025))

    with pytest.raises(ApiError) as captured:
        asyncio.run(_read_import_upload(upload))

    assert captured.value.status_code == 413
    assert captured.value.code == "IMPORT_FILE_TOO_LARGE"


def test_import_upload_accepts_content_within_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DELIVERY_IMPORT_MAX_BYTES", "1024")
    payload = b"numero_nf,serie_nf\n1,1\n"
    upload = UploadFile(filename="entregas.csv", file=io.BytesIO(payload))

    assert asyncio.run(_read_import_upload(upload)) == payload
