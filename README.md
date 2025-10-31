# Designing Robust Antimicrobial Supply Chains in Botswana

**Author:** Elliot S. Lee  
**Advised by:** Professor Bartolomeo Stellato  
**Department of Operations Research & Financial Engineering, Princeton University**

---

## Overview
This repository contains the code, data-processing pipelines, and model components for the project:
**“Designing Robust Antimicrobial Supply Chains under Epidemiological Demand Uncertainty in Botswana.”**

The code constructs and analyzes a national pharmaceutical logistics network for Botswana, using facility-level data, population data, and optimization-based modeling.

It includes:
- Geocoding and preprocessing scripts
- Distance-matrix generation using OSRM
- Robust optimization model implementation
- Visualization and reproducibility utilities

---

### Repository layout (simplified)

- `botswana_geocode/` — Scripts for geocoding settlements via Google Maps API  
- `data/` — Contains derived, shareable datasets (e.g., `distance_matrix.csv`)  
- `scripts/` — Optimization, OSRM, and analysis modules  
- `models/` — Core mathematical model notebooks  


---

## Data privacy and regeneration
To comply with Google Maps Platform Terms of Service and Botswana Ministry of Health data-sharing restrictions, this repository **excludes** all raw geocoded data and private credentials.

**Excluded (via .gitignore):**
- `.env` — contains private Google API key.
- `census_villages_geocoded.csv` and `census_villages_geocoded_google.csv` — include raw latitude/longitude data from the Google Geocoding API.
- Intermediate checkpoint files (`checkpoint.csv`, `*geocoded*.csv`).

These files must be **regenerated locally** using your own API key before running analyses.

---

## Reproducibility instructions

1. **Create a `.env` file** inside `botswana_geocode/`:
GOOGLE_API_KEY=your_own_google_api_key_here
2. **Run the geocoding script** to rebuild coordinates for all settlements:
cd botswana_geocode
python geocode_google.py
This will produce:
census_villages_geocoded_google.csv
(This file is private and not tracked in Git.)

3. **Generate the distance matrix** using the cleaned coordinates:
python scripts/build_distance_matrix.py

Output:
distance_matrix.csv
This matrix contains only derived distances/times — safe to share and used in all optimization steps.

4. **Run the optimization model:**
python scripts/run_optimization.py


---

## Safe data-sharing policy
- **Allowed for publication:**
- `distance_matrix.csv`, aggregated data tables, and all model outputs.
- Figures, maps, and visualizations where coordinates are embedded in graphics.
- **Not to be shared:**
- Any CSV containing raw latitude/longitude pairs or API response data.
- Any files containing active API keys.

If collaborators need to reproduce the results, they can regenerate geocoded data following the above steps with their own Google API key.

---

## File safety checklist
Before committing to GitHub, ensure the following lines exist in your `.gitignore`:

Secrets

.env

Geocoded data (raw coordinates)

geocoded.csv
census_villages_geocoded.csv
census_villages_geocoded_google.csv

Large/intermediate CSVs

*.csv
!data/distance_matrix.csv
!data/aggregated_results.csv