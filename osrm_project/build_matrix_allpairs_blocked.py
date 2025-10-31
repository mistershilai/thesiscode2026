# build_matrix_allpairs_blocked.py
import argparse, time
import pandas as pd
import requests

def chunks(df, n):
    for i in range(0, len(df), n):
        yield i, df.iloc[i:i+n]

def make_id(df):
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

    print(f"Total facilities: {len(df)}")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("source_id,source_name,dest_id,dest_name,distance_m,duration_s\n")

    base_url = f"{args.osrm}/table/v1/driving/"
    start_time = time.time()

    # nested block loops: process 50×50 submatrices
    for i, (i0, src_block) in enumerate(chunks(df, args.chunk)):
        for j, (j0, dst_block) in enumerate(chunks(df, args.chunk)):
            coords = ";".join(pd.concat([src_block, dst_block])["coord"].tolist())
            sources = ";".join(map(str, range(len(src_block))))
            destinations = ";".join(map(str, range(len(src_block), len(src_block) + len(dst_block))))
            params = {"sources": sources, "destinations": destinations, "annotations": "duration,distance"}
            url = base_url + coords
            try:
                r = requests.get(url, params=params, timeout=300)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"[block {i},{j}] request failed: {e}")
                continue
            if data.get("code") != "Ok":
                print(f"[block {i},{j}] OSRM error: {data}")
                continue
            dists = data.get("distances")
            durs = data.get("durations")
            if not dists or not durs:
                print(f"[block {i},{j}] missing data")
                continue

            with open(args.out, "a", encoding="utf-8") as f:
                for si, (s_id, s_name) in enumerate(zip(src_block["node_id"], src_block["label"])):
                    for di, (d_id, d_name) in enumerate(zip(dst_block["node_id"], dst_block["label"])):
                        dist = dists[si][di]
                        dur = durs[si][di]
                        if dist is None or dur is None:
                            continue
                        f.write(f"{s_id},{s_name},{d_id},{d_name},{dist},{dur}\n")

            if (j + 1) % 5 == 0:
                elapsed = time.time() - start_time
                print(f"[rowblock {i}] processed {j+1} dest blocks in {elapsed:.1f}s")

    print("done. wrote", args.out)

if __name__ == "__main__":
    main()
