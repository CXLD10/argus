# Test Fixtures

This directory contains static fixture data used by the offline test suite (INV-7: no live network in CI).

| File | Used by | Description |
|---|---|---|
| `cdse_s1_search_tobago.json` | `test_catalogue.py` | 2-product CDSE STAC search response for Tobago, Feb 2024. Products in reverse chronological order (proves sort). |
| `cmems_currents_tobago.parquet` | `test_forcing_providers.py` | Minimal CMEMS surface current parquet fixture (u/v components, 4 cells). |
| `labeled_detections.json` | `test_classifier.py` | 15 confirmed oil-slick + 15 look-alike labeled detections for classifier training/validation. |
| `open_meteo_winds_tobago.json` | `test_forcing_providers.py` | Open-Meteo hourly wind stub for Tobago, 24 hours. |
| `sar_with_blob_and_noise.npy` | `test_segmentor.py`, `test_features.py` | 2×200×200 float32 array: VV (channel 0) and VH (channel 1) with a planted 20×20 dark blob and salt-pepper noise patches. |
| `synthetic_sar_100x100.npy` | `test_preprocess.py`, `test_landmask.py` | 2×100×100 float32 synthetic SAR array for preprocessing tests. |

## Adding New Fixtures

1. Name the file descriptively: `<source>_<aoi>_<purpose>.<ext>`
2. Keep fixtures small (< 1 MB). Large binary data belongs in `data/eval/` or is fetched at live-test time.
3. Update this README.
4. Reference in the relevant test file's docstring.
5. Note quota impact in CLAUDE.md §9 if the fixture was derived from a live fetch.
