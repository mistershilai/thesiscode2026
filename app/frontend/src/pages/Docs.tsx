export default function Docs() {
  const apiBase = (import.meta as any).env?.VITE_API_URL || "/api";

  return (
    <div className="page docs-page">
      <h1>Documentation</h1>
      <p className="page-subtitle-tswana">Ditaelo</p>

      <div className="docs-section">
        <h2>Getting Started</h2>
        <div className="docs-card">
          <h3>Quick Start (Docker)</h3>
          <p>The easiest way to run Kaelo. Requires only Docker Desktop.</p>
          <pre className="docs-code">{`# 1. Install Docker Desktop from docker.com

# 2. Open a terminal in the project folder

# 3. Start everything
docker compose up

# 4. Open in your browser
http://localhost:8000`}</pre>
          <p className="docs-hint">
            This starts the Kaelo app, the OSRM routing engine, and loads all data automatically.
            First run may take a few minutes to build.
          </p>
        </div>

        <div className="docs-card">
          <h3>Local Development</h3>
          <pre className="docs-code">{`# Backend
cd app/backend
pip install -r requirements.txt
python -m uvicorn app.backend.main:app --reload

# Frontend (separate terminal)
cd app/frontend
npm install
npm run dev

# OSRM (separate terminal)
docker run -d -p 5001:5000 \\
  -v ./osrm_project:/data \\
  ghcr.io/project-osrm/osrm-backend:v5.27.1 \\
  osrm-routed --algorithm mld /data/botswana-latest.osrm`}</pre>
        </div>
      </div>

      <div className="docs-section">
        <h2>App Structure</h2>
        <div className="docs-grid">
          <div className="docs-card">
            <h3>Dashboard</h3>
            <p>
              Overview of Botswana's health facility network. Shows facility counts,
              population coverage, an interactive map with district boundaries, and
              regional breakdowns.
            </p>
          </div>
          <div className="docs-card">
            <h3>Simulate</h3>
            <p>
              Run multi-period simulations comparing Nominal, Static Robust, and ADR
              strategies. Customize demand, adjust parameters, and visualize unmet
              demand over time.
            </p>
          </div>
          <div className="docs-card">
            <h3>Plan</h3>
            <p>
              Real-world planning mode. Input current inventory, optionally provide
              last period's demand, and generate specific shipment and procurement
              orders for the next cycle.
            </p>
          </div>
        </div>
      </div>

      <div className="docs-section">
        <h2>API Reference</h2>
        <p className="docs-hint" style={{ marginBottom: "1rem" }}>
          Full interactive API docs available at{" "}
          <a href={`${apiBase.replace("/api", "")}/docs`} target="_blank" rel="noreferrer" className="docs-link">
            /docs
          </a>{" "}
          (Swagger UI) or{" "}
          <a href={`${apiBase.replace("/api", "")}/redoc`} target="_blank" rel="noreferrer" className="docs-link">
            /redoc
          </a>
        </p>

        <div className="docs-card">
          <h3>Core Endpoints</h3>
          <table className="facility-table">
            <thead>
              <tr>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>GET</td><td>/api/summary</td><td>Facility counts, population, DHMT stats</td></tr>
              <tr><td>GET</td><td>/api/regions</td><td>List all DHMT regions</td></tr>
              <tr><td>GET</td><td>/api/regions/{"{"}<em>name</em>{"}"}/facilities</td><td>Facilities in a region</td></tr>
              <tr><td>GET</td><td>/api/regions/{"{"}<em>name</em>{"}"}/demand</td><td>Demand matrix for a region</td></tr>
              <tr><td>GET</td><td>/api/facilities/geojson</td><td>All facilities as GeoJSON</td></tr>
              <tr><td>GET</td><td>/api/districts/geojson</td><td>District boundary polygons</td></tr>
              <tr><td>GET</td><td>/api/cms/products</td><td>CMS drug products and prices</td></tr>
            </tbody>
          </table>
        </div>

        <div className="docs-card">
          <h3>Optimization</h3>
          <table className="facility-table">
            <thead>
              <tr>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>POST</td><td>/api/optimize</td><td>Run multi-period simulation</td></tr>
              <tr><td>POST</td><td>/api/plan</td><td>Generate single-period shipment plan</td></tr>
            </tbody>
          </table>
        </div>

        <div className="docs-card">
          <h3>Data Management</h3>
          <table className="facility-table">
            <thead>
              <tr>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>POST</td><td>/api/cms/products/add</td><td>Add a new drug</td></tr>
              <tr><td>POST</td><td>/api/cms/products/remove</td><td>Remove a drug</td></tr>
              <tr><td>POST</td><td>/api/facilities/add</td><td>Add a facility (computes OSRM distances)</td></tr>
              <tr><td>POST</td><td>/api/facilities/remove</td><td>Remove a facility</td></tr>
              <tr><td>POST</td><td>/api/facilities/relocate</td><td>Move a facility and recompute distances</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="docs-section">
        <h2>Optimization Strategies</h2>
        <div className="docs-grid">
          <div className="docs-card">
            <h3>Nominal</h3>
            <p>
              Optimizes against mean expected demand. Fast but fragile: assumes
              demand will match forecasts exactly. Best for stable, predictable regions.
            </p>
          </div>
          <div className="docs-card">
            <h3>Static Robust</h3>
            <p>
              Accounts for demand uncertainty with a budgeted uncertainty set (Gamma).
              Fixed decisions that hedge against worst-case demand deviations.
              More conservative but reliable.
            </p>
          </div>
          <div className="docs-card">
            <h3>Adjustable Robust (ADR)</h3>
            <p>
              Affine decision rules that adapt shipments based on realized demand.
              The solver learns coefficients (alpha) that determine how to redistribute
              drugs when demand deviates from forecasts. Best overall performance.
            </p>
          </div>
        </div>
      </div>

      <div className="docs-section">
        <h2>Environment Variables</h2>
        <div className="docs-card">
          <table className="facility-table">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Default</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>OSRM_URL</td><td>http://localhost:5001</td><td>OSRM routing engine URL</td></tr>
              <tr><td>CORS_ORIGINS</td><td>http://localhost:5173</td><td>Allowed CORS origins (comma-separated)</td></tr>
              <tr><td>VITE_API_URL</td><td>/api</td><td>Frontend API base URL</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
