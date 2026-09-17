import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ENV = Path(__file__).resolve().parents[3] / ".env"
if _PROJECT_ENV.is_file():
    load_dotenv(dotenv_path=_PROJECT_ENV, override=False)

_test_database_url = os.getenv("TEST_DATABASE_URL")
if _test_database_url:
    # Test modules import the application database engine at collection time.
    # Point DATABASE_URL at the explicit test database before those imports happen.
    os.environ["DATABASE_URL"] = _test_database_url
