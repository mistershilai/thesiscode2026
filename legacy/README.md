# Legacy / archived code

These files are **not part of the reproducible pipeline** described in
[`../RUNNING.md`](../RUNNING.md). They are kept for reference and provenance only.

They are an earlier, Gaborone-focused experiment track and an older geocoding branch,
superseded by the notebook pipeline. Several of them read input files that are no longer
present in the repo (e.g. `gaborone_test/`, `data/offline_calibration/`,
`census_villages_geocoded_google.csv`), so they are **not expected to run as-is**.

| File | What it was |
|---|---|
| `scripts/run_compare_strategies.py` | Standalone nominal / static-robust / adjustable-robust comparison on a Gaborone offline-calibration dataset. A separate, simpler re-implementation of the demand simulation (not the canonical NB/ARO-ADR model in `national_pipeline`). |
| `scripts/run_nominal_test.py` | Nominal-only subset of the above (print-only). |
| `scripts/run_geocode.py` | Old batch-geocode runner. |
| `scripts/check_duplicates.py` | Ad-hoc duplicate check on `census_population_2022.csv`. |
| `scripts/output/res_*.csv` | Outputs from the comparison scripts (preserved). |
| `geocode_google.py` | Old Google-Maps geocoding branch; superseded by the `botswana_geocode/*.ipynb` deduped → strict → refined → uniform chain. |
| `nearest_facility.ipynb` | Standalone nearest-facility assignment; `national_pipeline.ipynb` computes its own assignment. |

The canonical simulation/optimization code lives in
`pipeline/05_optimization/` (`national_pipeline.ipynb` + `run_cms_two.py`).
