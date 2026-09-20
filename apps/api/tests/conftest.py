import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

_PROJECT_ENV = Path(__file__).resolve().parents[3] / ".env"
if _PROJECT_ENV.is_file():
    load_dotenv(dotenv_path=_PROJECT_ENV, override=False)

_application_database_url = os.getenv("DATABASE_URL")
_test_database_url = os.getenv("TEST_DATABASE_URL")


def _database_name(database_url: str) -> str:
    return make_url(database_url).database or ""


if _test_database_url:
    test_database_name = _database_name(_test_database_url)
    if "test" not in test_database_name.lower():
        raise RuntimeError(
            "TEST_DATABASE_URL must point to a dedicated test database; "
            f"received database {test_database_name!r}."
        )
    if (
        _application_database_url
        and _database_name(_application_database_url) == test_database_name
    ):
        raise RuntimeError(
            "TEST_DATABASE_URL must not point to the same database as DATABASE_URL."
        )

    # Test modules import the application database engine at collection time.
    # Point DATABASE_URL at the explicit test database before those imports happen.
    os.environ["DATABASE_URL"] = _test_database_url
