# -*- coding: utf-8 -*-
"""ustand.refine (2026-11-11): a red 1:8 refinement poses THE SAME continuum problem. Run: python3 tests/test_refine.py

Checks, both sides:
  geometry — 8 children per tet, each EXACTLY 1/8 of its parent's volume, the same orientation; midpoints exact;
  load — the fine nodal loads (consistent loads of the coarse traction) have the coarse resultant force and moment;
  brackets — on the box of test_prestress, the fine bracket overlaps the coarse one, its lower bound is >= the coarse
    lower bound (the P1 spaces nest with their supports), and its gap is smaller;
  a KNOWN answer — the mean sigma_zz over a whole layer is F / A = 10 exactly (equilibrium); the polarized bracket on
    the refined deck contains it and is narrower than the coarse one;
  planted errors — (a) bolt midpoints left unfixed: another problem, caught by the bracket; (b) the RBE3 spread anew
    over the fine nodes: the SAME resultant (so a resultant check cannot see it) but another traction — caught by
    comparing the nodal loads with the coarse traction's."""
import os
import pickle
import sys
import tempfile
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetfea as TF, refine as RF, cadbracket as CB, tetmesh as TM          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


def f8(x):
    return ("%.4f" % x)[:8].rjust(8)


def box_deck(n=3, L=10.0, E="200000.0", nu="0.3", F=(0.0, 0.0, 1000.0), ref=(5.0, 5.0, 12.0)):
    """the cube of tests/test_prestress.py (a copy: importing that module would run it)"""
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
    for k in range(n):
        for j in range(n):
            for i in range(n):
                for p in [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]:
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


def vol6(P):
    a = [[P[k + 1][r] - P[0][r] for k in range(3)] for r in range(3)]
    return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))


def save(deck, where, name):
    q = os.path.join(where, name)
    with open(q, "wb") as f:
        pickle.dump(deck, f)
    return q


quiet = lambda s: None
p = box_deck(n=3)
where = os.path.dirname(p)
d = TF.read_deck(p)
r = RF.red_refine(d)
q = save(r, where, "box_r1.deck.pkl")

# ---- geometry, exact
check(len(r["tets"]) == 8 * len(d["tets"]), f"8 children per tet ({len(r['tets'])} = 8 x {len(d['tets'])})")
Xd = {n: [TF._nas(c) for c in r["grids"][n]] for n in r["grids"]}
ok_vol = ok_sign = True
for i, t in enumerate(d["tets"]):
    V = vol6([Xd[n] for n in t])
    for c in r["tets"][8 * i:8 * i + 8]:
        v = vol6([Xd[n] for n in c])
        ok_vol &= (v == V / 8)
        ok_sign &= (v > 0) == (V > 0)
check(ok_vol, "every child is EXACTLY 1/8 of its parent's volume (so the volume is preserved exactly)")
check(ok_sign, "every child keeps its parent's orientation")
total = sum(abs(vol6([Xd[n] for n in t])) for t in r["tets"]) / 6
check(total == 1000, f"the refined volume is exactly 1000 ({total})")
mids = [n for n in r["grids"] if n not in d["grids"]]
check(all(any(Xd[m] == [(TF._nas(a) + TF._nas(b)) / 2 for a, b in zip(d["grids"][e0], d["grids"][e1])]
              for e0, e1 in [(t[a], t[b]) for t in d["tets"] for a, b in RF.EDGES]) for m in mids[:20]),
      "the first 20 midpoints are the exact means of an edge's ends")

# ---- the load: the fine nodal loads have the coarse resultant
ids = sorted(r["grids"])
idx = {n: i for i, n in enumerate(ids)}
X = np.array([[float(c) for c in Xd[n]] for n in ids])
T = np.array([[idx[n] for n in t] for t in r["tets"]])
Fm, own, _, _ = TM.faces(T)
fixed = {idx[n] for ind, deps in r["rbe2"] for n in deps if r["spc"].get(ind, "").startswith("123")}
kind = TM.classify(Fm, own, fixed, {idx[n] for n in r["traction"]["nodal"]})
fn = RF.traction_loads(X, Fm, kind, {idx[n]: v for n, v in r["traction"]["nodal"].items()})
Fsum, Msum = fn.sum(0), np.cross(X, fn).sum(0)
dc = TF.read_deck(p)
cid = sorted(dc["grids"])
cidx = {n: i for i, n in enumerate(cid)}
Xc = np.array([[float(TF._nas(c)) for c in dc["grids"][n]] for n in cid])
ref, _, rn = dc["rbe3"][0]
fl = TF.rbe3_loads({n: list(Xc[cidx[n]]) for n in rn + [ref]}, ref, rn, (0.0, 0.0, 1000.0), (0.0, 0.0, 0.0))
Fc = fl.sum(0)
Mc = sum(np.cross(Xc[cidx[n]], fl[i]) for i, n in enumerate(rn))
# MEASURED 2026-11-11: |F_fine - F_coarse| ~1e-13 (floats; the consistent loads of a linear field are exact in
# exact arithmetic)
check(np.abs(Fsum - Fc).max() < 1e-9 * 1000, f"fine resultant force = coarse ({Fsum} vs {Fc})")
check(np.abs(Msum - Mc).max() < 1e-9 * 1e4, f"fine resultant moment = coarse ({Msum} vs {Mc})")
check(kind.tolist().count(2) == 4 * 18, f"the 18 coarse loaded faces became exactly 72 fine ones "
                                        f"({kind.tolist().count(2)})")
check(kind.tolist().count(1) == 4 * 18, f"the 18 coarse fixed faces became exactly 72 fine ones "
                                        f"({kind.tolist().count(1)})")

# ---- brackets
bc = CB.bracket(p, 1, log=quiet)
bf = CB.bracket(q, 1, log=quiet)
c0, c1 = bc["compliance"], bf["compliance"]
print(f"MEASURED box n=3: coarse C in [{c0[0]:.6f}, {c0[1]:.6f}] ({100 * bc['gap']:.2f} %), refined "
      f"[{c1[0]:.6f}, {c1[1]:.6f}] ({100 * bf['gap']:.2f} %)")
check(max(c0[0], c1[0]) <= min(c0[1], c1[1]), "the refined bracket OVERLAPS the coarse one (both contain C)")
check(c1[0] >= c0[0] * (1 - 1e-9), "the refined lower bound >= the coarse one (nested P1 spaces with supports)")
check(bf["gap"] < bc["gap"], "the refined gap is smaller")
check(any("red refinement" in s for s in bf["rests_on"]), "the refined bracket says what it rests on")

# ---- the known answer: mean sigma_zz over the middle layer = F / A = 10
def mean_bracket(path, s):
    dk = TF.read_deck(path)
    mask, vol = CB.omega_box(dk, [-1, -1, 10 / 3 - 1e-6, 11, 11, 20 / 3 + 1e-6])
    sig = CB.mean_stress_extractor("zz", dk["mat"][0], dk["mat"][1], vol)
    out = []
    for sg in (s, -s):
        sub = {"F": (0.0, 0.0, 1000.0), "M": (0.0, 0.0, 0.0), "label": "pull",
               "prestress": {"omega": mask, "sigma": [[sg * x for x in row] for row in sig]}}
        out.append(CB.bracket(path, sub, log=quiet)["compliance"])
    (pl, ph), (ml, mh) = out
    s = float(s)
    return (pl - mh) / (4 * s), (ph - ml) / (4 * s), int(mask.sum())


s = Fr(1, 10)
lc = mean_bracket(p, s)
lf = mean_bracket(q, s)
print(f"MEASURED mean sigma_zz over the middle layer (exact 10): coarse [{lc[0]:.5f}, {lc[1]:.5f}] ({lc[2]} tets), "
      f"refined [{lf[0]:.5f}, {lf[1]:.5f}] ({lf[2]} tets)")
check(lc[2] * 8 == lf[2], "omega on the refined deck is exactly the children of the coarse omega")
check(lc[0] <= 10 <= lc[1], "coarse: the exact mean 10 inside")
check(lf[0] <= 10 <= lf[1], "refined: the exact mean 10 inside")
check(lf[1] - lf[0] < lc[1] - lc[0], "refined: the mean's bracket is narrower")

# ---- planted (a): bolt midpoints left unfixed — another problem (point supports): caught by the bracket
ra = RF.red_refine(d, planted="unfixed_bolt_midpoints")
qa = save(ra, where, "box_r1_a.deck.pkl")
try:
    ba = CB.bracket(qa, 1, log=quiet)
    ca = ba["compliance"]
    caught = ca[0] > c0[1] or ca[1] < c0[0]
    msg = f"[{ca[0]:.6f}, {ca[1]:.6f}] vs coarse [{c0[0]:.6f}, {c0[1]:.6f}]"
except Exception as e:                      # no fixed face left: no admissible stress field
    caught, msg = True, f"refused: {type(e).__name__}: {str(e)[:80]}"
print(f"MEASURED planted (a) unfixed bolt midpoints: {msg}")
check(caught, "planted (a): unfixed bolt midpoints — the bracket no longer agrees with the coarse problem")

# ---- planted (b): the RBE3 spread over the fine nodes — the same resultant, another traction
rb = RF.red_refine(d, planted="rbe3_over_fine_nodes")
ref_b, _, rn_b = rb["rbe3"][0]
flb = TF.rbe3_loads({n: list(X[idx[n]]) for n in rn_b + [ref_b]}, ref_b, rn_b, (0.0, 0.0, 1000.0), (0.0, 0.0, 0.0))
fb = np.zeros_like(fn)
for i, n in enumerate(rn_b):
    fb[idx[n]] += flb[i]
same_res = np.abs(fb.sum(0) - Fsum).max() < 1e-9 * 1000
diff = float(np.abs(fb - fn).max() / np.abs(fn).max())
print(f"MEASURED planted (b) RBE3 over the fine nodes: same resultant {same_res}; nodal loads differ from the coarse "
      f"traction's by {diff:.3f} of the largest")
check(same_res, "planted (b): the resultant is the same (a resultant check alone cannot see it)")
check(diff > 1e-3, "planted (b): the nodal loads are NOT the coarse traction's — caught")
try:
    TF.solve_cases(r, [{"F": (0.0, 0.0, 999.0), "M": (0.0, 0.0, 0.0)}], log=quiet)
    refused = False
except ValueError:
    refused = True
check(refused, "a refined deck refuses any load but its own traction")

if FAILS:
    print(f"REFINE RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"REFINE GREEN ({CHECKS} checks)")
