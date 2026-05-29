import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Scenario, CmsProduct } from "../api/client";

interface Props {
  value: string;
  onChange: (id: string) => void;
}

export default function ScenarioManager({ value, onChange }: Props) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [showEdit, setShowEdit] = useState(false);
  const [products, setProducts] = useState<CmsProduct[]>([]);
  const [edits, setEdits] = useState<Record<string, number>>({});

  const current = scenarios.find((s) => s.id === value);

  const loadScenarios = async () => {
    const list = await api.getScenarios();
    setScenarios(list);
    return list;
  };

  useEffect(() => {
    loadScenarios().catch((e) =>
      setError(e instanceof Error ? e.message : "Failed to load scenarios")
    );
  }, []);

  const newScenario = async () => {
    const name = window.prompt(
      `Name the new scenario (duplicates "${current?.label ?? value}").\nLetters, numbers, '_' or '-' only:`
    );
    if (!name) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.addScenario(name.trim(), value);
      setScenarios(res.scenarios);
      onChange(name.trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create scenario");
    } finally {
      setBusy(false);
    }
  };

  const deleteScenario = async () => {
    if (!current || current.builtin) return;
    if (!window.confirm(`Delete scenario "${current.label}"? This cannot be undone.`))
      return;
    setBusy(true);
    setError("");
    try {
      const res = await api.removeScenario(value);
      setScenarios(res.scenarios);
      onChange("2526");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete scenario");
    } finally {
      setBusy(false);
    }
  };

  const openEdit = async () => {
    setBusy(true);
    setError("");
    try {
      const prods = await api.getCmsProducts();
      setProducts(prods);
      const init: Record<string, number> = {};
      prods.forEach((p) => {
        init[p.product_code] = p.biweekly?.[value] ?? 0;
      });
      setEdits(init);
      setShowEdit(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load products");
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.updateScenario(value, edits);
      setScenarios(res.scenarios);
      setShowEdit(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save scenario");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <label>
        CMS Scenario <span className="label-tswana">Maemo a CMS</span>
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
              {s.builtin ? "" : " (custom)"}
            </option>
          ))}
        </select>
      </label>

      <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "-0.4rem" }}>
        <button type="button" className="btn-sm" disabled={busy} onClick={newScenario}>
          + New
        </button>
        {current && !current.builtin && (
          <>
            <button type="button" className="btn-sm" disabled={busy} onClick={openEdit}>
              Edit values
            </button>
            <button
              type="button"
              className="btn-sm"
              disabled={busy}
              style={{ color: "#f87171", borderColor: "rgba(248,113,113,0.3)" }}
              onClick={deleteScenario}
            >
              Delete
            </button>
          </>
        )}
      </div>

      {error && (
        <p style={{ fontSize: "0.75rem", color: "#f87171", margin: "0.2rem 0 0" }}>{error}</p>
      )}

      {showEdit && (
        <div className="modal-overlay" onClick={() => setShowEdit(false)}>
          <div
            className="modal-card"
            style={{ maxWidth: "640px", width: "90%" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="modal-title">Edit demand — {current?.label}</h3>
            <p className="modal-message">
              Biweekly demand per product (national totals, distributed by population share).
            </p>
            <div style={{ maxHeight: "50vh", overflowY: "auto", margin: "0.5rem 0" }}>
              <table style={{ width: "100%", fontSize: "0.8rem", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "#94a3b8" }}>
                    <th style={{ padding: "0.3rem" }}>Product</th>
                    <th style={{ padding: "0.3rem", width: "120px" }}>Biweekly</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.product_code} style={{ borderTop: "1px solid rgba(148,163,184,0.15)" }}>
                      <td style={{ padding: "0.3rem" }}>
                        {p.description || p.product_code}
                      </td>
                      <td style={{ padding: "0.3rem" }}>
                        <input
                          type="number"
                          min={0}
                          step={0.5}
                          value={edits[p.product_code] ?? 0}
                          onChange={(e) =>
                            setEdits((prev) => ({
                              ...prev,
                              [p.product_code]: +e.target.value,
                            }))
                          }
                          style={{ width: "100%" }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" disabled={busy} onClick={() => setShowEdit(false)}>
                Cancel
              </button>
              <button className="btn" disabled={busy} onClick={saveEdit}>
                {busy ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
