import uuid

from fastapi import APIRouter

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.v1.resources import (
    OperationResourcesResponse,
    _resource_error,
    _vehicle_response,
    _worker_response,
)
from fluxmed.application.resources.demo import ensure_demo_operation_resources

router = APIRouter(tags=["resources"])


@router.post(
    "/operations/{operation_id}/resources/demo",
    response_model=OperationResourcesResponse,
)
def generate_demo_operation_resources(
    operation_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> OperationResourcesResponse:
    del current_user
    try:
        view = ensure_demo_operation_resources(session, operation_id)
        return OperationResourcesResponse(
            operation_id=view.operation_id,
            operation_date=view.operation_date,
            selected_vehicle_ids=view.selected_vehicle_ids,
            selected_worker_ids=view.selected_worker_ids,
            unavailable_worker_ids=view.unavailable_worker_ids,
            vehicles=[_vehicle_response(item) for item in view.vehicles],
            workers=[_worker_response(item) for item in view.workers],
        )
    except Exception as exc:
        _resource_error(exc)
        raise
