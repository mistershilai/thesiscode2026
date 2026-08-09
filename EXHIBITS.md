# Exhibits map (paper figures/tables -> code)

Maps every figure and table in the paper *"Designing Robust Antimicrobial Supply
Chains under Epidemiological Demand Uncertainty in Botswana"* to the notebook (and
section) that produces it, and the data it consumes. Figure numbers follow document
order in `botswana_paper/main.tex` (Figures 1-8) and `botswana_paper/ecompanion.tex`
(Figures EC.1-EC.7).

Figures are generated as **vector PDFs** into `outputs/figures/`, each with a PNG
preview alongside it; `python3 sync_paper_figures.py` copies them into
`botswana_paper/figures/` and reports anything still raster. The LaTeX sources
include figures without an extension, so LaTeX prefers the PDF. The canonical
simulation notebook is `national_pipeline/national_pipeline.ipynb` (abbreviated
**NP** below). Locators use the notebook's section heading (stable across re-runs)
rather than cell index.

## Figures -- main paper

| # | Label | Graphic(s) | Produced by |
|---|-------|-----------|-------------|
| 1 | `fig:logistics` | `logistics_diagram.jpg` `[RASTER]` | Hand-drawn schematic (not code-generated) |
| 2 | `fig:network` | `facility_type_counts`, `speed_distribution` | `osrm_project/combined_workflow.ipynb`, sec. "Analysis & visualizations" (call `analyze()` on the `data/processed/*_matrix_named.csv` pair) |
| 3 | `fig:gaborone` | `unmetdemandaverage100gabs` | NP, sec. "Gaborone Simulation Results" |
| 4 | `fig:gabcost` | `costbreakdown`, `costbenefit`, `objectivecomparison` | NP, sec. "Gaborone Simulation Results" |
| 5 | `fig:heatmap` | `botswana_heatmap` | NP, sec. "National Results: Unmet Demand Heatmaps" |
| 6 | `fig:equity` | `equity_alpha` | NP, sec. "Equity: the alpha-fairness criterion of Section 4.5" |
| 7 | `fig:cmsmap` | `cms_unmet_map` | NP, sec. "cms unmet demand heatmaps by policy and scenario" |
| 8 | `fig:kappa` | `kappa` | NP, sec. "Sensitivity Analysis: Dispersion Mismatch (Kappa)" |
| 9 | `fig:epi` | `epidemic_gaborone_results` | NP, sec. "epidemic simulation results" |

## Figures -- e-companion

| # | Label | Graphic(s) | Produced by |
|---|-------|-----------|-------------|
| EC.1 | `fig:resistance` | `resistance_emergence_comparison` | NP, sec. "epidemic simulation results" |
| EC.2 | `fig:seirlong` | `seir_resistance_longhorizon` | NP, long-horizon SEIR extension cell |
| EC.3 | `fig:gamma` | `gamma_sensitivity` | NP, sec. "Sensitivity Analysis: Uncertainty Budget (Gamma)" |
| EC.4 | `fig:penalty` | `penalty_sensitivity` | NP, shortage-penalty sweep cell |
| EC.5 | `fig:seasonal` | `seasonal_unmet_no_multiplier`, `seasonal_unmet_with_multiplier` | NP, secs. "Seasonal Demand Model" / "Seasonal Simulation Functions" |
| EC.6 | `fig:floor` | `equity_frontier` | NP, sec. "Equity: the efficiency-fairness frontier" (minimum-stock-cover sweep) |
| EC.7 | `fig:cmsfull2526` | `cms_full_metrics_2526` | NP, cell writing `cms_full_metrics_{scenario}` |
| EC.8 | `fig:cmsfull2627` | `cms_full_metrics_2627` | NP, cell writing `cms_full_metrics_{scenario}` |
| EC.9 | `fig:natmaps` | `botswana_appendix_simulation_maps` | NP, sec. "National Results: Multi-Metric Choropleth Maps" |

## Raster exceptions

Vector export does not apply to these; INFORMS wants them at >=300 dpi instead.
They are listed in `RASTER_EXCEPTIONS` in `sync_paper_figures.py` so the audit
reports them separately rather than flagging them as unconverted plots.

- `logistics_diagram.jpg` -- hand-drawn supply chain schematic.
- `cmstopmh`, `gabsmultiechelon` -- screenshots of the interactive folium route
  maps (`outputs/figures/gabs_route.html`,
  `outputs/figures/gaborone_cms_pmh_clinics_routes.html`). Currently not included
  by either LaTeX source; re-shoot at >=300 dpi if they go back in.

## Tables

| # | Label | Content | Produced by |
|---|-------|---------|-------------|
| 1 | `tab:national_results` | Avg. per-period performance, all 18 districts | NP, national results section; from `cms_results_full.parquet` |
| 2 | `tab:cms_results` | Avg. unmet demand / procurement cost / objective by model | NP, CMS results section; from `cms_results_full.parquet` |
| 3 | `tab:seir_params` | SEIR parameters for the PMH case study | NP, epidemic/SEIR setup (input parameters) |
| 4 | `tab:epi_results` | Policy performance under epidemic-driven demand at PMH | NP, sec. "epidemic simulation results" |

## Data provenance (upstream of the exhibits)

- **`cms_results_full.parquet`** (national CMS run; Figures 5-6, EC.6-EC.7 and
  Tables 1-2): produced by the national simulation. Regenerate via
  `national_pipeline.ipynb`, or in batch via `run_cms_two.py` /
  `run_missing_regions.py` (HiGHS solver). 18 DHMTs x 3 policies (deterministic,
  static-robust, ARO-ADR) x 2 AMC scenarios x 26 periods. The CMS figures replot
  straight from this parquet -- no re-solving needed.
- **Facility / routing inputs** (Figure 2): `data/processed/facilities_with_warehouses.csv`
  and `data/processed/{distance,duration}_matrix_named.csv` (OSRM stage).
- **Demand parameters**: `antimicrobialglm/artifacts/*` from the MURIA-calibrated
  estimator (`antimicrobialglm/muria_estimator.py`); private, regenerate locally.

See `RUNNING.md` for the full stage-by-stage runbook and the figure-export step.
