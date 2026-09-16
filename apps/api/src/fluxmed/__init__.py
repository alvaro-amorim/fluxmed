"""FluxMed backend package."""

from pathlib import Path

from dotenv import load_dotenv


def _load_project_environment() -> None:
    """Load the repository-root .env for local development without overriding real env vars."""
    project_env = Path(__file__).resolve().parents[4] / ".env"
    if project_env.is_file():
        load_dotenv(dotenv_path=project_env, override=False)


_load_project_environment()
