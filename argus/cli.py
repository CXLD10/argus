"""Argus CLI entry point."""

from pathlib import Path
from typing import Annotated

import typer

from argus import __version__

_DEFAULT_OUTPUT_DIR = Path(".argus")
_DEFAULT_CONFIG_DIR = Path("config")

app = typer.Typer(
    name="argus",
    help="Argus Environmental Intelligence Platform.",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    """Argus Environmental Intelligence Platform."""


@app.command()
def version() -> None:
    """Print the Argus version and exit."""
    typer.echo(f"argus {__version__}")


@app.command()
def run(
    aoi: Annotated[str, typer.Option("--aoi", help="AOI name (config/aois/<name>.geojson)")],
    since: Annotated[str, typer.Option("--since", help="Start date YYYY-MM-DD")],
    live: Annotated[
        bool, typer.Option("--live", help="Use live CDSE data (requires credentials)")
    ] = False,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="Artifact output directory")
    ] = _DEFAULT_OUTPUT_DIR,
    config_dir: Annotated[
        Path, typer.Option("--config-dir", hidden=True, help="Config root")
    ] = _DEFAULT_CONFIG_DIR,
) -> None:
    """Run the detection pipeline for an AOI."""
    import numpy as np

    from argus.aoi.loader import AOIError, load_aoi
    from argus.domains.base import Acquisition
    from argus.domains.marine_oil.detector import OilDomainV0, make_analysis_run
    from argus.export.products import export_products
    from argus.preprocess.landmask import GeoTransform
    from argus.preprocess.sar import preprocess

    aoi_path = config_dir / "aois" / f"{aoi}.geojson"
    if not aoi_path.exists():
        typer.echo(f"error: AOI file not found: {aoi_path}", err=True)
        raise typer.Exit(1)

    try:
        aoi_obj = load_aoi(aoi_path)
    except AOIError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from None

    typer.echo(f"AOI: {aoi_obj.id}")

    if live:
        typer.echo("error: --live not yet implemented in Phase 0; run without --live", err=True)
        raise typer.Exit(1)

    typer.echo(f"offline: synthetic SAR for {aoi_obj.id} / {since}")

    bbox = aoi_obj.bbox  # (min_lon, min_lat, max_lon, max_lat)
    rows, cols = 100, 100
    rng = np.random.default_rng(42)
    vv_linear = rng.uniform(5e-4, 2e-3, (rows, cols)).astype(np.float32)
    vh_linear = rng.uniform(5e-5, 2e-4, (rows, cols)).astype(np.float32)
    # Plant a dark blob to represent a spill candidate
    vv_linear[35:55, 35:55] = 5e-6
    vh_linear[35:55, 35:55] = 5e-7

    transform = GeoTransform(
        min_lon=bbox[0],
        min_lat=bbox[1],
        max_lon=bbox[2],
        max_lat=bbox[3],
        cols=cols,
        rows=rows,
    )
    land_mask = np.zeros((rows, cols), dtype=bool)
    scene_id = f"synthetic-{aoi}-{since}"
    prep = preprocess(vv_linear, vh_linear, land_mask, transform, scene_id)

    run_obj = make_analysis_run(aoi_obj.id, scene_id)
    acq = Acquisition(
        scene_id=scene_id,
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=prep,
        attrs={"analysis_run_id": run_obj.id},
    )
    observations = OilDomainV0().analyze(acq)
    typer.echo(f"detected: {len(observations)} observation(s)")

    run_output_dir = output_dir / aoi / since
    artifacts = export_products(observations, run_obj, prep, run_output_dir)
    typer.echo(f"geojson: {artifacts['geojson']}")
    typer.echo(f"png:     {artifacts['png']}")


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Bind port")] = 8000,
    db_path: Annotated[Path, typer.Option("--db-path", help="SQLite database path")] = Path(
        "argus.db"
    ),
    config_dir: Annotated[
        Path, typer.Option("--config-dir", hidden=True, help="Config root")
    ] = _DEFAULT_CONFIG_DIR,
) -> None:
    """Start the Argus API server."""
    import uvicorn

    from argus.api.app import create_app

    fastapi_app = create_app(db_path=db_path, config_dir=config_dir)
    uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    app()
