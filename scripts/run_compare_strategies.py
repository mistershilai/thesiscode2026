#!/usr/bin/env python3
"""Run and compare Nominal, Static Robust (B), and ADR (C) strategies using in-repo data.
"""
import os
import json
import numpy as np
import pandas as pd
from scipy import stats

# Paths (match notebook)
POP_FACILITIES_CSV = 'gaborone_test/gaborone_population_nearest_facilities_osrm.csv'
AGE_BREAKDOWN = 'census_datacleaning/botswana_population_age_breakdown.csv'
MU_PATHS = ['gaborone_test/data/offline_calibration/mu_by_age_class.csv', 'data/offline_calibration/mu_by_age_class.csv']
OD_PATHS = ['gaborone_test/data/offline_calibration/overdispersion.json', 'data/offline_calibration/overdispersion.json']

DEMAND_CV = 0.3

# --- PREPARE ---
if not os.path.exists(POP_FACILITIES_CSV):
    raise FileNotFoundError(f'{POP_FACILITIES_CSV} not found; run spatial cells first')
if not os.path.exists(AGE_BREAKDOWN):
    raise FileNotFoundError(f'{AGE_BREAKDOWN} not found')

pop_fac = pd.read_csv(POP_FACILITIES_CSV)
# normalize population
if 'total_population' in pop_fac.columns:
    pop_fac['total_population'] = pop_fac['total_population'].astype(str).str.replace(',','').fillna('0').astype(int)
else:
    pop_cols = [c for c in pop_fac.columns if 'pop' in c.lower() or 'population' in c.lower()]
    if pop_cols:
        pop_fac['total_population'] = pop_fac[pop_cols[0]].astype(str).str.replace(',','').fillna('0').astype(int)
    else:
        pop_fac['total_population'] = 0

# facility assignment picks from existing nearest_* columns
nearest_name_cols = [c for c in pop_fac.columns if c.startswith('nearest_') and c.endswith('_name')]
osrm_dist_cols = [c for c in pop_fac.columns if c.startswith('osrm_dist_km_')]

def pick_nearest_fac(row):
    if osrm_dist_cols:
        best = None
        best_dist = None
        for col in osrm_dist_cols:
            d = row.get(col, np.nan)
            if pd.notna(d):
                subtype = col.replace('osrm_dist_km_','')
                name_col = f'nearest_{subtype}_name'
                name = row.get(name_col)
                if pd.notna(name) and str(name).strip() != '':
                    if best_dist is None or d < best_dist:
                        best = name
                        best_dist = d
        if best is not None:
            return best
    pref = ['nearest_Clinic_name','nearest_HealthPost_name','nearest_Hospital_name']
    for c in pref:
        if c in row and pd.notna(row[c]) and str(row[c]).strip() != '':
            return row[c]
    for c in nearest_name_cols:
        val = row.get(c)
        if pd.notna(val) and str(val).strip() != '':
            return val
    return None

pop_fac['facility_name_assigned'] = pop_fac.apply(pick_nearest_fac, axis=1)
pop_fac = pop_fac[pop_fac['facility_name_assigned'].notna()].copy()

age_df = pd.read_csv(AGE_BREAKDOWN)
gaborone_age = age_df[age_df['DistrictName'].str.lower() == 'gaborone']
if gaborone_age.empty:
    age_dist = age_df.groupby('AgeGroup')['Population'].sum()
else:
    age_dist = gaborone_age.groupby('AgeGroup')['Population'].sum()
age_props = (age_dist / age_dist.sum()).to_dict()

records = []
for _, r in pop_fac.iterrows():
    pop = int(r.get('total_population',0))
    fac = r.get('facility_name_assigned')
    if pd.isna(fac):
        continue
    for agegroup, prop in age_props.items():
        records.append({'facility_name': fac, 'agegroup': agegroup, 'Population': pop * prop})
facility_age_df = pd.DataFrame.from_records(records)

# load mu_by_age_class
mu_by_age_class = None
for p in MU_PATHS:
    if os.path.exists(p):
        mu_by_age_class = pd.read_csv(p)
        break
if mu_by_age_class is None:
    raise FileNotFoundError('mu_by_age_class.csv not found; run GLM exporter')

mu_pivot = mu_by_age_class.pivot(index='agegroup', columns='Class', values='mu')

# demand_by_facility
from collections import OrderedDict

demand_records = []
for fac, g in facility_age_df.groupby('facility_name'):
    row = {'facility_name': fac}
    for cls in mu_pivot.columns:
        vals = (g.set_index('agegroup')['Population'] * mu_pivot[cls]).fillna(0)
        row[cls] = vals.sum()
    demand_records.append(row)
demand_by_facility = pd.DataFrame.from_records(demand_records)
demand_by_facility = demand_by_facility.sort_values('facility_name').reset_index(drop=True)

D_nominal = OrderedDict()
drug_classes = [c for c in demand_by_facility.columns if c!='facility_name']
for _, row in demand_by_facility.iterrows():
    fname = row['facility_name']
    D_nominal[fname] = {drug: float(row[drug]) for drug in drug_classes}

alpha_map = {}
for p in OD_PATHS:
    if os.path.exists(p):
        with open(p) as jf:
            alpha_map = json.load(jf)
        break

sigma = {}
for fac in D_nominal:
    sigma[fac] = {}
    for drug in drug_classes:
        mu_val = D_nominal[fac].get(drug, 0.0)
        alpha = alpha_map.get(drug) if isinstance(alpha_map, dict) else None
        try:
            alpha = float(alpha) if alpha is not None else None
        except Exception:
            alpha = None
        if alpha is not None and mu_val >= 0:
            var = mu_val + alpha * (mu_val**2)
            sigma[fac][drug] = float(np.sqrt(max(var,0.0)))
        else:
            sigma[fac][drug] = float(DEMAND_CV * mu_val)

# --- simulation helpers ---

def mu_var_to_nbinom(mu, var):
    mu = float(mu)
    var = float(var)
    if var > mu + 1e-9:
        r = (mu * mu) / (var - mu)
        p = r / (r + mu)
        return float(r), float(p)
    return None, None


def sample_demands(demand_df, sigma_map, rng):
    samples = []
    drug_cols = [c for c in demand_df.columns if c != 'facility_name']
    for _, row in demand_df.iterrows():
        fac = row['facility_name']
        out = {'facility_name': fac}
        for drug in drug_cols:
            mu = float(row[drug])
            sigma_v = float(sigma_map.get(fac, {}).get(drug, max(0.0, 0.3 * mu)))
            var = sigma_v * sigma_v
            r, p = mu_var_to_nbinom(mu, var)
            if r is not None:
                seed = int(rng.integers(0, 2**31 - 1))
                draw = int(stats.nbinom(n=r, p=p).rvs(random_state=seed))
            else:
                draw = int(rng.poisson(mu))
            out[drug] = draw
        samples.append(out)
    return pd.DataFrame.from_records(samples)


def evaluate_local_policy(initial_inventory, demands_df):
    unmet = {}
    total_unmet = 0
    for _, row in demands_df.iterrows():
        fac = row['facility_name']
        unmet[fac] = {}
        for drug in [c for c in demands_df.columns if c != 'facility_name']:
            demand = int(row[drug])
            inv = int(initial_inventory.get(fac, {}).get(drug, 0))
            supplied = min(inv, demand)
            u = int(demand - supplied)
            unmet[fac][drug] = u
            total_unmet += u
    return unmet, total_unmet


def build_initial_inventory_from_mu(demand_df, multiplier=1.0):
    inv = {}
    drug_cols = [c for c in demand_df.columns if c != 'facility_name']
    for _, row in demand_df.iterrows():
        fac = row['facility_name']
        inv[fac] = {}
        for drug in drug_cols:
            inv[fac][drug] = int(round(float(row[drug]) * multiplier))
    return inv


def build_static_robust_inventory(demand_df, sigma_map, z=1.645, multiplier=1.0):
    inv = {}
    drug_cols = [c for c in demand_df.columns if c != 'facility_name']
    for _, row in demand_df.iterrows():
        fac = row['facility_name']
        inv[fac] = {}
        for drug in drug_cols:
            mu = float(row[drug])
            sigma_v = float(sigma_map.get(fac, {}).get(drug, max(0.0, 0.3 * mu)))
            qty = int(np.ceil((mu + z * sigma_v) * multiplier))
            inv[fac][drug] = max(qty, 0)
    return inv

# ADR recourse
try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except Exception:
    CVXPY_AVAILABLE = False


def solve_recourse_one_draw(F_bar, demands_df):
    facilities = list(demands_df['facility_name'])
    drugs = [c for c in demands_df.columns if c != 'facility_name']
    unmet_map = {fac: {drug: 0 for drug in drugs} for fac in facilities}
    total_unmet = 0
    for drug in drugs:
        demand_list = [int(demands_df.loc[k, drug]) for k in range(len(facilities))]
        total_demand_drug = sum(demand_list)
        if total_demand_drug == 0:
            continue
        avail = [int(F_bar.get(fac, {}).get(drug, 0)) for fac in facilities]
        if CVXPY_AVAILABLE:
            try:
                n = len(facilities)
                S = cp.Variable((n, n), nonneg=True)
                constraints = []
                for i in range(n):
                    constraints.append(cp.sum(S[i, :]) <= avail[i])
                for j in range(n):
                    constraints.append(cp.sum(S[:, j]) <= demand_list[j])
                obj = cp.Maximize(cp.sum(S))
                prob = cp.Problem(obj, constraints)
                prob.solve(solver=cp.SCS, verbose=False)
                shipped = 0.0
                if S.value is not None:
                    shipped = float(cp.sum(cp.pos(S)).value)
                else:
                    shipped = 0.0
                unmet_drug = int(round(total_demand_drug - shipped))
                if S.value is not None:
                    col_fulfilled = np.sum(np.maximum(S.value, 0.0), axis=0)
                    for j, fac in enumerate(facilities):
                        unmet_map[fac][drug] = int(round(max(0, demand_list[j] - col_fulfilled[j])))
                else:
                    for j, fac in enumerate(facilities):
                        unmet_map[fac][drug] = int(round(demand_list[j] * (unmet_drug / max(1, total_demand_drug))))
                total_unmet += unmet_drug
                continue
            except Exception:
                pass
        # greedy fallback
        avail_copy = avail.copy()
        for j in range(len(facilities)):
            need = demand_list[j]
            i_local = j
            take = min(avail_copy[i_local], need)
            avail_copy[i_local] -= take
            need -= take
            if need == 0:
                unmet_map[facilities[j]][drug] = 0
                continue
            for i in range(len(facilities)):
                if i == i_local:
                    continue
                if need <= 0:
                    break
                take = min(avail_copy[i], need)
                avail_copy[i] -= take
                need -= take
            unmet_map[facilities[j]][drug] = int(need)
            total_unmet += int(need)
    return unmet_map, total_unmet


def run_nominal_sim(demand_by_facility, sigma_map, initial_inventory=None, iterations=200, seed=42, inventory_multiplier=1.0):
    rng = np.random.default_rng(seed)
    if initial_inventory is None:
        initial_inventory = build_initial_inventory_from_mu(demand_by_facility, multiplier=inventory_multiplier)
    results = []
    for it in range(iterations):
        demands = sample_demands(demand_by_facility, sigma_map, rng)
        unmet_map, total_unmet = evaluate_local_policy(initial_inventory, demands)
        demand_cols = [c for c in demands.columns if c != 'facility_name']
        total_demand = int(demands[demand_cols].to_numpy().sum())
        pct_unmet = (float(total_unmet) / total_demand * 100.0) if total_demand > 0 else 0.0
        results.append({'iteration': it, 'total_unmet': total_unmet, 'total_demand': total_demand, 'pct_unmet': pct_unmet})
    return pd.DataFrame(results)


def run_static_robust_sim(demand_by_facility, sigma_map, z=1.645, iterations=200, seed=42, inventory_multiplier=1.0):
    initial_inventory = build_static_robust_inventory(demand_by_facility, sigma_map, z=z, multiplier=inventory_multiplier)
    rng = np.random.default_rng(seed)
    results = []
    for it in range(iterations):
        demands = sample_demands(demand_by_facility, sigma_map, rng)
        unmet_map, total_unmet = evaluate_local_policy(initial_inventory, demands)
        demand_cols = [c for c in demands.columns if c != 'facility_name']
        total_demand = int(demands[demand_cols].to_numpy().sum())
        pct_unmet = (float(total_unmet) / total_demand * 100.0) if total_demand > 0 else 0.0
        results.append({'iteration': it, 'total_unmet': total_unmet, 'total_demand': total_demand, 'pct_unmet': pct_unmet})
    return pd.DataFrame(results)


def run_adjustable_robust_sim(demand_by_facility, sigma_map, F_bar=None, z=1.645, iterations=200, seed=42, inventory_multiplier=1.0):
    if F_bar is None:
        F_bar = build_static_robust_inventory(demand_by_facility, sigma_map, z=z, multiplier=inventory_multiplier)
    rng = np.random.default_rng(seed)
    results = []
    for it in range(iterations):
        demands = sample_demands(demand_by_facility, sigma_map, rng)
        unmet_map, total_unmet = solve_recourse_one_draw(F_bar, demands)
        demand_cols = [c for c in demands.columns if c != 'facility_name']
        total_demand = int(demands[demand_cols].to_numpy().sum())
        pct_unmet = (float(total_unmet) / total_demand * 100.0) if total_demand > 0 else 0.0
        results.append({'iteration': it, 'total_unmet': total_unmet, 'total_demand': total_demand, 'pct_unmet': pct_unmet})
    return pd.DataFrame(results)

# --- Run comparisons ---
print('Facilities:', len(demand_by_facility))
print('Drug classes:', len(drug_classes))

inv_nominal = build_initial_inventory_from_mu(demand_by_facility, multiplier=1.0)
res_a = run_nominal_sim(demand_by_facility, sigma, initial_inventory=inv_nominal, iterations=200, seed=42)
res_b = run_static_robust_sim(demand_by_facility, sigma, z=1.645, iterations=200, seed=42)
F_bar = build_static_robust_inventory(demand_by_facility, sigma, z=1.645, multiplier=1.0)
res_c = run_adjustable_robust_sim(demand_by_facility, sigma, F_bar=F_bar, iterations=200, seed=42)

print('\nNominal percent-unmet:')
print(res_a['pct_unmet'].describe())
print('\nStatic Robust percent-unmet:')
print(res_b['pct_unmet'].describe())
print('\nADR percent-unmet:')
print(res_c['pct_unmet'].describe())

# Save results for inspection
os.makedirs('scripts/output', exist_ok=True)
res_a.to_csv('scripts/output/res_nominal.csv', index=False)
res_b.to_csv('scripts/output/res_static.csv', index=False)
res_c.to_csv('scripts/output/res_adr.csv', index=False)
print('\nSaved results to scripts/output/')
