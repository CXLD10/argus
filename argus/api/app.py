"""FastAPI application factory for the Argus API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from argus import __version__
from argus.api.routers import ai, aoi, hydro, impact, observations, predictions, waterbody
from argus.api.routers import health as health_router

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    db_path: Path = Path("argus.db"),
    config_dir: Path = Path("config"),
) -> FastAPI:
    """Create and configure the Argus FastAPI application."""
    app = FastAPI(
        title="Argus Environmental Intelligence API",
        version=__version__,
        description="Water health intelligence: oil slicks, water quality, flooding, choke points.",
        openapi_tags=[
            {"name": "meta", "description": "Health and liveness probes."},
            {"name": "aois", "description": "Area-of-interest management."},
            {"name": "observations", "description": "Detected environmental observations."},
            {"name": "predictions", "description": "Trajectory and forecast predictions."},
            {"name": "impact", "description": "Exposure-layer impact assessments."},
            {"name": "waterbody", "description": "Water body forecast and skill-gate endpoints."},
            {"name": "ai", "description": "Grounded AI reports, NL query, and anomaly explanations."},
            {"name": "hydro", "description": "Choke points, flood risk, and acid deposition risk (D3/D4)."},
        ],
    )
    app.state.db_path = db_path
    app.state.config_dir = config_dir

    app.include_router(health_router.router)
    app.include_router(aoi.router, prefix="/aois", tags=["aois"])
    app.include_router(observations.router, prefix="/aois", tags=["observations"])
    app.include_router(predictions.router, prefix="/aois", tags=["predictions"])
    app.include_router(impact.router, prefix="/aois", tags=["impact"])
    app.include_router(hydro.router, prefix="/aois", tags=["hydro"])
    app.include_router(waterbody.router, tags=["waterbody"])
    app.include_router(ai.router, tags=["ai"])

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        """Serve the Argus dashboard."""
        return FileResponse(_STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    return app
