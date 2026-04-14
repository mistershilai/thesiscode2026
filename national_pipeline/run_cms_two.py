"""
run_cms_two.py  –  CMS simulation pipeline for Princeton Research Computing
----------------------------------------------------------------------
Runs the 2025-26 / 2026-27 CMS simulation across all Botswana DHMTs.
Uses ProcessPoolExecutor to run regions in parallel (one worker per region,
capped by MAX_WORKERS to stay within 32 GB memory).

Usage:
    python run_cms.py

Output:
    results/cms_results_two.parquet   – main metrics (all regions × models × years)
    results/cms_failures_two.csv      – any regions that errored
"""

# Imports
import os
import re
import sys
import importlib.util
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
import cvxpy as cp
from scipy.spatial import cKDTree

# Paths - adjust if your project layout differs
BASE_DIR   = Path(__file__).parent                   # directory of this script
DATA_DIR   = BASE_DIR / ".."                         # parent dir has most data
OUT_DIR    = BASE_DIR / "results"
OUT_DIR.mkdir(exist_ok=True)

# Parallelism
# Keep peak memory ≤ 32 GB.  Each ARO-ADR solve can spike several GB.
# Start at 4; tune up after checking `seff <jobid>`.
MAX_WORKERS = 3

# Solver settings
os.environ["OMP_NUM_THREADS"]  = "1"   # prevent MOSEK from grabbing all cores
os.environ["MKL_NUM_THREADS"]  = "1"

# Load antimicrobialglm utils
_utils_path = DATA_DIR / "antimicrobialglm" / "antimicrobialglm_utils.py"
spec = importlib.util.spec_from_file_location("antimicrobialglm_utils", _utils_path)
antimicrobialglm_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(antimicrobialglm_utils)
estimate_antimicrobial_demand = antimicrobialglm_utils.estimate_antimicrobial_demand


# Data loading (runs once in the main process; workers inherit via fork)

def load_data():
    """Load all static data into module-level globals."""
    global pop, fac, DHMT_SOURCE_MAP, CMS_NAME
    global dist_matrix_df, time_matrix_df
    global age_df, district_adm
    global results_with_dhmt
    global m_ak, p_class, pi_inf_given_a, age_map
    global cms_active, cms_proc_cost, pop_fac_share

    # Population
    pop = pd.read_csv(DATA_DIR / "botswana_geocode/census_population_2022_geocoded_final_uniform.csv")
    pop.columns = pop.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("/", "_")
    pop.rename(columns={"city_town_village": "city/town/village", "census_district": "district"}, inplace=True)
    pop["district_norm"] = pop["district"].astype(str).str.strip().str.lower()
    pop = pop.dropna(subset=["latitude", "longitude"]).copy()

    # Facilities
    fac = pd.read_csv(DATA_DIR / "facilities_with_warehouses.csv")
    fac["DHMT_norm"]     = fac["DHMT"].astype(str).str.strip()
    fac["Facility_norm"] = fac["Facility Name"].astype(str).str.strip()
    ware = fac[fac["Is_Warehouse"] == True].copy()
    DHMT_WAREHOUSE_MAP = ware.groupby("DHMT_norm")["Facility_norm"].first().to_dict()
    CMS_NAME = "Central Medical Stores (CMS)"
    all_dhmts = fac["DHMT_norm"].dropna().unique()
    DHMT_SOURCE_MAP = {dhmt: DHMT_WAREHOUSE_MAP.get(dhmt, CMS_NAME) for dhmt in all_dhmts}

    fac.columns = fac.columns.str.strip()
    fac = fac.dropna(subset=["Latitude", "Longitude"])
    fac = fac.rename(columns={"Latitude": "latitude", "Longitude": "longitude"})
    fac["Service Delivery Type"] = fac["Service Delivery Type"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    fac = fac[~fac["Facility Name"].str.contains("prison|school", case=False, na=False)]

    # Distance / time matrices
    dist_matrix_df = pd.read_csv(DATA_DIR / "distance_matrix_named.csv", index_col=0)
    time_matrix_df = pd.read_csv(DATA_DIR / "duration_matrix_named.csv",     index_col=0)
    dist_matrix_df = _clean_matrix(dist_matrix_df)
    time_matrix_df = _clean_matrix(time_matrix_df)

    # Age breakdown
    age_df = pd.read_csv(DATA_DIR / "census_datacleaning/botswana_population_age_breakdown.csv")
    age_df["AgeGroup"] = age_df["AgeGroup"].astype(str).str.replace("–", "-", regex=False).str.strip()
    age_df = age_df.rename(columns={"DistrictName": "district", "AgeGroup": "agegroup", "Population": "pop"})
    age_df["pop"] = pd.to_numeric(age_df["pop"], errors="coerce").fillna(0)
    age_df["share"] = age_df["pop"] / age_df.groupby("district")["pop"].transform("sum")
    age_df["district_key"] = age_df["district"].astype(str).str.strip().str.lower()

    # District admissions
    district_adm = pd.read_csv(DATA_DIR / "district_admissions_estimates_2021.csv")
    district_adm = district_adm.rename(columns={
        "Health District": "district",
        "Estimated Admissions 2021": "annual_admissions_est"
    })
    district_adm["district"] = district_adm["district"].astype(str).str.strip()
    district_adm["annual_admissions_est"] = pd.to_numeric(district_adm["annual_admissions_est"], errors="coerce")
    district_adm["district_key"] = district_adm["district"].apply(lambda s: re.sub(r"\s+", " ", str(s)).strip().lower())

    # Nearest-facility assignments (national)
    _pop_nat = pop.copy()
    _pop_nat["total_population"] = pd.to_numeric(
        _pop_nat["total_population"].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    _pop_nat["pop_id"] = _pop_nat.index

    raw_results = {}
    for subtype in ["Health Post", "Clinic", "Hospital"]:
        raw_results[subtype] = nearest_facilities(_pop_nat, fac, subtype)

    results_with_dhmt = {}
    for subtype in raw_results:
        results_with_dhmt[subtype] = _attach_assigned_dhmt(raw_results[subtype], fac, subtype)

    # GLM artefacts
    ART_DIR = DATA_DIR / "antimicrobialglm/artifacts"
    _p_class_raw = pd.read_csv(ART_DIR / "p_class.csv")
    m_ak = pd.read_csv(ART_DIR / "m_ak.csv")

    age_map = {
        "<1": "<1", "1-5": "1-5",
        "6 to 10 years": "6-10",   "11 to 15 years": "11-15",
        "16 to 20 years": "16-20", "21 to 25 years": "21-25",
        "26 to 30 years": "26-30", "31 to 35 years": "31-35",
        "36 to 40 years": "36-40", "41 to 45 years": "41-45",
        "46 to 50 years": "46-50", "51 to 55 years": "51-55",
        "56 to 60 years": "56-60", "61 to 65 years": "61-65",
        "66+": "66+",
    }
    m_ak["agegroup"] = m_ak["agegroup"].replace(age_map)
    m_ak["infectionstatus"] = m_ak["infectionstatus"].astype(str).str.strip().str.lower()
    m_ak["patients"] = pd.to_numeric(m_ak["patients"], errors="coerce").fillna(0)
    m_ak["m_ak"] = pd.to_numeric(m_ak["m_ak"],      errors="coerce").fillna(0)

    tmp = m_ak.copy()
    pi_inf_given_a = tmp.groupby(["agegroup", "infectionstatus"], as_index=False)["patients"].sum()
    den = pi_inf_given_a.groupby("agegroup")["patients"].transform("sum")
    pi_inf_given_a["pi_inf_given_a"] = np.where(den > 0, pi_inf_given_a["patients"] / den, 0.0)
    pi_inf_given_a = pi_inf_given_a[["agegroup", "infectionstatus", "pi_inf_given_a"]]
    pi_inf_given_a["agegroup"] = pi_inf_given_a["agegroup"].replace(age_map)

    p_class = _p_class_raw.copy()

    # CMS data
    cms_raw = pd.read_csv(BASE_DIR / "antimicrobials.csv")
    cms_raw.columns = (
        cms_raw.columns.str.strip().str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_")
    )
    amc_cols = [c for c in cms_raw.columns if c.startswith("average_monthly")]
    cms = cms_raw.rename(columns={
        "product_code": "product_code",
        "product_description": "description",
        "unit_price_bwp": "unit_price_bwp",
        amc_cols[0]: "amc_2526",
        amc_cols[1]: "amc_2627",
    }).copy()
    for col in ["unit_price_bwp", "amc_2526", "amc_2627"]:
        cms[col] = pd.to_numeric(cms[col], errors="coerce").fillna(0.0)
    cms["biweekly_2526"] = cms["amc_2526"] / 2.0
    cms["biweekly_2627"] = cms["amc_2627"] / 2.0
    cms_active = cms[(cms["biweekly_2526"] > 0) | (cms["biweekly_2627"] > 0)].copy()
    cms_active = cms_active.set_index("product_code")
    cms_proc_cost = cms_active["unit_price_bwp"]

    # National population share per facility
    _clinic_nat = raw_results["Clinic"][["pop_id", "Facility Name_1", "crow_dist_km_1", "total_population"]].copy()
    _hp_nat     = raw_results["Health Post"][["pop_id", "Facility Name_1", "crow_dist_km_1", "total_population"]].copy()
    _hosp_nat   = raw_results["Hospital"][["pop_id", "Facility Name_1", "crow_dist_km_1", "total_population"]].copy()
    for df_, ft in [(_clinic_nat, "clinic"), (_hp_nat, "health_post"), (_hosp_nat, "hospital")]:
        df_.rename(columns={"Facility Name_1": "facility_name",
                             "crow_dist_km_1": "dist_km",
                             "total_population": "pop_total"}, inplace=True)
        df_["facility_type"] = ft

    choices_nat = pd.concat([_clinic_nat, _hp_nat, _hosp_nat], ignore_index=True)
    choices_nat["dist_km"] = pd.to_numeric(choices_nat["dist_km"], errors="coerce")
    choices_nat = choices_nat.dropna(subset=["facility_name", "dist_km"])
    choices_nat["facility_name"] = choices_nat["facility_name"].map(_clean_fac_name)
    choices_nat = choices_nat.sort_values(["pop_id", "dist_km"])
    closest_nat = choices_nat.drop_duplicates(subset=["pop_id"], keep="first")

    pop_fac_national = (
        closest_nat.groupby("facility_name", as_index=True)["pop_total"].sum().rename("pop_total")
    )
    national_pop = pop_fac_national.sum()
    pop_fac_share = (pop_fac_national / national_pop).rename("pop_share")

    print(f"Data loaded. {len(fac)} facilities, {len(pop)} pop points, "
          f"{len(cms_active)} active CMS products, {len(pop_fac_share)} facility shares.")


# Helper functions

def _clean_matrix(df):
    """Strip BOM / whitespace from matrix index/columns."""
    df.index   = df.index.astype(str).str.replace("\ufeff", "").str.strip()
    df.columns = df.columns.astype(str).str.replace("\ufeff", "").str.strip()
    df.index   = df.index.str.replace(r"\s+", " ", regex=True)
    df.columns = df.columns.str.replace(r"\s+", " ", regex=True)
    return df

def _clean_fac_name(x):
    s = str(x).replace("\ufeff", "").replace("\xa0", " ")
    return " ".join(s.split()).strip()

def _attach_assigned_dhmt(result_df, fac_df, subtype):
    fac_lookup = fac_df[["Facility Name", "DHMT"]].copy()
    fac_lookup["Facility Name"] = fac_lookup["Facility Name"].astype(str).str.strip()
    fac_lookup["DHMT"]          = fac_lookup["DHMT"].astype(str).str.strip()
    overrides = {
        "Mowana Health Post":   "Mahalapye",
        "Phuduhudu Health Post":"Kgalagadi North",
        "Tshwaane Health Post": "Kweneng",
    }
    fac_lookup["DHMT"] = fac_lookup.apply(
        lambda r: overrides.get(r["Facility Name"], r["DHMT"]), axis=1
    )
    fac_lookup = fac_lookup.drop_duplicates(subset=["Facility Name"])
    col = "Facility Name_1"
    out = result_df.copy()
    out[col] = out[col].astype(str).str.strip()
    out = out.merge(fac_lookup, left_on=col, right_on="Facility Name", how="left")
    out = out.rename(columns={"DHMT": f"assigned_dhmt_{subtype.lower().replace(' ', '_')}"})
    return out.drop(columns=["Facility Name"])

def nearest_facilities(pop_df, fac_df, subtype, n=1):
    if subtype == "Clinic":
        sub = fac_df[fac_df["Service Delivery Type"].str.lower().isin(["clinic", "clinic with maternity"])]
    elif subtype == "Hospital":
        sub = fac_df[
            fac_df["Service Delivery Type"].str.lower().isin(["primary hospital", "district hospital"]) |
            ((fac_df["Service Delivery Type"].str.lower() == "referral hospital") &
             (fac_df["Facility Name"].str.contains("Princess Marina|Nyangabgwe", case=False, na=False)))
        ]
    else:
        sub = fac_df[fac_df["Service Delivery Type"].str.lower() == subtype.lower()]
    if sub.empty:
        return pop_df
    tree = cKDTree(sub[["latitude", "longitude"]].to_numpy())
    dist, idx = tree.query(pop_df[["latitude", "longitude"]].to_numpy(), k=n)
    dist = dist[:, None] if n == 1 else dist
    idx  = idx[:, None]  if n == 1 else idx
    nearest = [sub.iloc[idx[:, i]].reset_index(drop=True).add_suffix(f"_{i+1}") for i in range(n)]
    merged = pd.concat(nearest, axis=1)
    merged["crow_dist_km_1"] = dist[:, 0]
    return pd.concat([pop_df.reset_index(drop=True), merged], axis=1)

def nb_sigma_from_mean(mu_mat: pd.DataFrame, kappa: float) -> pd.DataFrame:
    mu  = mu_mat.astype(float)
    var = mu + (mu ** 2) / float(kappa)
    return np.sqrt(var)

def make_nb_draws_from_mean(mean_mat: pd.DataFrame, kappa: float, T: int, seed: int = 0):
    rng   = np.random.default_rng(seed)
    mu    = mean_mat.values.astype(float)
    kappa = max(kappa, 1e-6)
    p     = kappa / (kappa + mu)
    return rng.negative_binomial(n=kappa, p=p, size=(T, *mu.shape)).astype(float)

def build_node_demand_matrix(demand_fac_long):
    tmp = demand_fac_long.copy()
    tmp["facility_name"] = tmp["facility_name"].astype(str).str.strip()
    return (
        tmp.pivot_table(index="facility_name", columns="Class",
                        values="expected_count", aggfunc="sum", fill_value=0.0)
        .sort_index()
    )

def expected_class_counts_by_facility(pop_fac_age_df):
    df = pop_fac_age_df.copy()
    df["patient_days"] = pd.to_numeric(df["patient_days"], errors="coerce").fillna(0.0)

    pi_tmp = pi_inf_given_a.copy()
    pi_tmp["agegroup"]       = pi_tmp["agegroup"].replace(age_map)
    pi_tmp["infectionstatus"] = pi_tmp["infectionstatus"].astype(str).str.strip().str.lower()
    df["agegroup"] = df["agegroup"].astype(str).str.strip()
    df = df.merge(pi_tmp, on="agegroup", how="left")
    df["infectionstatus"] = df["infectionstatus"].astype(str).str.strip().str.lower()
    df["patients_ak"] = df["patient_days"] * df["pi_inf_given_a"]

    m_tmp = m_ak.copy()
    m_tmp["agegroup"]       = m_tmp["agegroup"].replace(age_map)
    m_tmp["infectionstatus"] = m_tmp["infectionstatus"].astype(str).str.strip().str.lower()
    df = df.merge(m_tmp[["agegroup", "infectionstatus", "m_ak"]], on=["agegroup", "infectionstatus"], how="left")
    df["n_akh"] = df["patients_ak"] * df["m_ak"]

    p_tmp = p_class.copy()
    for col in ["agegroup", "infectionstatus", "hospital_type", "Class"]:
        if col in p_tmp.columns:
            p_tmp[col] = p_tmp[col].astype(str).str.strip()
    df["hospital_type"] = df["hospital_type"].astype(str).str.strip()
    df = df.merge(p_tmp, on=["agegroup", "infectionstatus", "hospital_type"], how="left")
    df["expected_count"] = df["n_akh"] * df["p_class"]

    out = (
        df.groupby(["facility_name", "facility_type", "Class"], as_index=False)["expected_count"].sum()
    )
    return out


# Region instance builder

_DISTRICT_MAP = {
    "barolong": "goodhope",
    "central bobonong": "bobirwa",
    "central boteti": "boteti",
    "central kalahari game reserve": "kgalagadi north",
    "central kgalagadi game reserve": "kgalagadi north",
    "central mahalapye": "mahalapye",
    "central serowe/ palapye": "palapye",
    "central serowe-palapye": "palapye",
    "central tutume": "tutume",
    "ckgr": "kgalagadi north",
    "jwaneng": "goodhope",
    "kweneng west": "kweneng east",
    "ngamiland delta": "ngamiland",
    "ngamiland east": "ngamiland",
    "ngamiland west": "ngamiland",
    "ngwaketse": "southern",
    "ngwaketse central": "southern",
    "ngwaketse west": "southern",
    "orapa": "boteti",
    "selibe phikwe": "selebi-phikwe",
    "selebi-phikwe": "selebi-phikwe",
    "sowa": "boteti",
    "sowa town": "boteti",
    "central madinare": "bobirwa",
    "central molalatau": "bobirwa",
    "kasane": "chobe",
    "kgalagadi rural": "kgalagadi south",
    "kweneng central": "kweneng east",
    "francistown": "francistown",
    "ghanzi farms": "ghanzi",
    "lobatse": "lobatse",
    "pandamatenga": "chobe",
    "tsabong": "kgalagadi south",
}

def _to_tier(s):
    s = str(s).lower().strip()
    if "warehouse" in s or "dhmt" in s or "store" in s: return "warehouse"
    if "tertiary" in s or "referral" in s or "hospital" in s: return "hospital"
    if "health post" in s or "healthpost" in s: return "health_post"
    return "clinic"

def build_region_instance(target_dhmt):
    target_norm   = str(target_dhmt).strip().lower()
    clean_name    = _clean_fac_name
    norm_name     = lambda s: re.sub(r"\s+", " ", str(s)).strip().lower()
    norm_district = lambda s: re.sub(r"\s+", " ", str(s)).strip().lower()

    fac_region = fac.copy()
    fac_region["_dhmt_norm"] = fac_region["DHMT"].astype(str).str.strip().str.lower()
    fac_region = fac_region.loc[fac_region["_dhmt_norm"] == target_norm].copy()
    if fac_region.empty:
        raise ValueError(f"no facilities found for DHMT = {target_dhmt}")

    if "facility_name" not in fac_region.columns:
        fac_region = fac_region.rename(columns={"Facility Name": "facility_name"})
    fac_region["facility_name"] = fac_region["facility_name"].map(clean_name)
    fac_region["tier"]          = fac_region["Service Delivery Type"].apply(_to_tier)
    fac_region["facility_key"]  = fac_region["facility_name"].apply(norm_name)

    source_node    = clean_name(DHMT_SOURCE_MAP[target_dhmt])
    facility_nodes = fac_region["facility_name"].dropna().astype(str).tolist()
    all_nodes      = facility_nodes.copy()
    if source_node not in all_nodes:
        all_nodes = [source_node] + all_nodes

    nodes_region = [n for n in all_nodes if n in dist_matrix_df.index and n in dist_matrix_df.columns]
    if source_node not in nodes_region:
        raise ValueError(f"source node '{source_node}' missing from distance matrix")
    if not nodes_region:
        raise ValueError(f"no matrix-matched nodes for DHMT = {target_dhmt}")

    D_region = dist_matrix_df.loc[nodes_region, nodes_region].copy()
    T_region = time_matrix_df.loc[nodes_region, nodes_region].copy()
    tier_map = dict(zip(fac_region["facility_name"], fac_region["tier"]))
    tier_map[source_node] = "warehouse"

    n_hosp = int((fac_region["tier"] == "hospital").sum())
    allowed = (
        {"warehouse": ["clinic","health_post"], "hospital": ["clinic","health_post"], "clinic": [], "health_post": []}
        if n_hosp == 0 else
        {"warehouse": ["hospital"], "hospital": ["clinic","health_post"], "clinic": ["hospital"], "health_post": ["hospital"]}
    )

    rows = []
    for u in nodes_region:
        u_tier = tier_map.get(u)
        if u_tier is None: continue
        for v_tier in allowed.get(u_tier, []):
            cand  = [v for v in nodes_region if v != u and tier_map.get(v) == v_tier]
            if not cand: continue
            dists = D_region.loc[u, cand].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
            for v, dist_val in dists.items():
                time_val = T_region.loc[u, v]
                if pd.isna(time_val) or np.isinf(time_val): continue
                rows.append({"u": u, "v": v, "u_tier": u_tier, "v_tier": v_tier,
                              "dist_km": float(dist_val)/1000.0, "time_min": float(time_val)/60.0})

    arcs_df = pd.DataFrame(rows).drop_duplicates(subset=["u","v"]).reset_index(drop=True)
    if arcs_df.empty:
        raise ValueError(f"no arcs for DHMT = {target_dhmt}")
    model_arcs = [(r.u, r.v) for r in arcs_df.itertuples(index=False)]

    # Population / demand pipeline
    hosp_df   = results_with_dhmt["Hospital"].copy()
    clinic_df = results_with_dhmt["Clinic"].copy()
    hp_df     = results_with_dhmt["Health Post"].copy()

    mask_h  = hosp_df["assigned_dhmt_hospital"].astype(str).str.strip().str.lower().eq(target_norm)
    mask_c  = clinic_df["assigned_dhmt_clinic"].astype(str).str.strip().str.lower().eq(target_norm)
    mask_hp = hp_df["assigned_dhmt_health_post"].astype(str).str.strip().str.lower().eq(target_norm)
    mask_any = mask_h | mask_c | mask_hp

    pop_dhmt_region = hosp_df.loc[mask_any].copy()
    if pop_dhmt_region.empty:
        raise ValueError(f"no population points assigned to DHMT = {target_dhmt}")

    merged_region = pop_dhmt_region.copy()
    merged_region["pop_id"] = merged_region.index
    merged_region = merged_region.rename(columns={
        "Facility Name_1": "nearest_Hospital_name",
        "latitude_1": "nearest_Hospital_lat",
        "longitude_1": "nearest_Hospital_lon",
        "DHMT_1": "nearest_Hospital_dhmt",
        "crow_dist_km_1": "crow_dist_km_Hospital",
    })

    def _sub(df_, cols, rename_):
        s = df_.copy(); s["pop_id"] = s.index
        return s[["pop_id"] + list(cols.keys())].rename(columns=cols)

    clinic_sub = _sub(clinic_df, {
        "Facility Name_1": "nearest_Clinic_name",
        "crow_dist_km_1":  "crow_dist_km_Clinic",
    }, {})
    hp_sub = _sub(hp_df, {
        "Facility Name_1": "nearest_HealthPost_name",
        "crow_dist_km_1":  "crow_dist_km_HealthPost",
    }, {})

    merged_region = (merged_region
                     .merge(clinic_sub, on="pop_id", how="left")
                     .merge(hp_sub,     on="pop_id", how="left")
                     .reset_index(drop=True))

    POP_COL = "total_population"
    merged_region[POP_COL] = pd.to_numeric(
        merged_region[POP_COL].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )

    def _build_pop_fac(name_col, dist_col, ftype):
        c = merged_region[["pop_id", name_col, dist_col, "district", POP_COL]].copy()
        c = c.rename(columns={name_col: "facility_name", dist_col: "dist_km",
                               "district": "district", POP_COL: "pop_total"})
        c["facility_type"] = ftype
        return c

    choices = pd.concat([
        _build_pop_fac("nearest_Clinic_name",     "crow_dist_km_Clinic",     "clinic"),
        _build_pop_fac("nearest_HealthPost_name",  "crow_dist_km_HealthPost", "health_post"),
    ], ignore_index=True)
    choices["facility_name"] = choices["facility_name"].astype(str).str.strip()
    choices["dist_km"] = pd.to_numeric(choices["dist_km"], errors="coerce")
    choices = choices.replace({"facility_name": {"": np.nan, "nan": np.nan}}).dropna(subset=["facility_name","dist_km"])
    closest = choices.sort_values(["pop_id","dist_km"]).drop_duplicates(subset=["pop_id"], keep="first")

    pop_fac_region = closest.groupby(["facility_name","facility_type","district"], as_index=False)["pop_total"].sum()
    pop_fac_region["district_key"] = pop_fac_region["district"].apply(norm_district).replace(_DISTRICT_MAP)

    adm_map = district_adm.drop_duplicates("district_key").set_index("district_key")["annual_admissions_est"]
    pop_fac_region["annual_admissions_est"] = pop_fac_region["district_key"].map(adm_map)
    missing_adm = sorted(pop_fac_region.loc[pop_fac_region["annual_admissions_est"].isna(), "district_key"].dropna().unique())
    if missing_adm:
        raise ValueError(f"missing admissions estimates for district keys: {missing_adm}")

    pop_fac_region["district_pop_total"]    = pop_fac_region.groupby("district_key")["pop_total"].transform("sum")
    pop_fac_region["facility_pop_share"]    = np.where(pop_fac_region["district_pop_total"] > 0,
                                                        pop_fac_region["pop_total"] / pop_fac_region["district_pop_total"], 0.0)
    pop_fac_region["facility_admissions_annual"] = pop_fac_region["facility_pop_share"] * pop_fac_region["annual_admissions_est"]

    age_work = age_df.copy()
    age_work["district_key"] = age_work["district"].astype(str).str.strip().str.lower().replace(_DISTRICT_MAP)
    age_df_agg = age_work.groupby(["district_key","agegroup"], as_index=False)["share"].sum()

    pop_fac_age = pop_fac_region.merge(age_df_agg[["district_key","agegroup","share"]], on="district_key", how="left")
    PLANNING_HORIZON_WEEKS, AVG_LOS_DAYS = 2, 5.0
    pop_fac_age["pop_count"]     = pop_fac_age["pop_total"] * pop_fac_age["share"]
    pop_fac_age["admissions_annual"] = pop_fac_age["facility_admissions_annual"] * pop_fac_age["share"]
    pop_fac_age["admissions"]    = pop_fac_age["admissions_annual"] * (PLANNING_HORIZON_WEEKS / 52.0)
    pop_fac_age["patient_days"]  = pop_fac_age["admissions"] * AVG_LOS_DAYS
    pop_fac_age["facility_key"]  = pop_fac_age["facility_name"].apply(norm_name)

    pop_fac_age = pop_fac_age[["facility_name","facility_key","facility_type","district","district_key",
                                "agegroup","pop_count","admissions_annual","admissions","patient_days"]]
    pop_fac_age = pop_fac_age.merge(fac_region[["facility_key","tier"]], on="facility_key", how="left")
    pop_fac_age["tier"] = pop_fac_age["tier"].fillna("clinic")
    tier_to_hosp_type = {"clinic":"Clinic","health_post":"Clinic","hospital":"Primary","warehouse":"Tertiary"}
    pop_fac_age["hospital_type"] = pop_fac_age["tier"].map(tier_to_hosp_type)

    demand_fac_region = expected_class_counts_by_facility(pop_fac_age)

    # Hospital demand
    pop_hosp = (merged_region.groupby(["nearest_Hospital_name","district"], as_index=False)[POP_COL]
                .sum().rename(columns={"nearest_Hospital_name":"facility_name","district":"district",POP_COL:"pop_total"}))
    pop_hosp["facility_type"]   = "hospital"
    pop_hosp["district_key"]    = pop_hosp["district"].apply(norm_district).replace(_DISTRICT_MAP)
    pop_hosp["annual_admissions_est"] = pop_hosp["district_key"].map(adm_map)
    pop_hosp["district_pop_total"]    = pop_hosp.groupby("district_key")["pop_total"].transform("sum")
    pop_hosp["facility_pop_share"]    = np.where(pop_hosp["district_pop_total"] > 0,
                                                  pop_hosp["pop_total"] / pop_hosp["district_pop_total"], 0.0)
    pop_hosp["facility_admissions_annual"] = pop_hosp["facility_pop_share"] * pop_hosp["annual_admissions_est"]
    pop_hosp_age = pop_hosp.merge(age_df_agg[["district_key","agegroup","share"]], on="district_key", how="left")
    pop_hosp_age["pop_count"]        = pop_hosp_age["pop_total"] * pop_hosp_age["share"]
    pop_hosp_age["admissions_annual"] = pop_hosp_age["facility_admissions_annual"] * pop_hosp_age["share"]
    pop_hosp_age["admissions"]        = pop_hosp_age["admissions_annual"] * (PLANNING_HORIZON_WEEKS / 52.0)
    pop_hosp_age["patient_days"]      = pop_hosp_age["admissions"] * AVG_LOS_DAYS
    pop_hosp_age["facility_key"]      = pop_hosp_age["facility_name"].apply(norm_name)
    pop_hosp_age = pop_hosp_age.merge(fac_region[["facility_key","tier"]], on="facility_key", how="left")
    pop_hosp_age["tier"] = pop_hosp_age["tier"].fillna("hospital")
    pop_hosp_age["hospital_type"] = pop_hosp_age["tier"].map(tier_to_hosp_type)

    hospital_demand_region = expected_class_counts_by_facility(pop_hosp_age)

    all_demand = pd.concat([demand_fac_region, hospital_demand_region], ignore_index=True)
    node_demand_mat = build_node_demand_matrix(all_demand)

    model_classes = sorted(node_demand_mat.columns.tolist())
    model_nodes   = list(D_region.index)
    mu_mat = node_demand_mat.reindex(index=model_nodes, columns=model_classes).fillna(0.0).astype(float)
    sigma_mat = nb_sigma_from_mean(mu_mat, kappa=10.0).reindex(index=model_nodes, columns=model_classes).fillna(0.0).astype(float)

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


# CMS instance builder

def build_cms_demand_matrix(nodes, cms_node, scenario="2526"):
    col           = f"biweekly_{scenario}"
    national_dem  = cms_active[col]
    demand_nodes  = [n for n in nodes if n != cms_node]
    shares        = pop_fac_share.reindex(demand_nodes).fillna(0.0)
    mu_demand     = pd.DataFrame(
        np.outer(shares.values, national_dem.values),
        index=demand_nodes, columns=national_dem.index,
    )
    return mu_demand.reindex(nodes).fillna(0.0).astype(float)

def build_cms_region_instance(region, scenario="2526"):
    base     = build_region_instance(region)
    mu_mat   = build_cms_demand_matrix(base["nodes"], base["CMS"], scenario=scenario)
    classes  = mu_mat.columns.tolist()
    sigma_mat = nb_sigma_from_mean(mu_mat, kappa=10.0).reindex(
        index=base["nodes"], columns=classes).fillna(0.0).astype(float)
    return {**base, "mu_mat": mu_mat, "sigma_mat": sigma_mat, "proc_cost": cms_proc_cost}


# Simulation functions (CMS-aware versions)

def _resolve_c_proc(procurement_cost_per_unit, classes):
    if np.isscalar(procurement_cost_per_unit):
        return np.full(len(classes), float(procurement_cost_per_unit))
    return pd.Series(procurement_cost_per_unit).reindex(classes).fillna(0.0).astype(float).to_numpy()

def _resolve_c_penalty(shortage_penalty_per_unit, classes):
    if np.isscalar(shortage_penalty_per_unit):
        return np.full(len(classes), float(shortage_penalty_per_unit))
    return pd.Series(shortage_penalty_per_unit).reindex(classes).fillna(0.0).astype(float).to_numpy()

def simulate_policy_under_draws_cms(
    T, CMS, nodes, arcs, classes, dist_km, mu_mat, demand_draws,
    transport_cost_per_km=0.5, shortage_penalty_per_unit=10.0,
    holding_cost_per_unit=0.1, procurement_cost_per_unit=0.0,
    supply_multiplier=0.0, arc_cap=None, storage_cap_per_node=None,
    solver=None, verbose=False, relax_integrality=False, I0_start=None,
):
    nodes   = list(nodes)
    arcs    = list(arcs)
    classes = list(classes)

    node_idx = {n: i for i, n in enumerate(nodes)}
    N, m, K  = len(nodes), len(arcs), len(classes)

    if arc_cap is None:
        raise ValueError("arc_cap must be provided")
    if np.isscalar(arc_cap):
        arc_cap_vec = np.full(m, float(arc_cap))
    else:
        arc_cap_vec = np.array([float(arc_cap[(i, j)]) for (i, j) in arcs], dtype=float)

    c_arc  = np.array([float(dist_km.loc[i, j]) for (i, j) in arcs], dtype=float)
    c_proc = _resolve_c_proc(procurement_cost_per_unit, classes)   # ← resolve once
    c_pen  = _resolve_c_penalty(shortage_penalty_per_unit, classes) # ← resolve once

    mu_mat = mu_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float)
    mu_np  = mu_mat.to_numpy()

    in_arcs  = [[] for _ in range(N)]
    out_arcs = [[] for _ in range(N)]
    for a, (i, j) in enumerate(arcs):
        out_arcs[node_idx[i]].append(a)
        in_arcs[node_idx[j]].append(a)

    if storage_cap_per_node is None:
        cap_vec = None
    else:
        cap_vec = (np.full(N, float(storage_cap_per_node)) if np.isscalar(storage_cap_per_node)
                   else pd.Series(storage_cap_per_node).reindex(nodes).astype(float).to_numpy())

    if I0_start is not None:
        I = I0_start.reindex(index=nodes, columns=classes).fillna(0.0)
    else:
        I = pd.DataFrame(0.0, index=nodes, columns=classes)
        I.loc[CMS, :] = supply_multiplier * mu_mat.sum(axis=0)
    metrics = []
    nominal_mu = mu_mat.copy()

    for t in range(T):
        I0 = I.to_numpy().copy()
        F  = cp.Variable((m, K), nonneg=True)
        u  = cp.Variable((N, K), nonneg=True)
        I1 = cp.Variable((N, K), nonneg=True)
        q  = cp.Variable(K, nonneg=True)
        constraints = []

        if relax_integrality:
            lam = cp.Variable(m, nonneg=True)
            y   = cp.Variable(m, nonneg=True)
            constraints += [y <= 1.0]
        else:
            lam = cp.Variable(m, integer=True)
            y   = cp.Variable(m, boolean=True)

        big_m = 1e5
        for a in range(m):
            constraints.append(cp.sum(F[a, :]) <= arc_cap_vec[a] * lam[a])
            constraints.append(lam[a] >= 0)
            constraints.append(lam[a] <= big_m * y[a])

        for n in range(N):
            for k in range(K):
                inflow  = cp.sum(F[in_arcs[n],  k]) if in_arcs[n]  else 0
                outflow = cp.sum(F[out_arcs[n], k]) if out_arcs[n] else 0
                supply  = q[k] if nodes[n] == CMS else 0.0
                demand  = float(mu_np[n, k])
                constraints.append(
                    I1[n, k] == I0[n, k] + inflow - outflow + supply - demand + u[n, k]
                )
                constraints.append(outflow <= I0[n, k] + inflow + supply)

        if cap_vec is not None:
            for n in range(N):
                constraints.append(cp.sum(I1[n, :]) <= cap_vec[n])

        obj = cp.Minimize(
            transport_cost_per_km    * cp.sum(cp.multiply(c_arc,  lam))
            + cp.sum(cp.multiply(c_pen.reshape(1, K), u))
            + holding_cost_per_unit     * cp.sum(I1)
            + cp.sum(cp.multiply(c_proc, q))    # ← per-drug cost
        )
        prob = cp.Problem(obj, constraints)
        prob.solve(solver=solver, verbose=verbose)
        if prob.status not in ("optimal", "optimal_inaccurate"):
            raise RuntimeError(f"Failed at t={t}: {prob.status}")

        F_val = np.maximum(np.asarray(F.value, dtype=float), 0.0)
        realized = pd.DataFrame(demand_draws[t], index=nodes, columns=classes)
        ship_by_arc = {(i, j): pd.Series(F_val[a, :], index=classes)
                       for a, (i, j) in enumerate(arcs)}
        q_ser   = pd.Series(np.maximum(np.asarray(q.value, dtype=float), 0.0), index=classes)
        lam_val = np.maximum(np.round(np.asarray(lam.value, dtype=float)).astype(int), 0)

        I_next = pd.DataFrame(0.0, index=nodes, columns=classes)
        unmet  = pd.DataFrame(0.0, index=nodes, columns=classes)
        for n_name in nodes:
            inflow  = pd.Series(0.0, index=classes)
            outflow = pd.Series(0.0, index=classes)
            for (i, j), ship_ser in ship_by_arc.items():
                if j == n_name: inflow  = inflow.add(ship_ser,  fill_value=0.0)
                if i == n_name: outflow = outflow.add(ship_ser, fill_value=0.0)
            add_supply  = q_ser if n_name == CMS else pd.Series(0.0, index=classes)
            demand_vec  = realized.loc[n_name, :]
            avail       = I.loc[n_name, :] + add_supply + inflow - outflow
            served      = np.minimum(avail, demand_vec)
            unmet.loc[n_name, :]  = demand_vec - served
            I_next.loc[n_name, :] = avail - served
        I = I_next.copy()

        transport_cost = sum(transport_cost_per_km * float(dist_km.loc[i, j]) * float(lam_val[a])
                             for a, (i, j) in enumerate(arcs))
        shortage_cost  = float((unmet.to_numpy() * c_pen).sum())
        holding_cost   = holding_cost_per_unit     * float(I.to_numpy().sum())
        proc_cost      = float((q_ser * pd.Series(c_proc, index=classes)).sum())

        total_demand = float(realized.to_numpy().sum())
        total_unmet  = float(unmet.to_numpy().sum())
        metrics.append({
            "t": t,
            "objective_realized":      transport_cost + shortage_cost + holding_cost + proc_cost,
            "transport_cost_realized": transport_cost,
            "shortage_cost_realized":  shortage_cost,
            "holding_cost_end":        holding_cost,
            "procurement_cost":        proc_cost,
            "unmet_pct_realized":      (total_unmet / total_demand * 100.0) if total_demand > 0 else 0.0,
            "total_unmet_units":       total_unmet,
            "total_demand_units":      total_demand,
            "total_procured_units":    float(q_ser.sum()),
        })
    return pd.DataFrame(metrics), nominal_mu, I


def simulate_static_robust_under_draws_cms(
    T, CMS, nodes, arcs, classes, dist_km, mu_mat, demand_draws, sigma_mat, Gamma,
    transport_cost_per_km=0.5, shortage_penalty_per_unit=10.0,
    holding_cost_per_unit=0.1, procurement_cost_per_unit=0.0,
    supply_multiplier=0.0, arc_cap=None, storage_cap_per_node=None,
    solver=None, verbose=False, relax_integrality=False, I0_start=None,
):
    nodes   = list(nodes)
    arcs    = list(arcs)
    classes = list(classes)

    node_idx = {n: i for i, n in enumerate(nodes)}
    N, m, K  = len(nodes), len(arcs), len(classes)

    if arc_cap is None:
        raise ValueError("arc_cap must be provided")
    if np.isscalar(arc_cap):
        arc_cap_vec = np.full(m, float(arc_cap))
    else:
        arc_cap_vec = np.array([float(arc_cap[(i, j)]) for (i, j) in arcs], dtype=float)

    c_arc  = np.array([float(dist_km.loc[i, j]) for (i, j) in arcs], dtype=float)
    c_proc = _resolve_c_proc(procurement_cost_per_unit, classes)   # ← resolve once
    c_pen  = _resolve_c_penalty(shortage_penalty_per_unit, classes) # ← resolve once

    mu_mat    = mu_mat.reindex(index=nodes,    columns=classes).fillna(0.0).astype(float)
    sigma_mat = sigma_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float)
    mu_np     = mu_mat.to_numpy()
    sigma_np  = sigma_mat.to_numpy()

    in_arcs  = [[] for _ in range(N)]
    out_arcs = [[] for _ in range(N)]
    for a, (i, j) in enumerate(arcs):
        out_arcs[node_idx[i]].append(a)
        in_arcs[node_idx[j]].append(a)

    if storage_cap_per_node is None:
        cap_vec = None
    else:
        cap_vec = (np.full(N, float(storage_cap_per_node)) if np.isscalar(storage_cap_per_node)
                   else pd.Series(storage_cap_per_node).reindex(nodes).astype(float).to_numpy())

    if I0_start is not None:
        I = I0_start.reindex(index=nodes, columns=classes).fillna(0.0)
    else:
        I = pd.DataFrame(0.0, index=nodes, columns=classes)
        I.loc[CMS, :] = supply_multiplier * mu_mat.sum(axis=0)
    metrics = []

    def nk_index(n, k): return n * K + k

    for t in range(T):
        I0 = I.to_numpy().copy()
        constraints = []
        Fbar = cp.Variable((m, K), nonneg=True)
        u    = cp.Variable((N, K), nonneg=True)
        I1   = cp.Variable((N, K), nonneg=True)
        q    = cp.Variable(K, nonneg=True)
        if relax_integrality:
            lam = cp.Variable(m, nonneg=True)
            y   = cp.Variable(m, nonneg=True)
            constraints += [y <= 1.0]
        else:
            lam = cp.Variable(m, integer=True)
            y   = cp.Variable(m, boolean=True)
        theta        = cp.Variable((N, K), nonneg=True)
        pi_plus      = cp.Variable((N * K, N), nonneg=True)
        pi_minus     = cp.Variable((N * K, N), nonneg=True)
        theta_ship   = cp.Variable((N, K), nonneg=True)
        pi_ship_plus  = cp.Variable((N * K, N), nonneg=True)
        pi_ship_minus = cp.Variable((N * K, N), nonneg=True)
        big_m = 1e5
        for a in range(m):
            constraints.append(cp.sum(Fbar[a, :]) <= arc_cap_vec[a] * lam[a])
            constraints.append(lam[a] >= 0)
            constraints.append(lam[a] <= big_m * y[a])
        for n in range(N):
            for k in range(K):
                nk      = nk_index(n, k)
                inflow  = cp.sum(Fbar[in_arcs[n],  k]) if in_arcs[n]  else 0
                outflow = cp.sum(Fbar[out_arcs[n], k]) if out_arcs[n] else 0
                supply  = q[k] if nodes[n] == CMS else 0.0
                demand  = float(mu_np[n, k])
                rhs = I0[n,k] + inflow - outflow + supply - demand + u[n,k] - I1[n,k]
                constraints.append(
                    Gamma * theta[n,k] + cp.sum(pi_plus[nk,:]) + cp.sum(pi_minus[nk,:]) <= rhs
                )
                constraints.append(theta[n,k] + pi_plus[nk,n]  >= -sigma_np[n,k])
                constraints.append(theta[n,k] + pi_minus[nk,n] >=  sigma_np[n,k])
                rhs_ship = I0[n,k] + inflow + supply - outflow
                constraints.append(
                    Gamma * theta_ship[n,k] + cp.sum(pi_ship_plus[nk,:]) + cp.sum(pi_ship_minus[nk,:]) <= rhs_ship
                )
                constraints.append(theta_ship[n,k] + pi_ship_plus[nk,n]  >= -sigma_np[n,k])
                constraints.append(theta_ship[n,k] + pi_ship_minus[nk,n] >=  sigma_np[n,k])
        if cap_vec is not None:
            for n in range(N):
                constraints.append(cp.sum(I1[n, :]) <= cap_vec[n])
        obj = cp.Minimize(
            transport_cost_per_km    * cp.sum(cp.multiply(c_arc,  lam))
            + cp.sum(cp.multiply(c_pen.reshape(1, K), u))
            + holding_cost_per_unit     * cp.sum(I1)
            + cp.sum(cp.multiply(c_proc, q))    # ← per-drug cost
        )
        prob = cp.Problem(obj, constraints)
        prob.solve(solver=solver, verbose=verbose)
        if prob.status not in ("optimal", "optimal_inaccurate"):
            raise RuntimeError(f"Failed at t={t}: {prob.status}")
        Fbar_val = np.maximum(np.asarray(Fbar.value, dtype=float), 0.0)
        realized = pd.DataFrame(demand_draws[t], index=nodes, columns=classes)
        ship_by_arc = {(i, j): pd.Series(Fbar_val[a, :], index=classes)
                       for a, (i, j) in enumerate(arcs)}
        q_ser   = pd.Series(np.maximum(np.asarray(q.value, dtype=float), 0.0), index=classes)
        lam_val = np.maximum(np.round(np.asarray(lam.value, dtype=float)).astype(int), 0)
        I_next = pd.DataFrame(0.0, index=nodes, columns=classes)
        unmet  = pd.DataFrame(0.0, index=nodes, columns=classes)
        for n_name in nodes:
            inflow  = pd.Series(0.0, index=classes)
            outflow = pd.Series(0.0, index=classes)
            for (i, j), ship_ser in ship_by_arc.items():
                if j == n_name: inflow  = inflow.add(ship_ser,  fill_value=0.0)
                if i == n_name: outflow = outflow.add(ship_ser, fill_value=0.0)
            add_supply = q_ser if n_name == CMS else pd.Series(0.0, index=classes)
            demand_vec = realized.loc[n_name, :]
            avail      = I.loc[n_name, :] + add_supply + inflow - outflow
            served     = np.minimum(np.maximum(avail, 0.0), demand_vec)
            unmet.loc[n_name, :]  = demand_vec - served
            I_next.loc[n_name, :] = avail - served
        I = I_next.copy()
        transport_cost = sum(transport_cost_per_km * float(dist_km.loc[i, j]) * lam_val[a]
                             for a, (i, j) in enumerate(arcs))
        shortage_cost  = float((unmet.to_numpy() * c_pen).sum())
        holding_cost   = holding_cost_per_unit     * float(I.to_numpy().sum())
        proc_cost      = float((q_ser * pd.Series(c_proc, index=classes)).sum())

        total_demand = float(realized.to_numpy().sum())
        total_unmet  = float(unmet.to_numpy().sum())
        metrics.append({
            "t": t,
            "objective_realized":      transport_cost + shortage_cost + holding_cost + proc_cost,
            "transport_cost_realized": transport_cost,
            "shortage_cost_realized":  shortage_cost,
            "holding_cost_end":        holding_cost,
            "procurement_cost":        proc_cost,
            "unmet_pct_realized":      (total_unmet / total_demand * 100.0) if total_demand > 0 else 0.0,
            "total_unmet_units":       total_unmet,
            "total_demand_units":      total_demand,
            "total_procured_units":    float(q_ser.sum()),
        })
    return pd.DataFrame(metrics), mu_mat.copy(), I


def simulate_aro_adr_under_draws_cms(
    T, CMS, nodes, arcs, arc_df, classes, dist_km, mu_mat, demand_draws, sigma_mat, Gamma,
    alpha_lb=-np.inf, alpha_ub=np.inf,
    transport_cost_per_km=0.5, shortage_penalty_per_unit=10.0,
    holding_cost_per_unit=0.1, procurement_cost_per_unit=0.1,
    supply_multiplier=0.0, arc_cap=None, storage_cap_per_node=None,
    solver=None, verbose=False, freeze_alpha_after_first=False, relax_integrality=False, I0_start=None,
):
    nodes   = list(nodes)
    arcs    = list(arcs)
    classes = list(classes)
    node_idx = {n: i for i, n in enumerate(nodes)}
    N, m, K  = len(nodes), len(arcs), len(classes)
    if arc_cap is None:
        raise ValueError("arc_cap must be provided")
    if Gamma < 0:
        raise ValueError("Gamma must be nonnegative")
    if np.isscalar(arc_cap):
        arc_cap_vec = np.full(m, float(arc_cap))
    else:
        arc_cap_vec = np.array([float(arc_cap[(i, j)]) for (i, j) in arcs], dtype=float)
    c_arc  = np.array([float(dist_km.loc[i, j]) for (i, j) in arcs], dtype=float)
    c_proc = _resolve_c_proc(procurement_cost_per_unit, classes)   # ← resolve once
    c_pen  = _resolve_c_penalty(shortage_penalty_per_unit, classes) # ← resolve once
    mu_mat    = mu_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float)
    mu_np     = mu_mat.to_numpy()
    sigma_mat = sigma_mat.reindex(index=nodes, columns=classes).fillna(0.0).astype(float)
    sigma_np  = sigma_mat.to_numpy()
    adaptive_arc_mask = np.array([
        1.0 if (row.u_tier in ["cms","warehouse","hospital"]
                and row.v_tier in ["clinic","warehouse","hospital","health_post"]) else 0.0
        for row in arc_df.itertuples(index=False)
    ], dtype=float)
    arc_dest_idx = np.array([node_idx[j] for (i, j) in arcs], dtype=int)
    in_arcs  = [[] for _ in range(N)]
    out_arcs = [[] for _ in range(N)]
    for a, (i, j) in enumerate(arcs):
        out_arcs[node_idx[i]].append(a)
        in_arcs[node_idx[j]].append(a)
    arcs_from_to = [[[] for _ in range(N)] for _ in range(N)]
    for a, (i, j) in enumerate(arcs):
        arcs_from_to[node_idx[i]][node_idx[j]].append(a)
    if storage_cap_per_node is None:
        cap_vec = None
    else:
        cap_vec = (np.full(N, float(storage_cap_per_node)) if np.isscalar(storage_cap_per_node)
                   else pd.Series(storage_cap_per_node).reindex(nodes).astype(float).to_numpy())
    if I0_start is not None:
        I = I0_start.reindex(index=nodes, columns=classes).fillna(0.0)
    else:
        I = pd.DataFrame(0.0, index=nodes, columns=classes)
        I.loc[CMS, :] = supply_multiplier * mu_mat.sum(axis=0)
    learned_alpha = None
    metrics = []
    def nk_index(n, k): return n * K + k
    for t in range(T):
        I0 = I.to_numpy().copy()
        Fbar = cp.Variable((m, K), nonneg=True)
        if freeze_alpha_after_first and learned_alpha is not None:
            alpha     = None
            alpha_val = np.asarray(learned_alpha, dtype=float)
        else:
            alpha     = cp.Variable((m, K))
            alpha_val = None
        u  = cp.Variable((N, K), nonneg=True)
        I1 = cp.Variable((N, K), nonneg=True)
        q  = cp.Variable(K, nonneg=True)
        constraints = []
        if relax_integrality:
            lam = cp.Variable(m, nonneg=True)
            y   = cp.Variable(m, nonneg=True)
            constraints += [y <= 1.0]
        else:
            lam = cp.Variable(m, integer=True)
            y   = cp.Variable(m, boolean=True)
        theta         = cp.Variable((N, K), nonneg=True)
        pi_plus       = cp.Variable((N * K, N), nonneg=True)
        pi_minus      = cp.Variable((N * K, N), nonneg=True)
        theta_ship    = cp.Variable((N, K), nonneg=True)
        pi_ship_plus  = cp.Variable((N * K, N), nonneg=True)
        pi_ship_minus = cp.Variable((N * K, N), nonneg=True)
        eta           = cp.Variable(m, nonneg=True)
        rho_plus      = cp.Variable((m, K), nonneg=True)
        rho_minus     = cp.Variable((m, K), nonneg=True)
        if alpha is not None:
            if np.isfinite(alpha_lb):
                constraints.append(alpha >= alpha_lb)
            if np.isfinite(alpha_ub):
                constraints.append(alpha <= alpha_ub)
        big_m = 1e5
        for a in range(m):
            j = arc_dest_idx[a]
            rhs_cap = arc_cap_vec[a] * lam[a] - cp.sum(Fbar[a, :])
            constraints.append(
                Gamma * eta[a] + cp.sum(rho_plus[a, :] + rho_minus[a, :]) <= rhs_cap
            )
            for k in range(K):
                coeff = alpha[a, k] if alpha is not None else alpha_val[a, k]
                constraints.append(eta[a] + rho_plus[a, k]  >= coeff * sigma_np[j, k])
                constraints.append(eta[a] + rho_minus[a, k] >= -coeff * sigma_np[j, k])
            constraints.append(lam[a] >= 0)
            constraints.append(lam[a] <= big_m * y[a])
        for n in range(N):
            for k in range(K):
                nk      = nk_index(n, k)
                inflow  = cp.sum(Fbar[in_arcs[n],  k]) if in_arcs[n]  else 0
                outflow = cp.sum(Fbar[out_arcs[n], k]) if out_arcs[n] else 0
                supply  = q[k] if nodes[n] == CMS else 0.0
                demand  = float(mu_np[n, k])
                rhs = I0[n,k] + inflow - outflow + supply - demand + u[n,k] - I1[n,k]
                constraints.append(
                    Gamma * theta[n,k] + cp.sum(pi_plus[nk,:]) + cp.sum(pi_minus[nk,:]) <= rhs
                )
                incoming_adaptive = [a for a in in_arcs[n] if adaptive_arc_mask[a] == 1.0]
                coeff_self = ((cp.sum(alpha[incoming_adaptive, k]) if incoming_adaptive else 0) - 1.0
                              if alpha is not None else
                              (float(np.sum(alpha_val[incoming_adaptive, k])) if incoming_adaptive else 0.0) - 1.0)
                constraints.append(theta[n,k] + pi_plus[nk,n]  >= coeff_self * sigma_np[n,k])
                constraints.append(theta[n,k] + pi_minus[nk,n] >= -coeff_self * sigma_np[n,k])
                for r in range(N):
                    nr_arcs = [a for a in arcs_from_to[n][r] if adaptive_arc_mask[a] == 1.0]
                    if not nr_arcs: continue
                    coeff_out = (-cp.sum(alpha[nr_arcs, k]) if alpha is not None
                                 else -float(np.sum(alpha_val[nr_arcs, k])))
                    constraints.append(theta[n,k] + pi_plus[nk,r]  >= coeff_out * sigma_np[r,k])
                    constraints.append(theta[n,k] + pi_minus[nk,r] >= -coeff_out * sigma_np[r,k])

                rhs_ship = I0[n,k] + inflow + supply - outflow
                constraints.append(
                    Gamma * theta_ship[n,k] + cp.sum(pi_ship_plus[nk,:]) + cp.sum(pi_ship_minus[nk,:]) <= rhs_ship
                )
                coeff_self_ship = ((-cp.sum(alpha[incoming_adaptive, k]) if incoming_adaptive else 0)
                                   if alpha is not None else
                                   (-float(np.sum(alpha_val[incoming_adaptive, k])) if incoming_adaptive else 0.0))
                constraints.append(theta_ship[n,k] + pi_ship_plus[nk,n]  >= coeff_self_ship * sigma_np[n,k])
                constraints.append(theta_ship[n,k] + pi_ship_minus[nk,n] >= -coeff_self_ship * sigma_np[n,k])
                for r in range(N):
                    nr_arcs = [a for a in arcs_from_to[n][r] if adaptive_arc_mask[a] == 1.0]
                    if not nr_arcs: continue
                    coeff_out_ship = (cp.sum(alpha[nr_arcs, k]) if alpha is not None
                                      else float(np.sum(alpha_val[nr_arcs, k])))
                    constraints.append(theta_ship[n,k] + pi_ship_plus[nk,r]  >= coeff_out_ship * sigma_np[r,k])
                    constraints.append(theta_ship[n,k] + pi_ship_minus[nk,r] >= -coeff_out_ship * sigma_np[r,k])
        if cap_vec is not None:
            for n in range(N):
                constraints.append(cp.sum(I1[n, :]) <= cap_vec[n])
        obj = cp.Minimize(
            transport_cost_per_km    * cp.sum(cp.multiply(c_arc,  lam))
            + cp.sum(cp.multiply(c_pen.reshape(1, K), u))
            + holding_cost_per_unit     * cp.sum(I1)
            + cp.sum(cp.multiply(c_proc, q))    # ← per-drug cost
        )
        prob = cp.Problem(obj, constraints)
        prob.solve(solver=solver, verbose=verbose)
        if prob.status not in ("optimal", "optimal_inaccurate"):
            raise RuntimeError(f"Failed at t={t}: {prob.status}")
        if alpha is not None:
            learned_alpha = np.asarray(alpha.value, dtype=float)
        Fbar_val  = np.maximum(np.asarray(Fbar.value, dtype=float), 0.0)
        alpha_use = (np.asarray(learned_alpha, dtype=float) if learned_alpha is not None
                     else np.asarray(alpha_val, dtype=float))
        realized    = pd.DataFrame(demand_draws[t], index=nodes, columns=classes)
        realized_np = realized.to_numpy()
        xi_real     = realized_np - mu_np
        ship_np = np.zeros((m, K), dtype=float)
        for a in range(m):
            dest = arc_dest_idx[a]
            ship_np[a, :] = (Fbar_val[a, :] + alpha_use[a, :] * xi_real[dest, :]
                             if adaptive_arc_mask[a] == 1.0 else Fbar_val[a, :])
        ship_np = np.maximum(ship_np, 0.0)
        ship_by_arc = {(i, j): pd.Series(ship_np[a, :], index=classes)
                       for a, (i, j) in enumerate(arcs)}
        q_ser   = pd.Series(np.maximum(np.asarray(q.value, dtype=float), 0.0), index=classes)
        lam_val = np.maximum(np.round(np.asarray(lam.value, dtype=float)).astype(int), 0)
        I_next = pd.DataFrame(0.0, index=nodes, columns=classes)
        unmet  = pd.DataFrame(0.0, index=nodes, columns=classes)
        for n_name in nodes:
            inflow  = pd.Series(0.0, index=classes)
            outflow = pd.Series(0.0, index=classes)
            for (i, j), ship_ser in ship_by_arc.items():
                if j == n_name: inflow  = inflow.add(ship_ser,  fill_value=0.0)
                if i == n_name: outflow = outflow.add(ship_ser, fill_value=0.0)
            add_supply = q_ser if n_name == CMS else pd.Series(0.0, index=classes)
            demand_vec = realized.loc[n_name, :]
            avail      = I.loc[n_name, :] + add_supply + inflow - outflow
            served     = np.minimum(avail, demand_vec)
            unmet.loc[n_name, :]  = demand_vec - served
            I_next.loc[n_name, :] = avail - served
        I = I_next.copy()
        transport_cost = sum(transport_cost_per_km * float(dist_km.loc[i, j]) * float(lam_val[a])
                             for a, (i, j) in enumerate(arcs))
        shortage_cost  = float((unmet.to_numpy() * c_pen).sum())
        holding_cost   = holding_cost_per_unit     * float(I.to_numpy().sum())
        proc_cost      = float((q_ser * pd.Series(c_proc, index=classes)).sum())
        total_demand = float(realized.to_numpy().sum())
        total_unmet  = float(unmet.to_numpy().sum())
        alpha_mean   = float(np.mean(learned_alpha)) if learned_alpha is not None else np.nan
        metrics.append({
            "t": t,
            "alpha_opt_mean":          alpha_mean,
            "objective_realized":      transport_cost + shortage_cost + holding_cost + proc_cost,
            "transport_cost_realized": transport_cost,
            "shortage_cost_realized":  shortage_cost,
            "holding_cost_end":        holding_cost,
            "procurement_cost":        proc_cost,
            "unmet_pct_realized":      (total_unmet / total_demand * 100.0) if total_demand > 0 else 0.0,
            "total_unmet_units":       total_unmet,
            "total_demand_units":      total_demand,
            "total_procured_units":    float(q_ser.sum()),
        })
    learned_alpha_out = pd.DataFrame(
        learned_alpha, index=[f"{i}->{j}" for (i, j) in arcs], columns=classes,
    )
    return pd.DataFrame(metrics), learned_alpha_out, I


# Region worker (runs in a subprocess)

def run_region(region):
    """Run both years for one region. Returns (list_of_metric_dicts, error_str_or_None)."""
    T = 26; kappa = 10.0; seed = 42; Gamma = 10.0
    results = []
    try:
        # Year 1: 2025-26
        inst_y1    = build_cms_region_instance(region, scenario="2526")
        classes_y1 = inst_y1["mu_mat"].columns.tolist()
        draws_y1   = make_nb_draws_from_mean(inst_y1["mu_mat"], kappa=kappa, T=T, seed=seed)
        shared_y1  = dict(T=T, CMS=inst_y1["CMS"], nodes=inst_y1["nodes"], arcs=inst_y1["arcs"],
                           classes=classes_y1, dist_km=inst_y1["dist_km"], mu_mat=inst_y1["mu_mat"],
                           demand_draws=draws_y1,
                           transport_cost_per_km=0.5, shortage_penalty_per_unit=5.0*inst_y1["proc_cost"],
                           holding_cost_per_unit=0.1, procurement_cost_per_unit=inst_y1["proc_cost"],
                           supply_multiplier=0.0, arc_cap=inst_y1["arc_cap"],
                           storage_cap_per_node=inst_y1["storage_cap_per_node"],
                           solver=cp.MOSEK, verbose=False, relax_integrality=True, I0_start=None)

        m_det_y1, _, final_I_det = simulate_policy_under_draws_cms(**shared_y1)
        m_rob_y1, _, final_I_rob = simulate_static_robust_under_draws_cms(**shared_y1, sigma_mat=inst_y1["sigma_mat"], Gamma=Gamma)
        m_aro_y1, _, final_I_aro = simulate_aro_adr_under_draws_cms(**shared_y1, arc_df=inst_y1["arc_df"],
                                                                     sigma_mat=inst_y1["sigma_mat"], Gamma=Gamma)
        for m, name in [(m_det_y1,"deterministic"), (m_rob_y1,"static_robust"), (m_aro_y1,"aro_adr")]:
            m["region"] = region; m["model"] = name; m["scenario"] = "2526"
            results.append(m)

        # Year 2: 2026-27 (carry forward final inventory)
        inst_y2    = build_cms_region_instance(region, scenario="2627")
        classes_y2 = inst_y2["mu_mat"].columns.tolist()
        draws_y2   = make_nb_draws_from_mean(inst_y2["mu_mat"], kappa=kappa, T=T, seed=seed)
        shared_y2  = dict(T=T, CMS=inst_y2["CMS"], nodes=inst_y2["nodes"], arcs=inst_y2["arcs"],
                           classes=classes_y2, dist_km=inst_y2["dist_km"], mu_mat=inst_y2["mu_mat"],
                           demand_draws=draws_y2,
                           transport_cost_per_km=0.5, shortage_penalty_per_unit=5.0*inst_y2["proc_cost"],
                           holding_cost_per_unit=0.1, procurement_cost_per_unit=inst_y2["proc_cost"],
                           supply_multiplier=0.0, arc_cap=inst_y2["arc_cap"],
                           storage_cap_per_node=inst_y2["storage_cap_per_node"],
                           solver=cp.MOSEK, verbose=False, relax_integrality=True)

        m_det_y2, _, _ = simulate_policy_under_draws_cms(**shared_y2,         I0_start=final_I_det)
        m_rob_y2, _, _ = simulate_static_robust_under_draws_cms(**shared_y2,  sigma_mat=inst_y2["sigma_mat"],
                                                                               Gamma=Gamma, I0_start=final_I_rob)
        m_aro_y2, _, _ = simulate_aro_adr_under_draws_cms(**shared_y2,        arc_df=inst_y2["arc_df"],
                                                                               sigma_mat=inst_y2["sigma_mat"],
                                                                               Gamma=Gamma, I0_start=final_I_aro)
        for m, name in [(m_det_y2,"deterministic"), (m_rob_y2,"static_robust"), (m_aro_y2,"aro_adr")]:
            m["region"] = region; m["model"] = name; m["scenario"] = "2627"
            results.append(m)

        print(f"  done: {region}", flush=True)
        return results, None

    except Exception as e:
        print(f"  failed: {region} - {e}", flush=True)
        return [], str(e)


# Main

if __name__ == "__main__":
    load_data()

    all_regions = sorted(fac["DHMT"].dropna().astype(str).unique().tolist())
    all_regions = [r for r in all_regions if r != "--"]
    completed = ['Boteti', 'Chobe', 'Ghanzi', 'Greater Francistown',
                'Greater Gaborone', 'Greater Phikwe', 'Kgalagadi North',
                'Kgalagadi South', 'Kgatleng', 'Kweneng', 'Greater Lobatse', 'Ngami']
    all_regions = sorted(fac["DHMT"].dropna().astype(str).unique().tolist())
    all_regions = [r for r in all_regions if r != "--" and r not in completed]
    all_regions = ["North East", "Southern", "Tutume"]
    print(f"Running {len(all_regions)} regions with max_workers={MAX_WORKERS}")

    cms_results  = []
    cms_failures = []

    existing_partial = OUT_DIR / "cms_results_partial_two.parquet"
    if existing_partial.exists():
        print(f"Found existing partial results at {existing_partial}, loading...")
        cms_results = [pd.read_parquet(existing_partial)]
    else:
        cms_results = []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_region, r): r for r in all_regions}
        for future in as_completed(futures):
            region = futures[future]
            results, error = future.result()
            if error:
                cms_failures.append({"region": region, "error": error})
            else:
                cms_results.extend(results)
            # incremental checkpoint after every completed region
            if cms_results:
                pd.concat(cms_results, ignore_index=True).to_parquet(
                    OUT_DIR / "cms_results_partial_two.parquet", index=False)

    # Final save
    results_df  = pd.concat(cms_results,  ignore_index=True) if cms_results  else pd.DataFrame()
    failures_df = pd.DataFrame(cms_failures)

    results_df.to_parquet( OUT_DIR / "cms_results_two.parquet",  index=False)
    failures_df.to_csv(    OUT_DIR / "cms_failures_two.csv",     index=False)

    print(f"\nDone. {len(results_df)} rows, {len(failures_df)} failures.")
    print(f"Results saved to {OUT_DIR}/")
