import os

import pytest
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.integration


def _test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    return url


def test_postgis_and_foundation_tables_are_available() -> None:
    engine = create_engine(_test_database_url(), pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            postgis_version = connection.scalar(text("SELECT PostGIS_Version()"))

        table_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert postgis_version
    assert {"alembic_version", "users", "operations"}.issubset(table_names)
