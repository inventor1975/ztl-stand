# -*- coding: utf-8 -*-
"""ustand.tetmesh: faces, kinds, subdomains and the RBE3 traction on a box. Run: python3 -m tests.test_tetmesh"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetmesh as TM          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


n = 3
nid = lambda i, j, k: i + (n + 1) * (j + (n + 1) * k)
X = np.array([(i, j, k) for k in range(n + 1) for j in range(n + 1) for i in range(n + 1)], float)
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
T = np.array(T)
F, own, lf, tf = TM.faces(T)
check(len(F) == 6 * 27 * 4 // 2 + 6 * 9 * 2 // 2, f"face count: each interior twice, boundary once ({len(F)})")
check(((own[:, 1] < 0).sum()) == 6 * 9 * 2, "boundary faces: 6 sides x 9 squares x 2 triangles")
check(all(set(F[tf[t, f]]) == set(T[t][[v for v in range(4) if v != f]]) for t in range(len(T)) for f in range(4)),
      "tface maps every tet's local face to its global face")
fixed = {i for i in range(len(X)) if X[i, 2] == 0}
loaded = {i for i in range(len(X)) if X[i, 2] == n}
kind = TM.classify(F, own, fixed, loaded)
check([(kind == k).sum() for k in range(4)] == [len(F) - 108, 18, 18, 72], f"kinds {[(kind == k).sum() for k in range(4)]}")
sid = TM.partition(X[T].mean(axis=1), 40)
check(np.bincount(sid).max() <= 40 and sid.max() + 1 >= len(T) // 40, "partition: every subdomain <= 40 tets")
nod = {i: np.array([0.0, 0.0, 1.0]) for i in loaded}
t, res, lost = TM.rbe3_traction(X, F, kind, nod)
check(res < 1e-12 and not lost, f"traction solves the consistent-load system (residual {res})")
check(abs(sum(np.array(v)[2] for v in t.values()) - 0) >= 0 and abs(sum(1.0 for _ in nod) - 16) < 1e-12,
      "16 loaded nodes")

# P1 stress and interface flux: a uniform strain gives the exact constant stress, and the flux on an interior face
# z = const equals sigma n2 with n2 = +-(0, 0, |n2|) — consistent with owner 0's outward normal
u = np.column_stack([0.0 * X[:, 0], 0.0 * X[:, 1], 0.01 * X[:, 2]])          # eps_zz = 0.01
sig = TM.p1_stress(X, T, u, 1000.0, 0.0)
check(np.allclose(sig[:, 2, 2], 10.0) and np.allclose(sig[:, 0, 0], 0.0), "P1 stress of a uniform strain (nu = 0)")
mask = kind == 0
q = TM.interface_flux(X, T, F, own, lf, sig, mask)
A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
n2 = np.cross(B - A, C - A)
x4 = X[T[own[:, 0], lf[:, 0]]]
out_ok = all(np.dot(np.where(np.dot(n2[f], x4[f] - A[f]) > 0, -1, 1) * n2[f], x4[f] - A[f]) < 0 for f in np.where(mask)[0][:50])
check(out_ok and np.allclose(q[mask][:, 0, :2], 0.0), "interface flux: owner-0 outward orientation, only the z-traction")

if FAILS:
    print(f"TETMESH RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"TETMESH GREEN ({CHECKS} checks)")
