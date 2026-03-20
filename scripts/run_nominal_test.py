#!/usr/bin/env python3
import os
import sys
import json
import pandas as pd
import numpy as np
from scipy import stats

# Paths (match notebook)
POP_FACILITIES_CSV = 'gaborone_test/gaborone_population_nearest_facilities_osrm.csv'
AGE_BREAKDOWN = 'census_datacleaning/botswana_population_age_breakdown.csv'
MU_PATHS = ['gaborone_test/data/offline_calibration/mu_by_age_class.csv', 'data/offline_calibration/mu_by_age_class.csv']
OD_PATHS = ['gaborone_test/data/offline_calibration/overdispersion.json', 'data/offline_calibration/overdispersion.json']

for p in [POP_FACILITIES_CSV, AGE_BREAKDOWN]:
    if not os.path.exists(p):
        print(f'ERROR: required file not found: {p}', file=sys.stderr)
        sys.exit(2)

print('Loading population/facility mapping...')
pop_fac = pd.read_csv(POP_FACILITIES_CSV)

# Normalize population
if 'total_population' in pop_fac.columns:
    pop_fac['total_population'] = pop_fac['total_population'].astype(str).str.replace(',','').fillna('0').astype(int)
else:
    pop_cols = [c for c in pop_fac.columns if 'pop' in c.lower() or 'population' in c.lower()]
    if pop_cols:
        pop_fac['total_population'] = pop_fac[pop_cols[0]].astype(str).str.replace(',','').fillna('0').astype(int)
    else:
        pop_fac['total_population'] = 0

# Determine nearest name and osrm columns
nearest_name_cols = [c for c in pop_fac.columns if c.startswith('nearest_') and c.endswith('_name')]
osrm_dist_cols = [c for c in pop_fac.columns if c.startswith('osrm_dist_km_')]

import numpy as np

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

# Load age breakdown
age_df = pd.read_csv(AGE_BREAKDOWN)
gaborone_age = age_df[age_df['DistrictName'].str.lower() == 'gaborone']
if gaborone_age.empty:
    age_dist = age_df.groupby('AgeGroup')['Population'].sum()
else:
    age_dist = gaborone_age.groupby('AgeGroup')['Population'].sum()
age_props = (age_dist / age_dist.sum()).to_dict()

# Expand tract populations into age shares
records = []
for _, r in pop_fac.iterrows():
    pop = int(r.get('total_population',0))
    fac = r.get('facility_name_assigned')
    if pd.isna(fac):
        continue
    for agegroup, prop in age_props.items():
        records.append({'facility_name': fac, 'agegroup': agegroup, 'Population': pop * prop})
facility_age_df = pd.DataFrame.from_records(records)

# Load mu_by_age_class
mu_by_age_class = None
for p in MU_PATHS:
    if os.path.exists(p):
        mu_by_age_class = pd.read_csv(p)
        break
if mu_by_age_class is None:
    print('ERROR: mu_by_age_class.csv not found; run GLM exporter', file=sys.stderr)
    sys.exit(2)

mu_pivot = mu_by_age_class.pivot(index='agegroup', columns='Class', values='mu')

# Compute demand_by_facility
print('Computing demand_by_facility...')
demand_records = []
for fac, g in facility_age_df.groupby('facility_name'):
    row = {'facility_name': fac}
    for cls in mu_pivot.columns:
        vals = (g.set_index('agegroup')['Population'] * mu_pivot[cls]).fillna(0)
        row[cls] = vals.sum()
    demand_records.append(row)
demand_by_facility = pd.DataFrame.from_records(demand_records)
demand_by_facility = demand_by_facility.sort_values('facility_name').reset_index(drop=True)

# D_nominal dict
D_nominal = {}
drug_classes = [c for c in demand_by_facility.columns if c!='facility_name']
for _, row in demand_by_facility.iterrows():
    fname = row['facility_name']
    D_nominal[fname] = {drug: float(row[drug]) for drug in drug_classes}

# Load overdispersion
alpha_map = {}
for p in OD_PATHS:
    if os.path.exists(p):
        with open(p) as jf:
            alpha_map = json.load(jf)
        break

DEMAND_CV = 0.3
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

print(f'Facilities: {len(demand_by_facility)}, drug classes: {len(drug_classes)}')

# Helpers for sampling and evaluation

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
            sigma_val = float(sigma_map.get(fac, {}).get(drug, max(0.0, 0.3 * mu)))
            var = sigma_val * sigma_val
            r, p = mu_var_to_nbinom(mu, var)
            if r is not None:
                seed = int(rng.integers(0, 2**31 - 1))
                try:
                    draw = int(stats.nbinom(n=r, p=p).rvs(random_state=seed))
                except Exception:
                    draw = int(rng.negative_binomial(int(max(1, round(r))), p))
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


def run_nominal_sim(demand_by_facility, sigma_map, initial_inventory=None, iterations=200, seed=0, inventory_multiplier=1.0):
    rng = np.random.default_rng(seed)
    if initial_inventory is None:
        initial_inventory = build_initial_inventory_from_mu(demand_by_facility, multiplier=inventory_multiplier)
    results = []
    for it in range(iterations):
        demands = sample_demands(demand_by_facility, sigma_map, rng)
        unmet_map, total_unmet = evaluate_local_policy(initial_inventory, demands)
        # compute total realized demand across all facilities and drugs for this draw
        drug_cols = [c for c in demands.columns if c != 'facility_name']
        total_demand = int(demands[drug_cols].sum().sum())
        pct_unmet = float(total_unmet) / float(total_demand) * 100.0 if total_demand > 0 else 0.0
        results.append({'iteration': it, 'total_unmet': total_unmet, 'total_demand': total_demand, 'pct_unmet': pct_unmet})
    return pd.DataFrame(results)

# Run quick test
print('Running nominal simulation (200 iterations)...')
res = run_nominal_sim(demand_by_facility, sigma, iterations=200, seed=42, inventory_multiplier=1.0)
print('Total unmet (units):')
print(res['total_unmet'].describe())
print('\nPercent unmet (% of realized demand):')
print(res['pct_unmet'].describe())

print('\nSample demand_by_facility (head):')
print(demand_by_facility.head().to_string(index=False))

sys.exit(0)
