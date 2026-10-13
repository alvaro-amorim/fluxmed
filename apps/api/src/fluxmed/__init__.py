"""FluxMed backend package."""

from pathlib import Path

from dotenv import load_dotenv


def _load_project_environment() -> None:
    """Load the repository-root .env for local development without overriding real env vars."""
    # A Docker or wheel installation may have fewer parent directories than the
    # original monorepo layout. Environment variables are supplied externally there.
    parents = Path(__file__).resolve().parents
    if len(parents) <= 4:
        return
    project_env = parents[4] / ".env"
    if project_env.is_file():
        load_dotenv(dotenv_path=project_env, override=False)


_load_project_environment()
