"""Stage 0 (2026-10-31, the curator's plan: frames next, the continuum decided by a NUMBER): how far does the stand
PROVE an engineering requirement on a stiffness system, as the number of unknowns grows?

Not the exact worst case (that is measured already: Muhanna's benchmarks, 81 unknowns ~8.5 min, 230 ~55 min per
displacement, BRICKS.md 7g) but what an engineer asks: "the tip moves at most nominal + m", every bar's modulus
anywhere in +-0.5 %, independently. The truss is the IFEM benchmark's cantilever (bench/hard-tasks/mkcant.py) with
k floors: 4k + 4 nodes' DOFs minus 3 supports = 4k + 1 unknowns, 5k + 1 moduli.

The nominal tip displacement is computed here in floats (numpy) only to SET the bound; the proof is the stand's.

    python3 bench/stage0/scale_truss.py 10 20 40 80 160 320 --margins 2,1 --jobs 24 --limit 1800
-> bench/stage0/scale_truss.jsonl
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "scale_truss.jsonl"


def deck(k):
    return subprocess.run([sys.executable, str(ROOT / "bench/hard-tasks/mkcant.py"), str(k)],
                          capture_output=True, text=True, check=True).stdout


def nominal_tip(text):
    nodes, bars, loads, fixed = {}, [], {}, set()
    for ln in text.splitlines():
        p = [s.strip() for s in ln.split(",")]
        if p[0] == "N":
            nodes[int(p[1])] = (float(p[2]), float(p[3]))
        elif p[0] == "E":
            bars.append((int(p[1]), int(p[2])))
        elif p[0] == "F":
            loads[(int(p[1]), p[2])] = float(p[3])
        elif p[0] == "D":
            fixed.add((int(p[1]), p[2]))
    ids = sorted(nodes)
    dof = {}
    for n in ids:
        for d in ("UX", "UY"):
            if (n, d) not in fixed:
                dof[(n, d)] = len(dof)
    K = np.zeros((len(dof), len(dof)))
    f = np.zeros(len(dof))
    for a, b in bars:
        (xa, ya), (xb, yb) = nodes[a], nodes[b]
        L = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
        c, s = (xb - xa) / L, (yb - ya) / L
        v = {(a, "UX"): -c, (a, "UY"): -s, (b, "UX"): c, (b, "UY"): s}
        for i, vi in v.items():
            for j, vj in v.items():
                if i in dof and j in dof:
                    K[dof[i], dof[j]] += vi * vj / L          # E = A = 1 in mkcant's deck
    for (n, d), val in loads.items():
        f[dof[(n, "U" + d[1])]] += val
    u = np.linalg.solve(K, f)
    top = max(ids)                                           # a top-floor node
    return top, float(u[dof[(top, "UX")]]), len(dof), len(bars)


def job(arg):
    k, m, limit = arg
    text = deck(k)
    top, ux, ndof, nbars = nominal_tip(text)
    bound = ux * (1 + m / 100)                                 # ux > 0 under FX loads
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(text)
        path = fh.name
    t0 = time.time()
    p = subprocess.run(["timeout", str(limit), sys.executable, "-m", "ustand.truss", path, "--tol", "0.5%",
                        "--req", f"U({top},X) <= {bound:.6f}"], capture_output=True, text=True, cwd=str(ROOT),
                       env={"OPENBLAS_NUM_THREADS": "1", "PATH": "/usr/bin:/bin"})
    wall = round(time.time() - t0, 1)
    pathlib.Path(path).unlink()
    verdict = "TIMEOUT" if p.returncode == 124 else next(
        (w for w in ("EARNED", "REFUTED", "OPEN", "STAND FAULT", "BRICK ERROR") if w in p.stdout), "ERROR")
    return {"k": k, "unknowns": ndof, "moduli": nbars, "margin_pct": m, "nominal": ux, "bound": bound,
            "verdict": verdict, "wall_s": wall, "rc": p.returncode, "tail": p.stdout[-300:] + p.stderr[-300:]}


def main():
    a = sys.argv[1:]
    first_opt = next((i for i, x in enumerate(a) if x.startswith("--")), len(a))
    ks = [int(x) for x in a[:first_opt]]
    margins = [float(x) for x in a[a.index("--margins") + 1].split(",")] if "--margins" in a else [2.0]
    jobs = int(a[a.index("--jobs") + 1]) if "--jobs" in a else 12
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 1800
    work = [(k, m, limit) for k in ks for m in margins]
    with ProcessPoolExecutor(jobs) as ex, open(OUT, "a") as fh:
        for r in ex.map(job, work):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(f"k={r['k']:4d} unknowns={r['unknowns']:5d} moduli={r['moduli']:5d} margin={r['margin_pct']}% "
                  f"{r['verdict']:8s} {r['wall_s']:8.1f}s", flush=True)


if __name__ == "__main__":
    main()
