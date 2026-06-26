# Argus — Quota and Attribution Standard

- **Owner:** Architecture Governance
- **Last updated:** 2026-06-27
- **Status:** Active — applies to all data access code
- **Related:** PRD NFR-1, NFR-5 · ADR-0002 D3, D4 · CLAUDE.md §9

---

## Free Tier Limits

| Source | Free Limit | Attribution Required | Tracked By |
|---|---|---|---|
| CDSE (Sentinel-1/2/3/5P) | ~1 GB/day (general-user quota) | Copernicus Programme | Scene.bytes_or_calls |
| Open-Meteo | ≤ 10,000 API calls/day | **CC BY 4.0 (required in all outputs)** | Scene.bytes_or_calls |
| Copernicus DEM / HydroSHEDS | Free (bulk download, one-time per AOI) | Copernicus Programme | One-time log entry |
| CMEMS (Copernicus Marine) | Free (general-user registration) | Copernicus Marine | Scene.bytes_or_calls |
| Anthropic API | Free/educational credits only | Not required | AIReport.model |

---

## Open-Meteo Attribution (Binding)

Any platform output derived from Open-Meteo data **must** include this attribution:

> Weather/forecast data provided by [Open-Meteo](https://open-meteo.com/) under CC BY 4.0.

This must appear in:
- Any API response that includes Open-Meteo-derived data (as a `_attribution` field)
- Any exported product (PDF, GeoJSON) that uses Open-Meteo data
- The web viewer's "About" or footer section
- Any AI-generated report that references weather data

---

## Quota Tracking Rules

### Per Acquisition

Every `Scene` record must populate `bytes_or_calls`:
- CDSE satellite download: actual bytes transferred (from HTTP Content-Length or measured)
- Open-Meteo API: number of API calls made (1 per HTTP request, not per variable)
- CMEMS: bytes transferred

### Budget Guards

The acquisition code must check the running quota before fetching:

```python
# Pseudocode
daily_bytes = store.sum_bytes_today(source="cdse")
if daily_bytes + estimated_bytes > CDSE_DAILY_LIMIT:
    raise QuotaExceededError("CDSE daily limit approached; aborting fetch.")
```

Constants (set in `config/settings.yaml`):
- `CDSE_DAILY_LIMIT_BYTES`: 900_000_000 (900 MB; 10% safety margin on 1 GB)
- `OPEN_METEO_DAILY_LIMIT_CALLS`: 9_000 (900 calls margin on 10k)
- `CMEMS_DAILY_LIMIT_BYTES`: 500_000_000 (TBD; conservative)

### Prefer Subsets

All acquisition code must prefer area-of-interest subsets over full product downloads.
The Process API (CDSE) is the default path; full downloads are a flagged fallback.

---

## Anthropic API Usage

- Log every API call: model, input_tokens, output_tokens, timestamp → stored in AIReport
- If cumulative monthly cost exceeds the free tier: switch to templated reports automatically
- Never make API calls in unit tests — use recorded responses (see TESTING.md §3.3)
- Pin the model version in config; do not use `claude-latest` or unversioned aliases

---

## Quota Violation Response

If a quota limit is reached:
1. Log a structured warning at WARN level with the source and current usage
2. Stop fetching from that source for the current run
3. Mark the `Scene.ingest_status = "quota_blocked"` (not "failed")
4. The run continues with whatever data was successfully acquired
5. Alert the operator if an alert channel is configured

Do not fail silently. Do not retry in a tight loop.
