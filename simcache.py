"""Persist simulation results so figures can be redrawn without re-solving.

The simulation cells in `national_pipeline.ipynb` hold their results only in
notebook memory. A cosmetic change to a figure -- a legend position, a font
size -- therefore cost a full re-solve, which for the sweeps runs to hours.
These helpers write each result to `outputs/results/` on the way past and read
it back on demand, so replotting is a second's work.

Every result is stored as a single tidy parquet: the per-period metric frames
are concatenated and the dictionary keys that identified them (policy, kappa,
Gamma, penalty, region) become ordinary columns.

    from simcache import save_run, load_run

    save_run("gaborone", {"deterministic": metrics_det,
                          "static_robust": metrics_rob,
                          "aro_adr":       metrics_adr}, keys=["policy"])

    frames = load_run("gaborone", keys=["policy"])     # -> {"deterministic": df, ...}

Nothing here overwrites the CMS results; `cms_results_full.parquet` is produced
by its own cell and is left alone.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent / "outputs" / "results"

__all__ = ["save_run", "load_run", "cached", "RESULTS_DIR", "run_path"]


def run_path(name: str) -> Path:
    return RESULTS_DIR / f"{name}.parquet"


def _as_tuple(key):
    return key if isinstance(key, tuple) else (key,)


def save_run(name: str, frames: dict, keys) -> Path:
    """Write a dict of per-period metric frames to one parquet.

    `frames` maps a key (a scalar, or a tuple for a swept grid) to a DataFrame.
    `keys` names the key components, and they become columns in the output.
    """
    keys = list(keys)
    rows = []
    for key, frame in frames.items():
        parts = _as_tuple(key)
        if len(parts) != len(keys):
            raise ValueError(
                f"{name}: key {key!r} has {len(parts)} parts but keys={keys}"
            )
        block = pd.DataFrame(frame).copy()
        for col, value in zip(keys, parts):
            block[col] = value
        rows.append(block)

    if not rows:
        raise ValueError(f"{name}: nothing to save")

    out = pd.concat(rows, ignore_index=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = run_path(name)
    out.to_parquet(path, index=False)
    return path


def load_run(name: str, keys) -> dict:
    """Read back what save_run wrote, restoring the original dict."""
    keys = list(keys)
    df = pd.read_parquet(run_path(name))
    frames = {}
    for key, block in df.groupby(keys, sort=False):
        parts = _as_tuple(key)
        frames[parts[0] if len(parts) == 1 else tuple(parts)] = (
            block.drop(columns=keys).reset_index(drop=True)
        )
    return frames


def cached(name: str) -> bool:
    """True when a saved run is on disk."""
    return run_path(name).exists()
