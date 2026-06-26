# Argus — Coding Standard

- **Owner:** Architecture Governance
- **Last updated:** 2026-06-27
- **Status:** Active — applies to all implementation work
- **Related:** [TESTING.md](TESTING.md) · [VALIDATORS.md](../governance/VALIDATORS.md) · CLAUDE.md

---

## 1. Language + Tooling

- Python 3.11+
- Package manager: `uv` (preferred) or Poetry
- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `mypy` (lenient to start; stricter as codebase matures)
- Test runner: `pytest`

---

## 2. Module Ownership

Each feature spec lists the files it **owns** (creates or is the sole editor of within its
phase). No two in-flight features may own the same file simultaneously. Ownership means:

- Only the owning feature's task may create or substantially edit the file
- Other tasks that need to call the module do so through its public interface
- Ownership transfers at phase boundary if a later feature needs to extend

---

## 3. Architecture Rules

### 3.1 Store Access

```python
# CORRECT
from argus.core.store import Store
store = Store(db_path=config.artifact_dir / "argus.db")
obs = store.get_observations(target_id=target.id)

# WRONG — never access SQLite directly
import sqlite3
conn = sqlite3.connect("argus.db")
```

### 3.2 Domain Interface

```python
# CORRECT — implement Domain protocol
from argus.domains.base import Domain
class MyDomain(Domain):
    domain_id = "my_domain"
    def search(self, target, t0, t1): ...
    def acquire(self, ref): ...
    def analyze(self, acq): ...

# WRONG — put domain logic in spine modules
# argus/ingest/my_domain_logic.py ← never
```

### 3.3 GPL Isolation

```python
# CORRECT — subprocess wrapper only in argus/predict/oil_trajectory/
# argus/predict/oil_trajectory/runner.py
import subprocess
result = subprocess.run(["python", "sim_worker.py", ...], capture_output=True)

# WRONG — anywhere else
import opendrift  # ← GPL contamination
```

### 3.4 Evidence Class

```python
# CORRECT — always set evidence_class explicitly
Observation(
    obs_type="oil_slick",
    evidence_class="measured",  # required; never omit
    ...
)

# WRONG — omit it or make it nullable in practice
Observation(obs_type="oil_slick")  # evidence_class missing
```

---

## 4. File Naming

| Kind | Convention | Example |
|---|---|---|
| Module | `snake_case.py` | `oil_darkspot.py` |
| Class | `PascalCase` | `OilTrajectory` |
| Function | `snake_case` | `analyze_sar` |
| Constant | `UPPER_SNAKE` | `MIN_WATER_BODY_HA` |
| Config file | `snake_case.yaml` | `oil_types.yaml` |
| Test file | `test_<module>.py` | `test_oil_detector.py` |
| Fixture | `<domain>_<description>.json` | `cdse_s1_search_tobago.json` |

---

## 5. Comments

Default: no comments. Add a comment only when the WHY is non-obvious:
- A hidden constraint (e.g., API quirk, quota interaction)
- A subtle invariant (e.g., "must process VV before VH or correlation breaks")
- A workaround for a specific upstream bug

Never comment WHAT the code does; well-named identifiers do that.
Never reference the current task or issue number in code (use the commit message).

---

## 6. Secrets and Credentials

- Never commit credentials. Use environment variables only.
- `config.py` reads from env; never from a `.env` file checked into git.
- `.gitignore` must include: `.env`, `*.pem`, `credentials.json`, `token.json`
- If a test inadvertently logs a credential: that is a defect, not a warning.

---

## 7. Quota Tracking

Every code path that fetches data from CDSE or Open-Meteo must update
`Scene.bytes_or_calls`. If a function fetches data and doesn't record quota usage, it
is incomplete. This is enforced by VAL-011 and code review.

```python
scene = Scene(
    ...
    bytes_or_calls=response.headers.get("Content-Length", 0),
)
```

---

## 8. Rng Seeds

Every stochastic operation (Monte Carlo simulation, random splits, augmentation) must accept
a `rng_seed: int` parameter and use it consistently. The seed is stored in `Prediction.rng_seed`.
Default seed for test fixtures: 42.

---

## 9. Incremental Development Pattern

Each phase spec lists features in dependency order. Within a feature:
1. Write the data model / schema change first (store.py, models.py)
2. Write the implementation second
3. Write the tests third (or TDD — write tests first, then implement)
4. Acceptance criteria must all pass before marking DONE in BOARD.md

Never mark a feature DONE if its tests are skipped or xfail.
