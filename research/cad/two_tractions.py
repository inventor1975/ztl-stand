# MEASURE: f(v) of the SAME P1 integer field against the two records of the load —
#   (a) the P1 lower side's: the nodal loads themselves (tetfea.traction_work_exact on fvec);
#   (b) the upper side's traction t_q (tetfea2.traction_work2 on the flux q).
import sys, numpy as np
from fractions import Fraction as Fr
from ustand import tetfea as TF, tetfea2 as T2, tetmesh as TM
quiet = lambda m: None
for path in sys.argv[1:]:
    d = TF.read_deck(path)
    ctx = TF.setup(d, log=quiet)
    L = TF.case_load(ctx, 1)
    u, vi, res = TF.case_field(ctx, L["ftot"], tol=1e-4, log=quiet)
    fa = TF.traction_work_exact(L["fvec"], vi)
    ids = sorted(d["grids"]); idx = {n: i for i, n in enumerate(ids)}
    X = np.array([[float(TF._nas(x)) for x in d["grids"][n]] for n in ids])
    T = np.array([[idx[n] for n in t] for t in d["tets"]])
    F, own, lf, tf = TM.faces(T)
    fixed = {idx[n] for ind, deps in d["rbe2"] for n in deps if d["spc"].get(ind, "").startswith("123")}
    kind, q = T2.traction_flux(d, X, F, own, idx, fixed, tuple(L["F"]), tuple(L["M"]))
    ctx2 = T2.setup2(d, log=quiet, solver=False)
    V = T2.embed_p1(ctx2, [2 * int(x) for x in vi])
    fb = T2.traction_work2(ctx2, q, V) / 2          # the field was doubled to make the midpoint means integers
    rel = float((fb - fa) / fa)
    low_a, *_ = TF.lower_bound(ctx, vi, L["fvec"])
    print(f"{path.split('/')[-1]}: f(v) nodal loads {float(fa):.12f}, t_q {float(fb):.12f}, relative difference {rel:.3e}; "
          f"the P1 lower bound would move by {2 * rel:.3e} relative ({float(low_a) * 2 * rel:.3e} absolute of {float(low_a):.6f})", flush=True)
