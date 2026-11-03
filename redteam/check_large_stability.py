"""Red team: frame.stability_lower on LARGE 2D frames (> 1500 unknowns: ZTL's CHOLMOD path when installed) against
redteam/ref2d's buckling (sparse shift-invert, ns = 2 and 4 sub-elements per member: its own convergence shown).
--mutant: the lower bound x 1.02.  PYTHONPATH=. python3 redteam/check_large_stability.py [--mutant]"""
import json, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla
import ref2d
from ustand import frame as FRM
from ustand import judge_ztl  # noqa: F401
import zenergy as ZE

MUT = "--mutant" in sys.argv


def deck(bays, st, seed):
    import random
    rng = random.Random(seed)
    lines = ["ET, 1, BEAM3", "MP, EX, 1, 210000000000", "R, 1, 0.01, 8e-05, 0.2"]
    nid = {}
    for s in range(st + 1):
        for b in range(bays + 1):
            nid[(b, s)] = len(nid) + 1
            lines.append(f"N, {nid[(b, s)]}, {b * 5}, {s * 3}")
    for s in range(st):
        for b in range(bays + 1):
            lines.append(f"E, {nid[(b, s)]}, {nid[(b, s + 1)]}")
    for s in range(1, st + 1):
        for b in range(bays):
            lines.append(f"E, {nid[(b, s)]}, {nid[(b + 1, s)]}")
    for b in range(bays + 1):
        lines += [f"D, {nid[(b, 0)]}, UX, 0", f"D, {nid[(b, 0)]}, UY, 0", f"D, {nid[(b, 0)]}, ROTZ, 0"]
    for s in range(1, st + 1):
        lines.append(f"F, {nid[(0, s)]}, FX, {rng.randint(1, 20) * 1000}")
        for b in range(bays + 1):
            lines.append(f"F, {nid[(b, s)]}, FY, -{rng.randint(5, 40) * 1000}")
    return "\n".join(lines) + "\n"


def ref_lambda(text, ns):
    K, KG = ref2d._matrices_sparse(text, ns)
    # smallest lam > 0 with (K + lam KG) singular: largest theta of -KG x = theta K x
    vals = sla.eigsh(-KG, k=1, M=K, which="LA", return_eigenvectors=False)
    return float(1 / vals.max())


out = []
for (bays, st, seed) in ((8, 24, 1), (19, 32, 2), (14, 44, 3), (24, 25, 4)):
    t = deck(bays, st, seed)
    nn = (bays + 1) * st * 3
    t0 = time.time()
    lo = FRM.stability_lower(t, "0").get("lam_low")
    dt = time.time() - t0
    r2, r4 = ref_lambda(t, 2), ref_lambda(t, 4)
    lo_f = float(lo) * (1.02 if MUT else 1) if lo is not None else None
    err = abs(r2 - r4)
    out.append({"bays": bays, "storeys": st, "unknowns": nn, "cholmod": nn >= ZE.SPARSE_CHOL_FROM and ZE._have_cholmod(),
                "lam_low": lo_f, "ref_ns2": r2, "ref_ns4": r4, "ref_change": err, "seconds": round(dt, 1),
                "violation": lo_f is not None and lo_f > r4 + 5 * err})
print(json.dumps({"mutant": MUT, "cases": out}, indent=0))
