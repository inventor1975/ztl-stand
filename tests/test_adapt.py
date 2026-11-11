# -*- coding: utf-8 -*-
"""Indicator-driven refinement (2026-11-11): the per-tet HYPERCIRCLE indicator eta_T^2 = ||tau - alpha C eps(u)||^2_T
and Doerfler marking, with red-green closure (ustand.refine.graded_refine). Run: python3 tests/test_adapt.py

Checks, both sides:
  identity — sum eta_T^2 equals the bracket's gap (upper - lower) on the box: traction, the 3b prestress (both signs),
    the 3c linear extractor (bending, both signs); no tet negative beyond rounding;
  PLANTED wrong tau — a tau that is not admissible for the load (the face data scaled by 1.05) breaks the identity;
  omega — on every round the region is the children of the coarse slab, |omega| EXACTLY the coarse one;
  marking — two rounds by the indicator against two rounds of a SHUFFLED indicator (the same number of tets marked,
    chosen at random) and against a BALL of the same count around the slab centre; what came out is recorded, and the
    indicator must not be worse than the shuffled one (a useless indicator would show here).

MEASURED 2026-11-11 (box n = 4):
  identity: traction sum 0.060550486784 = the gap; 3c bending (the beam load of tests/test_scl.py) s = +-3/10:
    24.8342878601 / 16.3061782402 = the gaps to 10 digits; min eta^2 > 0.
  planted: tau x 1.05 -> sum 0.066757 vs the gap 0.060550; sign-flipped face data on half the tets -> 0.575305.
  rounds (theta = 0.5, mean sigma_zz over the middle layer, exact 10, coarse width 0.30275):
    indicator 30 / 126 marked -> 906 / 2690 tets, width 0.18997 -> 0.11440;
    shuffled (the same marked counts at random) -> 1506 / 3065 tets, 0.22982 -> 0.21842;
    ball (the same marked counts nearest the centre) -> 804 / 1224 tets, 0.29949 -> 0.29944.
  The indicator halves the width of a random marking at fewer tets; a ball at the box centre (where the uniform
  pull has little error) gains almost nothing."""
import os
import pickle
import sys
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetfea as TF, refine as RF, cadbracket as CB                       # noqa: E402

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_refine.py")).read()
_ns = {"os": os, "tempfile": __import__("tempfile")}
exec(src[src.index("def f8(x):"):src.index("def vol6(P):")], _ns)
box_deck = _ns["box_deck"]
quiet = lambda m: None


def save(deck, where, name):
    q = os.path.join(where, name)
    with open(q, "wb") as f:
        pickle.dump(deck, f)
    return q


p = box_deck(n=4)
where = os.path.dirname(p)
d = TF.read_deck(p)

# ---- 1. the identity: sum eta^2 = upper - lower
r = CB.bracket(p, 1, log=quiet, dump_eta="return")
e = r["eta"]
print(f"MEASURED traction: sum eta^2 {e['sum']:.12f}, gap {e['gap']:.12f}, min eta^2 {e['min']:.3e}")
check(abs(e["sum"] - e["gap"]) <= 1e-8 * e["gap"], "traction: sum eta^2 = the gap (hypercircle)")
check(e["min"] >= -1e-12 * e["gap"], "traction: no tet negative beyond rounding")

layer = (-1, -1, 2.5 - 1e-6, 11, 11, 7.5 + 1e-6)
m3b, v3b = CB.omega_box(d, layer)
sig = CB.mean_stress_extractor("zz", d["mat"][0], d["mat"][1], v3b)
for sg in (Fr(1, 10), -Fr(1, 10)):
    sub = {"F": (0.0, 0.0, 1000.0), "M": (0.0, 0.0, 0.0), "label": "pull",
           "prestress": {"omega": m3b, "sigma": [[sg * x for x in row] for row in sig]}}
    e = CB.bracket(p, sub, log=quiet, dump_eta="return")["eta"]
    check(abs(e["sum"] - e["gap"]) <= 1e-8 * e["gap"], f"3b s = {sg}: sum eta^2 = the gap ({e['sum']:.10f} vs "
          f"{e['gap']:.10f})")

# the beam of tests/test_scl.py: bending of sigma_zz on the middle layer, exact 0.006 (M_x - 7 F_y) = 39
Fz, Mx, Fy = 1000.0, 10000.0, 500.0
ey = [Fr(0), Fr(1), Fr(0)]
Pi_zz, _ = CB.tangent_projector([0.0, 0.0, 1.0], ey)
EXACT = Fr(6, 1000) * (Fr(10000) - 7 * Fr(500))
slab = (-1, -1, 2.4, 11, 11, 7.6)


def scl_load(deck, sv, mask, vol):
    S0, S1 = CB.scl_extractor("bending", Pi_zz, ey, Fr(5), Fr(10), vol, deck["mat"][0], deck["mat"][1])
    return {"F": (0.0, Fy, Fz), "M": (Mx, 0.0, 0.0), "label": "t",
            "prestress": {"omega": mask, "S0": [[sv * x for x in rw] for rw in S0],
                          "S1": [[[sv * x for x in cc] for cc in rw] for rw in S1]}}


mc, vc = CB.omega_box(d, slab)
s_b = Fr(3, 10)
etas0 = []
for sv in (s_b, -s_b):
    rb = CB.bracket(p, scl_load(d, sv, mc, vc), log=quiet, dump_eta="return")
    e = rb["eta"]
    etas0.append(rb["_eta_array"])
    print(f"MEASURED 3c bending s = {sv}: sum eta^2 {e['sum']:.10f}, gap {e['gap']:.10f}")
    check(abs(e["sum"] - e["gap"]) <= 1e-8 * e["gap"], f"3c bending s = {sv}: sum eta^2 = the gap")
    check(e["min"] >= -1e-12 * e["gap"], f"3c bending s = {sv}: no tet negative beyond rounding")

# ---- 2. PLANTED: a tau not admissible for the load breaks the identity (through eta_indicator itself)
rr = CB.bracket(p, 1, log=quiet, dump_eta="return")
P_ = rr["_eta_parts"]
eta_h, _ = CB.eta_indicator(P_["X"], P_["T"], P_["G"], P_["energy"], P_["u"], P_["E"], P_["nu"])
check(abs(eta_h.sum() - rr["eta"]["gap"]) <= 1e-8 * rr["eta"]["gap"], "control: the honest inputs give the gap")
# (a) tau x 1.05: admissible for 1.05 l, not for l
eta_a, _ = CB.eta_indicator(P_["X"], P_["T"], 1.05 * P_["G"], 1.05 ** 2 * P_["energy"], P_["u"], P_["E"], P_["nu"])
print(f"MEASURED planted tau x 1.05: sum eta^2 {eta_a.sum():.6f} vs the gap {rr['eta']['gap']:.6f}")
check(abs(eta_a.sum() - rr["eta"]["gap"]) > 1e-3 * rr["eta"]["gap"], "PLANTED tau x 1.05: the identity FAILS")
# (b) the face data of half the tets flipped in sign (a field that is no longer continuous across faces)
Gb = P_["G"].copy()
Gb[::2] *= -1
eta_b, _ = CB.eta_indicator(P_["X"], P_["T"], Gb, P_["energy"], P_["u"], P_["E"], P_["nu"])
print(f"MEASURED planted sign-flipped face data: sum eta^2 {eta_b.sum():.6f} vs the gap {rr['eta']['gap']:.6f}")
check(abs(eta_b.sum() - rr["eta"]["gap"]) > 1e-3 * rr["eta"]["gap"], "PLANTED sign-flipped tau: the identity FAILS")

# ---- 3. two rounds: indicator vs shuffled indicator vs a ball of the same count, the same omega every round.
# A refined deck carries the traction of ONE load (its subcase 1: the pull F = 1000 on the box), so the rounds use
# the 3b mean sigma_zz over the middle layer, exact F / A = 10 (the beam load above is for the coarse identity only).
s_m = Fr(1, 10)


def mean_bracket(path, deck, children):
    if children:
        mask, vol = CB.children_of(deck, lambda co: CB.omega_box(co, layer))
    else:
        mask, vol = CB.omega_box(deck, layer)
    sg_ = CB.mean_stress_extractor("zz", deck["mat"][0], deck["mat"][1], vol)
    out, eta = [], np.zeros(len(deck["tets"]))
    for sv in (s_m, -s_m):
        sub = {"F": (0.0, 0.0, 1000.0), "M": (0.0, 0.0, 0.0), "label": "pull",
               "prestress": {"omega": mask, "sigma": [[sv * x for x in row] for row in sg_]}}
        b = CB.bracket(path, sub, log=quiet, dump_eta="return")
        out.append(b["compliance"])
        eta = eta + b["_eta_array"]
    (pl, ph), (ml, mh) = out
    s = float(s_m)
    return (pl - mh) / (4 * s), (ph - ml) / (4 * s), eta, vol


def centroids(deck):
    g = deck["grids"]
    return np.array([np.mean([[float(TF._nas(x)) for x in g[n]] for n in t], axis=0) for t in deck["tets"]])


rng = np.random.default_rng(0)
lo0, hi0, eta0, vol0 = mean_bracket(p, d, False)
check(lo0 <= 10 <= hi0, f"coarse: the exact 10 inside [{lo0:.5f}, {hi0:.5f}]")
runs = {}
for how in ("indicator", "shuffled", "ball"):
    deck, path, eta = d, p, eta0
    hist = []
    for rnd in (1, 2):
        mk = CB.doerfler(eta, 0.5)
        k_ = int(mk.sum())
        if how == "shuffled":
            mk = np.zeros(len(eta), bool)
            mk[rng.choice(len(eta), k_, replace=False)] = True
        elif how == "ball":
            c = centroids(deck)
            dist = np.linalg.norm(c - np.array([5.0, 5.0, 5.0]), axis=1)
            mk = np.zeros(len(eta), bool)
            mk[np.argsort(dist)[:k_]] = True
        nd = RF.graded_refine(deck, mk)
        nd["refined_from"]["deck"] = p
        o_, h_ = RF.conformity(nd)
        check(o_ == 0 and h_ == 0, f"{how} round {rnd}: conforming ({o_}, {h_})")
        path = save(nd, where, f"box_adapt_{how}_{rnd}.deck.pkl")
        deck = nd
        lo_, hi_, eta, vol_ = mean_bracket(path, deck, True)
        check(vol_ == vol0, f"{how} round {rnd}: |omega| EXACTLY the coarse one ({float(vol_)})")
        check(lo_ <= 10 <= hi_, f"{how} round {rnd}: the exact 10 inside [{lo_:.5f}, {hi_:.5f}]")
        hist.append((len(nd["tets"]), k_, hi_ - lo_))
    runs[how] = hist
    print(f"MEASURED {how}: " + "; ".join(f"round {i + 1}: {n} tets ({m} marked), width {w:.5f}"
                                          for i, (n, m, w) in enumerate(hist)) + f" (coarse {hi0 - lo0:.5f})")
wi, ws, wb = runs["indicator"][-1][2], runs["shuffled"][-1][2], runs["ball"][-1][2]
check(wi <= ws * (1 + 1e-9), f"the indicator is not worse than a SHUFFLED indicator after 2 rounds ({wi:.5f} vs "
      f"{ws:.5f})")
print(f"MEASURED after 2 rounds: indicator {wi:.5f} ({runs['indicator'][-1][0]} tets), shuffled {ws:.5f} "
      f"({runs['shuffled'][-1][0]}), ball {wb:.5f} ({runs['ball'][-1][0]}) — recorded; the ball comparison is not a "
      f"pass/fail check")

if FAILS:
    print(f"ADAPT RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"ADAPT GREEN ({CHECKS} checks)")
