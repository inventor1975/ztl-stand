# -*- coding: utf-8 -*-
"""ustand.errfloat: on random expression trees over random rationals, the exact value (Fractions) lies inside
[lower, upper] every time, and the bound is not absurdly loose. Run: python3 -m tests.test_errfloat"""
import os
import random
import sys
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand.errfloat import Ev          # noqa: E402

rnd = random.Random(11)
bad = loose = 0
N = 3000
for _ in range(N):
    xs = [Fr(rnd.randint(-10 ** 6, 10 ** 6), rnd.randint(1, 10 ** 6)) * Fr(10) ** rnd.randint(-8, 8) for _ in range(6)]
    E = [Ev.rounded(np.array([float(x)])) for x in xs]
    ex = list(xs)
    ops = []
    for k in range(12):                      # a random straight-line program
        i, j = rnd.randrange(len(ex)), rnd.randrange(len(ex))
        op = rnd.choice("+-*/q")
        if op == "/" and ex[j] == 0:
            op = "*"
        try:
            if op == "+":
                e_, v_ = E[i] + E[j], ex[i] + ex[j]
            elif op == "-":
                e_, v_ = E[i] - E[j], ex[i] - ex[j]
            elif op == "*":
                e_, v_ = E[i] * E[j], ex[i] * ex[j]
            elif op == "q":
                e_, v_ = E[i].sq(), ex[i] * ex[i]
            else:
                e_, v_ = E[i] / E[j], ex[i] / ex[j]
        except ZeroDivisionError:
            continue
        E.append(e_)
        ex.append(v_)
    s = Ev(np.concatenate([x.v for x in E]), np.concatenate([x.e for x in E])).sum()
    ex.append(sum(ex))
    E.append(s)
    for x, v in zip(E, ex):
        lo, hi = Fr(float(x.lower()[()] if x.v.ndim == 0 else x.lower()[0])), Fr(float(x.upper()[()] if x.v.ndim == 0 else x.upper()[0]))
        if not (lo <= v <= hi):
            bad += 1
        if v != 0 and abs(float(hi - lo) / float(abs(v))) > 1e-6:
            loose += 1
print(f"{N} programs: exact value outside the bound {bad} times; bound wider than 1e-6 relative in {loose} values")
if bad:
    print("ERRFLOAT RED")
    sys.exit(1)
print("ERRFLOAT GREEN")
