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
    rows, failures = [], []

    if serial:
        for r in missing:
            results, error = R.run_region(r)
            (failures.append((r, error)) if error else rows.extend(results))
            print(f"{'FAILED' if error else 'done'} {r}")
    else:
        workers = min(len(missing), max(1, (os.cpu_count() or 2) - 1))
        print(f"running {len(missing)} regions | workers={workers} | solver={R.SOLVER}")
        with ProcessPoolExecutor(max_workers=workers, initializer=R.load_data) as ex:
            futs = {ex.submit(R.run_region, r): r for r in missing}
            for fut in as_completed(futs):
                r = futs[fut]
                results, error = fut.result()
                if error:
                    failures.append((r, error)); print(f"FAILED {r}: {error}")
                else:
                    rows.extend(results); print(f"done {r} ({len(results)} rows)")

    df = pd.DataFrame(rows)
    R.OUT_DIR.mkdir(exist_ok=True)
    df.to_parquet(MISSING_OUT, index=False)
    print(f"\nwrote {MISSING_OUT}  shape={df.shape}"
          f"  regions={sorted(df['region'].unique()) if len(df) else []}")
    if failures:
        print("FAILURES:", failures)


def merge_missing():
    old = pd.read_parquet(EXISTING)
    new = pd.read_parquet(MISSING_OUT)
    full = pd.concat([old, new], ignore_index=True)
    full.to_parquet(FULL_OUT, index=False)
    print(f"merged -> {FULL_OUT}  ({full['region'].nunique()} regions)"
          f"  regions={sorted(full['region'].unique())}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "merge":
        merge_missing()
    else:
        main(serial="--serial" in sys.argv)
