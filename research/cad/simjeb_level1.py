"""Level 1 on every SimJEB bracket: cadmesh against the dataset's own numbers (volume, area, genus, vertex/face counts).
Usage: python3 research/cad/simjeb_level1.py <ext-data/simjeb> <out.jsonl> [jobs]"""
import csv, json, os, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import cadmesh as CM


def one(args):
    root, i = args
    p = os.path.join(root, "obj", f"{i}.obj")
    t = time.time()
    try:
        v, f, u = CM.read(p)
        rep, vol = CM.analyse(v, f, u)
    except Exception as e:
        return {"id": i, "error": f"{type(e).__name__}: {e}"}
    return {"id": i, "sec": round(time.time() - t, 2), "topology": rep["topology"], "volume": float(vol),
            "volume_proved": rep["volume"]["proved"], "area": [rep["surface_area"]["lo"], rep["surface_area"]["hi"]],
            "self_intersections": rep["self_intersection"]["pairs_found"]}


if __name__ == "__main__":
    root, out = sys.argv[1], sys.argv[2]
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    meta = {r["id"]: r for r in csv.DictReader(open(os.path.join(root, "all_bracket_metadata.tab")))}
    ids = sorted(meta, key=int)
    with Pool(jobs) as pool, open(out, "w") as f:
        for r in pool.imap_unordered(one, [(root, i) for i in ids]):
            m = meta[r["id"]]
            if "error" not in r:
                r["meta"] = {k: float(m[k]) for k in ("volume", "surface_area", "genus", "num_vertices", "num_faces")}
            f.write(json.dumps(r) + "\n")
            f.flush()
