# Designing Robust Antimicrobial Supply Chains in Botswana

**Author:** Elliot S. Lee
**Advised by:** Professor Bartolomeo Stellato
**Department of Operations Research & Financial Engineering, Princeton University**

---

## Overview

Code, data-processing pipelines, and optimization models for *"Designing Robust
Antimicrobial Supply Chains under Epidemiological Demand Uncertainty in Botswana."*
The pipeline runs from raw census and facility data through geocoding,
road-network distance-matrix construction, antimicrobial demand modeling, and
multi-echelon robust/adjustable-robust optimization with SEIR epidemic coupling.

For the end-to-end run order (commands, inputs/outputs, slow/paid steps) see
[`RUNNING.md`](RUNNING.md). For the folder structure see [`LAYOUT.md`](LAYOUT.md).
For the mapping from each paper figure/table to the code that produces it see
[`EXHIBITS.md`](EXHIBITS.md).

---

## Repository layout

```
data/            inputs: raw/ (private, gitignored), processed/ (matrices,
                 facilities, geocoded population), reference/ (drug lists, estimates)
census_datacleaning/   clean 2022 census microdata -> district age breakdowns
botswana_geocode/      geocode settlements via Google Maps (paid API)
osrm_project/          local OSRM routing server -> distance/duration matrices
antimicrobialglm/      MURIA-calibrated antimicrobial demand estimator
national_pipeline/     multi-echelon optimization + CMS simulation + SEIR coupling
outputs/         figures/ (all generated PNGs, HTML maps) and results/ (parquet)
app/             FastAPI + React viz app (for the Botswana government)
deploy/          Oracle Cloud / Docker deployment for the app + OSRM
legacy/          archived earlier experiments (not part of the pipeline)
```

Key modules:
- `antimicrobialglm/muria_estimator.py` - single source of truth for the demand
  estimator. Calibrates the synthetic-microdata + NB2 GLM of Report Section 4.5 to
  the real MURIA point-prevalence-survey microdata; `updatedantimicrobialglm.ipynb`
  is a thin driver. Exports to `antimicrobialglm/artifacts/`.
- `national_pipeline/national_pipeline.ipynb` - the canonical simulation path.
- `national_pipeline/run_cms_two.py` - the batch/cluster twin (HiGHS solver).

---

## Data availability and privacy

To comply with Google Maps Platform Terms of Service and Botswana Ministry of
Health data-sharing restrictions, the repository **excludes all private data**.
The following are gitignored and must be supplied/regenerated locally:

- `.env` files (Google Maps API key).
- Raw census microdata (`*.sav`) and geocoded settlement coordinates.
- `PPS -BW Consolidated Raw.xlsx` - the raw MURIA point-prevalence survey (private
  MoH data).
- `antimicrobialglm/artifacts/` - PPS-derived demand parameters (regenerate via
  `muria_estimator.py`).
- `kaelo_users.db`, OSRM road extracts, and other regenerable intermediates.

The two published Paramadhas-paper aggregate tables under `antimicrobialglm/` are
retained, as they are public. Because all Botswana government datasets are private,
full reproduction requires supplying equivalent local data.

---

## Reproducibility (summary)

Detailed, per-stage instructions are in [`RUNNING.md`](RUNNING.md). In brief:

1. `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. Clean census data (`census_datacleaning/`).
3. Geocode settlements with a Google Maps API key in `botswana_geocode/.env` (paid).
4. Build the OSRM server (Docker) and query the routing matrices (`osrm_project/`).
5. Fit the demand estimator on the MURIA data (`antimicrobialglm/`).
6. Run the optimization and simulation (`national_pipeline/national_pipeline.ipynb`).

The `app/` and containerized deployment are described in `deploy/` and
`docker-compose.yml`.
