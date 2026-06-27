"""FastAPI application factory for the Argus API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from argus.api.routers import aoi, impact, observations, predictions
from argus.api.schemas import HealthResponse


def create_app(
    db_path: Path = Path("argus.db"),
    config_dir: Path = Path("config"),
) -> FastAPI:
    """Create and configure the Argus FastAPI application.

    Args:
        db_path: Path to the SQLite database file.
        config_dir: Directory containing AOI definitions and other config.
    """
    app = FastAPI(
        title="Argus Environmental Intelligence API",
        version="0.1.0",
        description="Water health intelligence: oil slicks, water quality, flooding, choke points.",
    )
    app.state.db_path = db_path
    app.state.config_dir = config_dir

    app.include_router(aoi.router, prefix="/aois", tags=["aois"])
    app.include_router(observations.router, prefix="/aois", tags=["observations"])
    app.include_router(predictions.router, prefix="/aois", tags=["predictions"])
    app.include_router(impact.router, prefix="/aois", tags=["impact"])

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        """Readiness probe — always returns 200 OK."""
        return HealthResponse()

    return app
