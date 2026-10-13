import os
from typing import Literal, cast

CookieSameSite = Literal["lax", "strict"]

DEFAULT_DELIVERY_IMPORT_MAX_BYTES = 5 * 1024 * 1024


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def app_environment() -> str:
    return os.getenv("APP_ENV", "development").strip().lower()


def session_cookie_secure() -> bool:
    if app_environment() == "production":
        return True
    return _env_bool("SESSION_COOKIE_SECURE", False)


def session_cookie_samesite() -> CookieSameSite:
    value = os.getenv("SESSION_COOKIE_SAMESITE", "lax").strip().lower()
    if value not in {"lax", "strict"}:
        raise ValueError("SESSION_COOKIE_SAMESITE must be 'lax' or 'strict' in FluxMed V1.")
    return cast(CookieSameSite, value)


def delivery_import_max_bytes() -> int:
    raw = os.getenv(
        "DELIVERY_IMPORT_MAX_BYTES",
        str(DEFAULT_DELIVERY_IMPORT_MAX_BYTES),
    )
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("DELIVERY_IMPORT_MAX_BYTES must be an integer.") from exc
    if value <= 0:
        raise ValueError("DELIVERY_IMPORT_MAX_BYTES must be greater than zero.")
    return value
