# -*- coding: utf-8 -*-
"""ustand.tetfea: the deck is read as written, the RBE3 load is the one it defines, and the proved number is a LOWER
bound that sits just under the float compliance. Run: python3 -m tests.test_tetfea"""
import os
import sys
import tempfile
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetfea as TF          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


def f8(x):
    s = ("%.4f" % x)[:8]
    return s.rjust(8)


def box_deck(n=3, L=10.0, E="200000.0", nu="0.0", F=(0.0, 0.0, 1000.0), M=(0.0, 0.0, 0.0), ref=(5.0, 5.0, 12.0)):
    """A cube of n^3 cells, 6 Kuhn tets each; bottom face tied (RBE2) to an SPC'd node; top face loaded by an RBE3."""
    h = L / n
    nid = lambda i, j, k: 1 + i + (n + 1) * (j + (n + 1) * k)
    lines = ["SUBCASE        1", "  LABEL pull", "  SPC =        1", "  LOAD =        2", "BEGIN BULK"]
    for k in range(n + 1):
        for j in range(n + 1):
            for i in range(n + 1):
                lines.append("GRID    " + "%8d" % nid(i, j, k) + " " * 8 + f8(i * h) + f8(j * h) + f8(k * h))
    N = (n + 1) ** 3
    spc_node, ref_node = N + 1, N + 2
    lines.append("GRID    " + "%8d" % spc_node + " " * 8 + f8(5.0) + f8(5.0) + f8(-2.0))
    lines.append("GRID    " + "%8d" % ref_node + " " * 8 + f8(ref[0]) + f8(ref[1]) + f8(ref[2]))
    eid = 1
    perms = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
    for k in range(n):
        for j in range(n):
            for i in range(n):
                for p in perms:
                    pt, path = [i, j, k], [nid(i, j, k)]
                    for ax in p:
                        pt[ax] += 1
                        path.append(nid(*pt))
                    lines.append("CTETRA  " + "%8d" % eid + "       1" + "".join("%8d" % x for x in path))
                    eid += 1

    def cont(head, ids):
        out, row = [], head
        for x in ids:
            if len(row) >= 72:
                out.append(row)
                row = "+       "
            row += "%8d" % x
        out.append(row)
        return out
    bottom = [nid(i, j, 0) for j in range(n + 1) for i in range(n + 1)]
    top = [nid(i, j, n) for j in range(n + 1) for i in range(n + 1)]
    lines += cont("RBE2    " + "%8d" % (eid + 1) + "%8d" % spc_node + "  123456", bottom)
    lines += cont("RBE3    " + "%8d" % (eid + 2) + " " * 8 + "%8d" % ref_node + "  123456" + "1.0     " + "     123", top)
    lines.append("SPC            1" + "%8d" % spc_node + "  123456     0.0")
    lines.append("FORCE          2" + "%8d" % ref_node + "       0" + "1.0     " + "".join(f8(x) for x in F))
    lines.append("MAT1           1" + E.rjust(8) + " " * 8 + nu.rjust(8) + "  7.8-9 ")
    lines.append("ENDDATA")
    d = tempfile.mkdtemp()
    p = os.path.join(d, "box.fem")
    open(p, "w").write("\n".join(lines) + "\n")
    return p


# 1. Nastran small-field reals, exactly
check(TF._nas("4.43-9") == Fr(443, 10 ** 11) and TF._nas("-.201863") == Fr(-201863, 10 ** 6)
      and TF._nas("1.0     ") == 1 and TF._nas("4.2367-2") == Fr(42367, 10 ** 6) and TF._nas("1.5+3") == 1500,
      "Nastran reals read exactly")

# 2. the RBE3 distribution: sum = F, moment about the centroid = M + (x_ref - c) x F
rng = np.random.default_rng(3)
xyz = {i: list(rng.normal(size=3) * 5) for i in range(12)}
xyz[99] = [1.0, -2.0, 7.0]
F, M = (3.0, -1.0, 2.0), (0.5, 0.0, -4.0)
fl = TF.rbe3_loads(xyz, 99, list(range(12)), F, M)
X = np.array([xyz[i] for i in range(12)])
c = X.mean(axis=0)
check(np.allclose(fl.sum(axis=0), F, atol=1e-12), "RBE3: the nodal forces sum to F")
check(np.allclose(np.cross(X - c, fl).sum(axis=0), np.array(M) + np.cross(np.array(xyz[99]) - c, F), atol=1e-10),
      "RBE3: their moment about the centroid is M + (x_ref - c) x F")

# 3. the deck is read: counts, supports, load, material
p = box_deck()
deck = TF.read_deck(p)
check(len(deck["tets"]) == 6 * 27 and len(deck["rbe2"]) == 1 and len(deck["rbe2"][0][1]) == 16
      and len(deck["rbe3"][0][2]) == 16 and deck["mat"][0] == 200000 and deck["mat"][1] == 0
      and deck["subcases"][1]["LOAD"] == "2", f"box deck read ({len(deck['tets'])} tets)")

# 4. the bound: just under the float compliance (the pipeline's rounding is the only gap), and a LOWER bound
r = TF.solve(deck, 1, log=lambda s: None)
cf, lo = r["compliance_float"], r["compliance_lower_proved"]
check(lo <= cf * (1 + 1e-9) and lo >= cf * (1 - 1e-7), f"proved {lo} just under the float {cf}")
# a sanity of scale only (no exact solution here: the RBE3's equal nodal forces are not a uniform traction, so the
# 1D bar F^2 L / (E A) is a reference, not the truth): the same order as the bar
bar = 1000.0 ** 2 * 10.0 / (200000.0 * 100.0)
check(0.5 * bar < lo < 50 * bar, f"the same order as the 1D bar ({lo} vs {bar})")

# 5. a softer material gives a larger proved compliance (the bound follows E as 1/E for a fixed v-choice)
r2 = TF.solve(deck, 1, E=100000.0, nu=0.0, log=lambda s: None)
check(abs(r2["compliance_lower_proved"] / lo - 2.0) < 1e-6, "half the modulus: twice the compliance")

# 6. the VECTORISED binary64 bound on a(v, v) is never below the exact-integer one, and within 1e-10 of it
re = TF.solve(deck, 1, log=lambda s: None, exact=True)
rf = TF.solve(deck, 1, log=lambda s: None, exact=False)
check(rf["a_vv_up"] >= re["a_vv_up"] * (1 - 1e-15) and abs(rf["a_vv_up"] / re["a_vv_up"] - 1) < 1e-10,
      f"float a(v,v) bound {rf['a_vv_up']!r} vs exact {re['a_vv_up']!r}")
check(rf["compliance_lower_proved"] <= re["compliance_lower_proved"] * (1 + 1e-12),
      "the float route's lower bound is not above the exact route's")

if FAILS:
    print(f"TETFEA RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"TETFEA GREEN ({CHECKS} checks)")
