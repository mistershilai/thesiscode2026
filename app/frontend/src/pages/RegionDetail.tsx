import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { Facility } from "../api/client";
import FacilityMap from "../components/FacilityMap";

export default function RegionDetail() {
  const { region } = useParams<{ region: string }>();
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!region) return;
    api
      .getRegionFacilities(region)
      .then(setFacilities)
      .catch((e) => setError(e.message));
  }, [region]);

  if (error) return <div className="error">Error: {error}</div>;
  if (!facilities.length)
    return <div className="loading">Loading facilities...</div>;

  const typeCounts: Record<string, number> = {};
  facilities.forEach((f) => {
    typeCounts[f.type] = (typeCounts[f.type] || 0) + 1;
  });

  return (
    <div className="page">
      <Link to="/" className="back-link">
        &larr; Back to Dashboard
      </Link>
      <h1>{region}</h1>
      <p>{facilities.length} facilities</p>

      <div className="type-badges">
        {Object.entries(typeCounts).map(([type, count]) => (
          <span key={type} className="badge">
            {type}: {count}
          </span>
        ))}
      </div>

      <div className="map-container">
        <FacilityMap facilities={facilities} />
      </div>

      <div className="facility-table-wrapper">
        <table className="facility-table">
          <thead>
            <tr>
              <th>Facility Name</th>
              <th>Type</th>
              <th>Latitude</th>
              <th>Longitude</th>
            </tr>
          </thead>
          <tbody>
            {facilities.map((f) => (
              <tr key={f.name}>
                <td>{f.name}</td>
                <td>{f.type}</td>
                <td>{f.latitude.toFixed(4)}</td>
                <td>{f.longitude.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Link
        to={`/optimize?region=${encodeURIComponent(region!)}`}
        className="btn btn-primary"
      >
        Run Optimization for {region}
      </Link>
    </div>
  );
}
