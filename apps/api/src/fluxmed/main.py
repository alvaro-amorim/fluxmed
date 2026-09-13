from fastapi import FastAPI

app = FastAPI(
    title="FluxMed API",
    description="Backend API for FluxMed route planning.",
    version="0.1.0",
)


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Return process liveness without checking external dependencies."""
    return {"status": "ok"}
