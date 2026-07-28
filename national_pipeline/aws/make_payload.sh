#!/usr/bin/env bash
# Build payload.tar.gz with EXACTLY the inputs the CMS missing-region run needs.
# WARNING: this tarball contains PRIVATE Botswana MoH data (geocoded population,
# PPS-derived artifacts). Transfer only over encrypted channels (scp/SSH); delete
# it locally and remotely when done. It is gitignored.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT=national_pipeline/aws/payload.tar.gz
tar -czf "$OUT" \
  requirements.txt \
  national_pipeline/run_cms_two.py \
  national_pipeline/run_missing_regions.py \
  national_pipeline/antimicrobials.csv \
  national_pipeline/cms_results.parquet \
  antimicrobialglm/antimicrobialglm_utils.py \
  antimicrobialglm/artifacts \
  data/processed/facilities_with_warehouses.csv \
  data/processed/distance_matrix_named.csv \
  data/processed/duration_matrix_named.csv \
  data/reference/district_admissions_estimates_2021.csv \
  census_datacleaning/botswana_population_age_breakdown.csv \
  botswana_geocode/census_population_2022_geocoded_final_uniform.csv
echo "wrote $OUT ($(du -h "$OUT" | cut -f1)) — CONTAINS PRIVATE DATA"
