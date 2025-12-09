import pandas as pd

# loading both matrices
dist = pd.read_csv("distance_matrix_labeled.csv", index_col=0)
dur = pd.read_csv("duration_matrix_upperbound_labeled.csv", index_col=0)

# converting to numeric
dist = dist.apply(pd.to_numeric, errors="coerce")
dur = dur.apply(pd.to_numeric, errors="coerce")

# helper func for pairwise correction
def correct_pair(a, b, new_distance_m=None, new_duration_s=None):
    """correct distance/duration entries for facility pair (a,b) and its reverse."""
    if new_distance_m is not None:
        dist.loc[a, b] = new_distance_m
        dist.loc[b, a] = new_distance_m
    if new_duration_s is not None:
        dur.loc[a, b] = new_duration_s
        dur.loc[b, a] = new_duration_s
    print(f"✓ Corrected {a} ↔ {b}")

# manual corrections
# Moreomaoto and Phuduhudu
correct_pair(
    "Moreomaoto Health Post (Health Post)",
    "Phuduhudu Health Post (Health Post)",
    new_distance_m=36686.2,
    new_duration_s=2264.4  # about 70 km/h average
)

# corrected matrices saved
dist.to_csv("distance_matrix_labeled.csv")
dur.to_csv("duration_matrix_upperbound_labeled.csv")

print("\nAll corrections applied and saved to:")
print(" - distance_matrix_labeled.csv")
print(" - duration_matrix_upperbound_labeled.csv")
