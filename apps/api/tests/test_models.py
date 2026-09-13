import fluxmed.infrastructure.models  # noqa: F401
from fluxmed.infrastructure.database import Base


def test_foundation_models_are_registered() -> None:
    assert {"users", "operations"}.issubset(Base.metadata.tables)
