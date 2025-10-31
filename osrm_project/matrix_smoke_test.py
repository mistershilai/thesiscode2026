# matrix_smoke_test.py
import pandas as pd
import requests

CSV = "facilities_with_warehouses.csv"
OSRM = "http://localhost:5001"

# load and drop rows missing coords
df = pd.read_csv(CSV)
df = df.dropna(subset=["Latitude", "Longitude"])

# split sources (warehouses) and destinations (facilities)
src = df[df["Is_Warehouse"] == True].copy()
dst = df[df["Is_Warehouse"] == False].copy()

# take a tiny subset to see the structure (2 x 5)
src_small = src.head(2).reset_index(drop=True)
dst_small = dst.head(5).reset_index(drop=True)

def fmt_coord(row):
    # OSRM expects "lon,lat"
    return f'{row["Longitude"]},{row["Latitude"]}'

coords = [fmt_coord(r) for _, r in pd.concat([src_small, dst_small]).iterrows()]
n_src = len(src_small)  # first indices are sources
sources = ";".join(map(str, range(n_src)))
destinations = ";".join(map(str, range(n_src, n_src + len(dst_small))))

# build the /table request
url = f'{OSRM}/table/v1/driving/' + ";".join(coords)
# keeping everything above the same 

params = {
    "sources": sources,
    "destinations": destinations,
    "annotations": "duration,distance",  
}

resp = requests.get(url, params=params, timeout=60)
print("HTTP:", resp.status_code)
data = resp.json()
if data.get("code") != "Ok":
    print("OSRM error:", data)
    raise SystemExit(1)

# safely pulling arrays (distance may be missing if OSRM can’t compute it)
durations_raw = data.get("durations")
distances_raw = data.get("distances")

# building labeled dfs
if distances_raw is not None:
    dist = pd.DataFrame(distances_raw,
                        index=src_small["Facility Name"].tolist(),
                        columns=dst_small["Facility Name"].tolist())
    print("\nDistances (meters):")
    print(dist.round(1))
    dist.to_csv("distances_smoke_test.csv")

if durations_raw is not None:
    dur = pd.DataFrame(durations_raw,
                       index=src_small["Facility Name"].tolist(),
                       columns=dst_small["Facility Name"].tolist())
    print("\nDurations (seconds):")
    print(dur.round(1))
    dur.to_csv("durations_smoke_test.csv")

