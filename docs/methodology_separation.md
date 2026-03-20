**Methodology Separation: Offline vs Online**

Purpose: explicitly separate statistical estimation (offline) from operational/adaptive decisions (online). Keep dispersion (GLM overdispersion) fixed after offline calibration; update flows only online.

**Offline (Estimate & Calibrate)**
- **Estimate demand means (`mu`) and overdispersion (`alpha`)**: run the NB-GLM implementation in [antimicrobialglm/antimicrobialglm_utils.py](antimicrobialglm/antimicrobialglm_utils.py#L1-L200). Save outputs:
  - `Dbar` / nominal means per facility & drug (CSV)
  - `alpha` (per antimicrobial class) from `overdispersion` returned by the GLM
- **Calibrate per-location uncertainty (`sigma`)**: use the NB variance formula
  - Var(Y) = mu + alpha * mu^2
  - sigma = sqrt(Var(Y)) = sqrt(mu + alpha * mu^2)
  - Compute `sigma` for each facility × drug by matching drug → antimicrobial class and mu (from `Dbar`). Write `sigma` to CSV/JSON for use by solvers.
- **Calibrate Γ (Gamma, budget of uncertainty)**:
  - Decide experiment values for Γ (e.g. 0.5, 1.0, 2.0) or compute by aggregating standardized deviations:
    - normalized deviation per item = sigma_item / sum(sigma_all) (or other domain-specific mapping)
    - set Γ to represent expected number of items that can simultaneously be at worst-case magnitude.

**Online / ADR (Adaptive Reoptimization)**
- **What the ADR may update (online):**
  - Reallocate flows and routings: decision variables `F`, `lambda`, `I`, `U`, `y` in [gaborone_test/gaborone_simulation.ipynb](gaborone_test/gaborone_simulation.ipynb#L1488-L1528).
  - Optionally update nominal means `mu` with lightweight smoothing (e.g., exponential smoothing) based on incoming observations — but do NOT update `alpha` (dispersion) online.
- **What the ADR must NOT update:**
  - The GLM overdispersion (`alpha`) and offline-calibrated `sigma` and Γ. These are fixed during ADR experiments to preserve the statistical/conceptual separation.

**Exact Code Edits (recommended)**
- In [antimicrobialglm/antimicrobialglm_utils.py](antimicrobialglm/antimicrobialglm_utils.py#L1-L200): ensure the function writes both `glm_aggregated` (means) and `overdispersion` to disk (CSV/JSON) after fitting. It already returns `(glm_aggregated, overdispersion)`; add a helper to export these to a `data/offline_calibration/` folder.
- In [gaborone_test/gaborone_simulation.ipynb](gaborone_test/gaborone_simulation.ipynb#L1188-L1200): replace the ad-hoc sigma construction
  - Current: `sigma[facility][drug] = DEMAND_CV * D_nominal[facility][drug]`
  - Replace with: read class-specific `alpha` and compute
    - `mu = D_nominal[facility][drug]`
    - `var = mu + alpha[class_of_drug] * mu**2`
    - `sigma = np.sqrt(var)`
- Persist computed `sigma` to `data/offline_calibration/sigma_by_facility_drug.csv` and have optimizers read that file.
- In ADR routines (new module or notebook cell): implement `update_flows_only(observed_demands, Dbar, sigma_file, solver_params)` that reads fixed `sigma`, updates `D_nominal` (optionally via smoothing), and calls the existing `solve_robust` / `solve_deterministic` to re-optimize flows. Ensure `alpha` is never re-estimated in ADR.

**Experiment Definitions**
- Baselines: deterministic (Γ=0), robust (several Γ values), robust + ADR (online flow updates every decision epoch while keeping `sigma` fixed).
- Metrics: total cost, shortage, inventory, robustness gap under simulated realizations.

**Copilot-ready prompt (paste into Copilot Chat to implement changes)**
Implement these concrete changes in the repo:
1. Add an export in `antimicrobialglm/antimicrobialglm_utils.py` that writes `glm_aggregated` and `overdispersion` to `data/offline_calibration/glm_output.csv` and `data/offline_calibration/overdispersion.json` after fitting. Use class names as keys for overdispersion.
2. In `gaborone_test/gaborone_simulation.ipynb`, replace the `sigma = DEMAND_CV * D_nominal` block with code that reads `overdispersion.json`, maps drug→class, and computes `sigma = sqrt(mu + alpha * mu**2)` for every facility×drug. Save `sigma` to `data/offline_calibration/sigma_by_facility_drug.csv`.
3. Add a new ADR helper `scripts/adr_update_flows.py` with function `update_flows_only(observed_demands_csv, sigma_csv, gamma, solver_params)` that loads fixed `sigma`, updates `D_nominal` (optionally via smoothing), and calls the existing `solve_robust` to re-optimize flows. Ensure `alpha` is never re-estimated in ADR.
4. Add a small unit test that loads a tiny synthetic dataset, runs the GLM exporter, computes sigma, and runs one robust optimization to confirm end-to-end consistency.

If you want, I can implement items 1–3 now (export GLM outputs, replace sigma construction, scaffold ADR helper). Which should I do first?
