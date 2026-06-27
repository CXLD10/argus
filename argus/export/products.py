"""Phase 0 product export: GeoJSON FeatureCollection and PNG raster overview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from argus.core.models import AnalysisRun, Observation
from argus.preprocess.sar import PreprocessedScene


def export_geojson(
    observations: list[Observation],
    run: AnalysisRun,
    path: Path,
) -> Path:
    """Write a GeoJSON FeatureCollection of Observation polygons to *path*."""
    features = [_obs_to_feature(o) for o in observations]
    collection: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "analysis_run_id": run.id,
            "aoi_id": run.aoi_id,
            "domain_id": run.domain_id,
            "scene_id": run.scene_id,
        },
    }
    path.write_text(json.dumps(collection, indent=2))
    return path


def export_png(
    preprocessed: PreprocessedScene,
    observations: list[Observation],
    path: Path,
    *,
    vmin: float = -35.0,
    vmax: float = -5.0,
) -> Path:
    """Save a PNG: masked VV dB raster with candidate observation polygons overlaid."""
    fig = Figure(figsize=(8, 6), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)

    tr = preprocessed.transform
    extent = (tr.min_lon, tr.max_lon, tr.min_lat, tr.max_lat)

    # Replace NaN with vmin so imshow renders land areas in dark grey
    vv_display = np.where(np.isfinite(preprocessed.vv_db), preprocessed.vv_db, vmin)
    img = ax.imshow(
        vv_display,
        extent=extent,
        origin="upper",
        cmap="gray",
        vmin=vmin,
        vmax=vmax,
        aspect="auto",
    )
    fig.colorbar(img, ax=ax, label="VV σ⁰ (dB)")

    seen_labels: set[str] = set()
    for obs in observations:
        geom = obs.geometry
        label = "candidate" if "candidate" not in seen_labels else "_nolegend_"
        seen_labels.add("candidate")
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                xs = [c[0] for c in ring]
                ys = [c[1] for c in ring]
                ax.plot(xs, ys, color="red", linewidth=1.5, label=label)
        elif geom["type"] == "Point":
            c = geom["coordinates"]
            ax.plot(c[0], c[1], "r+", markersize=10, label=label)

    if seen_labels:
        ax.legend()

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"VV dB — {preprocessed.scene_id}")

    fig.tight_layout()
    fig.savefig(path)
    return path


def export_products(
    observations: list[Observation],
    run: AnalysisRun,
    preprocessed: PreprocessedScene,
    output_dir: Path,
) -> dict[str, Path]:
    """Export GeoJSON + PNG for a completed analysis run; return artifact paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    run_tag = run.id[:8]
    return {
        "geojson": export_geojson(
            observations,
            run,
            output_dir / f"observations_{run_tag}.geojson",
        ),
        "png": export_png(
            preprocessed,
            observations,
            output_dir / f"raster_{run_tag}.png",
        ),
    }


def _obs_to_feature(obs: Observation) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": obs.geometry,
        "properties": {
            "id": obs.id,
            "obs_type": obs.obs_type,
            "evidence_class": obs.evidence_class,
            "area_km2": obs.area_km2,
            "confidence": obs.confidence,
            "status": obs.status,
            "analysis_run_id": obs.analysis_run_id,
            "scene_id": obs.scene_id,
        },
    }
