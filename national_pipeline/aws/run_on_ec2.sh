#!/usr/bin/env bash
# Runs on a fresh Ubuntu 22.04+ EC2 instance. Expects ~/payload.tar.gz uploaded.
# Sets up the environment and runs the 7 missing CMS regions in parallel (HiGHS).
set -euo pipefail

sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip

mkdir -p ~/cms && cd ~/cms
tar -xzf ~/payload.tar.gz

python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
# highspy provides the HiGHS backend for cvxpy; gurobipy in requirements installs
# fine without a license (unused here).
pip install -r requirements.txt highspy

cd national_pipeline
echo "=== starting missing-region run (region-parallel, HiGHS) ==="
time python run_missing_regions.py

echo "=== DONE. Result: ~/cms/national_pipeline/results/cms_results_missing.parquet ==="
ls -la results/cms_results_missing.parquet
