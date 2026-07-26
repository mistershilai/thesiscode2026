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

## Progress

**Done**
- `legacy/` — archived older experiment scripts (not part of the pipeline).
- `outputs/figures/` — loose root figure PNGs relocated here (nothing reads them).
- `outputs/results/`, `data/{raw,processed,reference}/` — skeleton created.
- Private data protection: raw PPS + PPS-derived `artifacts/` gitignored.

**Deferred (the risky part — needs per-notebook path rewiring + verification runs)**
- Redirect notebook/script **writes** (`savefig`, `to_csv`, `to_parquet`) into
  `outputs/` — currently the notebooks still write figures next to their code and
  matrices to the repo root.
- Move **canonical data** (matrices, facilities, geocoded population, GLM inputs)
  into `data/` and rewire every read path in the 6 notebooks, `run_cms_two.py`,
  and `app/backend/core/data_loader.py`.
- Move stage code into `pipeline/NN_*/` and add `pipeline/common/paths.py` as the
  single source of truth for all file locations.
- Relocate `national_pipeline/*.png` and `*.parquet` into `outputs/`.

These require running each notebook (OSRM server + multi-hour simulations) to
confirm no path broke, so they are intentionally left for a supervised pass.

## Conventions (once migrated)
- Code reads/writes paths **only** via `pipeline/common/paths.py` — never bare
  relative strings — so future moves touch one file.
- `data/raw/` and anything PPS-derived stays gitignored; regenerate locally.
