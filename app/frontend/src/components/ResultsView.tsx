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
  const costData = results.map((r) => ({
    strategy: STRATEGY_LABELS[r.strategy] || r.strategy,
    Transport: r.summary.avg_transport_cost || 0,
    Shortage: r.summary.avg_shortage_cost || 0,
    Holding: r.summary.avg_holding_cost || 0,
  }));

  return (
    <div className="results">
      <h3>Summary</h3>
      <table className="summary-table">
        <thead>
          <tr>
            <th>Strategy</th>
            <th>Avg Unmet %</th>
            <th>Max Unmet %</th>
            <th>Total Cost</th>
            <th>Periods OK</th>
          </tr>
        </thead>
        <tbody>
          {summaries.map((s) => (
            <tr key={s.strategy}>
              <td>{s.strategy}</td>
              <td>{s.avg_unmet_pct ?? "-"}%</td>
              <td>{s.max_unmet_pct ?? "-"}%</td>
              <td>
                {s.total_cost != null
                  ? `BWP ${Number(s.total_cost).toLocaleString()}`
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
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={costData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="strategy" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="Transport" fill="#3b82f6" stackId="a" />
              <Bar dataKey="Shortage" fill="#ef4444" stackId="a" />
              <Bar dataKey="Holding" fill="#f59e0b" stackId="a" />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
