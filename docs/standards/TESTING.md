# Argus — Testing Standard

- **Owner:** Architecture Governance
- **Last updated:** 2026-06-27
- **Status:** Active — applies to all implementation work
- **Related:** [CODING.md](CODING.md) · [VALIDATORS.md](../governance/VALIDATORS.md) · CLAUDE.md §8

---

## 1. Principles

1. **Offline by default.** Unit tests never make live network calls. They run on fixtures.
2. **Fast.** The full unit test suite must complete in < 60 seconds.
3. **Deterministic.** Same inputs → same results every time.
4. **Independent.** Each test cleans up after itself. No shared mutable state.
5. **Honest.** Tests assert `evidence_class`, `citations`, and `uncertainty` fields
   explicitly — not by accident.

---

## 2. Test Categories

### 2.1 Unit Tests (`tests/`)

- Offline. No network, no filesystem writes outside a temp dir.
- Use `pytest` fixtures for synthetic data.
- Cover: models, store accessors, domain analyzers (synthetic rasters), predictors (mocked
  inputs), AI grounding guard, config loading.
- Target: 100% of acceptance criteria from feature specs.

### 2.2 Integration Tests (`tests/integration/`)

- Require `--live` flag: `pytest --live tests/integration/`
- **Never run in CI by default.**
- Include: real CDSE catalogue searches, real Open-Meteo calls, real CMEMS fetch.
- Must document quota impact in the test docstring.
- Must be idempotent (re-running does not double-count quota).

### 2.3 End-to-End Tests

- Offline by default (fixture mode): `tests/test_phase0_e2e.py` etc.
- One opt-in live path per phase: run manually against real data once, record result
  in BOARD.md HANDOFF.
- Assert: artifacts exist, schemas are valid, evidence_class correct.

### 2.4 Evaluation Tests (`tests/eval/`)

- Score predictors against `EvalCase` records in `data/eval/`.
- Do not use live data (cases store refs + ground truth, not raw imagery).
- Produce `SkillReport` records; assert `passed_gate` for Phase 5+.

---

## 3. Fixture Patterns

### 3.1 Synthetic Rasters

```python
import numpy as np

def make_synthetic_sar(rows=100, cols=100, dark_spot=True):
    """Return a (rows, cols) float32 array simulating SAR σ⁰ dB.
    dark_spot=True plants a 10x10 dark patch at center."""
    raster = np.full((rows, cols), -12.0, dtype=np.float32)  # water background
    if dark_spot:
        raster[45:55, 45:55] = -25.0  # dark blob
    return raster
```

### 3.2 Mocked HTTP (CDSE, Open-Meteo)

Use `responses` or `pytest-httpx` to intercept HTTP calls. Record a real response once
and store it as a JSON fixture in `tests/fixtures/`. Never make live calls in unit tests.

```python
import responses

@responses.activate
def test_catalogue_search():
    responses.add(
        responses.GET,
        "https://catalogue.dataspace.copernicus.eu/...",
        json=load_fixture("cdse_s1_search_tobago.json"),
    )
    result = search_s1_grd(aoi=tobago_aoi, t0=..., t1=...)
    assert len(result) > 0
```

### 3.3 Mocked LLM (Phase 6+)

```python
# tests/fixtures/ai/report_grounded.json — recorded LLM response
# tests/conftest.py
@pytest.fixture
def mock_anthropic(monkeypatch):
    """Replace Anthropic API client with a fixture-returning mock."""
    from tests.fixtures import load_ai_fixture
    monkeypatch.setattr("argus.ai.client.call_llm", load_ai_fixture)
```

No live Anthropic API calls in the default test suite. EVER.

### 3.4 In-Memory SQLite Store

```python
@pytest.fixture
def store(tmp_path):
    from argus.core.store import Store
    return Store(db_path=tmp_path / "test.db")
```

---

## 4. Honesty Assertions

Every test that creates an `Observation` must assert `evidence_class`:

```python
obs = analyzer.analyze(acquisition)[0]
assert obs.evidence_class in ("measured", "modeled", "inferred")
# Oil slicks must be measured
assert obs.evidence_class == "measured"
# Bloom presence must be inferred
assert obs.evidence_class == "inferred"
# Modeled risk must be modeled
assert prediction.evidence_class == "modeled"
```

Every test that creates a `Prediction` must assert `uncertainty` is non-null:

```python
pred = predictor.predict(ctx, rng_seed=42)
assert pred.uncertainty is not None
assert len(pred.uncertainty) > 0
```

Every test that exercises the AI layer must assert citations:

```python
report = assistant.report(scope)
assert len(report.citations) > 0
for cit in report.citations:
    # Each citation must be a valid record id in the store
    assert store.get_record(cit) is not None
```

---

## 5. Test File Ownership

Each feature spec lists the test files it owns. No two features own the same test file.

| Phase | Test files |
|---|---|
| F-000 | tests/test_smoke.py |
| F-001 | tests/test_config.py, tests/test_aoi_loader.py |
| F-002 | tests/test_catalogue.py |
| F-003 | tests/test_acquire.py, tests/test_store_scene.py |
| F-004 | tests/test_preprocess.py, tests/test_landmask.py |
| F-005 | tests/test_oil_detector.py, tests/test_store_observation.py |
| F-006 | tests/test_export.py, tests/test_phase0_e2e.py |
| F-007 | tests/test_segmentor.py, tests/test_features.py |
| F-008 | tests/test_classifier.py |
| F-009 | tests/test_eval_harness.py |
| F-010 | tests/test_observation_schema.py |
| F-011 | tests/test_oil_trajectory_service.py |
| F-012 | tests/test_forcing_providers.py |
| F-013 | tests/test_forecast_frames.py |
| F-014 | tests/test_impact_assessor.py |
| F-015 | tests/test_api.py |
| F-016 | tests/test_viewer.py (smoke) |
| F-017 | tests/test_alert_delivery.py |
| F-018 | tests/test_api_contracts.py |
| F-019 | tests/harness/test_validators.py |
| F-020 | tests/test_error_handling.py |
| F-021 | tests/test_logging.py |
| F-027 | tests/test_anomaly_detector.py |
| F-028 | tests/test_wq_forecast.py |
| F-029 | tests/test_skill_gate.py |
| F-030 | tests/test_grounding_guard.py |
| F-031 | tests/test_nl_reports.py |
| F-032 | tests/test_nl_query.py |
| F-033 | tests/test_anomaly_explain.py |

---

## 6. CI Configuration

```yaml
# .github/workflows/ci.yml
- name: Run unit tests
  run: pytest tests/ --ignore=tests/integration/ -v

- name: Lint
  run: ruff check argus/ tests/

- name: Type check
  run: mypy argus/ --ignore-missing-imports
```

Live tests: never in CI. Run manually and document quota use in HANDOFF.

---

## 7. Coverage Target

- Phase 0 acceptance criteria: 100% tested (offline)
- Phase 0–3 overall: ≥ 80% line coverage in `argus/`
- Grounding guard: 100% path coverage (critical safety component)
- Evidence class enforcement: 100% path coverage

Run: `pytest --cov=argus --cov-report=term-missing tests/`
