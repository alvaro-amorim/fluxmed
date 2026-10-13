import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint

from fluxmed.api.errors import (
    ApiError,
    api_error_handler,
    database_error_handler,
    unhandled_error_handler,
)
from fluxmed.api.v1.assistant import router as assistant_router
from fluxmed.api.v1.auth import router as auth_router
from fluxmed.api.v1.cities import router as cities_router
from fluxmed.api.v1.deliveries import router as deliveries_router
from fluxmed.api.v1.demo_resources import router as demo_resources_router
from fluxmed.api.v1.operations import router as operations_router
from fluxmed.api.v1.optimization import router as optimization_router
from fluxmed.api.v1.preflight import router as preflight_router
from fluxmed.api.v1.reports import router as reports_router
from fluxmed.api.v1.resources import router as resources_router
from fluxmed.api.v1.routing import router as routing_router
from fluxmed.application.optimization.trace import OptimizationTraceService
from fluxmed.infrastructure.database import database_is_ready, session_scope

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        with session_scope() as session:
            OptimizationTraceService(session).recover_interrupted_runs()
    except SQLAlchemyError:
        logger.error("Database unavailable during startup recovery")
    yield


app = FastAPI(
    title="FluxMed API",
    description="Backend API for FluxMed route planning.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_observability(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "request_failed request_id=%s method=%s path=%s error=%s",
            request_id,
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        raise

    duration_ms = round((perf_counter() - started_at) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(SQLAlchemyError, database_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cities_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(deliveries_router, prefix="/api/v1")
app.include_router(resources_router, prefix="/api/v1")
app.include_router(demo_resources_router, prefix="/api/v1")
app.include_router(preflight_router, prefix="/api/v1")
app.include_router(routing_router, prefix="/api/v1")
app.include_router(optimization_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Return process liveness without checking external dependencies."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready(response: Response) -> dict[str, object]:
    """Report whether the process can currently reach its required database."""
    database_ready = database_is_ready()
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if database_ready else "degraded",
        "checks": {"database": "ok" if database_ready else "unavailable"},
    }
