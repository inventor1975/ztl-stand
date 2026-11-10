"""Level 2a on every SimJEB bracket deck: the proved lower bound on the compliance (and the work-conjugate load-point
displacement / rotation) for the four load cases. Skips the brackets level 1 flagged (self-intersecting surface,
more than one body — a body not tied to a support makes the stiffness singular).
Usage: python3 research/cad/simjeb_level2a.py <dir with N.fem> <level1 results jsonl> <out.jsonl> [jobs]"""
import json, math, os, sys, time, traceback
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import tetfea as TF


def one(args):
    path, i = args
    t0 = time.time()
    try:
        deck = TF.read_deck(path)
        out = {"id": i, "cases": []}
        for r in TF.solve_cases(deck, sorted(deck["subcases"]), tol=1e-4, log=lambda s: None):
            sc = r["subcase"]
            M = math.sqrt(sum(x * x for x in r["M"]))
            out["cases"].append({k: r[k] for k in ("subcase", "label", "compliance_float", "compliance_lower_proved")}
                                | {"disp_lower": r.get("ref_disp_along_F_lower_proved"),
                                   "rot_lower": (r["compliance_lower_proved"] / M) if M else None})
        out["sec"] = round(time.time() - t0, 1)
        return out
    except Exception as e:
        return {"id": i, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-600:]}


if __name__ == "__main__":
    d, l1, out = sys.argv[1], sys.argv[2], sys.argv[3]
    jobs = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    skip = {}
    for line in open(l1):
        r = json.loads(line)
        if r.get("self_intersections") or r["topology"]["components"] > 1:
            skip[r["id"]] = "self-intersecting" if r.get("self_intersections") else f"{r['topology']['components']} bodies"
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["id"] for l in open(out)}
    todo = [(os.path.join(d, f), f[:-4]) for f in sorted(os.listdir(d), key=lambda s: int(s.split(".")[0]) if s[0].isdigit() else 0)
            if f.endswith(".fem") and f[:-4] not in skip and f[:-4] not in done]
    print(f"{len(todo)} decks to run, {len(skip)} skipped by level 1, {len(done)} already done", flush=True)
    with Pool(jobs) as pool, open(out, "a") as f:
        for r in pool.imap_unordered(one, todo):
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(r["id"], r.get("sec"), r.get("error", ""), flush=True)
