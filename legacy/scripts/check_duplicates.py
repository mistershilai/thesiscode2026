import pandas as pd

pd.set_option('display.max_rows', 200)

path = "census_population_2022.csv"

def main():
    df = pd.read_csv(path)
    print("shape:", df.shape)
    print("columns:", list(df.columns))

    # normalize column names (strip)
    df.columns = [c.strip() for c in df.columns]

    # Exact full-row duplicates
    full_dup_mask = df.duplicated(keep=False)
    full_dup_count = full_dup_mask.sum()
    full_dup_groups = df[full_dup_mask].groupby(list(df.columns)).size().sort_values(ascending=False)
    num_full_dup_groups = (full_dup_groups > 1).sum()

    print('\nExact duplicate rows (total rows that are part of duplicates):', full_dup_count)
    print('Number of full-row duplicate groups (unique rows with count>1):', num_full_dup_groups)
    print('\nTop full-row duplicate groups (count > 1):')
    print(full_dup_groups[full_dup_groups > 1].head(20))

    if full_dup_count:
        dups = df[full_dup_mask].copy()
        dups['__orig_index'] = dups.index
        print('\nSample duplicated rows (first 40):')
        print(dups.sort_values(list(df.columns)).head(40).to_string(index=False))
    else:
        print('\nNo exact full-row duplicates found.')

    # Duplicates by subset: City/Town/Village + Total Population
    subset_cols = None
    if "City/Town/Village" in df.columns and "Total Population" in df.columns:
        subset_cols = ["City/Town/Village", "Total Population"]
    elif "city/town/village" in [c.lower() for c in df.columns] and "total population" in [c.lower() for c in df.columns]:
        cols_lower = {c.lower(): c for c in df.columns}
        subset_cols = [cols_lower['city/town/village'], cols_lower['total population']]

    if subset_cols:
        subset_dup_mask = df.duplicated(subset=subset_cols, keep=False)
        subset_dup_count = subset_dup_mask.sum()
        subset_groups = df[subset_dup_mask].groupby(subset_cols).size().sort_values(ascending=False)
        print(f"\nRows with duplicated {subset_cols} (total rows part of such duplicates):", subset_dup_count)
        print(f"Number of (City,Population) groups appearing >1 time:", (subset_groups>1).sum())
        print('\nTop (City,Population) duplicate groups:')
        print(subset_groups[subset_groups>1].head(20))
        if subset_dup_count:
            print('\nSample rows sharing the same (City,Population):')
            print(df[subset_dup_mask].sort_values(subset_cols).head(40).to_string(index=False))
    else:
        print('\nCould not find City/Town/Village and Total Population columns to check subset duplicates.')

if __name__ == '__main__':
    main()
