"""
TEMPORARY helper (not part of the pipeline): compute only the CMS regions that are
missing from cms_results.parquet, in parallel, using the HiGHS solver, and write them
to results/cms_results_missing.parquet WITHOUT touching the existing parquet.

  cd national_pipeline
  python run_missing_regions.py          # compute the missing regions
  python run_missing_regions.py merge    # combine existing + missing -> cms_results_full.parquet

Notes:
- Solver is run_cms_two.SOLVER (HiGHS). MOSEK breaks on this problem.
- macOS uses 'spawn' for multiprocessing, so each worker re-runs load_data() via the
  ProcessPoolExecutor initializer (the cluster used 'fork' and inherited it).
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

import run_cms_two as R

EXISTING    = R.BASE_DIR / "cms_results.parquet"            # the 11 completed regions
MISSING_OUT = R.OUT_DIR / "cms_results_missing.parquet"     # just the newly computed regions
FULL_OUT    = R.BASE_DIR / "cms_results_full.parquet"       # existing + missing (merge step)


def missing_regions():
    full = sorted(r for r in R.fac["DHMT"].dropna().astype(str).unique() if r != "--")
    done = set(pd.read_parquet(EXISTING)["region"].unique())
    return [r for r in full if r not in done]


def main(serial=False):
    R.load_data()
    missing = missing_regions()
    print("missing regions:", missing)
    if not missing:
        print("nothing to do"); return
    rows, failures, done = [], [], []
    R.OUT_DIR.mkdir(exist_ok=True)

    def checkpoint():
        # write after each region so a crash/kill never loses completed regions
        if rows:
            pd.DataFrame(rows).to_parquet(MISSING_OUT, index=False)
            print(f"  [checkpoint] {len(done)} regions, {len(rows)} rows -> {MISSING_OUT.name}", flush=True)

    if serial:
        for r in missing:
            results, error = R.run_region(r)
            if error:
                failures.append((r, error)); print(f"FAILED {r}: {error}", flush=True)
            else:
                rows.extend(results); done.append(r); print(f"done {r} ({len(results)} rows)", flush=True)
                checkpoint()
    else:
        workers = min(len(missing), max(1, (os.cpu_count() or 2) - 1))
        print(f"running {len(missing)} regions | workers={workers} | solver={R.SOLVER}", flush=True)
        with ProcessPoolExecutor(max_workers=workers, initializer=R.load_data) as ex:
            futs = {ex.submit(R.run_region, r): r for r in missing}
            for fut in as_completed(futs):
                r = futs[fut]
                results, error = fut.result()
                if error:
                    failures.append((r, error)); print(f"FAILED {r}: {error}", flush=True)
                else:
                    rows.extend(results); done.append(r); print(f"done {r} ({len(results)} rows)", flush=True)
                    checkpoint()

    print(f"\nDONE. regions completed: {sorted(done)}  -> {MISSING_OUT}", flush=True)
    if failures:
        print("FAILURES:", failures, flush=True)


def merge_missing():
    old = pd.read_parquet(EXISTING)
    new = pd.read_parquet(MISSING_OUT)
    full = pd.concat([old, new], ignore_index=True)
    full.to_parquet(FULL_OUT, index=False)
    print(f"merged -> {FULL_OUT}  ({full['region'].nunique()} regions)"
          f"  regions={sorted(full['region'].unique())}")


def smoke(region="Okavango", T=2):
    """Fast end-to-end validation: run ONE small region with a tiny period count.
    Exercises instance build + all 3 HiGHS solvers + result assembly + checkpoint +
    merge, in minutes, and extrapolates the full serial runtime."""
    import time
    R.load_data()
    n_missing = len(missing_regions())
    print(f"SMOKE: region={region}  T={T} (full={26})  solver={R.SOLVER}", flush=True)
    t0 = time.time()
    results, error = R.run_region(region, T=T)
    dt = time.time() - t0
    if error:
        print(f"SMOKE FAILED: {error}"); return
    df = pd.DataFrame(results)
    print(f"SMOKE OK: {len(results)} rows in {dt:.0f}s | models={sorted(df['model'].unique())}"
          f" | scenarios={sorted(df['scenario'].unique())}")
    # prove the checkpoint + merge paths work
    R.OUT_DIR.mkdir(exist_ok=True)
    df.to_parquet(R.OUT_DIR / "cms_results_smoke.parquet", index=False)
    combined = pd.concat([pd.read_parquet(EXISTING), df], ignore_index=True)
    print(f"checkpoint write OK; merge concat OK ({combined['region'].nunique()} regions)")
    # extrapolate (linear in T; bigger regions run longer, so treat as a lower bound)
    per_region = dt * (26 / T)
    print(f"\nESTIMATE (rough lower bound): ~{per_region/60:.0f} min/region (full T=26); "
          f"serial x {n_missing} regions ~= {per_region*n_missing/3600:.1f} h")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "merge":
        merge_missing()
    elif cmd == "smoke":
        smoke()
    else:
        main(serial="--serial" in sys.argv)
