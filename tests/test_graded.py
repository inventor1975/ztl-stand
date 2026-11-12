# -*- coding: utf-8 -*-
"""ustand.refine.graded_refine (2026-11-11): LOCAL red-green refinement posing THE SAME continuum problem, conforming.
Run: python3 tests/test_graded.py

Checks, both sides:
  conformity — no face shared by more than 2 tets, no hanging edge (an edge whose midpoint is a node while the edge
    itself is still used); a PLANTED run without the green closure must show hanging edges;
  geometry — every coarse tet is filled EXACTLY by its children (rational volumes), orientation kept, total 1000;
  load — the fine consistent loads of the coarse traction have the coarse resultant force and moment;
  brackets — on the box, the graded bracket overlaps the coarse one, its lower bound is >= the coarse lower bound
    (the conforming P1 spaces nest), its gap is not larger;
  a second level on the graded deck — still conforming; the parent map still points to the ORIGINAL coarse tets;
  a KNOWN answer — mean sigma_zz over the middle layer = F / A = 10, by omega = the children of the coarse layer.

MEASURED 2026-11-11 (box n = 4, the ball (5, 5, 8.5) r 3.2): 46 of 384 tets marked -> 910 tets, patterns none 238 /
one 56 / face 40 / red 50, closure in 2 rounds. PLANTED no closure: 67 hanging edges (0 faces in > 2 tets — the
hanging node shows only as an edge check). C: coarse [0.515420, 0.575970] 11.75 %, graded [0.518896, 0.573380]
10.50 %, a second level [0.520233, 0.573119] 10.17 % (3904 tets). Mean sigma_zz (exact 10): coarse [9.84862,
10.15138], graded [9.86379, 10.13621]."""
# The default lower side became P2 on 2026-11-12; this file tests the P1 path, so it asks for lower="p1" explicitly.
import os
import pickle
import sys
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ustand import tetfea as TF, refine as RF, cadbracket as CB, tetmesh as TM, equil as EQ          # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


def load_box_deck():
    """box_deck of tests/test_refine.py, read from its source (importing that module would run it)"""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_refine.py")).read()
    start = src.index("def f8(x):")
    end = src.index("def vol6(P):")
    ns = {"os": os, "tempfile": __import__("tempfile")}
    exec(src[start:end], ns)
    return ns["box_deck"]


box_deck = load_box_deck()


def vol6(P):
    a = [[P[k + 1][r] - P[0][r] for k in range(3)] for r in range(3)]
    return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))


def save(deck, where, name):
    q = os.path.join(where, name)
    with open(q, "wb") as f:
        pickle.dump(deck, f)
    return q


def ball_mask(deck, c, r):
    g = deck["grids"]
    out = []
    for t in deck["tets"]:
        P = np.array([[float(TF._nas(x)) for x in g[n]] for n in t])
        out.append(bool(np.linalg.norm(P.mean(0) - np.asarray(c)) < r))
    return np.array(out)


quiet = lambda s: None
p = box_deck(n=4)
where = os.path.dirname(p)
d = TF.read_deck(p)

# the zone touches the LOADED top face (z = 10): loaded midpoints get the coarse traction's mean
marked = ball_mask(d, (5.0, 5.0, 8.5), 3.2)
r = RF.graded_refine(d, marked)
r["refined_from"]["deck"] = p
q = save(r, where, "box_g1.deck.pkl")
pats = r["refined_from"]["patterns"]
print(f"MEASURED box n=4: {int(marked.sum())} of {len(d['tets'])} tets marked -> {len(r['tets'])} tets; patterns {pats};"
      f" closure rounds {r['refined_from']['closure_rounds']}")
check(pats.get("none", 0) > 0 and pats.get("red", 0) > 0 and (pats.get("one", 0) + pats.get("opp", 0)
                                                              + pats.get("face", 0)) > 0,
      "the run has untouched, red AND green tets (the transition is exercised)")

# ---- conformity, both sides
over, hang = RF.conformity(r)
check(over == 0 and hang == 0, f"conforming: no face in > 2 tets ({over}), no hanging edge ({hang})")
rp = RF.graded_refine(d, marked, planted="no_closure")
over_p, hang_p = RF.conformity(rp)
print(f"MEASURED planted no_closure: faces in > 2 tets {over_p}, hanging edges {hang_p}")
check(hang_p > 0, f"PLANTED (no green closure): the conformity check SEES hanging edges ({hang_p})")

# ---- geometry, exact
Xd = {n: [TF._nas(c) for c in r["grids"][n]] for n in r["grids"]}
Xc = {n: [TF._nas(c) for c in d["grids"][n]] for n in d["grids"]}
kids = {}
for j, pa in enumerate(r["parent"]):
    kids.setdefault(pa, []).append(j)
ok_fill = ok_sign = True
for i, t in enumerate(d["tets"]):
    V = vol6([Xc[n] for n in t])
    vs = [vol6([Xd[n] for n in r["tets"][j]]) for j in kids[i]]
    ok_fill &= (sum(vs) == V)
    ok_sign &= all((v > 0) == (V > 0) for v in vs)
check(ok_fill, "every coarse tet is filled EXACTLY by its children (the sum of their rational volumes)")
check(ok_sign, "every child keeps its parent's orientation")
total = sum(abs(vol6([Xd[n] for n in t])) for t in r["tets"]) / 6
check(total == 1000, f"the graded volume is exactly 1000 ({total})")

# ---- the load: the same resultant
ids = sorted(r["grids"])
idx = {n: i for i, n in enumerate(ids)}
X = np.array([[float(c) for c in Xd[n]] for n in ids])
T = np.array([[idx[n] for n in t] for t in r["tets"]])
Fm, own, _, _ = TM.faces(T)
fixed = {idx[n] for ind, deps in r["rbe2"] for n in deps if r["spc"].get(ind, "").startswith("123")}
kind = TM.classify(Fm, own, fixed, {idx[n] for n in r["traction"]["nodal"]})
fn = RF.traction_loads(X, Fm, kind, {idx[n]: v for n, v in r["traction"]["nodal"].items()})
Fsum, Msum = fn.sum(0), np.cross(X, fn).sum(0)
cid = sorted(d["grids"])
cidx = {n: i for i, n in enumerate(cid)}
Xcf = np.array([[float(TF._nas(c)) for c in d["grids"][n]] for n in cid])
ref, _, rn = d["rbe3"][0]
fl = TF.rbe3_loads({n: list(Xcf[cidx[n]]) for n in rn + [ref]}, ref, rn, (0.0, 0.0, 1000.0), (0.0, 0.0, 0.0))
Fc = fl.sum(0)
Mc = sum(np.cross(Xcf[cidx[n]], fl[i]) for i, n in enumerate(rn))
check(np.abs(Fsum - Fc).max() < 1e-9 * 1000, f"graded resultant force = coarse ({Fsum} vs {Fc})")
check(np.abs(Msum - Mc).max() < 1e-9 * 1e4, f"graded resultant moment = coarse ({Msum} vs {Mc})")
check(any(n not in d["grids"] for n in r["traction"]["nodal"]), "the zone reaches the loaded face: midpoints carry t")

# ---- brackets
bc = CB.bracket(p, 1, log=quiet, lower="p1")
bg = CB.bracket(q, 1, log=quiet, lower="p1")
c0, c1 = bc["compliance"], bg["compliance"]
print(f"MEASURED box n=4: coarse C in [{c0[0]:.6f}, {c0[1]:.6f}] ({100 * bc['gap']:.2f} %), graded "
      f"[{c1[0]:.6f}, {c1[1]:.6f}] ({100 * bg['gap']:.2f} %)")
check(max(c0[0], c1[0]) <= min(c0[1], c1[1]), "the graded bracket OVERLAPS the coarse one (both contain C)")
check(c1[0] >= c0[0] * (1 - 1e-9), "the graded lower bound >= the coarse one (conforming P1 spaces nest)")
check(bg["gap"] <= bc["gap"] * (1 + 1e-9), "the graded gap is not larger")

# ---- a second level on the graded deck (the zone again), parent map to the ORIGINAL coarse tets
m2 = ball_mask(r, (5.0, 5.0, 8.5), 3.2)
r2 = RF.graded_refine(r, m2)
check(r2["refined_from"]["deck"] == p, "a second level keeps the ORIGINAL coarse deck as its root")
o2, h2 = RF.conformity(r2)
check(o2 == 0 and h2 == 0, f"second level conforming ({o2}, {h2}); {len(r2['tets'])} tets")
check(max(r2["parent"]) < len(d["tets"]) and len(r2["parent"]) == len(r2["tets"]),
      "second level: every tet maps to an ORIGINAL coarse tet")
q2 = save(r2, where, "box_g2.deck.pkl")
bg2 = CB.bracket(q2, 1, log=quiet, lower="p1")
c2 = bg2["compliance"]
print(f"MEASURED box n=4 second level: [{c2[0]:.6f}, {c2[1]:.6f}] ({100 * bg2['gap']:.2f} %), {len(r2['tets'])} tets")
check(max(c1[0], c2[0]) <= min(c1[1], c2[1]) and c2[0] >= c1[0] * (1 - 1e-9),
      "second level: overlaps the first, lower bound not lower")

# ---- the known answer through children_of on the graded deck: mean sigma_zz over the middle layer = 10
layer = [-1, -1, 10 / 4 * 2 - 1e-6 - 2.5, 11, 11, 10 / 4 * 3 + 1e-6]   # coarse tets of 2.5 < z_centroid < 7.5


def mean_bracket(path, s, children):
    dk = TF.read_deck(path)
    if children:
        mask, vol = CB.children_of(dk, lambda co: CB.omega_box(co, layer))
    else:
        mask, vol = CB.omega_box(dk, layer)
    sig = CB.mean_stress_extractor("zz", dk["mat"][0], dk["mat"][1], vol)
    out = []
    for sg in (s, -s):
        sub = {"F": (0.0, 0.0, 1000.0), "M": (0.0, 0.0, 0.0), "label": "pull",
               "prestress": {"omega": mask, "sigma": [[sg * x for x in row] for row in sig]}}
        out.append(CB.bracket(path, sub, log=quiet, lower="p1")["compliance"])
    (pl, ph), (ml, mh) = out
    s = float(s)
    return (pl - mh) / (4 * s), (ph - ml) / (4 * s), int(mask.sum()), vol


s = Fr(1, 10)
lc = mean_bracket(p, s, False)
lg = mean_bracket(q, s, True)
print(f"MEASURED mean sigma_zz over the middle layer (exact 10): coarse [{lc[0]:.5f}, {lc[1]:.5f}] ({lc[2]} tets), "
      f"graded [{lg[0]:.5f}, {lg[1]:.5f}] ({lg[2]} tets)")
check(lg[3] == lc[3], f"children_of on the graded deck: |omega| is EXACTLY the coarse one ({float(lg[3])})")
check(lc[0] <= 10 <= lc[1], "coarse: the exact mean 10 inside")
check(lg[0] <= 10 <= lg[1], "graded: the exact mean 10 inside")
check(lg[1] - lg[0] <= (lc[1] - lc[0]) * (1 + 1e-9), "graded: the mean's bracket is not wider")

# ---- the uniform red refinement still maps by its parent list (8i .. 8i+7)
ru = RF.red_refine(d)
check(ru["parent"] == [i for i in range(len(d["tets"])) for _ in range(8)], "red_refine's parent map is 8i .. 8i+7")
ou, hu = RF.conformity(ru)
check(ou == 0 and hu == 0, "the uniform red refinement is conforming too")

# ---- MANY ROUNDS (2026-11-11): a green tet is never refined and Bey's order is kept, so the shapes stay bounded
def quality(deck):
    """volume / longest edge^3, scaled to 1 on the regular tet."""
    g = deck["grids"]
    Xq = {n: np.array([float(TF._nas(c)) for c in g[n]]) for n in g}
    P = np.array([[Xq[n] for n in t] for t in deck["tets"]])
    vol = np.abs(np.einsum("ni,ni->n", P[:, 1] - P[:, 0], np.cross(P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]))) / 6
    ed = np.stack([np.linalg.norm(P[:, a] - P[:, b], axis=1) for a, b in RF.EDGES], 1)
    return vol / ed.max(1) ** 3 * 6 * np.sqrt(2)


def resultant(deck):
    Xr = {n: [TF._nas(c) for c in deck["grids"][n]] for n in deck["grids"]}
    ids_ = sorted(deck["grids"])
    ix = {n: i for i, n in enumerate(ids_)}
    Xn = np.array([[float(c) for c in Xr[n]] for n in ids_])
    Tn = np.array([[ix[n] for n in t] for t in deck["tets"]])
    Fq, ow, _, _ = TM.faces(Tn)
    fx = {ix[n] for ind, deps in deck["rbe2"] for n in deps if deck["spc"].get(ind, "").startswith("123")}
    kd = TM.classify(Fq, ow, fx, {ix[n] for n in deck["traction"]["nodal"]})
    f_ = RF.traction_loads(Xn, Fq, kd, {ix[n]: v for n, v in deck["traction"]["nodal"].items()})
    return f_.sum(0), np.cross(Xn, f_).sum(0)


def rounds(planted, n_rounds=5):
    dk, qs, conf = d, [], []
    for k in range(n_rounds):
        dk = RF.graded_refine(dk, ball_mask(dk, (5.0, 5.0, 8.5), 3.2 / 1.5 ** k), planted=planted)
        qs.append(float(quality(dk).min()))
        conf.append(RF.conformity(dk))
    return dk, qs, conf


d5, q5, c5 = rounds(None)
print(f"MEASURED 5 rounds toward (5, 5, 8.5): {len(d5['tets'])} tets, worst quality by round {[round(x, 4) for x in q5]}"
      f" (coarse {float(quality(d).min()):.4f})")
check(all(c == (0, 0) for c in c5), f"5 rounds: conforming after every round ({c5})")
check(all(x >= q5[0] * (1 - 1e-9) for x in q5), "5 rounds: the worst quality never falls below round 1's")
_, qp, _ = rounds("green_on_green", 2)
print(f"MEASURED planted green_on_green: worst quality by round {[round(x, 4) for x in qp]}")
check(qp[1] < 0.5 * q5[1], f"PLANTED (green tets refined): the quality check SEES it ({qp[1]:.4f} against {q5[1]:.4f})")
X5 = {n: [TF._nas(c) for c in d5["grids"][n]] for n in d5["grids"]}
kids5 = {}
for j, pa in enumerate(d5["parent"]):
    kids5.setdefault(pa, []).append(j)
check(all(sum(vol6([X5[n] for n in d5["tets"][j]]) for j in kids5[i]) == vol6([Xc[n] for n in t])
          for i, t in enumerate(d["tets"])), "5 rounds: every coarse tet is filled EXACTLY by its descendants")
check(all((vol6([X5[n] for n in d5["tets"][j]]) > 0) == (vol6([Xc[n] for n in d["tets"][pa]]) > 0)
          for j, pa in enumerate(d5["parent"])), "5 rounds: every tet keeps its root's orientation")
F5, M5 = resultant(d5)
check(np.abs(F5 - Fc).max() < 1e-9 * 1000 and np.abs(M5 - Mc).max() < 1e-9 * 1e4,
      f"5 rounds: the resultant is the coarse one ({F5}, {M5})")
check(len(d5["traction"]["nodal"]) > len(r["traction"]["nodal"]), "5 rounds: the load face is refined further")
# all marked = uniform red, three times: Bey's order kept -> the Kuhn tets of the box stay Kuhn tets
du = d
for _ in range(3):
    du = RF.graded_refine(du, np.ones(len(du["tets"]), bool))
qu = quality(du)
check(len(du["tets"]) == 512 * len(d["tets"]) and abs(float(qu.min()) - float(quality(d).min())) < 1e-9,
      f"3 uniform red rounds: {len(du['tets'])} tets, the worst quality stays the coarse one ({float(qu.min()):.4f})")

if FAILS:
    print(f"GRADED RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"GRADED GREEN ({CHECKS} checks)")
