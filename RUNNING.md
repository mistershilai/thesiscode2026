# Running the pipeline end-to-end

Ordered runbook for reproducing the analysis in *"Designing Robust Antimicrobial
Supply Chains under Epidemiological Demand Uncertainty in Botswana."* Each stage
lists its command, inputs, outputs, and tags:

- `[PAID]`    costs money / needs a paid credential (Google Maps API)
- `[SLOW]`    long-running (minutes to days) — plan accordingly
- `[PRIVATE]` gitignored private data (Botswana MoH / Google ToS); supply locally

The canonical path is the Jupyter notebooks, run in the order below.
`run_cms_two.py` is the SLURM/cluster batch twin of the national simulation (Stage 5b).

Legacy code in `legacy/` is not part of this pipeline (older Gaborone-only
experiments) and should not be run for reproduction.

---

## 0. Environment setup (once)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`gurobipy` (Stage 5) needs a Gurobi license (free academic licenses available);
otherwise `cvxpy` falls back to open-source solvers where applicable. Docker is
required for the OSRM routing server (Stage 3).

---

## 1. Census data cleaning

Notebook: `census_datacleaning/censusdatacleaning.ipynb`

- Reads: `[PRIVATE]` `botswanacensusmicrodata.sav` (626 MB SPSS microdata, gitignored)
- Writes: `census_population_2022_deduped.csv`, `botswana_population_age_breakdown.csv`, `census_population_with_coords.csv`

Deduplicates raw 2022 census microdata and produces district-level age breakdowns.

---

## 2. Geocoding  `[PAID]` `[SLOW]`

Settlement coordinates via the Google Maps Geocoding API. The API is billed per
request; a full run geocodes thousands of settlements.

1. Create `botswana_geocode/.env` (`[PRIVATE]`):
   ```
   GOOGLE_API_KEY=<your key>
   ```
2. Run the notebooks in order (each refines the previous):
   - `botswana_geocode/geocodedupdated_google.ipynb` -> `_geocoded_google_strict.csv` -> `_geocoded_google_refined.csv`
   - `botswana_geocode/fixinggeocode.ipynb` -> `census_population_2022_geocoded_final_uniform.csv` (canonical population)

- Reads: `census_population_2022_deduped.csv`
- Writes: `[PRIVATE]` `census_population_2022_geocoded_final_uniform.csv` (canonical), coverage summaries

---

## 3. Routing matrices (OSRM)  `[SLOW]`

Build a local OSRM routing server on Botswana road data, then query it for the
facility x settlement distance/duration matrices.

Build the OSRM server (one-time, slow — downloads a road extract and pre-processes it):
```bash
cd osrm_project
curl -L -o botswana-latest.osm.pbf https://download.geofabrik.de/africa/botswana-latest.osm.pbf
docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-extract   -p /opt/car.lua /data/botswana-latest.osm.pbf
docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-partition  /data/botswana-latest.osrm
docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-customize  /data/botswana-latest.osrm
```
Then start the server (`docker compose up osrm` from the repo root, exposed on port 5001).

Query the matrices — Notebook: `osrm_project/combined_workflow.ipynb` `[SLOW]` (many OSRM table queries)

- Reads: `facilities_with_warehouses.csv`, running OSRM server
- Writes: `distance_matrix_named.csv`, `duration_matrix_named.csv` (repo root — canonical, consumed downstream), `facility_id_lookup.csv`, plus `osrm_project/*_labeled.csv` and `matrix_summary.csv` (internal QA)

Note: the canonical matrices consumed by every downstream stage are the repo-root
copies. The `osrm_project/` copies of the plain/named matrices are QA exports read
by nothing downstream — do not point later stages at them.

---

## 4. Antimicrobial demand estimator (MURIA-calibrated)

Module: `antimicrobialglm/muria_estimator.py` (single source of truth); driven by
`antimicrobialglm/updatedantimicrobialglm.ipynb`.

- Reads: `[PRIVATE]` `PPS -BW Consolidated Raw.xlsx` (raw MURIA survey, gitignored) and the two published Paramadhas-paper tables `DocumentedInfectionbyAgeGroup.csv`, `AntibioticClassesAcrossHealthFacilities.csv`
- Writes: `[PRIVATE]` `antimicrobialglm/artifacts/{p_class,m_ak,p0_i_given_h,mu_hat_hospital_class,nb_params,nb_coefficients,synthetic_joint_nb_input}.csv` + `metadata.json` (PPS-derived; gitignored, regenerated locally)

Calibrates the synthetic-microdata + NB2 estimator of report Section 4.5 to the real
MURIA microdata: decode -> real marginals (age x infection, tier x class, HIV x class)
-> IPF-raked synthetic joint -> NB2 GLM -> validation against the real joint.
The estimated mean (mu) feeds Stage 5; the overdispersion (kappa) is a byproduct —
the simulations treat kappa as a swept sensitivity parameter, not a pinned value.

---

## 5. Main optimization and simulation

### 5a. Interactive (canonical)  `[SLOW]`

Notebook: `national_pipeline/national_pipeline.ipynb`

- Reads: canonical population, `facilities_with_warehouses.csv`, root `distance_matrix_named.csv` / `duration_matrix_named.csv`, `botswana_population_age_breakdown.csv`, `district_admissions_estimates_2021.csv`, `antimicrobialglm/artifacts/*`, `national_pipeline/{antimicrobials.csv,botswana.geojson}`
- Writes: `{region}_population_nearest_facilities*.csv`, `cms_results.parquet`, figures/maps

Runs nearest-facility assignment, multi-echelon network construction, node-level
demand, the nominal / static-robust / adjustable-robust (ARO-ADR) optimization
models, CMS-based demand simulation (2025-26 and 2026-27), SEIR epidemic coupling,
and resistance analysis. The national simulation sweeps are the slow part (hours;
scales with region count x Monte-Carlo draws).

### 5b. Batch / cluster (SLURM)  `[SLOW]`

Script: `national_pipeline/run_cms_two.py` — batch twin of the CMS national run,
sharing the same models as the notebook. Submitted via `national_pipeline/submit.sh`
on a SLURM cluster (`--time=7-00:00:00`); writes checkpoint + final parquet to
`national_pipeline/results/`. Use for the full national sweep that is too slow to
run interactively.

```bash
sbatch national_pipeline/submit.sh   # from the cluster checkout
```

---

## 6. Web application (optional)

FastAPI backend + React frontend that reads the same canonical CSVs and recomputes
optimization live (it does not read `cms_results.parquet`).

Local dev:
```bash
./app/start.sh          # backend on :8000, frontend on :5173
```

Containerized (backend + frontend + OSRM):
```bash
docker compose up -d --build
```

Auth uses a local SQLite DB (`kaelo_users.db`, gitignored). Set `JWT_SECRET` and
`ADMIN_PASSWORD` via environment — do not rely on the built-in defaults.

---

## Dependency graph (quick reference)

```
.sav -> [1] census cleaning -> deduped.csv -> [2] geocode [PAID] -> final_uniform.csv --+
                                                                                        |
facilities_with_warehouses.csv -> [3] OSRM [SLOW] -> distance/duration_matrix_named.csv-+
                                                                                        +-> [5] national_pipeline [SLOW] -> cms_results.parquet, figures
MURIA PPS + paper tables -> [4] demand estimator -> artifacts/*.csv --------------------+                                   |
                                                                                                                            +-> [6] app (recomputes live)
```
