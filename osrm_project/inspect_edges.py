import pandas as pd

df = pd.read_csv("edges_allpairs.csv")
print("Rows:", len(df))
print("Columns:", list(df.columns))
print(df.head(5))
