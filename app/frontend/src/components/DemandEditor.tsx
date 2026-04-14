import { useState, useRef } from "react";
import type { RegionDemand } from "../api/client";

interface Props {
  demandData: RegionDemand;
  onDemandChange: (demand: Record<string, Record<string, number>>) => void;
}

export default function DemandEditor({ demandData, onDemandChange }: Props) {
  const [editedDemand, setEditedDemand] = useState(demandData.demand);
  const [filterFacility, setFilterFacility] = useState("");
  const [filterDrug, setFilterDrug] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Get facilities and drug classes that have nonzero demand
  const activeFacilities = demandData.facilities.filter(
    (f) => editedDemand[f] && Object.keys(editedDemand[f]).length > 0
  );
  const activeDrugClasses = [
    ...new Set(
      Object.values(editedDemand).flatMap((d) => Object.keys(d))
    ),
  ].sort();

  const filteredFacilities = activeFacilities.filter((f) =>
    f.toLowerCase().includes(filterFacility.toLowerCase())
  );
  const filteredDrugs = activeDrugClasses.filter((d) =>
    d.toLowerCase().includes(filterDrug.toLowerCase())
  );

  const handleCellChange = (
    facility: string,
    drug: string,
    value: string
  ) => {
    const num = parseFloat(value);
    if (isNaN(num) || num < 0) return;

    const updated = { ...editedDemand };
    if (!updated[facility]) updated[facility] = {};
    updated[facility] = { ...updated[facility], [drug]: num };
    setEditedDemand(updated);
    onDemandChange(updated);
  };

  const handleScaleFacility = (facility: string, factor: number) => {
    const updated = { ...editedDemand };
    if (!updated[facility]) return;
    const scaled: Record<string, number> = {};
    for (const [drug, val] of Object.entries(updated[facility])) {
      scaled[drug] = Math.round(val * factor * 100) / 100;
    }
    updated[facility] = scaled;
    setEditedDemand(updated);
    onDemandChange(updated);
  };

  const handleScaleAll = (factor: number) => {
    const updated: Record<string, Record<string, number>> = {};
    for (const [fac, drugs] of Object.entries(editedDemand)) {
      updated[fac] = {};
      for (const [drug, val] of Object.entries(drugs)) {
        updated[fac][drug] = Math.round(val * factor * 100) / 100;
      }
    }
    setEditedDemand(updated);
    onDemandChange(updated);
  };

  const handleReset = () => {
    setEditedDemand(demandData.demand);
    onDemandChange(demandData.demand);
  };

  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.trim().split("\n");
      if (lines.length < 2) return;

      const headers = lines[0].split(",").map((h) => h.trim());
      const drugCols = headers.slice(1); // first col is facility name

      const newDemand: Record<string, Record<string, number>> = {};
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map((c) => c.trim());
        const facility = cols[0];
        newDemand[facility] = {};
        drugCols.forEach((drug, j) => {
          const val = parseFloat(cols[j + 1]);
          if (!isNaN(val) && val > 0) {
            newDemand[facility][drug] = val;
          }
        });
      }

      setEditedDemand(newDemand);
      onDemandChange(newDemand);
    };
    reader.readAsText(file);
    // Reset the file input so re-uploading the same file triggers onChange
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleCSVDownload = () => {
    const drugs = activeDrugClasses;
    const rows = ["facility," + drugs.join(",")];
    for (const fac of activeFacilities) {
      const vals = drugs.map((d) => (editedDemand[fac]?.[d] ?? 0).toString());
      rows.push(fac + "," + vals.join(","));
    }
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `demand_${demandData.region}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Total demand summary
  let totalDemand = 0;
  for (const drugs of Object.values(editedDemand)) {
    for (const val of Object.values(drugs)) {
      totalDemand += val;
    }
  }

  return (
    <div className="demand-editor">
      <div className="demand-header">
        <h3>Expected Demand</h3>
        <span className="demand-total">
          Total: {Math.round(totalDemand).toLocaleString()} units
        </span>
      </div>

      <div className="demand-toolbar">
        <button className="btn-sm" onClick={() => handleScaleAll(1.1)}>
          +10%
        </button>
        <button className="btn-sm" onClick={() => handleScaleAll(0.9)}>
          -10%
        </button>
        <button className="btn-sm" onClick={() => handleScaleAll(1.5)}>
          +50%
        </button>
        <button className="btn-sm" onClick={() => handleScaleAll(2.0)}>
          2x
        </button>
        <button className="btn-sm btn-sm-reset" onClick={handleReset}>
          Reset
        </button>
        <button className="btn-sm" onClick={handleCSVDownload}>
          Export CSV
        </button>
        <label className="btn-sm btn-sm-upload">
          Import CSV
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleCSVUpload}
            hidden
          />
        </label>
      </div>

      <div className="demand-filters">
        <input
          type="text"
          placeholder="Filter facilities..."
          value={filterFacility}
          onChange={(e) => setFilterFacility(e.target.value)}
        />
        <input
          type="text"
          placeholder="Filter drug classes..."
          value={filterDrug}
          onChange={(e) => setFilterDrug(e.target.value)}
        />
      </div>

      <div className="demand-table-wrapper">
        <table className="demand-table">
          <thead>
            <tr>
              <th className="demand-th-facility">Facility</th>
              {filteredDrugs.map((d) => (
                <th key={d} className="demand-th-drug" title={d}>
                  {d.length > 12 ? d.slice(0, 12) + "..." : d}
                </th>
              ))}
              <th>Scale</th>
            </tr>
          </thead>
          <tbody>
            {filteredFacilities.slice(0, 50).map((fac) => (
              <tr key={fac}>
                <td className="demand-td-facility" title={fac}>
                  {fac.length > 25 ? fac.slice(0, 25) + "..." : fac}
                </td>
                {filteredDrugs.map((drug) => (
                  <td key={drug} className="demand-td-value">
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      value={editedDemand[fac]?.[drug] ?? 0}
                      onChange={(e) =>
                        handleCellChange(fac, drug, e.target.value)
                      }
                    />
                  </td>
                ))}
                <td className="demand-td-scale">
                  <button
                    className="btn-xs"
                    onClick={() => handleScaleFacility(fac, 2)}
                    title="Double demand for this facility"
                  >
                    2x
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredFacilities.length > 50 && (
          <div className="demand-truncated">
            Showing 50 of {filteredFacilities.length} facilities. Use filter
            to narrow down.
          </div>
        )}
      </div>
    </div>
  );
}
