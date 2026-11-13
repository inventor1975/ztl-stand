# -*- coding: utf-8 -*-
"""ustand/assembly.py on hand-solved models (no task data): bars in series, a ground spring, a pure-shear panel whose
shear flow is the load over its width, a toleranced stiffness whose proved range holds the true extremes, the global
balance of a grid the size of a real roof diaphragm, and the refusals. Run: python3 tests/test_assembly.py"""
import os
import sys
import time
from fractions import Fraction as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import assembly as A   # noqa: E402

CHECKS, FAILS = 0, []


def check(c, what):
    global CHECKS
    CHECKS += 1
    if not c:
        FAILS.append(what)
        print("FAIL:", what)


def refused(spec, word):
    try:
        A.solve(spec)
    except A.AssemblyError as e:
        return word in str(e)
    return False


series = {"nodes": {"A": [0, 0], "B": [1, 0], "C": [2, 0]}, "fixed": [["A", "X"], ["A", "Y"], ["B", "Y"], ["C", "Y"]],
          "elements": [{"id": "ab", "type": "bar", "a": "A", "b": "B", "k": "100"}, {"id": "bc", "type": "bar", "a": "B", "b": "C", "k": "50"}],
          "loads": [["C", "X", "10"]], "outputs": [{"u": ["C", "X"]}, {"force": "ab"}, {"force": "bc"}]}
r = A.solve(series)
o = {x["output"]: x for x in r["outputs"]}
check(o["u(C,X)"]["nominal"] == F(3, 10) and o["u(C,X)"]["lo"] == o["u(C,X)"]["hi"] and o["force(ab)"]["nominal"] == 10 and o["force(bc)"]["nominal"] == 10,
      f"two bars in series: u = P/k1 + P/k2 = 3/10 exactly, each carries the load ({o['u(C,X)']})")
tol = {**series, "elements": [dict(series["elements"][0], k=["90", "110"]), series["elements"][1]]}
u = A.solve(tol)["outputs"][0]
true_lo, true_hi = F(10, 110) + F(1, 5), F(10, 90) + F(1, 5)
check(u["lo"] <= true_lo and true_hi <= u["hi"] and u["hi"] - u["lo"] < F(3, 100),
      f"a stiffness in a range: the proved range holds the true extremes and is not loose ({float(u['lo']):.5f} .. {float(u['hi']):.5f} around {float(true_lo):.5f} .. {float(true_hi):.5f})")
spring = {"nodes": {"A": [0, 0]}, "fixed": [["A", "Y"]], "elements": [{"id": "s", "type": "spring", "node": "A", "dir": "X", "k": "40"}],
          "loads": [["A", "X", "10"]], "outputs": [{"u": ["A", "X"]}, {"force": "s"}]}
o = A.solve(spring)["outputs"]
check(o[0]["nominal"] == F(1, 4) and o[1]["nominal"] == 10, "a spring to ground: u = P/k, and it carries P")
panel = {"nodes": {"bl": [0, 0], "br": [4, 0], "tr": [4, 2], "tl": [0, 2]},
         "fixed": [["bl", "X"], ["bl", "Y"], ["br", "X"], ["br", "Y"], ["tl", "Y"], ["tr", "Y"]],
         "elements": [{"id": "p", "type": "panel", "nodes": ["bl", "br", "tr", "tl"], "g": "12"}, {"id": "top", "type": "bar", "a": "tl", "b": "tr", "k": "1000"}],
         "loads": [["tr", "X", "24"]], "outputs": [{"flow": "p"}, {"u": ["tr", "X"]}, {"u": ["tl", "X"]}, {"force": "top"}]}
o = A.solve(panel)["outputs"]
check(o[0]["nominal"] == 6 and o[1]["nominal"] + o[2]["nominal"] == 2 and o[3]["nominal"] == 12,
      f"a pure-shear panel: its shear flow is the load over its width (24/4), its strain the flow over G', the top bar passes half the load ({[str(x['nominal']) for x in o]})")
# a grid the size of a real roof diaphragm: 40 x 6 panels of 6 x 30, bars on every grid line, springs along two lines
nx, ny, a, b = 40, 6, 6, 30
nodes = {f"n{i}_{j}": [i * a, j * b] for i in range(nx + 1) for j in range(ny + 1)}
els = []
for i in range(nx + 1):
    for j in range(ny + 1):
        if i < nx:
            els.append({"id": f"bx{i}_{j}", "type": "bar", "a": f"n{i}_{j}", "b": f"n{i + 1}_{j}", "k": "4000"})
        if j < ny:
            els.append({"id": f"by{i}_{j}", "type": "bar", "a": f"n{i}_{j}", "b": f"n{i}_{j + 1}", "k": "900"})
        if i < nx and j < ny:
            els.append({"id": f"p{i}_{j}", "type": "panel", "nodes": [f"n{i}_{j}", f"n{i + 1}_{j}", f"n{i + 1}_{j + 1}", f"n{i}_{j + 1}"], "g": ["18", "22"]})
springs = [f"sy{i}_{j}" for i in (0, nx) for j in range(ny + 1)]
for i in (0, nx):
    for j in range(ny + 1):
        els.append({"id": f"sy{i}_{j}", "type": "spring", "node": f"n{i}_{j}", "dir": "Y", "k": "50"})
for j in (0, ny):
    for i in range(0, nx + 1, 10):
        els.append({"id": f"sx{i}_{j}", "type": "spring", "node": f"n{i}_{j}", "dir": "X", "k": "50"})
loads = [[f"n{i}_{j}", "Y", "1"] for i in range(nx + 1) for j in (0, ny)]
grid = {"nodes": nodes, "fixed": [], "elements": els, "loads": loads,
        "outputs": [{"force": s} for s in springs] + [{"u": [f"n{nx // 2}_0", "Y"]}, {"flow": f"p0_{ny // 2}"}, {"flow": f"p{nx - 1}_{ny // 2}"}]}
t0 = time.time()
r = A.solve(grid)
dt = time.time() - t0
sp = r["outputs"][:len(springs)]
lo, hi, total = sum(x["lo"] for x in sp), sum(x["hi"] for x in sp), len(loads)
mid, f0, f1 = r["outputs"][-3], r["outputs"][-2], r["outputs"][-1]
check(r["unknowns"] == 2 * (nx + 1) * (ny + 1) and lo <= total <= hi and float(hi - lo) < 0.5 * total,
      f"a grid of {r['unknowns']} unknowns and {r['elements']} elements ({dt:.1f} s): the springs' proved forces balance the applied load "
      f"({float(lo):.2f} .. {float(hi):.2f} around {total})")
check(mid["lo"] > 0 and f0["lo"] > 0 and f1["hi"] < 0 and abs(float(f0["nominal"] + f1["nominal"])) < 1e-9,
      f"... the middle moves with the load, and the shear flow at the two ends is equal and opposite - with proved signs "
      f"({float(f0['lo']):.4f} .. {float(f0['hi']):.4f}; {float(f1['lo']):.4f} .. {float(f1['hi']):.4f})")
# refusals: a wrong model is refused in words, never solved
free_y = {"nodes": {"A": [0, 0], "B": [1, 0]}, "fixed": [["A", "X"], ["A", "Y"]], "elements": [{"id": "ab", "type": "bar", "a": "A", "b": "B", "k": "1"}],
          "loads": [["B", "X", "1"]], "outputs": [{"u": ["B", "X"]}]}
check(refused(free_y, "nothing holds B Y"), "PLANTED a displacement nothing holds is named")
skew = {**free_y, "nodes": {"A": [0, 0], "B": [1, 1]}, "fixed": [["A", "X"], ["A", "Y"]], "loads": []}
check(refused(skew, "irrational"), "PLANTED a bar whose direction is not exact is refused")
body = {"nodes": {"A": [0, 0], "B": [1, 0]}, "fixed": [["A", "Y"], ["B", "Y"]], "elements": [{"id": "ab", "type": "bar", "a": "A", "b": "B", "k": "1"}],
        "loads": [["B", "X", "1"]], "outputs": [{"u": ["B", "X"]}]}
check(refused(body, "mechanism"), "PLANTED a body free to slide is refused as a mechanism, not solved")
check(refused({**series, "elements": [dict(series["elements"][0], k="-5"), series["elements"][1]]}, "positive")
      and refused({**series, "outputs": [{"flow": "ab"}]}, "a panel has a flow")
      and refused({**series, "loads": [["A", "X", "1"]]}, "fixed")
      and refused({**panel, "elements": [dict(panel["elements"][0], nodes=["bl", "tr", "br", "tl"]), panel["elements"][1]]}, "rectangle"),
      "PLANTED a negative stiffness, a flow asked of a bar, a load on a support, a panel whose corners are out of order - each refused with its reason")
if FAILS:
    print(f"ASSEMBLY RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"ASSEMBLY GREEN ({CHECKS} checks)")
