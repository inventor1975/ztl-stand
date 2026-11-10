# -*- coding: utf-8 -*-
"""ustand.dd: the exact coarse balance leaves every floating subdomain balanced — on a box split in octants, with
arbitrary (deliberately unbalanced) interface fluxes. Run: python3 -m tests.test_dd"""
import os
import sys
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetmesh as TM, dd as DD          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


n = 4
nid = lambda i, j, k: i + (n + 1) * (j + (n + 1) * k)
Xq = [(Fr(i), Fr(j), Fr(k)) for k in range(n + 1) for j in range(n + 1) for i in range(n + 1)]
X = np.array([[float(c) for c in p] for p in Xq])
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
kind = TM.classify(F, own, {i for i in range(len(X)) if X[i, 2] == 0}, {i for i in range(len(X)) if X[i, 2] == n})
cen = X[T].mean(axis=1)
sid = (cen[:, 0] > n / 2).astype(int) + 2 * (cen[:, 1] > n / 2) + 4 * (cen[:, 2] > n / 2)
rng = np.random.default_rng(1)
s0 = sid[own[:, 0]]
s1 = np.where(own[:, 1] >= 0, sid[np.maximum(own[:, 1], 0)], -1)
q = {}
for f in np.where((own[:, 1] >= 0) & (s0 != s1))[0]:
    q[int(f)] = [[Fr(float(x)) for x in rng.normal(size=3)] for _ in range(3)]
for f in np.where(kind == 2)[0]:
    q[int(f)] = [[Fr(0), Fr(0), Fr(1)] for _ in range(3)]
for f in np.where(kind == 3)[0]:
    q[int(f)] = [[Fr(0)] * 3 for _ in range(3)]
q, rep = DD.coarse_balance(Xq, F, own, kind, sid, q)
check(rep["subdomains"] == 8 and rep["with_support"] == 4, f"8 octants, 4 on the support ({rep})")
check(rep["floating_unbalanced_after"] == [] and rep["unreached"] == [], f"every floating octant balanced EXACTLY ({rep})")

if FAILS:
    print(f"DD RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"DD GREEN ({CHECKS} checks)")
