import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "../api/client";
import type { Region, RegionDemand, OptimizationResult } from "../api/client";
import ResultsView from "../components/ResultsView";
import DemandEditor from "../components/DemandEditor";

const STRATEGIES = [
  { value: "nominal", label: "Nominal (Mean Demand)" },
  { value: "static_robust", label: "Static Robust" },
  { value: "adr", label: "Adjustable Robust (ADR)" },
];

export default function Optimize() {
  const [searchParams] = useSearchParams();
  const preselectedRegion = searchParams.get("region") || "";

  const [regions, setRegions] = useState<Region[]>([]);
  const [region, setRegion] = useState(preselectedRegion);
  const [strategy, setStrategy] = useState("nominal");
  const [scenario, setScenario] = useState("2526");
  const [periods, setPeriods] = useState(4);
  const [kappa, setKappa] = useState(10);
  const [gamma, setGamma] = useState(10);
  const [transportCost, setTransportCost] = useState(0.5);
  const [shortagePenalty, setShortagePenalty] = useState(5);
  const [holdingCost, setHoldingCost] = useState(0.1);
  const [supplyMult, setSupplyMult] = useState(0);
  const [demandMultiplier, setDemandMultiplier] = useState(1.0);

  const [demandData, setDemandData] = useState<RegionDemand | null>(null);
  const [customDemand, setCustomDemand] = useState<Record<
    string,
    Record<string, number>
  > | null>(null);
  const [showDemandEditor, setShowDemandEditor] = useState(false);
  const [loadingDemand, setLoadingDemand] = useState(false);

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<OptimizationResult[]>([]);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<{ done: number; total: number; current: string } | null>(null);

  useEffect(() => {
    api.getRegions().then(setRegions).catch(() => {});
  }, []);

  // Load demand when region or scenario changes
  const loadDemand = async () => {
    if (!region) return;
    setLoadingDemand(true);
    try {
      const data = await api.getRegionDemand(region, scenario, true);
      setDemandData(data);
      setCustomDemand(null); // reset custom overrides when loading fresh data
      setShowDemandEditor(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load demand");
    } finally {
      setLoadingDemand(false);
    }
  };

  const buildRequest = (strat: string) => ({
    region,
    strategy: strat,
    scenario,
    periods,
    kappa,
    gamma,
    transport_cost_per_km: transportCost,
    shortage_penalty: shortagePenalty,
    holding_cost: holdingCost,
    supply_multiplier: supplyMult,
    seed: 42,
    use_cms_data: true,
    demand_multiplier: demandMultiplier,
    custom_demand: customDemand,
  });

  const setSolving = (v: boolean) => {
    setLoading(v);
    (window as any).__setSolving?.(v);
  };

  const runOptimization = async () => {
    if (!region) return;
    setSolving(true);
    setError("");
    const label = STRATEGIES.find((s) => s.value === strategy)?.label || strategy;
    setProgress({ done: 0, total: 1, current: label });
    try {
      const result = await api.optimize(buildRequest(strategy));
      setResults((prev) => [...prev, result]);
      setProgress({ done: 1, total: 1, current: label });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSolving(false);
      setProgress(null);
    }
  };

  const compareAll = async () => {
    if (!region) return;
    setSolving(true);
    setError("");
    setResults([]);
    const completed: OptimizationResult[] = [];
    for (let i = 0; i < STRATEGIES.length; i++) {
      const s = STRATEGIES[i];
      setProgress({ done: i, total: STRATEGIES.length, current: s.label });
      try {
        const result = await api.optimize(buildRequest(s.value));
        completed.push(result);
        setResults([...completed]);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Unknown error");
        break;
      }
    }
    setProgress({ done: STRATEGIES.length, total: STRATEGIES.length, current: "Done" });
    setSolving(false);
    setProgress(null);
  };

  return (
    <div className="page">
      <Link to="/" className="back-link">
        &larr; Back to Dashboard
      </Link>
      <h1>Simulation Mode</h1>
      <p className="page-subtitle-tswana">Mokgwa wa Tshedimosetso</p>

      <div className="optimize-layout">
        <div className="params-panel">
          <h3>Parameters <span className="label-tswana">Ditogamaano</span></h3>

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
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
            >
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            CMS Scenario <span className="label-tswana">Maemo a CMS</span>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              <option value="2526">2025-26</option>
              <option value="2627">2026-27</option>
            </select>
          </label>

          <label>
            Periods (biweekly) <span className="label-tswana">Dinako</span>
            <input
              type="number"
              min={1}
              max={52}
              value={periods}
              onChange={(e) => setPeriods(+e.target.value)}
            />
          </label>

          <label>
            Kappa (NB dispersion) <span className="label-tswana">Kapa</span>
            <input
              type="number"
              min={0.1}
              step={0.5}
              value={kappa}
              onChange={(e) => setKappa(+e.target.value)}
            />
          </label>

          <label>
            Gamma (robustness budget) <span className="label-tswana">Tshireletso</span>
            <input
              type="number"
              min={0}
              step={1}
              value={gamma}
              onChange={(e) => setGamma(+e.target.value)}
            />
          </label>

          <label>
            Transport cost ($/km) <span className="label-tswana">Ditshenyegelo tsa dipalangwa</span>
            <input
              type="number"
              min={0}
              step={0.1}
              value={transportCost}
              onChange={(e) => setTransportCost(+e.target.value)}
            />
          </label>

          <label>
            Shortage penalty (x procurement cost) <span className="label-tswana">Kotlhao ya tlhaelo</span>
            <input
              type="number"
              min={0}
              step={0.5}
              value={shortagePenalty}
              onChange={(e) => setShortagePenalty(+e.target.value)}
            />
          </label>

          <label>
            Holding cost ($/unit) <span className="label-tswana">Ditshenyegelo tsa polokelo</span>
            <input
              type="number"
              min={0}
              step={0.01}
              value={holdingCost}
              onChange={(e) => setHoldingCost(+e.target.value)}
            />
          </label>

          <label>
            Supply multiplier <span className="label-tswana">Selekanyo sa phepelo</span>
            <input
              type="number"
              min={0}
              step={0.1}
              value={supplyMult}
              onChange={(e) => setSupplyMult(+e.target.value)}
            />
          </label>

          <label>
            Demand multiplier <span className="label-tswana">Selekanyo sa tlhokego</span>
            <input
              type="number"
              min={0}
              step={0.1}
              value={demandMultiplier}
              onChange={(e) => setDemandMultiplier(+e.target.value)}
            />
            <span className="param-hint">
              Scale all demand (1.0 = no change, 1.5 = +50%)
            </span>
          </label>

          <div className="demand-actions">
            <button
              className="btn btn-outline"
              onClick={loadDemand}
              disabled={!region || loadingDemand}
            >
              {loadingDemand
                ? "Loading..."
                : showDemandEditor
                  ? "Reload Demand"
                  : "Edit Demand"}
            </button>
            {customDemand && (
              <span className="custom-demand-badge">Custom demand active</span>
            )}
          </div>

          <div className="btn-group">
            <button
              className="btn btn-primary"
              onClick={runOptimization}
              disabled={loading || !region}
            >
              {loading ? "Running..." : "Run Strategy"}
            </button>
            <button
              className="btn btn-secondary"
              onClick={compareAll}
              disabled={loading || !region}
            >
              {loading ? "Running..." : "Compare All 3"}
            </button>
          </div>
        </div>

        <div className="results-panel">
          {error && <div className="error">{error}</div>}

          {showDemandEditor && demandData && (
            <DemandEditor
              demandData={demandData}
              onDemandChange={(demand) => setCustomDemand(demand)}
            />
          )}

          {loading && (
            <div className="loading solver-loading">
              <div className="solver-spinner" />
              <p>Running optimization... This may take a minute.</p>
              <p className="solver-tswana">Re tsamaisa ditharabololo... E ka tsaya metsotso.</p>
              {progress && (
                <div className="solver-progress">
                  <div className="solver-progress-bar">
                    <div
                      className="solver-progress-fill"
                      style={{ width: `${(progress.done / progress.total) * 100}%` }}
                    />
                  </div>
                  <div className="solver-progress-label">
                    {progress.done < progress.total
                      ? `Solving ${progress.current} (${progress.done + 1}/${progress.total})`
                      : `Complete (${progress.total}/${progress.total})`}
                  </div>
                </div>
              )}
            </div>
          )}
          {results.length > 0 && <ResultsView results={results} />}
          {!loading && results.length === 0 && !showDemandEditor && (
            <div className="empty-state">
              <p>Select a region and strategy, then click Run to see results.</p>
              <p className="empty-state-sub">Click "Edit Demand" to customize expected demand per facility.</p>
              <p className="empty-state-tswana">Tlhopha kgaolo le togamaano, o bo o tobetsa "Run" go bona dipholo.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
