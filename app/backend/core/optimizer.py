"""
optimizer.py – Supply chain optimization models (Nominal, Static Robust, ADR).
Extracted from national_pipeline/run_cms_two.py and scripts/run_compare_strategies.py.
"""

import logging
import re
import time
from typing import Optional

import cvxpy as cp
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

log = logging.getLogger(__name__)

from .data_loader import app_data, clean_fac_name

# ── District mapping ──────────────────────────────────────────────────────────
DISTRICT_MAP = {
    "barolong": "goodhope", "central bobonong": "bobirwa",
    "central boteti": "boteti", "central kalahari game reserve": "kgalagadi north",
    "central kgalagadi game reserve": "kgalagadi north",
    "central mahalapye": "mahalapye", "central serowe/ palapye": "palapye",
    "central serowe-palapye": "palapye", "central tutume": "tutume",
    "ckgr": "kgalagadi north", "jwaneng": "goodhope",
    "kweneng west": "kweneng east", "ngamiland delta": "ngamiland",
    "ngamiland east": "ngamiland", "ngamiland west": "ngamiland",
    "ngwaketse": "southern", "ngwaketse central": "southern",
    "ngwaketse west": "southern", "orapa": "boteti",
    "selibe phikwe": "selebi-phikwe", "selebi-phikwe": "selebi-phikwe",
    "sowa": "boteti", "sowa town": "boteti",
    "central madinare": "bobirwa", "central molalatau": "bobirwa",
    "kasane": "chobe", "kgalagadi rural": "kgalagadi south",
    "kweneng central": "kweneng east", "francistown": "francistown",
    "ghanzi farms": "ghanzi", "lobatse": "lobatse",
    "pandamatenga": "chobe", "tsabong": "kgalagadi south",
}


def _to_tier(s: str) -> str:
    s = str(s).lower().strip()
    if "warehouse" in s or "dhmt" in s or "store" in s:
        return "warehouse"
    if "tertiary" in s or "referral" in s or "hospital" in s:
        return "hospital"
    if "health post" in s or "healthpost" in s:
        return "health_post"
    return "clinic"


def _norm_name(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _norm_district(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def nb_sigma_from_mean(mu_mat: pd.DataFrame, kappa: float) -> pd.DataFrame:
    mu = mu_mat.astype(float)
    var = mu + (mu ** 2) / float(kappa)
    return np.sqrt(var)


def make_nb_draws(mean_mat: pd.DataFrame, kappa: float, T: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    mu = mean_mat.values.astype(float)
    kappa = max(kappa, 1e-6)
    p = kappa / (kappa + mu)
    return rng.negative_binomial(n=kappa, p=p, size=(T, *mu.shape)).astype(float)


def expected_class_counts_by_facility(pop_fac_age_df: pd.DataFrame) -> pd.DataFrame:
    d = app_data
    df = pop_fac_age_df.copy()
    df["patient_days"] = pd.to_numeric(df["patient_days"], errors="coerce").fillna(0.0)

    pi_tmp = d.pi_inf_given_a.copy()
    pi_tmp["agegroup"] = pi_tmp["agegroup"].replace(d.age_map)
    pi_tmp["infectionstatus"] = pi_tmp["infectionstatus"].astype(str).str.strip().str.lower()
    df["agegroup"] = df["agegroup"].astype(str).str.strip()
    df = df.merge(pi_tmp, on="agegroup", how="left")
    df["infectionstatus"] = df["infectionstatus"].astype(str).str.strip().str.lower()
    df["patients_ak"] = df["patient_days"] * df["pi_inf_given_a"]

    m_tmp = d.m_ak.copy()
    m_tmp["agegroup"] = m_tmp["agegroup"].replace(d.age_map)
    m_tmp["infectionstatus"] = m_tmp["infectionstatus"].astype(str).str.strip().str.lower()
    df = df.merge(
        m_tmp[["agegroup", "infectionstatus", "m_ak"]],
        on=["agegroup", "infectionstatus"], how="left",
    )
    df["n_akh"] = df["patients_ak"] * df["m_ak"]

    p_tmp = d.p_class.copy()
    for col in ["agegroup", "infectionstatus", "hospital_type", "Class"]:
        if col in p_tmp.columns:
            p_tmp[col] = p_tmp[col].astype(str).str.strip()
    df["hospital_type"] = df["hospital_type"].astype(str).str.strip()
    df = df.merge(p_tmp, on=["agegroup", "infectionstatus", "hospital_type"], how="left")
    df["expected_count"] = df["n_akh"] * df["p_class"]

    return df.groupby(
        ["facility_name", "facility_type", "Class"], as_index=False
    )["expected_count"].sum()


def build_node_demand_matrix(demand_fac_long: pd.DataFrame) -> pd.DataFrame:
    tmp = demand_fac_long.copy()
    tmp["facility_name"] = tmp["facility_name"].astype(str).str.strip()
    return (
        tmp.pivot_table(
            index="facility_name", columns="Class",
            values="expected_count", aggfunc="sum", fill_value=0.0,
        ).sort_index()
    )


# ══════════════════════════════════════════════════════════════════════════════
# REGION INSTANCE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_region_instance(target_dhmt: str) -> dict:
    d = app_data
    target_norm = str(target_dhmt).strip().lower()

    fac_region = d.fac.copy()
    fac_region["_dhmt_norm"] = fac_region["DHMT"].astype(str).str.strip().str.lower()
    fac_region = fac_region.loc[fac_region["_dhmt_norm"] == target_norm].copy()
    if fac_region.empty:
        raise ValueError(f"No facilities found for DHMT = {target_dhmt}")

    if "facility_name" not in fac_region.columns:
        fac_region = fac_region.rename(columns={"Facility Name": "facility_name"})
    fac_region["facility_name"] = fac_region["facility_name"].map(clean_fac_name)
    fac_region["tier"] = fac_region["Service Delivery Type"].apply(_to_tier)
    fac_region["facility_key"] = fac_region["facility_name"].apply(_norm_name)

    source_node = clean_fac_name(d.DHMT_SOURCE_MAP[target_dhmt])
    facility_nodes = list(dict.fromkeys(fac_region["facility_name"].dropna().astype(str).tolist()))
    all_nodes = facility_nodes.copy()
    if source_node not in all_nodes:
        all_nodes = [source_node] + all_nodes

    nodes_region = list(dict.fromkeys(
        n for n in all_nodes
        if n in d.dist_matrix_df.index and n in d.dist_matrix_df.columns
    ))
    if source_node not in nodes_region:
        raise ValueError(f"Source node '{source_node}' missing from distance matrix")

    # De-duplicate distance/time matrix indices before slicing
    _dm = d.dist_matrix_df
    _dm = _dm[~_dm.index.duplicated(keep='first')]
    _dm = _dm.loc[:, ~_dm.columns.duplicated(keep='first')]
    D_region = _dm.loc[nodes_region, nodes_region].copy()
    _tm = d.time_matrix_df
    _tm = _tm[~_tm.index.duplicated(keep='first')]
    _tm = _tm.loc[:, ~_tm.columns.duplicated(keep='first')]
    T_region = _tm.loc[nodes_region, nodes_region].copy()
    tier_map = dict(zip(fac_region["facility_name"], fac_region["tier"]))
    tier_map[source_node] = "warehouse"

    n_hosp = int((fac_region["tier"] == "hospital").sum())
    allowed = (
        {"warehouse": ["clinic", "health_post"], "hospital": ["clinic", "health_post"],
         "clinic": [], "health_post": []}
        if n_hosp == 0 else
        {"warehouse": ["hospital"], "hospital": ["clinic", "health_post"],
         "clinic": ["hospital"], "health_post": ["hospital"]}
    )

    rows = []
    for u in nodes_region:
        u_tier = tier_map.get(u)
        if u_tier is None:
            continue
        for v_tier in allowed.get(u_tier, []):
            cand = [v for v in nodes_region if v != u and tier_map.get(v) == v_tier]
            if not cand:
                continue
            dists = D_region.loc[u, cand].astype(float).replace(
                [np.inf, -np.inf], np.nan
            ).dropna()
            for v, dist_val in dists.items():
                dv = float(dist_val.iloc[0]) if isinstance(dist_val, pd.Series) else float(dist_val)
                tv = T_region.loc[u, v]
                time_val = float(tv.iloc[0]) if isinstance(tv, pd.Series) else float(tv)
                if pd.isna(time_val) or np.isinf(time_val):
                    continue
                rows.append({
                    "u": u, "v": v, "u_tier": u_tier, "v_tier": v_tier,
                    "dist_km": dv / 1000.0,
                    "time_min": time_val / 60.0,
                })

    arcs_df = pd.DataFrame(rows).drop_duplicates(subset=["u", "v"]).reset_index(drop=True)
    if arcs_df.empty:
        raise ValueError(f"No arcs for DHMT = {target_dhmt}")
    model_arcs = [(r.u, r.v) for r in arcs_df.itertuples(index=False)]

    # ── Population / demand pipeline ──────────────────────────────────────
    hosp_df = d.results_with_dhmt["Hospital"].copy()
    clinic_df = d.results_with_dhmt["Clinic"].copy()
    hp_df = d.results_with_dhmt["Health Post"].copy()

    mask_h = hosp_df["assigned_dhmt_hospital"].astype(str).str.strip().str.lower().eq(target_norm)
    mask_c = clinic_df["assigned_dhmt_clinic"].astype(str).str.strip().str.lower().eq(target_norm)
    mask_hp = hp_df["assigned_dhmt_health_post"].astype(str).str.strip().str.lower().eq(target_norm)

    pop_dhmt = hosp_df.loc[mask_h | mask_c | mask_hp].copy()
    if pop_dhmt.empty:
        raise ValueError(f"No population points assigned to DHMT = {target_dhmt}")

    merged_region = pop_dhmt.copy()
    merged_region["pop_id"] = merged_region.index
    merged_region = merged_region.rename(columns={
        "Facility Name_1": "nearest_Hospital_name",
        "crow_dist_km_1": "crow_dist_km_Hospital",
    })

    def _sub(df_, cols):
        s = df_.copy()
        s["pop_id"] = s.index
        return s[["pop_id"] + list(cols.keys())].rename(columns=cols)

    clinic_sub = _sub(clinic_df, {
        "Facility Name_1": "nearest_Clinic_name",
        "crow_dist_km_1": "crow_dist_km_Clinic",
    })
    hp_sub = _sub(hp_df, {
        "Facility Name_1": "nearest_HealthPost_name",
        "crow_dist_km_1": "crow_dist_km_HealthPost",
    })

    merged_region = (
        merged_region
        .merge(clinic_sub, on="pop_id", how="left")
        .merge(hp_sub, on="pop_id", how="left")
        .reset_index(drop=True)
    )

    POP_COL = "total_population"
    merged_region[POP_COL] = pd.to_numeric(
        merged_region[POP_COL].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )

    def _build_pop_fac(name_col, dist_col, ftype):
        c = merged_region[["pop_id", name_col, dist_col, "district", POP_COL]].copy()
        return c.rename(columns={
            name_col: "facility_name", dist_col: "dist_km",
            "district": "district", POP_COL: "pop_total",
        }).assign(facility_type=ftype)

    choices = pd.concat([
        _build_pop_fac("nearest_Clinic_name", "crow_dist_km_Clinic", "clinic"),
        _build_pop_fac("nearest_HealthPost_name", "crow_dist_km_HealthPost", "health_post"),
    ], ignore_index=True)
    choices["facility_name"] = choices["facility_name"].astype(str).str.strip()
    choices["dist_km"] = pd.to_numeric(choices["dist_km"], errors="coerce")
    choices = choices.replace({"facility_name": {"": np.nan, "nan": np.nan}}).dropna(
        subset=["facility_name", "dist_km"]
    )
    closest = choices.sort_values(["pop_id", "dist_km"]).drop_duplicates(
        subset=["pop_id"], keep="first"
    )

    pop_fac_region = closest.groupby(
        ["facility_name", "facility_type", "district"], as_index=False
    )["pop_total"].sum()
    pop_fac_region["district_key"] = (
        pop_fac_region["district"].apply(_norm_district).replace(DISTRICT_MAP)
    )

    adm_map = d.district_adm.drop_duplicates("district_key").set_index("district_key")[
        "annual_admissions_est"
    ]
    pop_fac_region["annual_admissions_est"] = pop_fac_region["district_key"].map(adm_map)
    pop_fac_region["annual_admissions_est"] = pop_fac_region["annual_admissions_est"].fillna(
        pop_fac_region["annual_admissions_est"].median()
    )

    pop_fac_region["district_pop_total"] = pop_fac_region.groupby("district_key")[
        "pop_total"
    ].transform("sum")
    pop_fac_region["facility_pop_share"] = np.where(
        pop_fac_region["district_pop_total"] > 0,
        pop_fac_region["pop_total"] / pop_fac_region["district_pop_total"],
        0.0,
    )
    pop_fac_region["facility_admissions_annual"] = (
        pop_fac_region["facility_pop_share"] * pop_fac_region["annual_admissions_est"]
    )

    age_work = d.age_df.copy()
    age_work["district_key"] = (
        age_work["district"].astype(str).str.strip().str.lower().replace(DISTRICT_MAP)
    )
    age_df_agg = age_work.groupby(["district_key", "agegroup"], as_index=False)["share"].sum()

    pop_fac_age = pop_fac_region.merge(
        age_df_agg[["district_key", "agegroup", "share"]], on="district_key", how="left"
    )
    PLANNING_HORIZON_WEEKS, AVG_LOS_DAYS = 2, 5.0
    pop_fac_age["pop_count"] = pop_fac_age["pop_total"] * pop_fac_age["share"]
    pop_fac_age["admissions_annual"] = (
        pop_fac_age["facility_admissions_annual"] * pop_fac_age["share"]
    )
    pop_fac_age["admissions"] = pop_fac_age["admissions_annual"] * (PLANNING_HORIZON_WEEKS / 52.0)
    pop_fac_age["patient_days"] = pop_fac_age["admissions"] * AVG_LOS_DAYS
    pop_fac_age["facility_key"] = pop_fac_age["facility_name"].apply(_norm_name)
    pop_fac_age = pop_fac_age.merge(
        fac_region[["facility_key", "tier"]], on="facility_key", how="left"
    )
    pop_fac_age["tier"] = pop_fac_age["tier"].fillna("clinic")
    tier_to_hosp_type = {
        "clinic": "Clinic", "health_post": "Clinic",
        "hospital": "Primary", "warehouse": "Tertiary",
    }
    pop_fac_age["hospital_type"] = pop_fac_age["tier"].map(tier_to_hosp_type)

    demand_fac = expected_class_counts_by_facility(pop_fac_age)
    node_demand_mat = build_node_demand_matrix(demand_fac)

    model_classes = sorted(node_demand_mat.columns.tolist())
    model_nodes = list(D_region.index)
    mu_mat = node_demand_mat.reindex(index=model_nodes, columns=model_classes).fillna(0.0).astype(float)
    sigma_mat = nb_sigma_from_mean(mu_mat, kappa=10.0).reindex(
        index=model_nodes, columns=model_classes
    ).fillna(0.0).astype(float)

    return {
        "region": target_dhmt,
        "CMS": source_node,
        "nodes": model_nodes,
        "arcs": model_arcs,
        "arc_df": arcs_df,
        "dist_km": D_region / 1000.0,
        "mu_mat": mu_mat,
        "sigma_mat": sigma_mat,
        "storage_cap_per_node": None,
        "arc_cap": 2000.0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CMS INSTANCE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_cms_region_instance(region: str, scenario: str = "2526") -> dict:
    d = app_data
    base = build_region_instance(region)
    col = f"biweekly_{scenario}"
    national_dem = d.cms_active[col]
    demand_nodes = [n for n in base["nodes"] if n != base["CMS"]]
    shares = d.pop_fac_share.reindex(demand_nodes).fillna(0.0)
    mu_demand = pd.DataFrame(
        np.outer(shares.values, national_dem.values),
        index=demand_nodes, columns=national_dem.index,
    )
    mu_mat = mu_demand.reindex(base["nodes"]).fillna(0.0).astype(float)
    # Drop drug classes with negligible total demand to reduce problem size
    active_cols = mu_mat.columns[mu_mat.sum(axis=0) > 0.01]
    mu_mat = mu_mat[active_cols]
    classes = mu_mat.columns.tolist()
    sigma_mat = nb_sigma_from_mean(mu_mat, kappa=10.0).reindex(
        index=base["nodes"], columns=classes
    ).fillna(0.0).astype(float)
    return {**base, "mu_mat": mu_mat, "sigma_mat": sigma_mat, "proc_cost": d.cms_proc_cost}


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATION: run T periods of a policy under NB demand draws
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_costs(cost_input, classes):
    if np.isscalar(cost_input):
        return np.full(len(classes), float(cost_input))
    return pd.Series(cost_input).reindex(classes).fillna(0.0).astype(float).to_numpy()


def run_simulation(
    instance: dict,
    strategy: str = "nominal",
    T: int = 12,
    kappa: float = 10.0,
    Gamma: float = 10.0,
    transport_cost_per_km: float = 0.5,
    shortage_penalty: float = 10.0,
    holding_cost: float = 0.1,
    procurement_cost=0.0,
    supply_multiplier: float = 0.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Run a simulation for a given strategy and return period-level metrics.

    strategy: "nominal" | "static_robust" | "adr"
    """
    nodes = list(instance["nodes"])
    arcs = list(instance["arcs"])
    mu_mat = instance["mu_mat"]
    sigma_mat = instance["sigma_mat"]
    dist_km = instance["dist_km"]
    CMS = instance["CMS"]
    arc_cap = instance.get("arc_cap", 2000.0)

    classes = list(mu_mat.columns)
    N, m, K = len(nodes), len(arcs), len(classes)

    demand_draws = make_nb_draws(mu_mat, kappa, T, seed)

    node_idx = {n: i for i, n in enumerate(nodes)}
    arc_cap_vec = np.full(m, float(arc_cap)) if np.isscalar(arc_cap) else np.array(
        [float(arc_cap[(i, j)]) for (i, j) in arcs]
    )
    c_arc = np.array([float(dist_km.loc[i, j]) for (i, j) in arcs], dtype=float)
    c_proc = _resolve_costs(procurement_cost, classes)
    c_pen = _resolve_costs(shortage_penalty, classes)

    mu_np = mu_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float).to_numpy()
    sigma_np = sigma_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float).to_numpy()

    # Incidence matrices for vectorized flow constraints
    A_in = np.zeros((N, m))
    A_out = np.zeros((N, m))
    for a, (i, j) in enumerate(arcs):
        A_out[node_idx[i], a] = 1.0
        A_in[node_idx[j], a] = 1.0

    cms_idx = node_idx[CMS]
    cms_mask = np.zeros((N, 1))
    cms_mask[cms_idx] = 1.0

    I = pd.DataFrame(0.0, index=nodes, columns=classes)
    I.loc[CMS, :] = supply_multiplier * mu_mat.sum(axis=0)
    metrics = []

    # Build CVXPY problem once; use Parameter for inventory so we re-solve
    # without reconstructing the expression tree each period.
    I0_param = cp.Parameter((N, K), nonneg=True)

    F = cp.Variable((m, K), nonneg=True)
    u = cp.Variable((N, K), nonneg=True)
    I1 = cp.Variable((N, K), nonneg=True)
    q = cp.Variable(K, nonneg=True)
    lam = cp.Variable(m, nonneg=True)
    y = cp.Variable(m, nonneg=True)

    big_m = 1e5
    net_flow = A_in @ F - A_out @ F          # (N, K)
    supply = cms_mask @ cp.reshape(q, (1, K), order='C')  # (N, K) — only CMS row nonzero

    constraints = [
        y <= 1.0,
        lam <= big_m * y,
    ]

    # Precompute arc destination indices (needed by ADR)
    arc_dest_idx = np.array([node_idx[j] for (_, j) in arcs], dtype=int)
    arc_src_idx = np.array([node_idx[i] for (i, _) in arcs], dtype=int)

    # alpha variable for ADR (None for other strategies)
    alpha = None

    if strategy == "nominal":
        constraints += [
            cp.sum(F, axis=1) <= cp.multiply(arc_cap_vec, lam),
            I1 == I0_param + net_flow + supply - mu_np + u,
            A_out @ F <= I0_param + A_in @ F + supply,
        ]

    elif strategy == "static_robust":
        constraints.append(cp.sum(F, axis=1) <= cp.multiply(arc_cap_vec, lam))
        # Dual variables are (N, K) scalars — off-diagonal entries are
        # always zero at optimality (no cross-node adaptive terms).
        theta = cp.Variable((N, K), nonneg=True)
        pi_plus = cp.Variable((N, K), nonneg=True)
        pi_minus = cp.Variable((N, K), nonneg=True)
        theta_ship = cp.Variable((N, K), nonneg=True)
        pi_ship_plus = cp.Variable((N, K), nonneg=True)
        pi_ship_minus = cp.Variable((N, K), nonneg=True)

        rhs = I0_param + net_flow + supply - mu_np + u - I1
        rhs_ship = I0_param + net_flow + supply

        constraints += [
            Gamma * theta + pi_plus + pi_minus <= rhs,
            theta + pi_plus >= -sigma_np,
            theta + pi_minus >= sigma_np,
            Gamma * theta_ship + pi_ship_plus + pi_ship_minus <= rhs_ship,
            theta_ship + pi_ship_plus >= -sigma_np,
            theta_ship + pi_ship_minus >= sigma_np,
        ]

    elif strategy == "adr":
        # ── Affine Decision Rules: ship[a] = F[a] + alpha[a] * (d - mu) ──
        arc_df = instance.get("arc_df")
        if arc_df is None:
            raise ValueError("arc_df required for ADR strategy")

        # Identify adaptive arcs (CMS/warehouse/hospital → downstream)
        adaptive_arc_mask = np.array([
            1.0 if (row.u_tier in ["cms", "warehouse", "hospital"]
                    and row.v_tier in ["clinic", "warehouse", "hospital", "health_post"])
            else 0.0
            for row in arc_df.itertuples(index=False)
        ], dtype=float)
        A_adapt = np.where(adaptive_arc_mask == 1.0)[0]
        non_adapt = np.where(adaptive_arc_mask == 0.0)[0]

        # Incidence matrix for incoming adaptive arcs: (N, m)
        A_in_adapt = np.zeros((N, m))
        for a in A_adapt:
            A_in_adapt[arc_dest_idx[a], a] = 1.0

        # Source-outgoing map: S_out[n, p] = 1 if A_adapt[p] is outgoing from n
        S_out = np.zeros((N, len(A_adapt)))
        for p, a in enumerate(A_adapt):
            S_out[arc_src_idx[a], p] = 1.0

        src_adapt = arc_src_idx[A_adapt]
        dst_adapt = arc_dest_idx[A_adapt]
        sigma_dest = sigma_np[arc_dest_idx, :]  # (m, K)

        # Variables
        alpha = cp.Variable((m, K))
        eta = cp.Variable(m, nonneg=True)
        rho_plus = cp.Variable((m, K), nonneg=True)
        rho_minus = cp.Variable((m, K), nonneg=True)

        # Demand balance duals: self-node (N,K) + cross-node (len(A_adapt),K)
        theta = cp.Variable((N, K), nonneg=True)
        pi_self_plus = cp.Variable((N, K), nonneg=True)
        pi_self_minus = cp.Variable((N, K), nonneg=True)
        pi_cross_plus = cp.Variable((len(A_adapt), K), nonneg=True)
        pi_cross_minus = cp.Variable((len(A_adapt), K), nonneg=True)

        # Ship balance duals
        theta_ship = cp.Variable((N, K), nonneg=True)
        pis_self_plus = cp.Variable((N, K), nonneg=True)
        pis_self_minus = cp.Variable((N, K), nonneg=True)
        pis_cross_plus = cp.Variable((len(A_adapt), K), nonneg=True)
        pis_cross_minus = cp.Variable((len(A_adapt), K), nonneg=True)

        # Non-adaptive arcs: alpha = 0
        if len(non_adapt) > 0:
            constraints.append(alpha[non_adapt, :] == 0)

        # Robust arc capacity: Gamma*eta + sum_k(rho) <= cap*lam - sum_k(F)
        eta_col = cp.reshape(eta, (m, 1), order='C')
        constraints += [
            Gamma * eta + cp.sum(rho_plus + rho_minus, axis=1)
                <= cp.multiply(arc_cap_vec, lam) - cp.sum(F, axis=1),
            eta_col + rho_plus >= cp.multiply(alpha, sigma_dest),
            eta_col + rho_minus >= -cp.multiply(alpha, sigma_dest),
        ]

        # Demand balance robust constraints
        rhs = I0_param + net_flow + supply - mu_np + u - I1
        coeff_self = A_in_adapt @ alpha - 1  # (N, K)
        constraints += [
            Gamma * theta + pi_self_plus + pi_self_minus
                + S_out @ pi_cross_plus + S_out @ pi_cross_minus <= rhs,
            theta + pi_self_plus >= cp.multiply(coeff_self, sigma_np),
            theta + pi_self_minus >= -cp.multiply(coeff_self, sigma_np),
            theta[src_adapt, :] + pi_cross_plus
                >= -cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
            theta[src_adapt, :] + pi_cross_minus
                >= cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
        ]

        # Ship balance robust constraints
        rhs_ship = I0_param + net_flow + supply
        coeff_self_ship = -(A_in_adapt @ alpha)  # (N, K)
        constraints += [
            Gamma * theta_ship + pis_self_plus + pis_self_minus
                + S_out @ pis_cross_plus + S_out @ pis_cross_minus <= rhs_ship,
            theta_ship + pis_self_plus >= cp.multiply(coeff_self_ship, sigma_np),
            theta_ship + pis_self_minus >= -cp.multiply(coeff_self_ship, sigma_np),
            theta_ship[src_adapt, :] + pis_cross_plus
                >= cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
            theta_ship[src_adapt, :] + pis_cross_minus
                >= -cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
        ]

    obj = cp.Minimize(
        transport_cost_per_km * cp.sum(cp.multiply(c_arc, lam))
        + cp.sum(cp.multiply(c_pen.reshape(1, K), u))
        + holding_cost * cp.sum(I1)
        + cp.sum(cp.multiply(c_proc, q))
    )
    t0 = time.perf_counter()
    prob = cp.Problem(obj, constraints)
    log.info("CVXPY problem built: N=%d, m=%d, K=%d, strategy=%s (%.2fs)",
             N, m, K, strategy, time.perf_counter() - t0)

    for t in range(T):
        I0_param.value = I.to_numpy().astype(float)
        t1 = time.perf_counter()
        prob.solve(solver=cp.HIGHS, verbose=False)
        log.info("  period %d/%d solved in %.3fs [%s]",
                 t + 1, T, time.perf_counter() - t1, prob.status)

        if prob.status not in ("optimal", "optimal_inaccurate"):
            metrics.append({
                "t": t, "status": prob.status,
                "objective": None, "transport_cost": None,
                "shortage_cost": None, "holding_cost": None,
                "procurement_cost": None, "unmet_pct": None,
                "total_unmet": None, "total_demand": None,
            })
            continue

        F_val = np.maximum(np.asarray(F.value, dtype=float), 0.0)
        q_val = np.maximum(np.asarray(q.value, dtype=float), 0.0)
        lam_val = np.maximum(np.asarray(lam.value, dtype=float), 0.0)

        # For ADR: adapt shipments to realized demand deviation
        if alpha is not None:
            alpha_val = np.asarray(alpha.value, dtype=float)
            xi_real = demand_draws[t] - mu_np  # (N, K)
            ship_np = F_val.copy()
            ship_np[A_adapt, :] += alpha_val[A_adapt, :] * xi_real[dst_adapt, :]
            ship_np = np.maximum(ship_np, 0.0)
        else:
            ship_np = F_val

        # Vectorized post-solve simulation using incidence matrices
        inflow_np = A_in @ ship_np           # (N, K)
        outflow_np = A_out @ ship_np          # (N, K)
        supply_np = np.zeros((N, K))
        supply_np[cms_idx, :] = q_val
        demand_np = demand_draws[t]          # (N, K)
        I_np = I.to_numpy()

        avail = I_np + supply_np + inflow_np - outflow_np
        served = np.minimum(avail, demand_np)
        unmet_np = demand_np - served
        I_next_np = avail - served
        I = pd.DataFrame(I_next_np, index=nodes, columns=classes)

        transport_cost = transport_cost_per_km * float((c_arc * lam_val).sum())
        shortage_cost = float((unmet_np * c_pen).sum())
        hold_cost = holding_cost * float(I_next_np.sum())
        proc_cost = float((q_val * c_proc).sum())
        total_demand = float(demand_np.sum())
        total_unmet = float(unmet_np.sum())

        metrics.append({
            "t": t,
            "status": "optimal",
            "objective": transport_cost + shortage_cost + hold_cost + proc_cost,
            "transport_cost": transport_cost,
            "shortage_cost": shortage_cost,
            "holding_cost": hold_cost,
            "procurement_cost": proc_cost,
            "unmet_pct": (total_unmet / total_demand * 100.0) if total_demand > 0 else 0.0,
            "total_unmet": total_unmet,
            "total_demand": total_demand,
        })

    return pd.DataFrame(metrics)


# ══════════════════════════════════════════════════════════════════════════════
# PLANNING MODE: solve one period with real inventory, return shipment plan
# ══════════════════════════════════════════════════════════════════════════════

def run_planning(
    instance: dict,
    strategy: str = "nominal",
    kappa: float = 10.0,
    Gamma: float = 10.0,
    transport_cost_per_km: float = 0.5,
    shortage_penalty: float = 10.0,
    holding_cost: float = 0.1,
    procurement_cost=0.0,
    initial_inventory: dict | None = None,
    last_demand: dict | None = None,
) -> dict:
    """
    Solve ONE period with real inputs and return actionable shipment decisions.

    initial_inventory: {facility_name: {drug: quantity}} — current stock on hand
    last_demand:       {facility_name: {drug: quantity}} — last period realized demand
    """
    nodes = list(instance["nodes"])
    arcs = list(instance["arcs"])
    mu_mat = instance["mu_mat"]
    sigma_mat = instance["sigma_mat"]
    dist_km = instance["dist_km"]
    CMS = instance["CMS"]
    arc_cap = instance.get("arc_cap", 2000.0)

    classes = list(mu_mat.columns)
    N, m, K = len(nodes), len(arcs), len(classes)

    node_idx = {n: i for i, n in enumerate(nodes)}
    arc_cap_vec = np.full(m, float(arc_cap)) if np.isscalar(arc_cap) else np.array(
        [float(arc_cap[(i, j)]) for (i, j) in arcs]
    )
    c_arc = np.array([float(dist_km.loc[i, j]) for (i, j) in arcs], dtype=float)
    c_proc = _resolve_costs(procurement_cost, classes)
    c_pen = _resolve_costs(shortage_penalty, classes)

    mu_np = mu_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float).to_numpy()
    sigma_np = sigma_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float).to_numpy()

    # Build I0 from user-supplied inventory
    I0 = pd.DataFrame(0.0, index=nodes, columns=classes)
    if initial_inventory:
        for fac, drugs in initial_inventory.items():
            if fac not in I0.index:
                continue
            for drug, qty in drugs.items():
                if drug in I0.columns:
                    I0.loc[fac, drug] = float(qty)
    I0_np = I0.to_numpy().astype(float)

    # If user provided last demand, use it to refine sigma
    if last_demand:
        last_df = pd.DataFrame(0.0, index=nodes, columns=classes)
        for fac, drugs in last_demand.items():
            if fac not in last_df.index:
                continue
            for drug, qty in drugs.items():
                if drug in last_df.columns:
                    last_df.loc[fac, drug] = float(qty)
        # Blend: use last demand as mu if provided (more recent signal)
        mu_np = last_df.to_numpy().astype(float)
        # Recompute sigma based on observed demand
        sigma_np = nb_sigma_from_mean(
            pd.DataFrame(mu_np, index=nodes, columns=classes), kappa
        ).to_numpy().astype(float)

    # Incidence matrices
    A_in = np.zeros((N, m))
    A_out = np.zeros((N, m))
    for a, (i, j) in enumerate(arcs):
        A_out[node_idx[i], a] = 1.0
        A_in[node_idx[j], a] = 1.0

    cms_idx = node_idx[CMS]
    cms_mask = np.zeros((N, 1))
    cms_mask[cms_idx] = 1.0

    arc_dest_idx = np.array([node_idx[j] for (_, j) in arcs], dtype=int)
    arc_src_idx = np.array([node_idx[i] for (i, _) in arcs], dtype=int)

    # Build CVXPY problem (single period)
    F = cp.Variable((m, K), nonneg=True)
    u = cp.Variable((N, K), nonneg=True)
    I1 = cp.Variable((N, K), nonneg=True)
    q = cp.Variable(K, nonneg=True)
    lam = cp.Variable(m, nonneg=True)
    y = cp.Variable(m, nonneg=True)

    big_m = 1e5
    net_flow = A_in @ F - A_out @ F
    supply = cms_mask @ cp.reshape(q, (1, K), order='C')

    constraints = [
        y <= 1.0,
        lam <= big_m * y,
    ]

    if strategy == "nominal":
        constraints += [
            cp.sum(F, axis=1) <= cp.multiply(arc_cap_vec, lam),
            I1 == I0_np + net_flow + supply - mu_np + u,
            A_out @ F <= I0_np + A_in @ F + supply,
        ]
    elif strategy == "static_robust":
        constraints.append(cp.sum(F, axis=1) <= cp.multiply(arc_cap_vec, lam))
        theta = cp.Variable((N, K), nonneg=True)
        pi_plus = cp.Variable((N, K), nonneg=True)
        pi_minus = cp.Variable((N, K), nonneg=True)
        theta_ship = cp.Variable((N, K), nonneg=True)
        pi_ship_plus = cp.Variable((N, K), nonneg=True)
        pi_ship_minus = cp.Variable((N, K), nonneg=True)

        rhs = I0_np + net_flow + supply - mu_np + u - I1
        rhs_ship = I0_np + net_flow + supply
        constraints += [
            Gamma * theta + pi_plus + pi_minus <= rhs,
            theta + pi_plus >= -sigma_np,
            theta + pi_minus >= sigma_np,
            Gamma * theta_ship + pi_ship_plus + pi_ship_minus <= rhs_ship,
            theta_ship + pi_ship_plus >= -sigma_np,
            theta_ship + pi_ship_minus >= sigma_np,
        ]
    elif strategy == "adr":
        arc_df = instance.get("arc_df")
        if arc_df is None:
            raise ValueError("arc_df required for ADR strategy")
        adaptive_arc_mask = np.array([
            1.0 if (row.u_tier in ["cms", "warehouse", "hospital"]
                    and row.v_tier in ["clinic", "warehouse", "hospital", "health_post"])
            else 0.0
            for row in arc_df.itertuples(index=False)
        ], dtype=float)
        A_adapt = np.where(adaptive_arc_mask == 1.0)[0]
        non_adapt = np.where(adaptive_arc_mask == 0.0)[0]
        A_in_adapt = np.zeros((N, m))
        for a in A_adapt:
            A_in_adapt[arc_dest_idx[a], a] = 1.0
        S_out = np.zeros((N, len(A_adapt)))
        for p, a in enumerate(A_adapt):
            S_out[arc_src_idx[a], p] = 1.0
        src_adapt = arc_src_idx[A_adapt]
        dst_adapt = arc_dest_idx[A_adapt]
        sigma_dest = sigma_np[arc_dest_idx, :]

        alpha = cp.Variable((m, K))
        eta = cp.Variable(m, nonneg=True)
        rho_plus = cp.Variable((m, K), nonneg=True)
        rho_minus = cp.Variable((m, K), nonneg=True)
        theta = cp.Variable((N, K), nonneg=True)
        pi_self_plus = cp.Variable((N, K), nonneg=True)
        pi_self_minus = cp.Variable((N, K), nonneg=True)
        pi_cross_plus = cp.Variable((len(A_adapt), K), nonneg=True)
        pi_cross_minus = cp.Variable((len(A_adapt), K), nonneg=True)
        theta_ship = cp.Variable((N, K), nonneg=True)
        pis_self_plus = cp.Variable((N, K), nonneg=True)
        pis_self_minus = cp.Variable((N, K), nonneg=True)
        pis_cross_plus = cp.Variable((len(A_adapt), K), nonneg=True)
        pis_cross_minus = cp.Variable((len(A_adapt), K), nonneg=True)

        if len(non_adapt) > 0:
            constraints.append(alpha[non_adapt, :] == 0)
        eta_col = cp.reshape(eta, (m, 1), order='C')
        constraints += [
            Gamma * eta + cp.sum(rho_plus + rho_minus, axis=1)
                <= cp.multiply(arc_cap_vec, lam) - cp.sum(F, axis=1),
            eta_col + rho_plus >= cp.multiply(alpha, sigma_dest),
            eta_col + rho_minus >= -cp.multiply(alpha, sigma_dest),
        ]
        rhs = I0_np + net_flow + supply - mu_np + u - I1
        coeff_self = A_in_adapt @ alpha - 1
        constraints += [
            Gamma * theta + pi_self_plus + pi_self_minus
                + S_out @ pi_cross_plus + S_out @ pi_cross_minus <= rhs,
            theta + pi_self_plus >= cp.multiply(coeff_self, sigma_np),
            theta + pi_self_minus >= -cp.multiply(coeff_self, sigma_np),
            theta[src_adapt, :] + pi_cross_plus
                >= -cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
            theta[src_adapt, :] + pi_cross_minus
                >= cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
        ]
        rhs_ship = I0_np + net_flow + supply
        coeff_self_ship = -(A_in_adapt @ alpha)
        constraints += [
            Gamma * theta_ship + pis_self_plus + pis_self_minus
                + S_out @ pis_cross_plus + S_out @ pis_cross_minus <= rhs_ship,
            theta_ship + pis_self_plus >= cp.multiply(coeff_self_ship, sigma_np),
            theta_ship + pis_self_minus >= -cp.multiply(coeff_self_ship, sigma_np),
            theta_ship[src_adapt, :] + pis_cross_plus
                >= cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
            theta_ship[src_adapt, :] + pis_cross_minus
                >= -cp.multiply(alpha[A_adapt, :], sigma_np[dst_adapt, :]),
        ]

    obj = cp.Minimize(
        transport_cost_per_km * cp.sum(cp.multiply(c_arc, lam))
        + cp.sum(cp.multiply(c_pen.reshape(1, K), u))
        + holding_cost * cp.sum(I1)
        + cp.sum(cp.multiply(c_proc, q))
    )

    t0 = time.perf_counter()
    prob = cp.Problem(obj, constraints)
    prob.solve(solver=cp.HIGHS, verbose=False)
    solve_time = time.perf_counter() - t0
    log.info("Planning solve: N=%d, m=%d, K=%d, strategy=%s, %.2fs [%s]",
             N, m, K, strategy, solve_time, prob.status)

    if prob.status not in ("optimal", "optimal_inaccurate"):
        return {"status": prob.status, "shipments": [], "procurement": [], "summary": {}}

    F_val = np.maximum(np.asarray(F.value, dtype=float), 0.0)
    q_val = np.maximum(np.asarray(q.value, dtype=float), 0.0)

    # Build shipment recommendations
    shipments = []
    for a, (i, j) in enumerate(arcs):
        flow = F_val[a, :]
        for k_idx, drug in enumerate(classes):
            qty = float(flow[k_idx])
            if qty > 0.5:  # threshold to avoid noise
                shipments.append({
                    "from": i,
                    "to": j,
                    "drug": drug,
                    "quantity": round(qty, 1),
                    "distance_km": round(float(dist_km.loc[i, j]), 1),
                })

    # Procurement recommendations
    procurement = []
    for k_idx, drug in enumerate(classes):
        qty = float(q_val[k_idx])
        if qty > 0.5:
            procurement.append({
                "drug": drug,
                "quantity": round(qty, 1),
                "unit_cost": round(float(c_proc[k_idx]), 2),
                "total_cost": round(qty * float(c_proc[k_idx]), 2),
            })

    # Summary
    total_shipped = float(F_val.sum())
    total_procured = float(q_val.sum())
    total_cost = float(prob.value) if prob.value is not None else 0.0

    return {
        "status": "optimal",
        "solve_time_s": round(solve_time, 2),
        "strategy": strategy,
        "shipments": sorted(shipments, key=lambda s: -s["quantity"]),
        "procurement": sorted(procurement, key=lambda p: -p["quantity"]),
        "summary": {
            "total_shipments": len(shipments),
            "total_units_shipped": round(total_shipped, 1),
            "total_procurement_orders": len(procurement),
            "total_units_procured": round(total_procured, 1),
            "total_cost": round(total_cost, 2),
            "active_routes": int((F_val.sum(axis=1) > 0.5).sum()),
        },
    }
