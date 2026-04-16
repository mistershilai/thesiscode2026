# Designing Robust Antimicrobial Supply Chains in Botswana

**Author:** Elliot S. Lee  
**Advised by:** Professor Bartolomeo Stellato  
**Department of Operations Research & Financial Engineering, Princeton University**

---

## Overview

This repository contains the code, data-processing pipelines, and optimization models for:
**”Designing Robust Antimicrobial Supply Chains under Epidemiological Demand Uncertainty in Botswana.”**

The pipeline goes from raw census/facility data through geocoding, distance-matrix construction, demand modeling, and multi-echelon robust optimization with epidemic coupling.

---

## Repository layout

### Data preparation

- `census_datacleaning/` - deduplicate and clean raw 2022 Botswana census microdata, produce `census_population_2022_deduped.csv` and district-level age breakdowns
  - `censusdatacleaning.ipynb`
- `botswana_geocode/` - geocode census settlements via Google Maps API, resolve coordinate mismatches
  - `geocode_google.py` - batch geocoding script
  - `geocodedupdated_google.ipynb` - refinement and QA of geocoded coordinates
  - `fixinggeocode.ipynb` - targeted fixes for problem settlements
- `osrm_project/` - build and query a local OSRM routing server on Botswana road data, produce distance and duration matrices
  - `combined_workflow.ipynb` - end-to-end pipeline: facility checks, OSRM table API queries, matrix pivoting, labeling, upper-bound correction, and analysis/visualization

### Demand modeling

- `antimicrobialglm/` - fit a negative binomial GLM for antimicrobial prescription counts by age group, infection status, hospital type, and drug class
  - `updatedantimicrobialglm.ipynb` - loads admission/infection and antibiotic class tables, constructs synthetic joint counts via IPF, fits NB2 regression, exports calibrated parameters and conditional probabilities to `artifacts/`
  - `artifacts/` - exported CSVs and metadata (coefficients, fitted means, p(class|stratum), NB parameters)

### Optimization and simulation

- `national_pipeline/` - the main multi-echelon supply chain model
  - `national_pipeline.ipynb` - nearest-facility assignment, OSRM routing, node-level demand construction, robust/nominal/greedy optimization, CMS-based demand simulation (2025-26 and 2026-27), SEIR epidemic coupling, resistance emergence analysis, and national-level choropleths/visualizations
  - `run_cms_two.py` - batch script for CMS simulation runs
  - `results/` - simulation output (parquet files, figures)
- `nearest_facility.ipynb` - standalone nearest-facility assignment using the facility and population data
- `app/` - web application (frontend + backend) for interactive visualization
  - `start.sh` - launch script

### Supporting files

- `scripts/` - utility scripts (`check_duplicates.py`, geocode runners, strategy comparisons)
- `distance_matrix.csv`, `duration_matrix.csv` - precomputed national routing matrices
- `facilities_with_warehouses.csv` - master facility list with warehouse assignments
- `priorityantimicrobialsbotswana.csv` - priority antimicrobial drug list
- `district_admissions_estimates_2021.csv`, `district_facility_distribution_2021.csv` - district-level inputs
- `Dockerfile`, `docker-compose.yml` - containerized OSRM server setup
- `requirements.txt` - Python dependencies
- `docs/` - methodology notes and report drafts

---

## Data privacy and regeneration

To comply with Google Maps Platform Terms of Service and Botswana Ministry of Health data-sharing restrictions, this repository **excludes** all raw geocoded data and private credentials, as well as datasets regarding antimicrobial use and procurement. 

**Excluded (via .gitignore):**
- `.env` - contains private Google API key
- `census_villages_geocoded.csv` and `census_villages_geocoded_google.csv` - raw latitude/longitude data from the Google Geocoding API
- Intermediate checkpoint files (`checkpoint.csv`, `*geocoded*.csv`)

These files must be regenerated locally with a valid API key before running the pipeline.

---

## Reproducibility

Note: as all datasets related to Botswana government data are not public, one must generate own datasets to test reproducibility.

1. **Create a `.env` file** inside `botswana_geocode/`:
   ```
   GOOGLE_API_KEY=<key>
   ```
2. **Run the geocoding script** to rebuild settlement coordinates:
   ```
   cd botswana_geocode && python geocode_google.py
   ```
3. **Start the OSRM server** and run the combined workflow notebook to produce distance/duration matrices.
4. **Run the national pipeline notebook** to execute optimization and simulation.
