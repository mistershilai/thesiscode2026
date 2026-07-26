# Repository layout

Target structure for the MSOM submission. The migration is being done in
**verifiable phases** so the pipeline keeps running; this file tracks progress.

```
thesiscode2026/
├── README.md  RUNNING.md  LAYOUT.md  requirements.txt
├── data/
│   ├── raw/          # [PRIVATE] inputs (.sav, geocoded, PPS) — gitignored, kept local
│   ├── processed/    # matrices, facilities, deduped census, geocoded population
│   └── reference/    # antimicrobials, district estimates, priority lists
├── pipeline/
│   ├── 01_census/    02_geocode/   03_routing/
│   ├── 04_demand_glm/  05_optimization/
│   └── common/       # shared config incl. paths.py
├── outputs/
│   ├── results/      # *.parquet simulation outputs
│   └── figures/      # *.png, *.html maps
├── app/     deploy/     legacy/
```

## Scope decision

Code stays in its current stage directories (`census_datacleaning/`,
`botswana_geocode/`, `osrm_project/`, `antimicrobialglm/`, `national_pipeline/`,
`app/`). We are NOT moving code into `pipeline/NN_*/` — that is pure churn with
notebook-import risk for little gain. The reorg moves DATA and OUTPUTS only.

## Progress

**Done**
- `legacy/` — archived older experiment scripts (not part of the pipeline).
- `outputs/figures/` — loose root figure PNGs relocated (nothing reads them).
- `data/processed/` — routing matrices + `facilities_with_warehouses.csv` moved
  and all consumers rewired (notebooks, `run_cms_two.py`, `app/` , docker-compose).
- `data/reference/` — root reference files (`district_admissions_estimates_2021.csv`,
  `district_facility_distribution_2021.csv`, `priorityantimicrobialsbotswana.*`).
- Private data protection: raw PPS + PPS-derived `artifacts/` gitignored.
- Each move verified locally via `run_cms_two.load_data()`.

**Intentionally left in place (not root clutter; already in stage dirs)**
- `census_datacleaning/botswana_population_age_breakdown.csv`,
  `botswana_geocode/census_population_2022_geocoded_final_uniform.csv` (private),
  `national_pipeline/{antimicrobials.csv, botswana.geojson}`.

**Still open**
- One `national_pipeline.ipynb` run to confirm the notebook read/write edits end-to-end.
- Redirect notebook figure/parquet writes into `outputs/` (still write beside code).
- Stale `Dockerfile` data paths (separate task). README + report §4.5 updates.

## Conventions (once migrated)
- Code reads/writes paths **only** via `pipeline/common/paths.py` — never bare
  relative strings — so future moves touch one file.
- `data/raw/` and anything PPS-derived stays gitignored; regenerate locally.
