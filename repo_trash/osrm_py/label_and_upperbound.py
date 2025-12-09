# label_and_upperbound.py
# postprocessing for duration and distance matrices

import pandas as pd

def main():
    # loading facility metadata
    fac = pd.read_csv("facilities_with_warehouses.csv")
    category_map = fac.set_index("Facility Name")["Service Delivery Type"].to_dict()

    # loading base matrices
    dur = pd.read_csv("duration_matrix_named.csv", index_col=0)
    dist = pd.read_csv("distance_matrix_named.csv", index_col=0)

    # applying upper bound to duration
    dur_upper = dur * 1.2

    # adding facility type labels
    dur_upper.index = [f"{name} ({category_map.get(name, '--')})" for name in dur_upper.index]
    dur_upper.columns = [f"{name} ({category_map.get(name, '--')})" for name in dur_upper.columns]
    dist.index = [f"{name} ({category_map.get(name, '--')})" for name in dist.index]
    dist.columns = [f"{name} ({category_map.get(name, '--')})" for name in dist.columns]

    # saving final outputs
    dur_upper.to_csv("duration_matrix_upperbound_labeled.csv")
    dist.to_csv("distance_matrix_labeled.csv")

    print("  - duration_matrix_upperbound_labeled.csv")
    print("  - distance_matrix_labeled.csv")

if __name__ == "__main__":
    main()
