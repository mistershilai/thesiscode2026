# pivot_matrices.py
import pandas as pd

df = pd.read_csv("edges_allpairs.csv")  

# drop duplicates: keep the smallest distance for each (source_id, dest_id)
df = df.sort_values("distance_m").drop_duplicates(subset=["source_id", "dest_id"], keep="first")

# build wide matrices using numeric IDs
dist = df.pivot(index="source_id", columns="dest_id", values="distance_m")
dur  = df.pivot(index="source_id", columns="dest_id", values="duration_s")
names = df[["source_id", "source_name"]].drop_duplicates().set_index("source_id")
names.to_csv("facility_id_lookup.csv")

dist.to_csv("distance_matrix.csv")
dur.to_csv("duration_matrix.csv")
print("Wrote distance_matrix.csv and duration_matrix.csv")

print("Shapes:")
print("  Distance:", dist.shape)
print("  Duration:", dur.shape)

