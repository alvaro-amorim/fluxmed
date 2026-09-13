"""SQLAlchemy persistence models.

Importing this package registers the current models in Base.metadata for Alembic.
"""

from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.city import (
    CityModel,
    DistrictModel,
    IntersectionModel,
    RoadSegmentModel,
    StreetModel,
)
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.operation_revision import OperationRevisionModel
from fluxmed.infrastructure.models.user import UserModel

__all__ = [
    "AuthSessionModel",
    "CityModel",
    "DistrictModel",
    "IntersectionModel",
    "OperationModel",
    "OperationRevisionModel",
    "RoadSegmentModel",
    "StreetModel",
    "UserModel",
]
