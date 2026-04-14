export default function Methodology() {
  return (
    <div className="page docs-page">
      <h1>Methodology</h1>
      <p className="page-subtitle-tswana">Mekgwa ya Thuto</p>

      <div className="docs-section">
        <h2>Overview</h2>
        <p className="docs-card" style={{ padding: "1.25rem" }}>
          Kaelo solves a multi-period network flow optimization problem for each health district.
          At each biweekly decision epoch, the model determines how much of each antimicrobial
          to procure at CMS, how to distribute stock across the district's facilities, and how many
          vehicle trips to dispatch, all while accounting for demand uncertainty. Three allocation
          strategies are available, each offering a different tradeoff between cost and resilience.
        </p>
      </div>

      <div className="docs-section">
        <h2>Network Structure</h2>
        <p style={{ color: "#94a3b8", lineHeight: 1.7, marginBottom: "0.75rem" }}>
          The distribution network is modeled as a directed graph <em>G = (N, A)</em> where
          nodes <em>N</em> represent health facilities (CMS, DHMT warehouses, hospitals, clinics,
          health posts) and arcs <em>A</em> represent feasible delivery routes. Pairwise road
          distances are computed using OSRM routing on the Botswana road network. Flows follow
          the supply chain hierarchy: CMS to warehouses, warehouses to hospitals, hospitals to
          clinics and health posts.
        </p>
      </div>

      <div className="docs-section">
        <h2>Objective Function</h2>
        <div className="docs-card">
          <p style={{ color: "#94a3b8", lineHeight: 1.7 }}>
            The model minimizes the total cost across transportation, shortage penalties, holding
            costs, and procurement:
          </p>
          <pre className="docs-code">{`min  v · Σ Dist(i,j) · λ(i,j)        (transport)
   + Σ Δ(n,k) · U(n,k)              (shortage penalty)
   + h · Σ I(n,k)                    (holding cost)
   + Σ c(k) · q(k)                   (procurement)`}</pre>
          <p style={{ color: "#64748b", fontSize: "0.85rem", marginTop: "0.5rem" }}>
            Where <em>v</em> is per-km transport cost, <em>&Delta;</em> is the shortage
            penalty (set as a multiplier of procurement cost per drug), <em>h</em> is holding
            cost per unit, and <em>c(k)</em> is the unit procurement cost from CMS data.
          </p>
        </div>
      </div>

      <div className="docs-section">
        <h2>Core Constraints</h2>
        <div className="docs-grid">
          <div className="docs-card">
            <h3>Inventory Balance</h3>
            <pre className="docs-code">{`I(t+1) = I(t) + inflow - outflow
         - demand + unmet`}</pre>
            <p>
              End-of-period inventory equals beginning inventory plus net shipments minus
              realized demand, with any shortfall captured by the unmet demand variable.
            </p>
          </div>
          <div className="docs-card">
            <h3>Shipping Feasibility</h3>
            <pre className="docs-code">{`outflow(n) ≤ I(n) + inflow(n) + supply(n)`}</pre>
            <p>
              A facility cannot ship more than it has available (current stock plus incoming
              shipments plus any CMS procurement).
            </p>
          </div>
          <div className="docs-card">
            <h3>Arc Capacity</h3>
            <pre className="docs-code">{`Σ F(i,j,k) ≤ cap · λ(i,j)
λ(i,j) ≤ M · y(i,j)`}</pre>
            <p>
              Total flow on each route is bounded by vehicle capacity times the number of
              trips dispatched. Routes must be activated before they can carry flow.
            </p>
          </div>
        </div>
      </div>

      <div className="docs-section">
        <h2>Demand Uncertainty</h2>
        <div className="docs-card">
          <p style={{ color: "#94a3b8", lineHeight: 1.7, marginBottom: "0.75rem" }}>
            Demand is modeled as uncertain using a budgeted polyhedral uncertainty set
            (Bertsimas and Sim, 2004):
          </p>
          <pre className="docs-code">{`D(n,k) = μ(n,k) + ξ(n,k)

where |ξ(n,k)| ≤ σ(n,k)
  and Σ |ξ(n,k)| / σ(n,k) ≤ Γ`}</pre>
          <p style={{ color: "#94a3b8", lineHeight: 1.7, marginTop: "0.75rem" }}>
            Here <em>&mu;</em> is the expected demand (derived from CMS procurement records
            distributed by population share), <em>&sigma;</em> is the maximum deviation
            calibrated from the Negative Binomial variance, and <em>&Gamma;</em> (Gamma)
            controls how many facilities can simultaneously experience worst-case demand.
            Higher Gamma means more conservative planning.
          </p>
          <p style={{ color: "#64748b", fontSize: "0.85rem", marginTop: "0.5rem" }}>
            The Negative Binomial distribution was used in initial model testing to generate
            synthetic demand draws and calibrate the uncertainty set radius &sigma;. In production,
            demand means come directly from CMS national procurement data.
          </p>
        </div>
      </div>

      <div className="docs-section">
        <h2>The Three Strategies</h2>
        <div className="docs-grid">
          <div className="docs-card">
            <h3>1. Nominal (Deterministic)</h3>
            <p>
              Uses mean demand <em>&mu;</em> with no uncertainty hedging. Shipment quantities
              are fixed at the forecast each period. Fast to solve but vulnerable to demand
              shocks. Best for stable, predictable regions.
            </p>
          </div>

          <div className="docs-card">
            <h3>2. Static Robust</h3>
            <p>
              Hedges against worst-case demand within the uncertainty set. Decisions are fixed
              upfront and cannot adapt once shipments are dispatched. The robust counterpart
              is derived via LP duality, introducing dual variables (&theta;, &pi;) that
              enforce feasibility for all demand realizations within the budget.
            </p>
            <pre className="docs-code">{`Γ·θ + Σ(π+ + π-) ≤ rhs
θ + π+(n) ≥ -σ(n,k)
θ + π-(n) ≥  σ(n,k)`}</pre>
          </div>

          <div className="docs-card">
            <h3>3. Adjustable Robust (ADR)</h3>
            <p>
              Extends static robust by allowing shipments to adapt to realized demand via
              affine decision rules:
            </p>
            <pre className="docs-code">{`F(u,v,k) = F̄(u,v,k) + α(u,v,k) · ξ(v,k)`}</pre>
            <p>
              The solver jointly optimizes base shipments <em>F&#772;</em> and response
              coefficients <em>&alpha;</em>. When demand at a destination deviates from
              forecast, the adaptive rule automatically adjusts the shipment quantity. This
              is the most powerful strategy, typically achieving the lowest unmet demand at
              only a marginal cost increase over static robust.
            </p>
          </div>
        </div>
      </div>

      <div className="docs-section">
        <h2>Key Results from Research</h2>
        <div className="docs-card">
          <p style={{ color: "#94a3b8", lineHeight: 1.7, marginBottom: "0.5rem" }}>
            Across national simulations spanning 18 districts and 84 antimicrobial products:
          </p>
          <table className="facility-table" style={{ marginTop: "0.75rem" }}>
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Avg Unmet Demand</th>
                <th>vs Deterministic</th>
                <th>Cost Premium</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Nominal</td>
                <td>~21%</td>
                <td>baseline</td>
                <td>baseline</td>
              </tr>
              <tr>
                <td>Static Robust</td>
                <td>~6%</td>
                <td>-70%</td>
                <td>+12%</td>
              </tr>
              <tr>
                <td>ADR</td>
                <td>~3%</td>
                <td>-85%</td>
                <td>+13%</td>
              </tr>
            </tbody>
          </table>
          <p style={{ color: "#64748b", fontSize: "0.85rem", marginTop: "0.75rem" }}>
            Results from CMS-provided procurement data (2025-26 scenario, 11 DHMTs).
            The ADR policy reduces unmet demand by 85% relative to deterministic planning
            while incurring only a modest procurement cost premium. Full results and
            sensitivity analyses are available in the research paper.
          </p>
        </div>
      </div>

      <div className="docs-section">
        <h2>Planning Mode</h2>
        <div className="docs-card">
          <p style={{ color: "#94a3b8", lineHeight: 1.7 }}>
            Planning mode solves a single-period version of the optimization with user-supplied
            initial inventory. Instead of simulating demand draws, it solves one decision epoch
            and returns specific shipment and procurement recommendations. If last-period
            demand is provided, it replaces the CMS-derived forecast as the mean, allowing the
            model to adapt to the most recent consumption signal.
          </p>
        </div>
      </div>

      <div className="docs-section">
        <h2>Solver and Implementation</h2>
        <div className="docs-card">
          <p style={{ color: "#94a3b8", lineHeight: 1.7, marginBottom: "0.5rem" }}>
            The optimization is formulated in CVXPY and solved using the HiGHS LP solver.
            Key implementation optimizations:
          </p>
          <ul style={{ color: "#94a3b8", lineHeight: 1.8, paddingLeft: "1.25rem" }}>
            <li>Dual variables decomposed into self-node + cross-node components, reducing ADR variable count by ~10x</li>
            <li>All constraints vectorized as matrix operations (no Python loops)</li>
            <li>Problem compiled once with CVXPY Parameters, re-solved across periods without re-canonicalization</li>
            <li>Road distances computed via OSRM with Botswana road network data</li>
          </ul>
        </div>
      </div>

      <div className="docs-section">
        <h2>Reference</h2>
        <div className="docs-card">
          <p style={{ color: "#94a3b8", lineHeight: 1.7 }}>
            Lee, E.S. (2026). <em>Designing Robust Antimicrobial Supply Chains with
            Epidemiological Demand Uncertainty in Botswana: A Network Optimization Model.</em>{" "}
            Senior thesis, Department of Operations Research and Financial Engineering,
            Princeton University. Advised by Prof. Bartolomeo Stellato.
          </p>
        </div>
      </div>
    </div>
  );
}
