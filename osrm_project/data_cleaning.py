import pandas as pd

dur = pd.read_csv("duration_matrix_upperbound_labeled.csv", index_col=0)
dist = pd.read_csv("distance_matrix_named.csv", index_col=0)

print("Duration matrix:", dur.shape)
print("Distance matrix:", dist.shape)

fac_with_missing = [f for f in dur.index if "(--)" in f]
print(f"Facilities with missing category: {len(fac_with_missing)}")
for name in fac_with_missing:
    print(name)

import pandas as pd

# load your labeled matrices
dur = pd.read_csv("duration_matrix_upperbound_labeled.csv", index_col=0)
dist = pd.read_csv("distance_matrix_named.csv", index_col=0)

# replace the old labels with corrected ones
dur.index = dur.index.str.replace("Mahalapye District Hospital (--)", "Mahalapye District Hospital (Primary Hospital)")
dur.columns = dur.columns.str.replace("Mahalapye District Hospital (--)", "Mahalapye District Hospital (Primary Hospital)")

for name in ["SSKB (Mogoditshane BDF) Clinic", "Ntshe Clinic", "Prisons Clinic"]:
    old = f"{name} (--)"
    new = f"{name} (Clinic)"
    dur.index = dur.index.str.replace(old, new)
    dur.columns = dur.columns.str.replace(old, new)
    dist.index = dist.index.str.replace(old, new)
    dist.columns = dist.columns.str.replace(old, new)

# also update Mahalapye in distance matrix
dist.index = dist.index.str.replace("Mahalapye District Hospital (--)", "Mahalapye District Hospital (Primary Hospital)")
dist.columns = dist.columns.str.replace("Mahalapye District Hospital (--)", "Mahalapye District Hospital (Primary Hospital)")

# save back
dur.to_csv("duration_matrix_upperbound_labeled.csv")
dist.to_csv("distance_matrix_named.csv")