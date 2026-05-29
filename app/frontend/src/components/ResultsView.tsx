import { useState } from "react";
import type { OptimizationResult } from "../api/client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";

const COST_COMPONENTS = [
  { key: "Procurement", field: "avg_procurement_cost", color: "#10b981" },
  { key: "Transport", field: "avg_transport_cost", color: "#3b82f6" },
  { key: "Holding", field: "avg_holding_cost", color: "#f59e0b" },
  { key: "Shortage", field: "avg_shortage_cost", color: "#ef4444" },
] as const;

const STRATEGY_COLORS: Record<string, string> = {
  nominal: "#3b82f6",
  static_robust: "#f59e0b",
  adr: "#10b981",
};

const STRATEGY_LABELS: Record<string, string> = {
  nominal: "Nominal",
  static_robust: "Static Robust",
  adr: "ADR",
};

interface Props {
  results: OptimizationResult[];
}

export default function ResultsView({ results }: Props) {
  const [enabledComponents, setEnabledComponents] = useState<Record<string, boolean>>({
    Procurement: true,
    Transport: true,
    Holding: true,
    Shortage: true,
  });

  // Summary comparison table
  const summaries = results.map((r) => ({
    strategy: STRATEGY_LABELS[r.strategy] || r.strategy,
    ...r.summary,
  }));

  // Unmet % over time (multi-line if multiple strategies)
  const maxT = Math.max(...results.flatMap((r) => r.periods.map((p) => p.t)));
  const timeData = Array.from({ length: maxT + 1 }, (_, t) => {
    const point: Record<string, number | string> = { period: t };
    results.forEach((r) => {
      const p = r.periods.find((p) => p.t === t);
      point[r.strategy] = p?.unmet_pct ?? 0;
    });
    return point;
  });

  // Cost breakdown
  const costData = results.map((r) => {
    const s: any = r.summary;
    const row: Record<string, number | string> = {
      strategy: STRATEGY_LABELS[r.strategy] || r.strategy,
    };
    COST_COMPONENTS.forEach((c) => {
      row[c.key] = Number(s[c.field]) || 0;
    });
    return row;
  });

  return (
    <div className="results">
      <h3>Summary</h3>
      <table className="summary-table">
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Avg Unmet %</th>
            <th>Max Unmet %</th>
            <th>Total Procurement Cost</th>
            <th>Total Transport Cost</th>
            <th>Total Holding Cost</th>
            <th>Total Shortage Cost</th>
            <th>Periods OK</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((s: any) => (
            <tr key={s.strategy}>
              <td>{s.strategy}</td>
              <td>{s.avg_unmet_pct ?? "-"}%</td>
              <td>{s.max_unmet_pct ?? "-"}%</td>
              <td>
                {s.total_procurement_cost != null
                  ? `BWP ${Math.round(Number(s.total_procurement_cost)).toLocaleString()}`
                  : "-"}
              </td>
              <td>
                {s.total_transport_cost != null
                  ? `BWP ${Math.round(Number(s.total_transport_cost)).toLocaleString()}`
                  : "-"}
              </td>
              <td>
                {s.total_holding_cost != null
                  ? `BWP ${Math.round(Number(s.total_holding_cost)).toLocaleString()}`
                  : "-"}
              </td>
              <td>
                {s.total_shortage_cost != null
                  ? `BWP ${Math.round(Number(s.total_shortage_cost)).toLocaleString()}`
                  : "-"}
              </td>
              <td>
                {s.periods_solved ?? "-"}/{(s.periods_solved ?? 0) + (s.periods_failed ?? 0)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Unmet Demand Over Time</h3>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={timeData} margin={{ top: 10, right: 30, left: 10, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" label={{ value: "Biweekly Period", position: "insideBottom", offset: -15 }} />
          <YAxis label={{ value: "Unmet %", angle: -90, position: "insideLeft" }} />
          <Tooltip />
          <Legend verticalAlign="top" />
          {results.map((r) => (
            <Line
              key={r.strategy}
              type="monotone"
              dataKey={r.strategy}
              name={STRATEGY_LABELS[r.strategy] || r.strategy}
              stroke={STRATEGY_COLORS[r.strategy] || "#6b7280"}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {costData.length > 1 && (
        <>
          <h3>Average Cost Breakdown</h3>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", margin: "0.5rem 0 0.75rem" }}>
            {COST_COMPONENTS.map((c) => (
              <label key={c.key} style={{ display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer", fontSize: "0.85rem" }}>
                <input
                  type="checkbox"
                  checked={enabledComponents[c.key]}
                  onChange={(e) =>
                    setEnabledComponents({ ...enabledComponents, [c.key]: e.target.checked })
                  }
                  style={{ width: "auto", accentColor: c.color }}
                />
                <span style={{ color: c.color }}>{c.key}</span>
              </label>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={costData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="strategy" />
              <YAxis />
              <Tooltip />
              <Legend />
              {COST_COMPONENTS.filter((c) => enabledComponents[c.key]).map((c) => (
                <Bar key={c.key} dataKey={c.key} fill={c.color} stackId="a" />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
