from fastapi import FastAPI

from fluxmed.api.errors import ApiError, api_error_handler
from fluxmed.api.v1.auth import router as auth_router
from fluxmed.api.v1.cities import router as cities_router
from fluxmed.api.v1.deliveries import router as deliveries_router
from fluxmed.api.v1.operations import router as operations_router

app = FastAPI(
    title="FluxMed API",
    description="Backend API for FluxMed route planning.",
    version="0.1.0",
)

app.add_exception_handler(ApiError, api_error_handler)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cities_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(deliveries_router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Return process liveness without checking external dependencies."""
    return {"status": "ok"}
