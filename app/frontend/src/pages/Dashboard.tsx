import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Summary, Region } from "../api/client";
import AnimatedTagline from "../components/AnimatedTagline";
import BotswanaMap from "../components/BotswanaMap";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getSummary(), api.getRegions()])
      .then(([s, r]) => {
        setSummary(s);
        setRegions(r);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error">Error: {error}</div>;
  if (!summary) return <div className="loading">Loading data...</div>;

  const typeData = Object.entries(summary.facility_type_counts).map(
    ([name, count]) => ({ name, count })
  );
  const regionData = regions
    .map((r) => ({ name: r.name, facilities: r.facility_count }))
    .sort((a, b) => b.facilities - a.facilities);

  return (
    <div className="page">
      <AnimatedTagline />
      <p className="dashboard-subtitle">
        Delivering the right medicine, to the right place, at the right time.
      </p>
      <p className="dashboard-subtitle-tswana">
        Go isa melemo e e siameng, kwa lefelong le le siameng, ka nako e e siameng.
      </p>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{summary.total_facilities}</div>
          <div className="stat-label">Health Facilities</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {(summary.total_population / 1e6).toFixed(2)}M
          </div>
          <div className="stat-label">Population Served</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{summary.dhmt_count}</div>
          <div className="stat-label">DHMT Regions</div>
        </div>
      </div>

      <div className="chart-card" style={{ marginBottom: "1.5rem" }}>
        <h3>Health Facility Network</h3>
        <BotswanaMap height="500px" />
      </div>

      <div className="charts-row">
        <div className="chart-card">
          <h3>Facility Types</h3>
          <ResponsiveContainer width="100%" height={500}>
            <BarChart data={typeData} margin={{ top: 10, right: 10, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                interval={0}
                angle={-40}
                textAnchor="end"
                tick={{ fontSize: 11 }}
                height={120}
              />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Facilities by Region</h3>
          <ResponsiveContainer width="100%" height={500}>
            <BarChart data={regionData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} interval={0} />
              <Tooltip />
              <Bar dataKey="facilities" fill="#10b981" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="regions-list">
        <h3>Regions</h3>
        <div className="region-cards">
          {regions.map((r) => (
            <Link
              key={r.name}
              to={`/region/${encodeURIComponent(r.name)}`}
              className="region-card"
            >
              <div className="region-name">{r.name}</div>
              <div className="region-meta">
                {r.facility_count} facilities &middot; Source: {r.source_node}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
