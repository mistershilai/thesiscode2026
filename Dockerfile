# ── Stage 1: Build frontend ──────────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY app/frontend/package.json app/frontend/package-lock.json* ./
RUN npm install
COPY app/frontend/ .
RUN npm run build

# ── Stage 2: Python backend + built frontend ────────────────────────
FROM python:3.12-slim
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY app/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/backend/ /app/app/backend/

# Copy built frontend into backend's expected location
COPY --from=frontend-build /build/dist /app/app/frontend/dist

# Copy data files the backend needs. Destinations match data_loader's BASE_DIR
# reads (BASE_DIR resolves to /app in the container).
# NOTE: antimicrobialglm/artifacts/* and the geocoded population are
# gitignored/private — regenerate/supply them locally before building.
COPY data/processed/facilities_with_warehouses.csv /app/data/processed/facilities_with_warehouses.csv
COPY data/processed/distance_matrix_named.csv /app/data/processed/distance_matrix_named.csv
COPY data/processed/duration_matrix_named.csv /app/data/processed/duration_matrix_named.csv
COPY data/reference/district_admissions_estimates_2021.csv /app/data/reference/district_admissions_estimates_2021.csv
COPY census_datacleaning/botswana_population_age_breakdown.csv /app/census_datacleaning/botswana_population_age_breakdown.csv
COPY botswana_geocode/census_population_2022_geocoded_final_uniform.csv /app/botswana_geocode/census_population_2022_geocoded_final_uniform.csv
COPY antimicrobialglm/artifacts/ /app/antimicrobialglm/artifacts/
COPY national_pipeline/antimicrobials.csv /app/national_pipeline/antimicrobials.csv
COPY national_pipeline/botswana.geojson /app/national_pipeline/botswana.geojson
COPY national_pipeline/cms_scenarios/ /app/national_pipeline/cms_scenarios/

# Set env vars
ENV PYTHONUNBUFFERED=1
ENV CORS_ORIGINS=*
ENV OSRM_URL=http://osrm:5000

# Data files are copied directly to their BASE_DIR-relative /app paths above;
# no symlink indirection needed.

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
