# matrixanalysis.py
# summary analysis and visualization of labeled OSRM matrices

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from textwrap import wrap
from collections import Counter

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": 150
})


def deduplicate_labels(labels):
    """Ensure labels are unique by appending suffixes (1), (2), etc."""
    counts = Counter()
    new_labels = []
    for lbl in labels:
        counts[lbl] += 1
        if counts[lbl] > 1:
            new_labels.append(f"{lbl} ({counts[lbl]})")
        else:
            new_labels.append(lbl)
    return new_labels


def main():
    # loading data
    dist = pd.read_csv("distance_matrix_labeled.csv", index_col=0)
    dur = pd.read_csv("duration_matrix_upperbound_labeled.csv", index_col=0)
    fac = pd.read_csv("facilities_with_warehouses.csv")

    print(f"Loaded {dist.shape[0]}×{dist.shape[1]} matrices with {len(fac)} facilities.\n")

    # ensuring unique labels
    if dist.index.duplicated().any() or dist.columns.duplicated().any():
        print("Warning: Duplicate facility names found — disambiguating.")
        dist.index = deduplicate_labels(dist.index)
        dist.columns = deduplicate_labels(dist.columns)
        dur.index = dist.index
        dur.columns = dist.columns

    # converting to numeric arrays
    dist_np = dist.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    dur_np = dur.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)

    # computing asymmetries in route
    dist_asym_np = np.abs(dist_np - dist_np.T)
    dur_asym_np = np.abs(dur_np - dur_np.T)

    # replacing nans with 0
    dist_asym_np = np.nan_to_num(dist_asym_np, nan=0.0)
    dur_asym_np = np.nan_to_num(dur_asym_np, nan=0.0)

    # summary stats
    mean_dist_asym = np.mean(dist_asym_np)
    max_dist_asym = np.max(dist_asym_np)
    mean_dur_asym = np.mean(dur_asym_np)
    max_dur_asym = np.max(dur_asym_np)

    print(f"Mean distance asymmetry (m): {mean_dist_asym:,.2f}")
    print(f"Max distance asymmetry (m): {max_dist_asym:,.2f}")
    print(f"Mean duration asymmetry (s): {mean_dur_asym:,.2f}")
    print(f"Max duration asymmetry (s): {max_dur_asym:,.2f}\n")

    # facility type summaries
    type_counts = fac["Service Delivery Type"].value_counts().sort_values(ascending=False)
    print("=== Facility Type Counts ===")
    print(type_counts, "\n")

    # subtype highlights
    def count_matches(substring):
        return fac["Service Delivery Type"].str.contains(substring, case=False, na=False).sum()

    highlights = {
        "Warehouses": count_matches("warehouse"),
        "Primary Hospitals": count_matches("primary"),
        "Referral Hospitals": count_matches("referral"),
        "Clinics": count_matches("(clinic)"),
        "Health Posts": count_matches("health post"),
        "Clinics with Maternity": count_matches("maternity"),
        "District Hospitals": count_matches("district"),
    }

    for k, v in highlights.items():
        print(f"{k}: {v}")
    print()

    # saving numeric summaries
    summary = {
        "mean_dist_asym_m": mean_dist_asym,
        "max_dist_asym_m": max_dist_asym,
        "mean_dur_asym_s": mean_dur_asym,
        "max_dur_asym_s": max_dur_asym,
        "n_facilities": len(fac),
    }
    pd.DataFrame([summary]).to_csv("matrix_summary.csv", index=False)

    # visualize facility type counts
    plt.figure(figsize=(8, 4))
    sns.barplot(y=type_counts.index, x=type_counts.values, palette="viridis")
    plt.title("Number of Facilities by Service Delivery Type")
    plt.xlabel("Count")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig("facility_type_counts.png")
    plt.close()

    # visualize distribution of pairwise asymmetry
    plt.figure(figsize=(7, 4))
    flat_asym = dist_asym_np[np.triu_indices_from(dist_asym_np, k=1)]
    sns.histplot(flat_asym / 1000, bins=50, color="coral", kde=True)
    plt.xlim(0, 15)
    plt.xlabel("Asymmetry (km)")
    plt.ylabel("Number of facility pairs")
    plt.title("Distribution of Pairwise Distance Asymmetries")
    plt.tight_layout()
    plt.savefig("asymmetry_distribution.png")
    plt.close()

    # visualize implied speeds
    valid = (dist_np > 0) & (dur_np > 0)
    speed_mps = (dist_np[valid] / dur_np[valid]).flatten()
    plt.figure(figsize=(7, 4))
    sns.histplot(speed_mps * 3.6, bins=40, color="seagreen")  # convert m/s → km/h
    plt.xlabel("Implied Travel Speed (km/h)")
    plt.ylabel("Number of facility pairs")
    plt.title("Distribution of Implied Travel Speeds (1.2× duration scaling)")
    plt.tight_layout()
    plt.savefig("speed_distribution.png")
    plt.close()

    # mean +/- sd speed
    mean_speed = np.nanmean(speed_mps * 3.6)
    sd_speed = np.nanstd(speed_mps * 3.6)
    print(f"Mean implied speed: {mean_speed:.1f} km/h (SD = {sd_speed:.1f})")

    print("\n✓ Saved outputs:")
    print("  - matrix_summary.csv")
    print("  - facility_type_counts.png")
    print("  - asymmetry_distribution.png")
    print("  - speed_distribution.png")

if __name__ == "__main__":
    main()
