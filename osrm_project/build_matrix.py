# build_matrix.py
import argparse, math, time
import pandas as pd
import requests

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield i, lst[i:i+n]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="facilities_with_warehouses.csv")
    ap.add_argument("--osrm", default="http://localhost:5001", help="OSRM base URL")
    ap.add_argument("--chunk", type=int, default=50, help="destinations per request")
    ap.add_argument("--limit", type=int, default=0, help="limit number of destinations (0 = all)")
    ap.add_argument("--out", default="edges_long.csv", help="output CSV (long form)")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=["Latitude", "Longitude"]).copy()

    # split sources (warehouses) vs destinations (facilities)
    src = df[df["Is_Warehouse"] == True].copy()
    dst = df[df["Is_Warehouse"] == False].copy()

    if args.limit > 0:
        dst = dst.head(args.limit).copy()

    # robust IDs: prefer New Facility Code, then Old Facility Code, then fallback to row index
    def make_id(s: pd.DataFrame) -> pd.Series:
        a = s.get("New Facility Code")
        b = s.get("Old Facility Code")
        out = a.fillna(b)
        out = out.where(out.notna(), s.reset_index().index.astype(str))
        return out.astype(str)

    src["node_id"] = make_id(src)
    dst["node_id"] = make_id(dst)

    src["label"] = src["Facility Name"].astype(str)
    dst["label"] = dst["Facility Name"].astype(str)

    # coords as lon,lat strings
    def fmt(r): 
        return f'{r["Longitude"]},{r["Latitude"]}'
    src_coords = src.apply(fmt, axis=1).tolist()

    # write header
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("source_id,source_name,dest_id,dest_name,distance_m,duration_s\n")

    n_src = len(src_coords)
    base_url = f'{args.osrm}/table/v1/driving/'

    print(f"sources: {len(src)}   destinations: {len(dst)}   chunk: {args.chunk}")
    start_time = time.time()

    for j, (offset, dst_chunk) in enumerate(chunks(dst, args.chunk), 1):
        dst_coords = dst_chunk.apply(fmt, axis=1).tolist()
        coords = ";".join(src_coords + dst_coords)

        sources = ";".join(map(str, range(n_src)))
        destinations = ";".join(map(str, range(n_src, n_src + len(dst_coords))))
        params = {
            "sources": sources,
            "destinations": destinations,
            "annotations": "duration,distance",
        }

        url = base_url + coords
        try:
            r = requests.get(url, params=params, timeout=120)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[chunk {j}] request failed at dest offset {offset}: {e}")
            continue

        if data.get("code") != "Ok":
            print(f"[chunk {j}] OSRM error at dest offset {offset}: {data}")
            continue

        dists = data.get("distances")
        durs  = data.get("durations")
        if dists is None or durs is None:
            print(f"[chunk {j}] missing distances/durations at dest offset {offset}")
            continue

        # write long-form rows
        with open(args.out, "a", encoding="utf-8") as f:
            for si, (s_id, s_name) in enumerate(zip(src["node_id"], src["label"])):
                for di, (d_id, d_name) in enumerate(zip(dst_chunk["node_id"], dst_chunk["label"])):
                    dist = dists[si][di]
                    dur  = durs[si][di]
                    if dist is None or dur is None:
                        continue
                    f.write(f"{s_id},{s_name},{d_id},{d_name},{dist},{dur}\n")

        if j % 5 == 0:
            elapsed = time.time() - start_time
            print(f"[{j} chunks] processed {offset + len(dst_chunk)}/{len(dst)} destinations in {elapsed:.1f}s")

    print(f"done. wrote {args.out}")

if __name__ == "__main__":
    main()

