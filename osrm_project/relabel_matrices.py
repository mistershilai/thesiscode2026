# relabel_matrices.py
import pandas as pd

# loading lookup table
names = pd.read_csv("facility_id_lookup.csv")  # from earlier pivot step
name_map = names.set_index("source_id")["source_name"].to_dict()

# reloading distance and duration matrices
dist = pd.read_csv("distance_matrix.csv", index_col=0)
dur  = pd.read_csv("duration_matrix.csv", index_col=0)

# replacing row/column IDs with readable names
dist.index  = dist.index.map(name_map)
dist.columns = dist.columns.map(name_map)
dur.index   = dur.index.map(name_map)
dur.columns  = dur.columns.map(name_map)

# writing labeled versions
dist.to_csv("distance_matrix_named.csv")
dur.to_csv("duration_matrix_named.csv")
print("wrote distance_matrix_named.csv and duration_matrix_named.csv")
