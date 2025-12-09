# build_matrix_allpairs.py
import argparse, time
import pandas as pd
import requests

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield i, lst[i:i+n]

def make_id(df: pd.DataFrame) -> pd.Series:
    a = df.get("New Facility Code")
    b = df.get("Old Facility Code")
    out = a.fillna(b)
    out = out.where(out.notna(), df.reset_index().index.astype(str))
    return out.astype(str)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--osrm", default="http://localhost:5001")
    ap.add_argument("--chunk", type=int, default=50)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="edges_allpairs.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.csv).dropna(subset=["Latitude","Longitude"]).copy()
    if args.limit > 0:
        df = df.head(args.limit).copy()

    df["node_id"] = make_id(df)
    df["label"] = df["Facility Name"].astype(str)
    df["coord"] = df.apply(lambda r: f'{r["Longitude"]},{r["Latitude"]}', axis=1)

    all_coords = df["coord"].tolist()
    n_total = len(all_coords)
    print(f"Total nodes: {n_total}")

    base_url = f'{args.osrm}/table/v1/driving/'

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("source_id,source_name,dest_id,dest_name,distance_m,duration_s\n")

    start_time = time.time()

    # break destinations into chunks; sources are always full list
    for j, (offset, dst_chunk) in enumerate(chunks(df, args.chunk), 1):
        dst_coords = dst_chunk["coord"].tolist()
        coords = ";".join(all_coords + dst_coords)

        sources = ";".join(map(str, range(n_total)))
        destinations = ";".join(map(str, range(n_total, n_total + len(dst_coords))))
        params = {
            "sources": sources,
            "destinations": destinations,
            "annotations": "duration,distance",
        }

        url = base_url + coords
        try:
            r = requests.get(url, params=params, timeout=300)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[chunk {j}] request failed at dest offset {offset}: {e}")
            continue

        if data.get("code") != "Ok":
            print(f"[chunk {j}] OSRM error: {data}")
            continue

        dists = data.get("distances")
        durs  = data.get("durations")
        if not dists or not durs:
            print(f"[chunk {j}] missing data")
            continue

        with open(args.out, "a", encoding="utf-8") as f:
            for si, (s_id, s_name) in enumerate(zip(df["node_id"], df["label"])):
                for di, (d_id, d_name) in enumerate(zip(dst_chunk["node_id"], dst_chunk["label"])):
                    dist = dists[si][di]
                    dur  = durs[si][di]
                    if dist is None or dur is None:
                        continue
                    f.write(f"{s_id},{s_name},{d_id},{d_name},{dist},{dur}\n")

        if j % 5 == 0:
            elapsed = time.time() - start_time
            print(f"[{j} chunks] processed {offset + len(dst_chunk)}/{len(df)} destinations in {elapsed:.1f}s")

    print(f"done. wrote {args.out}")

if __name__ == "__main__":
    main()

