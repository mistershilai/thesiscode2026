#!/usr/bin/env python3
# run_geocode.py
# Runs the geocoding loop with a tqdm progress bar and applies compatibility monkeypatches.
import os
import sys
import time
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from tqdm import tqdm

# Compatibility monkeypatch for older tqdm expecting pandas internals
try:
    import pandas.core.common as pcc
    def _is_builtin_func(obj):
        import types as _types
        return isinstance(obj, (_types.BuiltinFunctionType, _types.BuiltinMethodType))
    pcc.is_builtin_func = _is_builtin_func
    pd.Series._is_builtin_func = staticmethod(_is_builtin_func)
    tqdm.pandas = lambda *a, **k: None
    print('Applied pandas/tqdm compatibility monkeypatch')
except Exception as e:
    print('Compatibility monkeypatch failed:', e)

# Load deduped census file
candidates = ['census_population_2022_deduped.csv', 'census_datacleaning/census_population_2022_deduped.csv']
src = next((p for p in candidates if os.path.exists(p)), None)
if src is None:
    print('Deduped census CSV not found; expected one of:', candidates)
    sys.exit(2)

print('Reading', src)
census = pd.read_csv(src)

# normalize columns
census.columns = census.columns.str.strip().str.lower().str.replace(' ', '_')

# attempt to use expected column names
if 'census_district' not in census.columns or 'city/town/village' not in census.columns:
    # tolerate alternate names
    if 'city_town_village' in census.columns:
        census['city/town/village'] = census['city_town_village']
    if 'census_district' not in census.columns and 'district' in census.columns:
        census['census_district'] = census['district']

# build unique towns
towns = census[[col for col in census.columns if col in ['census_district', 'city/town/village']]].drop_duplicates().copy()
# ensure columns exist
if 'census_district' not in towns.columns or 'city/town/village' not in towns.columns:
    print('Required columns not found in census file; columns available:', list(census.columns))
    sys.exit(3)

# build queries
towns['query'] = towns['city/town/village'].astype(str) + ', ' + towns['census_district'].astype(str) + ', Botswana'

geolocator = Nominatim(user_agent='botswana_census_geocoder')
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# iterate with tqdm and store results
locations = []
for q in tqdm(towns['query'], desc='geocoding', unit='loc'):
    try:
        loc = geocode(q, timeout=10)
        locations.append(loc)
    except Exception as e:
        print('ERROR for query', q, type(e).__name__, e)
        locations.append(None)

# attach results
towns['location'] = locations
towns['latitude'] = towns['location'].apply(lambda loc: loc.latitude if loc else None)
towns['longitude'] = towns['location'].apply(lambda loc: loc.longitude if loc else None)

out = 'census_villages_geocoded.csv'
towns.to_csv(out, index=False)
print('Wrote', out)
print('Done')
