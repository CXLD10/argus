#!/usr/bin/env python3
"""F-053: Argus performance benchmark — offline pipeline stage latencies.

Measures each major pipeline stage against targets from phase-11.md spec.
All measurements use synthetic data so no network is required.

Targets:
  scene_acquisition   < 1 s
  sar_preprocess      < 30 s
  oil_detection       < 60 s
  wq_analysis         < 30 s
  wq_forecast_fit     < 30 s
  anomaly_detect      < 5 s
  ai_report_offline   < 30 s
  api_health_latency  < 0.5 s
  full_aoi_run        < 600 s  (10 min)
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# ── Targets ───────────────────────────────────────────────────────────────────

TARGETS_S: dict[str, float] = {
    "scene_acquisition_s": 1.0,
    "sar_preprocess_s": 30.0,
    "oil_detection_s": 60.0,
    "wq_analysis_s": 30.0,
    "wq_forecast_fit_s": 30.0,
    "anomaly_detect_s": 5.0,
    "ai_report_offline_s": 30.0,
    "api_health_latency_s": 0.5,
    "full_aoi_run_s": 600.0,
}

results: dict[str, float] = {}


def _timer(label: str):
    """Context manager: time a block and store result under label."""
    class _T:
        def __enter__(self):
            self.t0 = time.perf_counter()
            return self
        def __exit__(self, *_):
            elapsed = time.perf_counter() - self.t0
            results[label] = elapsed
            status = "✓" if elapsed <= TARGETS_S.get(label, float("inf")) else "✗"
            print(f"  {status} {label}: {elapsed:.3f}s  (target: ≤{TARGETS_S.get(label, '?')}s)")
    return _T()


def _make_synthetic_sar(rows: int = 512, cols: int = 512, seed: int = 42):
    rng = np.random.default_rng(seed)
    vv = rng.uniform(5e-4, 2e-3, (rows, cols)).astype(np.float32)
    vh = rng.uniform(5e-5, 2e-4, (rows, cols)).astype(np.float32)
    vv[200:280, 200:280] = 5e-6
    return vv, vh


def _make_synthetic_optical(rows: int = 512, cols: int = 512, seed: int = 42):
    rng = np.random.default_rng(seed)
    return {
        "B2": rng.uniform(0.04, 0.08, (rows, cols)).astype(np.float32),
        "B3": rng.uniform(0.05, 0.10, (rows, cols)).astype(np.float32),
        "B4": rng.uniform(0.03, 0.06, (rows, cols)).astype(np.float32),
        "B5": rng.uniform(0.06, 0.15, (rows, cols)).astype(np.float32),
        "B6": rng.uniform(0.10, 0.20, (rows, cols)).astype(np.float32),
    }


def _make_synthetic_obs_history(n: int = 90, seed: int = 42):
    from argus.core.models import Observation
    rng = np.random.default_rng(seed)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    obs_list = []
    weather: dict[str, dict] = {}
    for d in range(n):
        doy = (base + timedelta(days=d)).timetuple().tm_yday
        val = 0.05 + 0.02 * math.sin(2 * math.pi * doy / 365) + float(rng.normal(0, 0.003))
        obs_list.append(Observation(
            id=str(uuid.uuid4()),
            analysis_run_id="bench_run",
            scene_id="bench_scene",
            obs_type="chlorophyll_a",
            evidence_class="measured",
            geometry={"type": "Point", "coordinates": [-61.25, 11.15]},
            area_km2=0.5,
            confidence=0.85,
            value=max(0.001, val),
            unit="ndci_index",
            domain="inland_wq",
            target_id="wb-tobago",
            created_at=base + timedelta(days=d),
        ))
        date_str = (base + timedelta(days=d)).date().isoformat()
        weather[date_str] = {
            "precip_7d": float(rng.uniform(0, 20)),
            "temp_7d": float(rng.uniform(22, 32)),
        }
    return obs_list, weather


def main(aoi_slug: str) -> int:
    print(f"\n{'═'*64}")
    print(f"  Argus Performance Benchmark — F-053")
    print(f"  AOI:    {aoi_slug}")
    print(f"  Date:   {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'═'*64}\n")

    full_start = time.perf_counter()

    # ── Scene acquisition (synthetic, simulates filesystem load) ─────────────
    print("Stage 1: Scene acquisition (synthetic)")
    with _timer("scene_acquisition_s"):
        vv, vh = _make_synthetic_sar()

    # ── SAR preprocessing ─────────────────────────────────────────────────────
    print("Stage 2: SAR preprocessing (512×512)")
    from argus.preprocess.landmask import GeoTransform
    from argus.preprocess.sar import preprocess

    with _timer("sar_preprocess_s"):
        transform = GeoTransform(
            min_lon=-61.4, min_lat=11.0, max_lon=-61.1, max_lat=11.3,
            cols=512, rows=512,
        )
        land_mask = np.zeros((512, 512), dtype=bool)
        prep = preprocess(vv, vh, land_mask, transform, "bench-scene-001")

    # ── Oil detection ─────────────────────────────────────────────────────────
    print("Stage 3: Oil detection")
    from argus.domains.base import Acquisition
    from argus.domains.marine_oil.detector import OilDomainV0, make_analysis_run
    from argus.aoi.loader import load_aoi

    aoi_path = _REPO_ROOT / "config" / "aois" / f"{aoi_slug}.geojson"
    if not aoi_path.exists():
        aoi_path = _REPO_ROOT / "config" / "aois" / "tobago.geojson"
    aoi = load_aoi(aoi_path)
    run_obj = make_analysis_run(aoi.id, "bench-scene-001")

    with _timer("oil_detection_s"):
        acq = Acquisition(
            scene_id="bench-scene-001",
            source_ref=None,  # type: ignore[arg-type]
            preprocessed=prep,
            attrs={"analysis_run_id": run_obj.id},
        )
        observations = OilDomainV0().analyze(acq)

    print(f"    → {len(observations)} oil observations")

    # ── WQ analysis ───────────────────────────────────────────────────────────
    print("Stage 4: Water quality analysis (512×512 optical)")
    from argus.domains.inland_wq import InlandWqDomain
    from argus.preprocess.optical import preprocess_optical

    bands = _make_synthetic_optical()
    optical = preprocess_optical(bands)
    wq_acq = Acquisition(
        scene_id="bench-wq-scene-001",
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=optical,
        attrs={"analysis_run_id": "bench_wq_run"},
    )
    with _timer("wq_analysis_s"):
        wq_obs = InlandWqDomain(auth=None).analyze(wq_acq)
    print(f"    → {len(wq_obs)} WQ observations")

    # ── WQ forecast fit ───────────────────────────────────────────────────────
    print("Stage 5: WQ forecast model fit (90 synthetic obs)")
    from argus.predict.wq_forecast import WQForecaster

    hist_obs, hist_weather = _make_synthetic_obs_history(n=90)
    with _timer("wq_forecast_fit_s"):
        forecaster = WQForecaster.from_history(hist_obs, hist_weather, rng_seed=42)

    # ── Anomaly detection ─────────────────────────────────────────────────────
    print("Stage 6: Anomaly detection")
    from argus.predict.anomaly_detector.detector import AnomalyDetector
    from argus.predict.base import PredictContext

    base = datetime(2024, 1, 1, tzinfo=UTC)
    detector = AnomalyDetector()
    detector.fit(hist_obs)

    with _timer("anomaly_detect_s"):
        ctx = PredictContext(
            obs=hist_obs[-5:],
            aoi_id=aoi.id,
            t0=base + timedelta(days=85),
            t1=base + timedelta(days=90),
        )
        _ = detector.predict(ctx, rng_seed=42)

    # ── AI report (offline template, no LLM) ─────────────────────────────────
    print("Stage 7: AI offline report (template, no LLM)")
    import os
    os.environ["ARGUS_AI_OFFLINE"] = "true"
    from argus.ai.base import Scope
    from argus.ai.fallback import generate_template_report

    scope = Scope(
        aoi_id=aoi.id,
        t0=datetime.now(UTC) - timedelta(days=30),
        t1=datetime.now(UTC),
    )
    with _timer("ai_report_offline_s"):
        report = generate_template_report(scope, wq_obs)
    print(f"    → {len(report.citations)} citations, {len(report.text)} chars")

    # ── API health check latency ──────────────────────────────────────────────
    print("Stage 8: API health endpoint latency")
    import tempfile
    from argus.api.app import create_app
    from fastapi.testclient import TestClient

    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "config"
        (config_dir / "aois").mkdir(parents=True)
        (config_dir / "aois" / "tobago.geojson").write_bytes(
            (_REPO_ROOT / "config" / "aois" / "tobago.geojson").read_bytes()
        )
        db_path = Path(tmpdir) / "bench.db"
        app = create_app(db_path=db_path, config_dir=config_dir)
        client = TestClient(app)
        with _timer("api_health_latency_s"):
            _ = client.get("/health")

    # ── Full AOI run latency ──────────────────────────────────────────────────
    results["full_aoi_run_s"] = time.perf_counter() - full_start
    target = TARGETS_S["full_aoi_run_s"]
    elapsed = results["full_aoi_run_s"]
    status = "✓" if elapsed <= target else "✗"
    print(f"\n  {status} full_aoi_run_s: {elapsed:.3f}s  (target: ≤{target}s)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═'*64}")
    print("  RESULTS SUMMARY")
    print(f"{'─'*64}")
    failures = []
    for stage, measured in results.items():
        target = TARGETS_S.get(stage, float("inf"))
        ok = measured <= target
        indicator = "PASS" if ok else "FAIL"
        print(f"  {indicator:4s}  {stage:<30s}  {measured:7.3f}s  / {target}s")
        if not ok:
            failures.append(stage)

    print(f"{'═'*64}")
    if failures:
        print(f"  ✗ {len(failures)} stage(s) exceeded target: {', '.join(failures)}")
    else:
        print("  ✓ All stages within target")
    print(f"{'═'*64}\n")

    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Argus performance benchmark")
    parser.add_argument("--aoi", default="tobago", help="AOI slug to use")
    args = parser.parse_args()
    sys.exit(main(args.aoi))
