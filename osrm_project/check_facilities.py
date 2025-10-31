import pandas as pd

path = "facilities_with_warehouses.csv"  # change if different
df = pd.read_csv(path)

print("Columns:", list(df.columns))
print("Rows:", len(df))
print("Nulls in Latitude/Longitude:", df['Latitude'].isna().sum(), df['Longitude'].isna().sum())
print("Warehouses:", (df['Is_Warehouse'] == True).sum())
print("Facilities:", (df['Is_Warehouse'] == False).sum())

# sanity check
print(df[['Facility Name','Latitude','Longitude','Is_Warehouse']].head(5))
