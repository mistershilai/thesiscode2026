# Exhibits map (paper figures/tables -> code)

Maps every figure and table in the paper *"Designing Robust Antimicrobial Supply
Chains under Epidemiological Demand Uncertainty in Botswana"* to the notebook (and
section) that produces it, and the data it consumes. Figure/table numbers follow
document order in `Final_Report/main.tex`.

Generated PNGs live in `outputs/figures/`; the canonical simulation notebook is
`national_pipeline/national_pipeline.ipynb` (abbreviated **NP** below). Locators
use the notebook's section heading (stable across re-runs) rather than cell index.

## Figures

| # | Label | Graphic(s) | Produced by |
|---|-------|-----------|-------------|
| 1 | `fig:health_flow` | `DiagramofLogisticsBotswana...jpg` | Hand-drawn schematic (not code-generated) |
| 2 | `fig:faccts` | `facility_type_counts.png`, `speed_distribution.png` | `osrm_project/combined_workflow.ipynb`, sec. "Analysis & visualizations" |
| 3 | `fig:unmetdemandgabs` | `unmetdemandgabs.png`, `unmetdemandaverage100gabs.png` | NP, sec. "Gaborone Simulation Results" |
| 4 | `fig:costbreakdown` | `costbreakdown.png`, `costbenefit.png`, `objectivecomparison.png` | NP, sec. "Gaborone Simulation Results" |
| 5 | `fig:cmspmh` | `cmstopmh.png`, `gabsmultiechelon.png` | NP, folium route maps -> `outputs/figures/gabs_route.html`, `gaborone_cms_pmh_clinics_routes.html`; PNGs are screenshots of these interactive maps |
| 6 | `fig:kappa` | `kappa.png` | NP, sec. "Sensitivity Analysis: Dispersion Mismatch (Kappa)" |
| 7 | `fig:seasonal_unmet_flat` | `seasonal_unmet_no_multiplier.png`, `seasonal_unmet_with_multiplier.png`, `seasonal_multiplier.png` | NP, secs. "Seasonal Demand Model" / "Seasonal Simulation Functions" |
| 8 | `fig:botswana_heatmap` | `botswana_heatmap.png` | NP, sec. "National Results: Unmet Demand Heatmaps" |
| 9 | `fig:cms_unmet_map` | `cms_unmet_map.png` | NP, sec. "cms unmet demand heatmaps by policy and scenario" |
| 10 | `fig:cms_bar` | `cms_bar.png` | NP, sec. "cms unmet demand heatmaps by policy and scenario" |
| 11 | `fig:epi_results` | `epidemic_gaborone_results.png` | NP, sec. "epidemic simulation results" |
| 12 | `fig:epi_resistance` | `resistance_emergence_comparison.png` | NP, sec. "epidemic simulation results" |
| 13 | `fig:gamma_sensitivity` | `gamma_sensitivity.png` | NP, sec. "Sensitivity Analysis: Uncertainty Budget (Gamma)" |
| 14 | `fig:botswana_appendix_simulation_maps` | `botswana_appendix_simulation_maps.png` | NP, sec. "National Results: Multi-Metric Choropleth Maps" |
| 15 | `fig:cms_full_2526` | `cms_full_metrics_2526.png` | NP, cell writing `cms_full_metrics_{scenario}.png` (scenario="2526") |
| 16 | `fig:cms_full_2627` | `cms_full_metrics_2627.png` | NP, same cell, scenario="2627" |

## Tables

| # | Label | Content | Produced by |
|---|-------|---------|-------------|
| 1 | `tab:national_results` | Avg. per-period performance, all 18 districts | NP, national results section; from `cms_results_full.parquet` |
| 2 | `tab:cms_results` | Avg. unmet demand / procurement cost / objective by model | NP, CMS results section; from `cms_results_full.parquet` |
| 3 | `tab:seir_params` | SEIR parameters for the PMH case study | NP, epidemic/SEIR setup (input parameters) |
| 4 | `tab:epi_results` | Policy performance under epidemic-driven demand at PMH | NP, sec. "epidemic simulation results" |

## Data provenance (upstream of the exhibits)

- **`cms_results_full.parquet`** (national CMS run; Figures 8-10, 14-16 and Tables 1-2):
  produced by the national simulation. Regenerate via `national_pipeline.ipynb`, or
  in batch via `run_cms_two.py` / `run_missing_regions.py` (HiGHS solver). 18 DHMTs
  x 3 policies (deterministic, static-robust, ARO-ADR) x 2 AMC scenarios x 26 periods.
- **Facility / routing inputs** (Figure 2): `data/processed/facilities_with_warehouses.csv`
  and `data/processed/{distance,duration}_matrix_named.csv` (OSRM stage).
- **Demand parameters**: `antimicrobialglm/artifacts/*` from the MURIA-calibrated
  estimator (`antimicrobialglm/muria_estimator.py`); private, regenerate locally.

See `RUNNING.md` for the full stage-by-stage runbook.
