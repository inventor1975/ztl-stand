"""2b on a whole real bracket, NO decomposition: SimJEB 631 (82k tets), the global hybridized choice, float energy;
with the 2a lower bound beside it. Usage: python3 research/cad/upper631.py <deck.fem> [subcase]"""
import sys, time, json, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import tetfea as TF, tetmesh as TM, equil as EQ

path, sc = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1
t0 = time.time()
d = TF.read_deck(path)
ids = sorted(d["grids"]); idx = {n: i for i, n in enumerate(ids)}
X = np.array([[float(TF._nas(x)) for x in d["grids"][n]] for n in ids])
T = np.array([[idx[n] for n in t] for t in d["tets"]])
F, own, lf, tf = TM.faces(T)
fixed = {idx[n] for ind, deps in d["rbe2"] for n in deps if d["spc"].get(ind, "").startswith("123")}
ref, _, rn = d["rbe3"][0]
kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
lid = int(d["subcases"][sc]["LOAD"])
Fv, Mv = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
if lid in d["force"]:
    _, s_, v = d["force"][lid]; Fv = tuple(float(s_ * x) for x in v)
if lid in d["moment"]:
    _, s_, v = d["moment"][lid]; Mv = tuple(float(s_ * x) for x in v)
xyz = {n: list(X[idx[n]]) for n in rn + [ref]}
fl = TF.rbe3_loads(xyz, ref, rn, Fv, Mv)
tr, res, lost = TM.rbe3_traction(X, F, kind, {idx[n]: fl[i] for i, n in enumerate(rn)})
q = np.zeros((len(F), 3, 3))
A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
n2 = np.linalg.norm(np.cross(B - A, C - A), axis=1)
for fid in np.where(kind == 2)[0]:
    for p in range(3):
        q[fid, p] = tr[int(F[fid, p])] * n2[fid]
np.save(os.path.join(os.environ.get("OUT", "/tmp"), f"q631_s{sc}.npy"), q)
print(f"mesh {len(T)} tets, {len(F)} faces; kinds {[int((kind == k).sum()) for k in range(4)]}; traction residual "
      f"{res:.1e}, lost {len(lost)}; {time.time() - t0:.1f} s", flush=True)
E, nu = float(d["mat"][0]), float(d["mat"][1])
g, e, info = EQ.choose(X, T, F, own, tf, kind, E, nu, q, direct=False, tol=1e-8, log=lambda m: print(m, flush=True))
print(f"UPPER (float choice) {e:.6f}; {info}; {time.time() - t0:.1f} s", flush=True)
lo = TF.solve_cases(d, [sc], tol=1e-4, log=lambda s: None)[0]
print(f"LOWER (proved, 2a) {lo['compliance_lower_proved']:.6f}; float FE {lo['compliance_float']:.6f}; "
      f"gap {e / lo['compliance_lower_proved'] - 1:.3%}; {time.time() - t0:.1f} s", flush=True)
np.save(os.path.join(os.environ.get("OUT", "/tmp"), f"g631_s{sc}.npy"), g)
