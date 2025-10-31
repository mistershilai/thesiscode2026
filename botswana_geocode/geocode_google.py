import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

# load your Google API key securely from .env
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise SystemExit("Missing GOOGLE_API_KEY in .env file")

BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
df = pd.read_csv("../census_villages_geocoded.csv")

# only geocode rows missing coordinates from OSM
missing_rows = df[df["latitude"].isna()].copy()

for i, row in missing_rows.iterrows():
    query = f"{row['city/town/village']}, {row['census_district']}, Botswana"
    params = {"address": query, "key": API_KEY}
    try:
        r = requests.get(BASE_URL, params=params, timeout=10)
        data = r.json()
        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            df.at[i, "latitude"] = loc["lat"]
            df.at[i, "longitude"] = loc["lng"]
        else:
            df.at[i, "latitude"] = None
            df.at[i, "longitude"] = None
    except Exception as e:
        print(f"Error on row {i}: {e}")
    time.sleep(0.25)  # avoid throttling

df.to_csv("census_villages_geocoded_google.csv", index=False)
print("Done! Results saved as census_villages_geocoded_google.csv")
