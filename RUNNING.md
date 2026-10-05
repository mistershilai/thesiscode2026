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
- Writes: `data/processed/{distance_matrix_named,duration_matrix_named}.csv` (canonical, consumed downstream), `facility_id_lookup.csv`, plus `osrm_project/*_labeled.csv` and `outputs/{matrix_summary,facility_type_counts}.csv` (internal QA)
- Figures: `outputs/figures/{facility_type_counts,speed_distribution,asymmetry_distribution}.{pdf,png}`

`analyze()` defaults to the `*_labeled.csv` QA exports; to regenerate the paper's
Figure 2 from the canonical matrices, call it directly:

```python
analyze(labeled_dist_csv='data/processed/distance_matrix_named.csv',
        labeled_dur_csv='data/processed/duration_matrix_named.csv')
```

Note: the canonical matrices consumed by every downstream stage are the
`data/processed/` copies. The `osrm_project/` copies of the plain/named matrices
are QA exports read by nothing downstream — do not point later stages at them.

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

- Reads: canonical population, `facilities_with_warehouses.csv`, `data/processed/{distance_matrix_named,duration_matrix_named}.csv`, `botswana_population_age_breakdown.csv`, `district_admissions_estimates_2021.csv`, `antimicrobialglm/artifacts/*`, `national_pipeline/{antimicrobials.csv,botswana.geojson}`
- Writes: `{region}_population_nearest_facilities*.csv`, `outputs/results/budget/*.parquet`, figures/maps

Runs nearest-facility assignment, multi-echelon network construction, node-level
demand, the nominal / static-robust / adjustable-robust (ARO-ADR) optimization
models, SEIR epidemic coupling, and resistance analysis. The national simulation
sweeps are the slow part (hours; scales with region count x Monte-Carlo draws).

Every run uses the budget model: each policy minimizes unmet demand first, subject
to a per-period cap on transport + procurement spend, `B = BUDGET_FACTOR * B_ref`,
where `B_ref` is the spend that serves the period's forecast in full. Both
`BUDGET_FACTOR` (notebook budget-settings cell, and the top of `run_cms_two.py`)
must match. The CMS-data run is not solved in the notebook; it reads the output of
5b, so run 5b before the CMS cells.

### 5b. CMS-data national run  `[SLOW]`

Script: `national_pipeline/run_cms_two.py` — the CMS-data run (2025-26, then
2026-27 from year 1's final inventory) for every DHMT, sharing the CMS budget
solvers with the notebook. Runs `MAX_WORKERS` (3) regions at a time on the local
machine, checkpoints after every region, and resumes from the checkpoint when
re-run. Writes `outputs/results/budget/cms_results.parquet`, which the notebook's
CMS cells read.

```bash
cd national_pipeline
python run_cms_two.py                          # every DHMT
python run_cms_two.py --regions Chobe Ghanzi   # a subset
```

`submit.sh` is the old SLURM wrapper and is no longer needed.

---

## 6. Figures for the paper

Every plot is written by `figstyle.save_figure()`, which emits a **vector PDF**
(the submission artifact) next to a PNG preview. INFORMS requires vector art for
plots -- "the preferred formats are PDF or EPS, whenever they can guarantee the
vector format" (INFORMS style instructions, Sec. 9.1) -- and rejects PNG/BMP
bitmaps for graphs; the print edition is converted to grayscale by default, so
`figstyle` also supplies the linestyle / marker / hatch encodings and the
luminance-monotone colormap that keep figures readable without colour.

Two conventions keep figures consistent with the typeset page:

- **Drawn at printed size.** `figsize=figure_size(width_frac, aspect)` sets the
  figure to the width it occupies in the paper, so `\includegraphics` scales it by
  1.0 and the point sizes in the code are the point sizes on the page. (Previously
  figures were drawn 5-22in wide and scaled down 2-3.5x, so nominally-10pt labels
  printed anywhere from 2.8pt to 7.8pt.) `figure_size` also caps the height at
  7.6in so a float cannot overrun the text block.
- **No titles inside the art.** INFORMS typesets the caption via `\FIGURE`; an
  in-figure title duplicates it in a different font. Row/column parameter labels
  on grid figures are kept - those are labels, not titles.

Every simulation caches its per-period metrics through `simcache.py`, so a figure
can be restyled without re-solving. Budget-model runs go to
`outputs/results/budget/` (the notebook's budget-settings cell redirects
`simcache.RESULTS_DIR`); the older shortage-penalty caches stay in
`outputs/results/` and are no longer read:

```python
from simcache import load_run
frames = load_run("sweep_gamma", keys=["true_kappa", "Gamma", "policy"])
```

Cached runs, in the order the notebook writes them: `gaborone`,
`gaborone_martingale_{pure_martingale,mean_reverting}`, `gaborone_replications`,
`sweep_kappa`, `sweep_gamma`, `sweep_budget`, `equity_frontier`,
`seasonal_flat_replications`, `seasonal` and `seasonal_replications`, `national`,
`epidemic`, `epidemic_closed_loop`. The CMS run writes `cms_results.parquet` to the
same directory from `run_cms_two.py`; the CMS maps and the district-level equity
figure read it.

Regenerate figures by re-running the producing notebook (see `EXHIBITS.md` for
the figure -> notebook map), then copy them into the paper and audit:

```bash
python3 sync_paper_figures.py           # copy outputs/figures/* -> botswana_paper/figures/
python3 sync_paper_figures.py --check   # audit only; non-zero exit on any problem
```

The audit reports three things: plots with no vector PDF, figures too tall for the
text block (the "Overfull \vbox ... while \output is active" warning, which on the
page looks like the figure running down over the page number), and figures included
at anything other than 1.0x their drawn size (which rescales all their text). When
a figure legitimately changes size, it prints the `width=` to put in the `.tex`.

`botswana_paper/{main,ecompanion}.tex` include figures **without an extension**
and declare `\DeclareGraphicsExtensions{.pdf,.png,.jpg,.jpeg}`, so LaTeX picks
the PDF whenever one exists and falls back to the PNG otherwise -- the paper
always builds, and each regenerated figure silently upgrades to vector.

Raster is correct for genuine images only: the hand-drawn logistics diagram, and
screenshots of the interactive folium route maps
(`outputs/figures/*.html` -> `cmstopmh`, `gabsmultiechelon`). Those must be
supplied at >=300 dpi. `sync_paper_figures.py` lists them separately rather
than flagging them.

---

## 7. Web application (optional)

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
facilities_with_warehouses.csv -> [3] OSRM [SLOW] -> data/processed/*_matrix_named.csv--+
                                                                                        +-> [5] national_pipeline [SLOW] -> cms_results.parquet, figures
MURIA PPS + paper tables -> [4] demand estimator -> artifacts/*.csv --------------------+                                   |
                                                                                                                            +-> [6] app (recomputes live)
```
