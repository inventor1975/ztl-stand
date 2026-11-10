# -*- coding: utf-8 -*-
"""ustand.alfeld: the element's energy by the double Piola map from the reference EQUALS the energy of the element
built directly (sympy) on the tet — exactly, on random tets and random balanced face data. Run: python3 -m tests.test_alfeld"""
import os
import random
import sys
from fractions import Fraction as Fr

import sympy as sp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import alfeld as AL          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


rnd = random.Random(7)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for k in range(n):
    while True:
        P = [[Fr(rnd.randint(-30, 30), rnd.randint(1, 7)) for _ in range(3)] for _ in range(4)]
        Ps = [sp.Matrix([sp.Rational(c.numerator, c.denominator) for c in p]) for p in P]
        if sp.Matrix.hstack(Ps[1] - Ps[0], Ps[2] - Ps[0], Ps[3] - Ps[0]).det() != 0:
            break
    d = AL.build_on(Ps)
    BAL = d["BAL"]
    g0 = sp.Matrix([sp.Rational(rnd.randint(-9, 9), rnd.randint(1, 5)) for _ in range(36)])
    g = g0 - BAL.T * (BAL * BAL.T).inv() * (BAL * g0)            # the balanced part
    check((BAL * g).is_zero_matrix, f"tet {k}: g balanced (direct BAL)")
    gF = [Fr(str(v)) for v in g]
    Fv, Mv = AL.balance(P, gF)
    check(all(v == 0 for v in Fv + Mv), f"tet {k}: alfeld.balance agrees (force and moment 0)")
    e1 = (g.T * d["S1"] * g)[0, 0]
    e2 = (g.T * d["S2"] * g)[0, 0]
    tt, tr2 = AL.energy(P, gF)
    check(tt == Fr(str(e1)) and tr2 == Fr(str(e2)),
          f"tet {k}: Piola energy = direct energy exactly ({float(tt)} vs {float(e1)}; {float(tr2)} vs {float(e2)})")
    # an unbalanced g is caught
    gu = list(gF)
    gu[0] += 1
    Fu, Mu = AL.balance(P, gu)
    check(any(v != 0 for v in Fu + Mu), f"tet {k}: an unbalanced g is caught")

# the VECTORISED float forms agree with the exact per-tet ones (a CHOICE tool: agreement to rounding)
import numpy as np                       # noqa: E402
Ps = []
for k in range(5):
    while True:
        P = [[Fr(rnd.randint(-30, 30), rnd.randint(1, 7)) for _ in range(3)] for _ in range(4)]
        Pm = sp.Matrix([[sp.Rational(c.numerator, c.denominator) for c in p] for p in P])
        if (Pm[1:, :] - sp.ones(3, 1) * Pm[0, :]).det() != 0:
            break
    Ps.append(P)
Q1, Q2, BALv = AL.float_forms([[[float(c) for c in p] for p in P] for P in Ps])
worst = 0.0
for k, P in enumerate(Ps):
    g = [Fr(rnd.randint(-9, 9), 3) for _ in range(36)]
    # balance g exactly (least-norm correction through the exact balance map)
    cols = []
    for j in range(36):
        e = [Fr(0)] * 36
        e[j] = Fr(1)
        Fv, Mv = AL.balance(P, e)
        cols.append(Fv + Mv)
    A = sp.Matrix(6, 36, lambda i, j: sp.Rational(cols[j][i].numerator, cols[j][i].denominator))
    gs = sp.Matrix([sp.Rational(x.numerator, x.denominator) for x in g])
    gs = gs - A.T * (A * A.T).inv() * (A * gs)
    gF = [Fr(str(v)) for v in gs]
    tt, tr2 = AL.energy(P, gF)
    gf = np.array([float(x) for x in gF])
    worst = max(worst, abs(gf @ Q1[k] @ gf / float(tt) - 1), abs(gf @ Q2[k] @ gf / float(tr2) - 1),
                float(np.abs(BALv[k] @ gf).max()))
check(worst < 1e-9, f"vectorised float forms agree with the exact element (worst {worst:.1e})")

# the VECTORISED rigorous upper bound (errfloat) is >= the exact energy and within 1e-10 of it
Pe, ge, ex = [], [], Fr(0)
Em, num = Fr(113800), Fr(342, 1000)
for k in range(12):
    P = [[Fr(rnd.randint(-3000, 3000), rnd.randint(1, 97)) for _ in range(3)] for _ in range(4)]
    BM = AL.bal_matrix(P)
    Am = sp.Matrix([[sp.Rational(x.numerator, x.denominator) for x in row] for row in BM])
    gv = sp.Matrix([sp.Rational(rnd.randint(-9 ** 6, 9 ** 6), rnd.randint(1, 10 ** 6)) for _ in range(36)])
    gv = gv - Am.T * (Am * Am.T).inv() * (Am * gv)
    gq = [Fr(str(v)) for v in gv]
    tt, tr2 = AL.energy(P, gq)
    ex += ((1 + num) * tt - num * tr2) / Em
    Pe.append(P)
    ge.append(gq)
upb = AL.energy_upper_ev(Pe, ge, Em, num)
check(Fr(upb) >= ex and upb / float(ex) - 1 < 1e-10, f"errfloat energy upper {upb!r} >= exact {float(ex)!r}")

if FAILS:
    print(f"ALFELD RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"ALFELD GREEN ({CHECKS} checks, {n} random tets)")
