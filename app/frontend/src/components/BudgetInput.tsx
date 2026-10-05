import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ForecastCostRequest } from "../api/client";

interface Props {
  /** Inputs that set the cost of serving the forecast; null until a region is chosen. */
  request: ForecastCostRequest | null;
  value: number | null;
  onChange: (budget: number | null) => void;
}

/**
 * Budget per period (BWP) for transport + procurement. Shows the spend that
 * serves the forecast in full as a reference, and prefills the field with it
 * until the planner types their own number.
 */
export default function BudgetInput({ request, value, onChange }: Props) {
  const [forecastCost, setForecastCost] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const edited = useRef(false);
  const key = request ? JSON.stringify(request) : "";

  // A new region or scenario is a new planning problem: prefill again.
  const scope = request ? `${request.region}|${request.scenario}` : "";
  useEffect(() => {
    edited.current = false;
  }, [scope]);

  useEffect(() => {
    if (!request) {
      setForecastCost(null);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      setLoading(true);
      setError("");
      api
        .forecastCost(request)
        .then((r) => {
          if (cancelled) return;
          setForecastCost(r.forecast_cost);
          if (!edited.current) onChange(Math.ceil(r.forecast_cost));
        })
        .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Failed"))
        .finally(() => !cancelled && setLoading(false));
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const ratio = value != null && forecastCost ? value / forecastCost : null;

  return (
    <label>
      Budget per period (BWP) <span className="label-tswana">Tekanyetsokabo</span>
      <input
        type="number"
        min={0}
        step={1000}
        value={value ?? ""}
        placeholder={request ? "Enter a budget" : "Select a region first"}
        onChange={(e) => {
          edited.current = true;
          onChange(e.target.value === "" ? null : +e.target.value);
        }}
      />
      <span className="param-hint">
        Transport + procurement spend allowed each period. Unmet demand is minimized first
        within it.
        {loading && " Computing forecast cost..."}
        {!loading && forecastCost != null && (
          <>
            {" "}Serving the forecast in full costs about BWP{" "}
            {Math.round(forecastCost).toLocaleString()} per period
            {ratio != null && ` (this budget is ${ratio.toFixed(2)}x that)`}.
          </>
        )}
        {error && ` Could not compute forecast cost: ${error}`}
      </span>
    </label>
  );
}
