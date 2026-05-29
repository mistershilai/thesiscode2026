import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { Facility } from "../api/client";
import FacilityMap from "../components/FacilityMap";
import ConfirmModal from "../components/ConfirmModal";
import { useAuth } from "../auth";

const apiBase = (import.meta as any).env?.VITE_API_URL || "/api";

export default function RegionDetail() {
  const { region } = useParams<{ region: string }>();
  const { user } = useAuth();
  const canEdit = !!user;
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  // Add-facility form
  const [showAdd, setShowAdd] = useState(false);
  const [newFac, setNewFac] = useState({
    name: "",
    type: "Clinic",
    lat: "",
    lon: "",
    parentHospital: "",
  });

  // Relocate inline editor + confirm
  const [relocating, setRelocating] = useState<{ name: string; lat: string; lon: string } | null>(null);
  const [confirmRelocate, setConfirmRelocate] = useState<{ name: string; lat: number; lon: number } | null>(null);

  // Remove confirm + hospital-rerouting
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<{
    name: string;
    downstream: string[];
    availableHospitals: string[];
  } | null>(null);
  const [replacementHospital, setReplacementHospital] = useState("");

  const refresh = () => {
    if (!region) return;
    api.getRegionFacilities(region).then(setFacilities).catch((e) => setError(e.message));
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [region]);

  const addFacility = async () => {
    if (!region) return;
    setStatus("");
    const lat = parseFloat(newFac.lat);
    const lon = parseFloat(newFac.lon);
    if (!newFac.name || !lat || !lon) {
      setStatus("Name, latitude, and longitude are required");
      return;
    }
    try {
      const r = await fetch(`${apiBase}/facilities/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("kaelo_token") || ""}` },
        body: JSON.stringify({
          name: newFac.name,
          type: newFac.type,
          dhmt: region,
          latitude: lat,
          longitude: lon,
          parent_hospital: newFac.parentHospital || undefined,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed");
      setStatus(`Added ${newFac.name}: ${d.distances_computed} routes computed via ${d.distance_method}`);
      setNewFac({ name: "", type: "Clinic", lat: "", lon: "", parentHospital: "" });
      setShowAdd(false);
      refresh();
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    }
  };

  const removeFacility = async (name: string, replacement?: string) => {
    setStatus("");
    try {
      const r = await fetch(`${apiBase}/facilities/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("kaelo_token") || ""}` },
        body: JSON.stringify({ name, replacement_hospital: replacement || undefined }),
      });
      const d = await r.json();
      if (r.status === 409) {
        const detail = d.detail;
        setPendingRemove({
          name,
          downstream: detail.downstream_facilities,
          availableHospitals: detail.available_hospitals,
        });
        setReplacementHospital("");
        return;
      }
      if (!r.ok) throw new Error(d.detail || "Failed");
      setStatus(`Removed ${name} (${d.total_facilities} remaining)`);
      setPendingRemove(null);
      refresh();
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    }
  };

  const relocateFacility = async (name: string, lat: number, lon: number) => {
    setStatus("");
    try {
      const r = await fetch(`${apiBase}/facilities/relocate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("kaelo_token") || ""}` },
        body: JSON.stringify({ name, latitude: lat, longitude: lon }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed");
      setStatus(`Relocated ${name}: ${d.distances_recomputed} routes recomputed`);
      setRelocating(null);
      refresh();
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    }
  };

  if (error) return <div className="error">Error: {error}</div>;
  if (!facilities.length)
    return <div className="loading">Loading facilities...</div>;

  const typeCounts: Record<string, number> = {};
  facilities.forEach((f) => {
    typeCounts[f.type] = (typeCounts[f.type] || 0) + 1;
  });

  const hospitalTypes = ["Primary Hospital", "District Hospital", "Referral Hospital", "Warehouse"];
  const regionHospitals = facilities.filter((f) => hospitalTypes.includes(f.type));

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

      {status && (
        <div style={{ fontSize: "0.8rem", color: "#94a3b8", margin: "0.5rem 0" }}>{status}</div>
      )}

      <div className="facility-table-wrapper">
        <table className="facility-table">
          <thead>
            <tr>
              <th>Facility Name</th>
              <th>Type</th>
              <th>Latitude</th>
              <th>Longitude</th>
              {canEdit && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {facilities.map((f) => {
              const isEditing = relocating?.name === f.name;
              return (
                <>
                  <tr key={f.name}>
                    <td>{f.name}</td>
                    <td>{f.type}</td>
                    <td>{f.latitude.toFixed(4)}</td>
                    <td>{f.longitude.toFixed(4)}</td>
                    {canEdit && (
                      <td>
                        <button
                          className="btn-xs"
                          style={{ color: "#60a5fa", borderColor: "rgba(59,130,246,0.25)", marginRight: "0.3rem" }}
                          onClick={() =>
                            setRelocating(
                              isEditing
                                ? null
                                : { name: f.name, lat: String(f.latitude), lon: String(f.longitude) }
                            )
                          }
                        >
                          {isEditing ? "cancel" : "move"}
                        </button>
                        <button
                          className="btn-xs"
                          style={{ color: "#f87171", borderColor: "rgba(239,68,68,0.25)" }}
                          onClick={() => setConfirmRemove(f.name)}
                        >
                          remove
                        </button>
                      </td>
                    )}
                  </tr>
                  {canEdit && isEditing && (
                    <tr key={`${f.name}-edit`}>
                      <td colSpan={5}>
                        <div style={{ display: "flex", gap: "0.4rem", padding: "0.35rem 0" }}>
                          <input
                            type="number"
                            step="0.000001"
                            placeholder="Latitude"
                            value={relocating.lat}
                            onChange={(e) => setRelocating({ ...relocating, lat: e.target.value })}
                          />
                          <input
                            type="number"
                            step="0.000001"
                            placeholder="Longitude"
                            value={relocating.lon}
                            onChange={(e) => setRelocating({ ...relocating, lon: e.target.value })}
                          />
                          <button
                            className="btn-xs"
                            disabled={!relocating.lat || !relocating.lon}
                            onClick={() =>
                              setConfirmRelocate({
                                name: relocating.name,
                                lat: parseFloat(relocating.lat),
                                lon: parseFloat(relocating.lon),
                              })
                            }
                          >
                            save
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>

      {canEdit && (
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.75rem", flexWrap: "wrap" }}>
          <Link
            to={`/optimize?region=${encodeURIComponent(region!)}`}
            className="btn btn-primary"
          >
            Run Optimization for {region}
          </Link>
          <button className="btn btn-primary" onClick={() => setShowAdd((s) => !s)}>
            {showAdd ? "Cancel Add" : "Add Facility"}
          </button>
        </div>
      )}

      {canEdit && showAdd && (
        <div className="add-form" style={{ marginTop: "0.75rem" }}>
          <h4>Add New Facility to {region}</h4>
          <label>
            Name
            <input
              type="text"
              placeholder="e.g. Maun Clinic"
              value={newFac.name}
              onChange={(e) => setNewFac({ ...newFac, name: e.target.value })}
            />
          </label>
          <label>
            Type
            <select value={newFac.type} onChange={(e) => setNewFac({ ...newFac, type: e.target.value })}>
              <option>Clinic</option>
              <option>Clinic with Maternity</option>
              <option>Health Post</option>
              <option>Primary Hospital</option>
              <option>District Hospital</option>
            </select>
          </label>
          {["Clinic", "Clinic with Maternity", "Health Post"].includes(newFac.type) && (
            <label>
              Route from hospital
              <select
                value={newFac.parentHospital}
                onChange={(e) => setNewFac({ ...newFac, parentHospital: e.target.value })}
              >
                <option value="">Auto (nearest)</option>
                {regionHospitals.map((f) => (
                  <option key={f.name} value={f.name}>
                    {f.name} ({f.type})
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Latitude
            <input
              type="number"
              step="0.000001"
              value={newFac.lat}
              onChange={(e) => setNewFac({ ...newFac, lat: e.target.value })}
            />
          </label>
          <label>
            Longitude
            <input
              type="number"
              step="0.000001"
              value={newFac.lon}
              onChange={(e) => setNewFac({ ...newFac, lon: e.target.value })}
            />
          </label>
          <button className="btn btn-primary" onClick={addFacility}>
            Add Facility
          </button>
        </div>
      )}

      {pendingRemove && (
        <div className="add-form" style={{ borderColor: "rgba(245,158,11,0.3)", marginTop: "0.75rem" }}>
          <h4 style={{ color: "#fbbf24" }}>Reroute Required</h4>
          <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
            Removing <strong>{pendingRemove.name}</strong> will affect{" "}
            {pendingRemove.downstream.length} downstream facilities. Choose a replacement hospital:
          </p>
          {pendingRemove.availableHospitals.length > 0 ? (
            <label>
              Replacement hospital
              <select
                value={replacementHospital}
                onChange={(e) => setReplacementHospital(e.target.value)}
              >
                <option value="">Select...</option>
                {pendingRemove.availableHospitals.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p style={{ color: "#f87171" }}>No other hospitals in this region. Add a new hospital first.</p>
          )}
          <div style={{ display: "flex", gap: "0.4rem" }}>
            <button
              className="btn-sm"
              disabled={!replacementHospital}
              onClick={() => removeFacility(pendingRemove.name, replacementHospital)}
            >
              Confirm removal
            </button>
            <button className="btn-sm" onClick={() => setPendingRemove(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {confirmRemove && (
        <ConfirmModal
          title="Remove Facility"
          message={`Are you sure you want to remove "${confirmRemove}"? This action cannot be undone and will require OSRM recalculation if re-added.`}
          onConfirm={() => {
            removeFacility(confirmRemove);
            setConfirmRemove(null);
          }}
          onCancel={() => setConfirmRemove(null)}
        />
      )}

      {confirmRelocate && (
        <ConfirmModal
          title="Relocate Facility"
          message={`Are you sure you want to move "${confirmRelocate.name}" to (${confirmRelocate.lat}, ${confirmRelocate.lon})? This will recompute OSRM routes for this facility and overwrite the saved distance/duration matrices.`}
          onConfirm={() => {
            relocateFacility(confirmRelocate.name, confirmRelocate.lat, confirmRelocate.lon);
            setConfirmRelocate(null);
          }}
          onCancel={() => setConfirmRelocate(null)}
        />
      )}
    </div>
  );
}
