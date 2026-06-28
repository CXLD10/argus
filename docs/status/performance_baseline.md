# Performance Baseline

- **Status:** Active
- **Last updated:** 2026-06-29
- **Owner:** CXLD10

Measured pipeline stage latencies from the F-053 benchmark.
Run: `python scripts/benchmark/run_benchmark.py`

---

## Baseline Measurements (2026-06-29)

**Environment:** WSL2, Intel/AMD, no GPU, Python 3.13, offline mode (no network)

| Stage | Measured | Target | Status |
|---|---|---|---|
| Scene acquisition (synthetic SAR 512×512) | 0.016 s | < 1 s | PASS |
| SAR preprocessing (512×512) | 0.082 s | < 30 s | PASS |
| Oil detection | 0.045 s | < 60 s | PASS |
| WQ optical analysis (512×512) | 0.004 s | < 30 s | PASS |
| WQ forecast model fit (90 obs) | 0.013 s | < 30 s | PASS |
| Anomaly detection | < 0.001 s | < 5 s | PASS |
| AI report (offline template) | < 0.001 s | < 30 s | PASS |
| API health endpoint latency | 0.005 s | < 0.5 s | PASS |
| Full AOI run (all stages combined) | 0.960 s | < 600 s | PASS |

**All 9 stages pass.** Offline pipeline completes in ~1 second — well within the 10-minute target.

---

## Notes

- Measurements use 512×512 synthetic arrays (realistic for Sentinel-1/2 tiles).
- Trajectory simulation is excluded from the offline benchmark (subprocess calling
  OpenDrift requires live install; measured separately when needed).
- WQ forecast fit uses 90 synthetic observations — a realistic minimum history.
- Live network stages (CDSE acquisition, Open-Meteo fetch) are excluded from
  default benchmark. These are bounded by external API latency, not by Argus code.
- The AI report uses the deterministic template fallback (ARGUS_AI_OFFLINE=true).
  Live LLM call latency depends on Anthropic API — not measured here.

---

## Re-running

```bash
# Offline benchmark (all targets must pass)
python scripts/benchmark/run_benchmark.py

# With shell wrapper
./scripts/benchmark/run_benchmark.sh --aoi gulf-paria-tt
```

Results are printed to stdout with PASS/FAIL per stage.
