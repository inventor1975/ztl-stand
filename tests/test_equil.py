# -*- coding: utf-8 -*-
"""ustand.equil: the hybridized choice equals the global KKT on the box (research/cad/upper_box.py: 8.782992 at n = 3,
8.767626 at n = 4, nu = 0.3), and its fluxes are continuous and balanced in floats. Run: python3 -m tests.test_equil"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetmesh as TM, equil as EQ, alfeld as AL          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


def box(n, L=10.0):
    h = L / n
    nid = lambda i, j, k: i + (n + 1) * (j + (n + 1) * k)
    X = np.array([(i * h, j * h, k * h) for k in range(n + 1) for j in range(n + 1) for i in range(n + 1)])
    T = []
    for k in range(n):
        for j in range(n):
            for i in range(n):
                for p in [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]:
                    pt, path = [i, j, k], [nid(i, j, k)]
                    for ax in p:
                        pt[ax] += 1
                        path.append(nid(*pt))
                    T.append(path)
    return X, np.array(T)


for n, ref in ((3, 8.782992), (4, 8.767626)):
    X, T = box(n)
    F, own, lf, tf = TM.faces(T)
    fixed = {i for i in range(len(X)) if X[i, 2] == 0}
    loaded = {i for i in range(len(X)) if X[i, 2] == 10.0}
    kind = TM.classify(F, own, fixed, loaded)
    q = np.zeros((len(F), 3, 3))
    A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    q[kind == 2, :, 2] = 3.0 * np.linalg.norm(np.cross(B - A, C - A), axis=1)[kind == 2, None]
    g, e, info = EQ.choose(X, T, F, own, tf, kind, 1000.0, 0.3, q)
    check(abs(e - ref) < 2e-6, f"n = {n}: hybrid energy {e:.7f} = the global KKT's {ref}")
    _, _, BAL = AL.float_forms(X[T])
    check(float(np.abs(np.einsum("nij,nj->ni", BAL, g)).max()) < 1e-8 * float(np.abs(g).max()),
          f"n = {n}: every tet balanced in floats")
    # continuity: for each interior face, the two tets' outward data at the same vertex sum to ~0
    loc = np.array([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]])
    acc = {}
    for t in range(len(T)):
        for f in range(4):
            fid = tf[t, f]
            if kind[fid] != 0:
                continue
            for jv, v in enumerate(T[t, loc[f]]):
                acc.setdefault((fid, v), np.zeros(3))
                acc[(fid, v)] = acc[(fid, v)] + g[t, f * 9 + jv * 3:f * 9 + jv * 3 + 3]
    worst = max(float(np.abs(x).max()) for x in acc.values())
    check(worst < 1e-8 * float(np.abs(g).max()), f"n = {n}: traction continuous on interior faces ({worst:.1e})")
    # the MATRIX-FREE trace solve (CG + face-block Jacobi + auxiliary space) must reach the same energy: until
    # 2026-11-11 no test went through this path at all
    gm, em, im = EQ.choose(X, T, F, own, tf, kind, 1000.0, 0.3, q, matfree=True, tol=1e-10)
    check(abs(em - ref) < 2e-6, f"n = {n}: matrix-free energy {em:.7f} = the global KKT's {ref}")
    check(float(np.abs(np.einsum("nij,nj->ni", BAL, gm)).max()) < 1e-8 * float(np.abs(gm).max()),
          f"n = {n}: matrix-free choice balanced in floats")
    # the auxiliary map is the CONJUGATE trace: Pi^T A Pi <= K, close to K (the injection gave a ratio ~250), and the
    # iteration count must not grow with n (the injection: 196 at n = 4, 326 at n = 12)
    check(0.8 < im["aux_rayleigh"] <= 1.0 + 1e-9, f"n = {n}: (Pi u)^T A (Pi u) / u^T K u = {im['aux_rayleigh']:.4f} in (0.8, 1]")
    check(im["cg_iterations"] < 120, f"n = {n}: matrix-free CG took {im['cg_iterations']} iterations (< 120)")
    # the tet-patch Schwarz smoother (2026-11-11) must reach the same energy: it only steers CG
    gs, es, _ = EQ.choose(X, T, F, own, tf, kind, 1000.0, 0.3, q, matfree=True, tol=1e-10, smoother="schwarz")
    check(abs(es - ref) < 2e-6, f"n = {n}: matrix-free + Schwarz energy {es:.7f} = the global KKT's {ref}")
    try:
        EQ.choose(X, T, F, own, tf, kind, 1000.0, 0.3, q, matfree=True, tol=1e-10, smoother="gauss")
        check(False, "an unknown smoother is refused")
    except ValueError:
        check(True, "an unknown smoother is refused")

# ---- SLIVERS (2026-11-11): a box with one layer squashed to 3 % of its height. Its tets are flat (quality 0.008),
# their faces form the sliver block of the Jacobi smoother; the choice must still be the direct solve's
X, T = box(4)
zs = np.unique(X[:, 2])
X = X.copy()
X[X[:, 2] == zs[2], 2] = zs[1] + 0.03 * (zs[2] - zs[1])
F, own, lf, tf = TM.faces(T)
kind = TM.classify(F, own, {i for i in range(len(X)) if X[i, 2] == 0}, {i for i in range(len(X)) if X[i, 2] == 10.0})
q = np.zeros((len(F), 3, 3))
A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
q[kind == 2, :, 2] = 3.0 * np.linalg.norm(np.cross(B - A, C - A), axis=1)[kind == 2, None]
q[kind == 2, :, 0] = 1.0 * np.linalg.norm(np.cross(B - A, C - A), axis=1)[kind == 2, None]
_, ed, _ = EQ.choose(X, T, F, own, tf, kind, 1000.0, 0.3, q)
_, e1, i1 = EQ.choose(X, T, F, own, tf, kind, 1000.0, 0.3, q, matfree=True, tol=1e-10)
_, e0, i0 = EQ.choose(X, T, F, own, tf, kind, 1000.0, 0.3, q, matfree=True, tol=1e-10, sliver_q=0.0)
print(f"MEASURED squashed layer: direct {ed:.8f}; matrix-free {e1:.8f} in {i1['cg_iterations']} its with the sliver "
      f"block ({i1['sliver_faces']} faces), {e0:.8f} in {i0['cg_iterations']} its without")
check(i1["sliver_faces"] > 0 and i0["sliver_faces"] == 0, "the squashed layer's faces are in the sliver block")
check(abs(e1 - e0) < 1e-9 * e0, "slivers: the same energy with and without the block (it only steers CG)")
# MEASURED: the DIRECT solve comes out 2.1e-7 lower here, whatever the CG tolerance. It is the direct solve that is
# off: on this mesh with the vertical load alone its relative flux jump is 3.3e-9, the matrix-free one's 1.4e-12
# (LU rounding on the stiff system; a discontinuous flux relaxes the constraint, hence the lower energy).
check(abs(e1 - ed) < 1e-6 * ed, f"slivers: matrix-free energy within 1e-6 of the direct solve's ({(e1 - ed) / ed:.1e})")
check(2 * i1["cg_iterations"] < i0["cg_iterations"], "slivers: the block at least halves the CG iterations")

if FAILS:
    print(f"EQUIL RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"EQUIL GREEN ({CHECKS} checks)")
