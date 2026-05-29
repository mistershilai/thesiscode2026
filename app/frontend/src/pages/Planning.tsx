import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  Region,
  RegionDemand,
  PlanningResult,
  Shipment,
} from "../api/client";
import ConfirmModal from "../components/ConfirmModal";

const STRATEGIES = [
  { value: "nominal", label: "Nominal" },
  { value: "static_robust", label: "Static Robust" },
  { value: "adr", label: "Adjustable Robust (ADR)" },
];

export default function Planning() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [region, setRegion] = useState("");
  const [strategy, setStrategy] = useState("static_robust");
  const [scenario, setScenario] = useState("2526");
  const [gamma, setGamma] = useState(10);
  const [shortagePenalty, setShortagePenalty] = useState(5);
  const [transportCostPerKm, setTransportCostPerKm] = useState(0.5);
  const [holdingCost, setHoldingCost] = useState(0.1);
  const [arcCap, setArcCap] = useState(2000);
  const [roundUp, setRoundUp] = useState(false);

  const [demandData, setDemandData] = useState<RegionDemand | null>(null);
  const [inventory, setInventory] = useState<Record<string, Record<string, number>>>({});
  const [lastDemand, setLastDemand] = useState<Record<string, Record<string, number>>>({});
  const [useLastDemand, setUseLastDemand] = useState(false);

  // CMS product prices (editable)
  const [cmsProducts, setCmsProducts] = useState<
    { product_code: string; description: string; unit_price_bwp: number }[]
  >([]);
  const [customPrices, setCustomPrices] = useState<Record<string, number>>({});
  const [showPrices, setShowPrices] = useState(false);

  // Add drug / facility forms
  const [showAddDrug, setShowAddDrug] = useState(false);
  const [newDrug, setNewDrug] = useState({ code: "", description: "", price: 0, demand: 0 });
  const [showAddFacility, setShowAddFacility] = useState(false);
  const [newFac, setNewFac] = useState({ name: "", type: "Clinic", dhmt: "", lat: 0, lon: 0, parentHospital: "" });
  const [regionFacilities, setRegionFacilities] = useState<{ name: string; type: string; latitude: number; longitude: number }[]>([]);
  const [addStatus, setAddStatus] = useState("");

  // Relocate (edit coordinates)
  const [relocating, setRelocating] = useState<{ name: string; lat: string; lon: string } | null>(null);

  // Confirm modal
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);
  const [confirmRelocate, setConfirmRelocate] = useState<{ name: string; lat: number; lon: number } | null>(null);

  // Hospital removal rerouting
  const [pendingRemove, setPendingRemove] = useState<{
    name: string;
    downstream: string[];
    availableHospitals: string[];
  } | null>(null);
  const [replacementHospital, setReplacementHospital] = useState("");

  const apiBase = (import.meta as any).env?.VITE_API_URL || "/api";

  const removeFacility = async (name: string, replacement?: string) => {
    setAddStatus("");
    try {
      const r = await fetch(`${apiBase}/facilities/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("kaelo_token") || ""}` },
        body: JSON.stringify({ name, replacement_hospital: replacement || undefined }),
      });
      const d = await r.json();
      if (r.status === 409) {
        // Hospital removal: needs rerouting
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
      setAddStatus(`Removed ${name} (${d.total_facilities} remaining)`);
      setPendingRemove(null);
      api.getRegionDemand(region, scenario, true).then(setDemandData);
      api.getRegions().then(setRegions);
    } catch (e: any) {
      setAddStatus(`Error: ${e.message}`);
    }
  };

  const relocateFacility = async (name: string, lat: number, lon: number) => {
    setAddStatus("");
    try {
      const r = await fetch(`${apiBase}/facilities/relocate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("kaelo_token") || ""}` },
        body: JSON.stringify({ name, latitude: lat, longitude: lon }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Failed");
      setAddStatus(`Relocated ${name}: ${d.distances_recomputed} routes recomputed`);
      setRelocating(null);
      api.getRegionFacilities(region).then((facs) =>
        setRegionFacilities(facs.map((f) => ({ name: f.name, type: f.type, latitude: f.latitude, longitude: f.longitude })))
      ).catch(console.error);
    } catch (e: any) {
      setAddStatus(`Error: ${e.message}`);
    }
  };

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<PlanningResult | null>(null);

  useEffect(() => {
    api.getRegions().then(setRegions).catch(console.error);
    api.getCmsProducts().then(setCmsProducts).catch(console.error);
  }, []);

  // Load facility/drug info when region changes
  useEffect(() => {
    if (!region) return;
    setResult(null);
    setInventory({});
    setLastDemand({});
    api.getRegionDemand(region, scenario, true).then(setDemandData).catch(console.error);
    api.getRegionFacilities(region).then((facs) =>
      setRegionFacilities(facs.map((f) => ({ name: f.name, type: f.type, latitude: f.latitude, longitude: f.longitude })))
    ).catch(console.error);
  }, [region, scenario]);

  const setSolving = (v: boolean) => {
    setLoading(v);
    (window as any).__setSolving?.(v);
  };

  const runPlan = async () => {
    if (!region) return;
    setSolving(true);
    setError("");
    try {
      const res = await api.plan({
        region,
        strategy,
        scenario,
        kappa: 10,
        gamma,
        transport_cost_per_km: transportCostPerKm,
        shortage_penalty: shortagePenalty,
        holding_cost: holdingCost,
        use_cms_data: true,
        initial_inventory: Object.keys(inventory).length > 0 ? inventory : null,
        last_demand: useLastDemand && Object.keys(lastDemand).length > 0 ? lastDemand : null,
        custom_prices: Object.keys(customPrices).length > 0 ? customPrices : null,
        arc_cap: arcCap,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSolving(false);
    }
  };

  // When "round up" is toggled, apply ceil() to all shipment/procurement
  // quantities and recompute procurement cost + unit totals. Transport,
  // holding, shortage are unchanged (unit totals are counts, not costs
  // tied to the LP's λ decisions).
  const displayed = result
    ? (() => {
        if (!roundUp) return result;
        const shipments = result.shipments.map((s) => ({
          ...s,
          quantity: Math.ceil(s.quantity),
        }));
        let newProcCost = 0;
        let newUnitsProcured = 0;
        const procurement = result.procurement.map((p) => {
          const q = Math.ceil(p.quantity);
          const total = Math.round(q * p.unit_cost * 100) / 100;
          newProcCost += q * p.unit_cost;
          newUnitsProcured += q;
          return { ...p, quantity: q, total_cost: total };
        });
        const newUnitsShipped = shipments.reduce((sum, s) => sum + s.quantity, 0);
        return {
          ...result,
          shipments,
          procurement,
          summary: {
            ...result.summary,
            total_procurement_cost: Math.round(newProcCost * 100) / 100,
            total_units_procured: newUnitsProcured,
            total_units_shipped: newUnitsShipped,
          },
        };
      })()
    : null;

  // Group shipments by route for display (uses `displayed`, so rounded when toggled)
  const groupedShipments = displayed
    ? displayed.shipments.reduce<Record<string, Shipment[]>>((acc, s) => {
        const key = `${s.from} → ${s.to}`;
        (acc[key] ??= []).push(s);
        return acc;
      }, {})
    : {};

  return (
    <div className="page">
      <Link to="/" className="back-link">
        &larr; Back to Dashboard
      </Link>
      <h1>Planning Mode</h1>
      <p className="page-subtitle-tswana">Peakanyo ya Phepelo</p>

      <div className="optimize-layout">
        <div className="params-panel">
          <h3>Configuration <span className="label-tswana">Thulaganyo</span></h3>

          <label>
            Region <span className="label-tswana">Kgaolo</span>
            <select value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="">Select region...</option>
              {regions.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.name} ({r.facility_count} facilities)
                </option>
              ))}
            </select>
          </label>

          <label>
            Strategy <span className="label-tswana">Togamaano</span>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </label>

          <label>
            Robustness (Gamma) <span className="label-tswana">Tshireletso</span>
            <input type="number" min={0} step={1} value={gamma}
              onChange={(e) => setGamma(+e.target.value)} />
          </label>

          <label>
            Shortage penalty (x cost) <span className="label-tswana">Kotlhao ya tlhaelo</span>
            <input type="number" min={0} step={0.5} value={shortagePenalty}
              onChange={(e) => setShortagePenalty(+e.target.value)} />
          </label>

          <label>
            Transport cost (BWP/km) <span className="label-tswana">Tlhwatlhwa ya dipalangwa</span>
            <input type="number" min={0} step={0.1} value={transportCostPerKm}
              onChange={(e) => setTransportCostPerKm(+e.target.value)} />
          </label>

          <label>
            Holding cost (BWP/unit/period) <span className="label-tswana">Tlhwatlhwa ya polokelo</span>
            <input type="number" min={0} step={0.05} value={holdingCost}
              onChange={(e) => setHoldingCost(+e.target.value)} />
          </label>

          <label>
            Shipment capacity (units/trip) <span className="label-tswana">Bogolo jwa lebokoso</span>
            <input type="number" min={1} step={100} value={arcCap}
              onChange={(e) => setArcCap(+e.target.value)} />
          </label>

          {demandData && (
            <div style={{ marginTop: "0.75rem" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={useLastDemand}
                  onChange={(e) => setUseLastDemand(e.target.checked)}
                  style={{ width: "auto" }}
                />
                Evaluate against this cycle's order request
                <span className="label-tswana">Sekaseka kopo ya jaanong</span>
              </label>
              <span className="param-hint">
                Compute realized shortage & holding by applying the committed plan to this cycle's
                actual order quantities (post-hoc, non-anticipative).
              </span>
            </div>
          )}

          {region && (
            <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.4rem" }}>
              <button
                className="btn-sm"
                style={{ flex: 1 }}
                onClick={() => {
                  const url = `${apiBase}/regions/${encodeURIComponent(region)}/template`;
                  const token = localStorage.getItem("kaelo_token") || "";
                  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
                    .then((r) => {
                      if (!r.ok) throw new Error(`HTTP ${r.status}`);
                      return r.blob();
                    })
                    .then((blob) => {
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob);
                      a.download = `${region.replace(/[/ ]/g, "_")}_template.xlsx`;
                      a.click();
                      URL.revokeObjectURL(a.href);
                      setAddStatus("Template downloaded");
                    })
                    .catch((e) => setAddStatus(`Download failed: ${e.message}`));
                }}
              >
                Download Template
              </button>
              <label
                className="btn-sm"
                style={{ flex: 1, textAlign: "center", cursor: "pointer" }}
              >
                Upload Filled
                <input
                  type="file"
                  accept=".xlsx"
                  style={{ display: "none" }}
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    const token = localStorage.getItem("kaelo_token") || "";
                    const fd = new FormData();
                    fd.append("file", f);
                    try {
                      const r = await fetch(
                        `${apiBase}/regions/${encodeURIComponent(region)}/parse-template`,
                        {
                          method: "POST",
                          headers: { Authorization: `Bearer ${token}` },
                          body: fd,
                        }
                      );
                      const d = await r.json();
                      if (!r.ok) throw new Error(d.detail || "Parse failed");
                      setInventory(d.inventory || {});
                      setLastDemand(d.order_request || {});
                      if (d.order_request_rows > 0) setUseLastDemand(true);
                      setAddStatus(
                        `Loaded ${d.inventory_rows} inventory rows, ${d.order_request_rows} order rows`
                      );
                    } catch (err: any) {
                      setAddStatus(`Upload failed: ${err.message}`);
                    } finally {
                      e.target.value = "";
                    }
                  }}
                />
              </label>
            </div>
          )}

          {cmsProducts.length > 0 && (
            <div style={{ marginTop: "0.75rem" }}>
              <button
                className="btn-sm"
                onClick={() => setShowPrices(!showPrices)}
                style={{ width: "100%" }}
              >
                {showPrices ? "Hide Prices" : "Edit Unit Prices"}
                <span className="label-tswana" style={{ marginLeft: "0.4rem" }}>
                  Ditlhwatlhwa
                </span>
              </button>
              {Object.keys(customPrices).length > 0 && (
                <span className="custom-demand-badge" style={{ marginTop: "0.35rem", display: "inline-block" }}>
                  {Object.keys(customPrices).length} prices modified
                </span>
              )}
              {showPrices && (
                <div className="price-editor">
                  <div className="price-list">
                    {cmsProducts.map((p) => (
                      <div key={p.product_code} className="price-row">
                        <span className="price-drug" title={`${p.product_code}: ${p.description}`}>
                          {p.description || p.product_code}
                        </span>
                        <input
                          type="number"
                          min={0}
                          step={0.5}
                          className="price-input"
                          placeholder={String(p.unit_price_bwp)}
                          value={customPrices[p.product_code] ?? ""}
                          onChange={(e) => {
                            const val = e.target.value;
                            setCustomPrices((prev) => {
                              if (val === "" || +val === p.unit_price_bwp) {
                                const next = { ...prev };
                                delete next[p.product_code];
                                return next;
                              }
                              return { ...prev, [p.product_code]: +val };
                            });
                          }}
                        />
                        <span className="price-unit">BWP</span>
                        <button
                          className="btn-xs"
                          style={{ color: "#f87171", borderColor: "rgba(239,68,68,0.25)", marginLeft: "0.2rem" }}
                          title={`Remove ${p.product_code}`}
                          onClick={() => {
                            if (!window.confirm(`Remove "${p.description || p.product_code}"?`)) return;
                            (async () => {
                              try {
                                const r = await fetch(`${apiBase}/cms/products/remove`, {
                                  method: "POST",
                                  headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("kaelo_token") || ""}` },
                                  body: JSON.stringify({ product_code: p.product_code }),
                                });
                                const d = await r.json();
                                if (!r.ok) throw new Error(d.detail || "Failed");
                                setAddStatus(`Removed ${p.description || p.product_code} (${d.total_products} remaining)`);
                                api.getCmsProducts().then(setCmsProducts);
                              } catch (e: any) { setAddStatus(`Error: ${e.message}`); }
                            })();
                          }}
                        >
                          &times;
                        </button>
                      </div>
                    ))}
                  </div>
                  <button
                    className="btn-sm btn-sm-reset"
                    style={{ marginTop: "0.5rem", width: "100%" }}
                    onClick={() => setCustomPrices({})}
                  >
                    Reset all prices
                  </button>
                </div>
              )}
            </div>
          )}

          <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.4rem" }}>
            <button className="btn-sm" style={{ flex: 1 }} onClick={() => { setShowAddDrug(!showAddDrug); setShowAddFacility(false); }}>
              + Drug <span className="label-tswana">Molemo</span>
            </button>
            <button className="btn-sm" style={{ flex: 1 }} onClick={() => { setShowAddFacility(!showAddFacility); setShowAddDrug(false); }}>
              + Facility <span className="label-tswana">Lefelo</span>
            </button>
          </div>

          {addStatus && (
            <div className={addStatus.startsWith("Error") ? "error" : "custom-demand-badge"}
              style={{ marginTop: "0.5rem", display: "block", fontSize: "0.75rem" }}>
              {addStatus}
            </div>
          )}

          {showAddDrug && (
            <div className="add-form">
              <h4>Add Drug <span className="label-tswana">Tsenya Molemo</span></h4>
              <label>
                Product Code
                <input type="text" placeholder="e.g. AMX010" value={newDrug.code}
                  onChange={(e) => setNewDrug({ ...newDrug, code: e.target.value })} />
              </label>
              <label>
                Description
                <input type="text" placeholder="e.g. Amoxicillin 500mg Capsule" value={newDrug.description}
                  onChange={(e) => setNewDrug({ ...newDrug, description: e.target.value })} />
              </label>
              <label>
                Unit Price (BWP)
                <input type="number" min={0} step={0.5} value={newDrug.price || ""}
                  onChange={(e) => setNewDrug({ ...newDrug, price: +e.target.value })} />
              </label>
              <label>
                Biweekly Demand (national)
                <input type="number" min={0} value={newDrug.demand || ""}
                  onChange={(e) => setNewDrug({ ...newDrug, demand: +e.target.value })} />
              </label>
              <button className="btn-sm" style={{ width: "100%", marginTop: "0.5rem" }}
                onClick={async () => {
                  setAddStatus("");
                  try {
                    const base = (import.meta as any).env?.VITE_API_URL || "/api";
                    const r = await fetch(`${base}/cms/products/add`, {
                      method: "POST", headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        product_code: newDrug.code, description: newDrug.description,
                        unit_price_bwp: newDrug.price, biweekly_demand: newDrug.demand,
                      }),
                    });
                    const d = await r.json();
                    if (!r.ok) throw new Error(d.detail || "Failed");
                    setAddStatus(`Added ${newDrug.code} (${d.total_products} total drugs)`);
                    setNewDrug({ code: "", description: "", price: 0, demand: 0 });
                    api.getCmsProducts().then(setCmsProducts);
                  } catch (e: any) { setAddStatus(`Error: ${e.message}`); }
                }}>
                Add Drug
              </button>
            </div>
          )}

          {showAddFacility && (
            <div className="add-form">
              <h4>Manage Facilities <span className="label-tswana">Laola Mafelo</span></h4>

              {/* Facility list with remove/relocate */}
              {region && demandData && (
                <div className="facility-remove-list">
                  <span className="param-hint" style={{ marginBottom: "0.4rem", display: "block" }}>
                    Manage facilities in {region}:
                  </span>
                  <div style={{ maxHeight: "220px", overflowY: "auto", marginBottom: "0.75rem" }}>
                    {demandData.facilities.map((fac) => {
                      const rf = regionFacilities.find((f) => f.name === fac);
                      const isEditing = relocating?.name === fac;
                      return (
                        <div key={fac}>
                          <div className="facility-remove-row">
                            <span className="facility-remove-name">{fac}</span>
                            <button
                              className="btn-xs"
                              style={{ color: "#60a5fa", borderColor: "rgba(59,130,246,0.25)" }}
                              onClick={() =>
                                setRelocating(
                                  isEditing
                                    ? null
                                    : {
                                        name: fac,
                                        lat: rf ? String(rf.latitude) : "",
                                        lon: rf ? String(rf.longitude) : "",
                                      }
                                )
                              }
                            >
                              {isEditing ? "cancel" : "move"}
                            </button>
                            <button
                              className="btn-xs"
                              style={{ color: "#f87171", borderColor: "rgba(239,68,68,0.25)" }}
                              onClick={() => setConfirmTarget(fac)}
                            >
                              remove
                            </button>
                          </div>
                          {isEditing && (
                            <div style={{ display: "flex", gap: "0.3rem", padding: "0.35rem 0.25rem 0.5rem 0.25rem" }}>
                              <input
                                type="number"
                                step="0.000001"
                                placeholder="Latitude"
                                value={relocating.lat}
                                onChange={(e) => setRelocating({ ...relocating, lat: e.target.value })}
                                style={{ flex: 1, minWidth: 0 }}
                              />
                              <input
                                type="number"
                                step="0.000001"
                                placeholder="Longitude"
                                value={relocating.lon}
                                onChange={(e) => setRelocating({ ...relocating, lon: e.target.value })}
                                style={{ flex: 1, minWidth: 0 }}
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
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Hospital rerouting dialog */}
              {pendingRemove && (
                <div className="add-form" style={{ borderColor: "rgba(245,158,11,0.3)", marginBottom: "0.75rem" }}>
                  <h4 style={{ color: "#fbbf24" }}>Reroute Required</h4>
                  <p style={{ fontSize: "0.75rem", color: "#94a3b8", marginBottom: "0.5rem" }}>
                    Removing <strong style={{ color: "#e2e8f0" }}>{pendingRemove.name}</strong> will
                    affect {pendingRemove.downstream.length} downstream facilities.
                    Choose a replacement hospital:
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
                          <option key={h} value={h}>{h}</option>
                        ))}
                      </select>
                    </label>
                  ) : (
                    <p style={{ fontSize: "0.75rem", color: "#f87171" }}>
                      No other hospitals in this region. Add a new hospital first.
                    </p>
                  )}
                  <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.5rem" }}>
                    <button
                      className="btn-sm"
                      style={{ flex: 1, color: "#fbbf24", borderColor: "rgba(245,158,11,0.3)" }}
                      disabled={!replacementHospital}
                      onClick={() => removeFacility(pendingRemove.name, replacementHospital)}
                    >
                      Confirm removal
                    </button>
                    <button
                      className="btn-sm"
                      style={{ flex: 1 }}
                      onClick={() => setPendingRemove(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              <h4 style={{ marginTop: "0.5rem" }}>Add New <span className="label-tswana">Tsenya Lefelo</span></h4>
              <label>
                Name
                <input type="text" placeholder="e.g. Maun Clinic" value={newFac.name}
                  onChange={(e) => setNewFac({ ...newFac, name: e.target.value })} />
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
              <label>
                DHMT Region
                <select value={newFac.dhmt} onChange={(e) => setNewFac({ ...newFac, dhmt: e.target.value })}>
                  <option value="">Select...</option>
                  {regions.map((r) => (
                    <option key={r.name} value={r.name}>{r.name}</option>
                  ))}
                </select>
              </label>
              {["Clinic", "Clinic with Maternity", "Health Post"].includes(newFac.type) && (
                <label>
                  Route from hospital <span className="label-tswana">Tswa kwa bookelong</span>
                  <select
                    value={newFac.parentHospital}
                    onChange={(e) => setNewFac({ ...newFac, parentHospital: e.target.value })}
                  >
                    <option value="">Auto (nearest)</option>
                    {regionFacilities
                      .filter((f) =>
                        ["Primary Hospital", "District Hospital", "Referral Hospital", "Warehouse"].includes(f.type)
                      )
                      .map((f) => (
                        <option key={f.name} value={f.name}>
                          {f.name} ({f.type})
                        </option>
                      ))}
                  </select>
                  <span className="param-hint">
                    Which hospital/warehouse supplies this facility
                  </span>
                </label>
              )}

              <label>
                Latitude
                <input type="number" step={0.0001} placeholder="-24.6282" value={newFac.lat || ""}
                  onChange={(e) => setNewFac({ ...newFac, lat: +e.target.value })} />
              </label>
              <label>
                Longitude
                <input type="number" step={0.0001} placeholder="25.9231" value={newFac.lon || ""}
                  onChange={(e) => setNewFac({ ...newFac, lon: +e.target.value })} />
              </label>
              <span className="param-hint">
                Road distances computed via OSRM routing engine
              </span>
              <button className="btn-sm" style={{ width: "100%", marginTop: "0.5rem" }}
                onClick={async () => {
                  setAddStatus("");
                  try {
                    const base = (import.meta as any).env?.VITE_API_URL || "/api";
                    const r = await fetch(`${base}/facilities/add`, {
                      method: "POST", headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        name: newFac.name, type: newFac.type, dhmt: newFac.dhmt,
                        latitude: newFac.lat, longitude: newFac.lon,
                        parent_hospital: newFac.parentHospital || undefined,
                      }),
                    });
                    const d = await r.json();
                    if (!r.ok) throw new Error(d.detail || "Failed");
                    setAddStatus(`Added ${newFac.name}: ${d.distances_computed} routes computed via ${d.distance_method}`);
                    setNewFac({ name: "", type: "Clinic", dhmt: "", lat: 0, lon: 0, parentHospital: "" });
                    api.getRegionFacilities(region).then((facs) =>
                      setRegionFacilities(facs.map((f) => ({ name: f.name, type: f.type, latitude: f.latitude, longitude: f.longitude })))
                    );
                    api.getRegions().then(setRegions);
                  } catch (e: any) { setAddStatus(`Error: ${e.message}`); }
                }}>
                Add Facility
              </button>
            </div>
          )}

          <div className="btn-group">
            <button
              className="btn btn-primary"
              onClick={runPlan}
              disabled={loading || !region}
            >
              {loading ? "Solving..." : "Generate Plan"}
            </button>
          </div>
        </div>

        <div className="results-panel">
          {error && <div className="error">{error}</div>}

          {loading && (
            <div className="loading solver-loading">
              <div className="solver-spinner" />
              <p>Computing optimal shipment plan...</p>
              <p className="solver-tswana">Re bala leano le le siameng la phepelo...</p>
            </div>
          )}

          {!loading && !result && demandData && (
            <>
              <div className="plan-inventory-section">
                <h3>Current Inventory <span className="label-tswana">Setoko sa Gompieno</span></h3>
                <p className="param-hint" style={{ marginBottom: "0.75rem" }}>
                  Enter current stock at each facility. Leave blank or 0 for empty shelves.
                </p>
                <div className="demand-table-wrapper" style={{ maxHeight: "350px" }}>
                  <table className="demand-table">
                    <thead>
                      <tr>
                        <th className="demand-th-facility">Facility</th>
                        {demandData.drug_classes.map((d) => (
                          <th key={d} className="demand-th-drug" title={cmsProducts.find((p) => p.product_code === d)?.description || d}>
                            {d.length > 8 ? d.slice(0, 8) + "..." : d}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {demandData.facilities.map((fac) => (
                        <tr key={fac}>
                          <td className="demand-td-facility" title={fac}>
                            {fac.length > 25 ? fac.slice(0, 25) + "..." : fac}
                          </td>
                          {demandData.drug_classes.map((drug) => (
                            <td key={drug} className="demand-td-value">
                              <input
                                type="number"
                                min={0}
                                placeholder="0"
                                value={inventory[fac]?.[drug] ?? ""}
                                onChange={(e) => {
                                  const val = +e.target.value;
                                  setInventory((prev) => ({
                                    ...prev,
                                    [fac]: { ...(prev[fac] || {}), [drug]: val },
                                  }));
                                }}
                              />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {useLastDemand && (
                <div className="plan-inventory-section" style={{ marginTop: "1.5rem" }}>
                  <h3>This Cycle Order Request <span className="label-tswana">Kopo ya Jaanong</span></h3>
                  <p className="param-hint" style={{ marginBottom: "0.75rem" }}>
                    Enter the realized order request from facilities this cycle. The plan was committed
                    against the forecast before this was known — we evaluate the committed plan against
                    these realized quantities to report actual shortage and holding.
                  </p>
                  <div className="demand-table-wrapper" style={{ maxHeight: "300px" }}>
                    <table className="demand-table">
                      <thead>
                        <tr>
                          <th className="demand-th-facility">Facility</th>
                          {demandData.drug_classes.map((d) => (
                            <th key={d} className="demand-th-drug" title={cmsProducts.find((p) => p.product_code === d)?.description || d}>
                              {d.length > 8 ? d.slice(0, 8) + "..." : d}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {demandData.facilities.map((fac) => (
                          <tr key={fac}>
                            <td className="demand-td-facility" title={fac}>
                              {fac.length > 25 ? fac.slice(0, 25) + "..." : fac}
                            </td>
                            {demandData.drug_classes.map((drug) => {
                              const defaultVal = demandData.demand[fac]?.[drug];
                              return (
                                <td key={drug} className="demand-td-value">
                                  <input
                                    type="number"
                                    min={0}
                                    placeholder={defaultVal ? String(Math.round(defaultVal)) : "0"}
                                    value={lastDemand[fac]?.[drug] ?? ""}
                                    onChange={(e) => {
                                      const val = +e.target.value;
                                      setLastDemand((prev) => ({
                                        ...prev,
                                        [fac]: { ...(prev[fac] || {}), [drug]: val },
                                      }));
                                    }}
                                  />
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="empty-state" style={{ paddingTop: "2rem" }}>
                <p>Enter inventory above, then click "Generate Plan".</p>
                <p className="empty-state-tswana">Tsenya setoko fa godimo, o bo o tobetsa "Generate Plan".</p>
              </div>
            </>
          )}

          {!loading && !result && !demandData && (
            <div className="empty-state">
              <p>Select a region to begin planning.</p>
              <p className="empty-state-tswana">Tlhopha kgaolo go simolola peakanyo.</p>
            </div>
          )}

          {result && displayed && result.status === "optimal" && (
            <div className="plan-results">
              <h3>Shipment Plan <span className="label-tswana">Leano la Phepelo</span></h3>

              <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", flexWrap: "wrap", marginBottom: "0.75rem" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={roundUp}
                    onChange={(e) => setRoundUp(e.target.checked)}
                    style={{ width: "auto" }}
                  />
                  Round up to whole units
                </label>
                <button
                  className="btn-sm"
                  onClick={async () => {
                    const token = localStorage.getItem("kaelo_token") || "";
                    try {
                      const r = await fetch(`${apiBase}/plan/export`, {
                        method: "POST",
                        headers: {
                          "Content-Type": "application/json",
                          Authorization: `Bearer ${token}`,
                        },
                        body: JSON.stringify({
                          region,
                          strategy: result.strategy,
                          // Send raw unrounded values; backend re-applies
                          // ceil when round_up is true so the two paths agree.
                          summary: result.summary,
                          shipments: result.shipments,
                          procurement: result.procurement,
                          round_up: roundUp,
                        }),
                      });
                      if (!r.ok) throw new Error(`HTTP ${r.status}`);
                      const blob = await r.blob();
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(blob);
                      a.download = `${region.replace(/[/ ]/g, "_")}_plan${roundUp ? "_rounded" : ""}.xlsx`;
                      a.click();
                      URL.revokeObjectURL(a.href);
                    } catch (e: any) {
                      alert(`Download failed: ${e.message}`);
                    }
                  }}
                >
                  Download Plan (xlsx)
                </button>
              </div>

              <div className="stats-grid" style={{ marginBottom: "1.5rem" }}>
                <div className="stat-card">
                  <div className="stat-value">{displayed.summary.active_routes}</div>
                  <div className="stat-label">Active Routes</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {displayed.summary.total_units_shipped.toLocaleString()}
                  </div>
                  <div className="stat-label">Units to Ship</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {displayed.summary.total_units_procured.toLocaleString()}
                  </div>
                  <div className="stat-label">Units to Procure</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    BWP {Math.round(displayed.summary.total_procurement_cost).toLocaleString()}
                  </div>
                  <div className="stat-label">Total Procurement Cost</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    BWP {Math.round(displayed.summary.total_transport_cost).toLocaleString()}
                  </div>
                  <div className="stat-label">Total Transport Cost</div>
                </div>
                {displayed.summary.total_holding_cost != null && (
                  <div className="stat-card">
                    <div className="stat-value">
                      BWP {Math.round(displayed.summary.total_holding_cost).toLocaleString()}
                    </div>
                    <div className="stat-label">Realized Holding Cost</div>
                  </div>
                )}
                {displayed.summary.total_shortage_cost != null && (
                  <div className="stat-card">
                    <div className="stat-value">
                      BWP {Math.round(displayed.summary.total_shortage_cost).toLocaleString()}
                    </div>
                    <div className="stat-label">Realized Shortage Cost</div>
                  </div>
                )}
              </div>

              {displayed.procurement.length > 0 && (
                <>
                  <h3>Procurement Orders <span className="label-tswana">Ditaelo tsa Theko</span></h3>
                  <div className="facility-table-wrapper">
                    <table className="facility-table">
                      <thead>
                        <tr>
                          <th>Drug</th>
                          <th>Quantity</th>
                          <th>Unit Cost (BWP)</th>
                          <th>Total Cost (BWP)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {displayed.procurement.map((p, i) => (
                          <tr key={i}>
                            <td>{p.drug}</td>
                            <td>{p.quantity.toLocaleString()}</td>
                            <td>{p.unit_cost.toLocaleString()}</td>
                            <td>{p.total_cost.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}

              <h3 style={{ marginTop: "1.5rem" }}>
                Shipment Routes <span className="label-tswana">Ditsela tsa Phepelo</span>
              </h3>
              <div className="shipment-routes">
                {Object.entries(groupedShipments).map(([route, shipments]) => (
                  <div key={route} className="shipment-route-card">
                    <div className="route-header">
                      <span className="route-label">{route}</span>
                      <span className="route-distance">
                        {shipments[0].distance_km} km
                      </span>
                    </div>
                    <div className="route-drugs">
                      {shipments.map((s, i) => (
                        <div key={i} className="route-drug-row">
                          <span className="route-drug-name">{s.drug}</span>
                          <span className="route-drug-qty">
                            {s.quantity.toLocaleString()} units
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <p className="param-hint" style={{ marginTop: "1rem", textAlign: "center" }}>
                Solved in {result.solve_time_s}s using {result.strategy} strategy
              </p>
            </div>
          )}

          {result && result.status !== "optimal" && (
            <div className="error">
              Solver returned status: {result.status}. Try adjusting parameters.
            </div>
          )}
        </div>
      </div>

      {confirmTarget && (
        <ConfirmModal
          title="Remove Facility"
          message={`Are you sure you want to remove "${confirmTarget}"? This action cannot be undone and will require OSRM recalculation if re-added.`}
          onConfirm={() => {
            removeFacility(confirmTarget);
            setConfirmTarget(null);
          }}
          onCancel={() => setConfirmTarget(null)}
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
