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

if FAILS:
    print(f"EQUIL RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"EQUIL GREEN ({CHECKS} checks)")
