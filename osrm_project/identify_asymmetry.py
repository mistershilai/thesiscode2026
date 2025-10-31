import pandas as pd
import numpy as np

# load, clean
dist = pd.read_csv("distance_matrix_labeled.csv", index_col=0)
dist = dist.apply(pd.to_numeric, errors="coerce")

# drop duplicate rows, align
dist = dist.loc[~dist.index.duplicated(keep="first")]
dist = dist.loc[:, ~dist.columns.duplicated(keep="first")]
common = dist.index.intersection(dist.columns)
dist = dist.loc[common, common]

# removing route artifacts
dist = dist.mask(dist > 1e5)

# computing route asymmetries
asym = (dist - dist.T).abs().fillna(0)

# converting to long form with forward/reverse distances
asym_pairs = (
    asym.stack()
    .reset_index()
    .rename(columns={"level_0": "From", "level_1": "To", 0: "Asymmetry"})
)

# dropping self-pairs
asym_pairs = asym_pairs[asym_pairs["From"] != asym_pairs["To"]]

# keeping only one direction per unordered pair to avoid duplicates
asym_pairs = asym_pairs[
    asym_pairs.apply(lambda x: x["From"] < x["To"], axis=1)
]

# adding forward and reverse distances
asym_pairs["Distance_Forward"] = [
    dist.loc[f, t] for f, t in zip(asym_pairs["From"], asym_pairs["To"])
]
asym_pairs["Distance_Reverse"] = [
    dist.loc[t, f] for f, t in zip(asym_pairs["From"], asym_pairs["To"])
]

# dropping NaNs and sorting
asym_pairs = asym_pairs.dropna().sort_values("Asymmetry", ascending=False)

# results to be displayed
top = asym_pairs.iloc[0]
print(f"Largest asymmetry: {top['Asymmetry']:.2f} km between {top['From']} and {top['To']}")
print(f"{top['From']} → {top['To']}: {top['Distance_Forward']:.2f} km")
print(f"{top['To']} → {top['From']}: {top['Distance_Reverse']:.2f} km")

print("\nTop 20 asymmetric facility pairs:")
print(
    asym_pairs.head(20)
    .loc[:, ["From", "To", "Asymmetry", "Distance_Forward", "Distance_Reverse"]]
    .to_string(index=False)
)

# save and export
asym_pairs.to_csv("asymmetry_report_with_distances.csv", index=False)
