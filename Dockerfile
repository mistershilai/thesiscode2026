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

# Copy data files the backend needs
COPY facilities_with_warehouses.csv /data/facilities_with_warehouses.csv
COPY distance_matrix_named.csv /data/distance_matrix_named.csv
COPY duration_matrix_named.csv /data/duration_matrix_named.csv
COPY national_pipeline/antimicrobials.csv /data/national_pipeline/antimicrobials.csv
COPY national_pipeline/botswana.geojson /data/national_pipeline/botswana.geojson
COPY national_pipeline/botswana_age_distribution.csv /data/national_pipeline/botswana_age_distribution.csv
COPY national_pipeline/district_admissions.csv /data/national_pipeline/district_admissions.csv
COPY national_pipeline/glm_*.csv /data/national_pipeline/
COPY botswana_geocode/census_population_2022_geocoded_final_uniform.csv /data/botswana_geocode/census_population_2022_geocoded_final_uniform.csv

# Set env vars
ENV PYTHONUNBUFFERED=1
ENV CORS_ORIGINS=*
ENV OSRM_URL=http://osrm:5000

# The data_loader uses BASE_DIR relative to the source file.
# We need to symlink /data contents so the path resolution works.
RUN ln -sf /data/facilities_with_warehouses.csv /app/facilities_with_warehouses.csv && \
    ln -sf /data/distance_matrix_named.csv /app/distance_matrix_named.csv && \
    ln -sf /data/duration_matrix_named.csv /app/duration_matrix_named.csv && \
    ln -sf /data/national_pipeline /app/national_pipeline && \
    ln -sf /data/botswana_geocode /app/botswana_geocode

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
