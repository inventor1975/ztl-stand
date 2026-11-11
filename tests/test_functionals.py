# -*- coding: utf-8 -*-
"""Level 3d (2026-11-12): ONE solve per load, ONE per functional — cadbracket.bracket_functionals combines the fields
v_f + s v_p (lower) and g_f + s g_p (upper, errfloat) instead of solving f + s p and f - s p from scratch.
Run: python3 tests/test_functionals.py

Checks, both sides:
  agreement — at the SAME explicit s the four numbers L(+-s), U(+-s) and both ends of the functional's bracket equal
    the present two-run bracket (two calls of cadbracket.bracket with --prestress-scale = +-s) to 1e-6 relative
    (the CG tolerance; the fields are the same minimisers, so the agreement is in fact much closer — printed);
  the compliance of f (s = 0) equals cadbracket.bracket's own bracket of f;
  KNOWN answers — the box of tests/test_prestress.py: the mean sigma_zz over the middle layer = F / A = 10 (3b, a
    constant extractor); tests/test_scl.py's beam: sigma_m = 10, sigma_b = 39 (3c, linear extractors, BOTH in one call);
  the chosen s* = sqrt(w_f / w_p) gives a bracket not wider than at deliberately poor s (s* / 8, 8 s*);
  a REFINED deck (red_refine, omega = the children of the coarse layer): the prestress-only load is posed (its own
    traction left off), the bracket contains 10 and overlaps the coarse one; a different traction is still refused;
  PLANTED (cadbracket.bracket_functionals(planted=...)) — each must turn a check RED:
    (i) g_p chosen and finished with the traction left on (the combined field then equilibrates f + s f, not f);
    (ii) the cross term X_f dropped; (iii) v_p combined with the wrong sign (v_f - s v_p).
"""
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


def load_box_deck():
    """box_deck of tests/test_prestress.py, read from its source (importing that module would run it)"""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_prestress.py")).read()
    ns = {"os": os, "tempfile": __import__("tempfile")}
    exec(src[src.index("def f8(x):"):src.index("def n2out(P, f):")], ns)
    return ns["box_deck"]


box_deck = load_box_deck()
quiet = lambda m: None
RTOL = 1e-6
LAYER = (-1, -1, 2.4, 11, 11, 7.6)                    # the middle layer 2.5 < z < 7.5 (n = 4: 192 tets, |omega| 500)


def rel(a, b, scale=None):
    scale = max(abs(a), abs(b), 1e-300) if scale is None else scale
    return abs(a - b) / scale


def two_run(path, load, pre, s):
    """the present path: two full runs of cadbracket.bracket with s and -s, the subtraction in exact rationals"""
    out = []
    for sv in (s, -s):
        sf = Fr(sv)
        pr = {"omega": pre["omega"]}
        if "S1" in pre:
            pr["S0"] = [[sf * x for x in rw] for rw in pre["S0"]]
            pr["S1"] = [[[sf * x for x in c] for c in rw] for rw in pre["S1"]]
        else:
            pr["sigma"] = [[sf * x for x in rw] for rw in pre["sigma"]]
        out.append(CB.bracket(path, dict(load, prestress=pr), log=quiet)["compliance"])
    (pl, ph), (ml, mh) = out
    S = Fr(s)
    return {"L_plus": pl, "U_plus": ph, "L_minus": ml, "U_minus": mh,
            "bracket": [float((Fr(pl) - Fr(mh)) / (4 * S)), float((Fr(ph) - Fr(ml)) / (4 * S))]}


def agree(new, old, what, tol=RTOL):
    """the four numbers and the bracket's ends; the ends relative to the bracket's scale (they may be near 0)"""
    worst = max(rel(new[k], old[k]) for k in ("L_plus", "U_plus", "L_minus", "U_minus"))
    sc = max(abs(old["bracket"][0]), abs(old["bracket"][1]), old["bracket"][1] - old["bracket"][0])
    worst_b = max(rel(new["bracket"][i], old["bracket"][i], sc) for i in (0, 1))
    ok = worst <= tol and worst_b <= tol
    if what:
        check(ok, f"{what}: the new bracket equals the two-run one (four numbers {worst:.1e}, ends {worst_b:.1e} "
                  f"relative; tolerance {tol:.0e})")
    return ok, worst, worst_b


def width(r):
    return r["bracket"][1] - r["bracket"][0]


def inside(r, x):
    return r["bracket"][0] <= x <= r["bracket"][1]


# ================================================================ 1. 3b, a constant extractor: mean sigma_zz = 10
p = box_deck(n=4)
d = TF.read_deck(p)
E, nu = d["mat"][0], d["mat"][1]
mask, volw = CB.omega_box(d, LAYER)
check(int(mask.sum()) == 192 and volw == 500, "omega = the middle layer: 192 tets, |omega| = 500")
sig_zz = CB.mean_stress_extractor("zz", E, nu, volw)
LOAD = {"F": (0.0, 0.0, 1000.0), "M": (0.0, 0.0, 0.0), "label": "pull"}
S_ZZ = 0.03125                                         # a dyadic s near test_prestress's sqrt(c_f / c_p)
fz = {"label": "mean zz", "omega": mask, "sigma": sig_zz}
r1 = CB.bracket_functionals(p, LOAD, [fz], s_values=[[S_ZZ]], log=quiet)
f1 = r1["functionals"][0]
e1 = f1["at_s"][0]
old1 = two_run(p, LOAD, fz, S_ZZ)
ok, a4, ab = agree(e1, old1, "3b zz at s = 1/32")
b0 = CB.bracket(p, 1, log=quiet)["compliance"]
check(rel(r1["compliance"][0], b0[0]) <= 1e-12 and rel(r1["compliance"][1], b0[1]) <= 1e-12,
      f"the compliance of f (s = 0) equals cadbracket.bracket's ({r1['compliance']} vs {b0})")
check(inside(f1, 10.0) and inside(e1, 10.0), f"3b zz: the exact 10 inside at s* ({f1['bracket']}) and at s = 1/32 "
      f"({e1['bracket']})")
for r_ in (f1, e1):
    check(r_["L_plus"] <= r_["U_plus"] and r_["L_minus"] <= r_["U_minus"], f"3b zz s = {r_['s']}: both compliance "
          f"brackets ordered")
poor = [CB.bracket_functionals(p, LOAD, [fz], s_values=[[f1["s"] / 8, f1["s"] * 8]], log=quiet)["functionals"][0]
        ["at_s"]][0]
check(all(width(f1) <= width(x) * (1 + 1e-9) for x in poor), f"3b zz: s* = {f1['s']:.6g} not wider "
      f"({width(f1):.6f}) than s*/8 ({width(poor[0]):.6f}) or 8 s* ({width(poor[1]):.6f})")
print(f"MEASURED 3b zz (box n = 4): s* = {f1['s']:.6g}, [{f1['bracket'][0]:.6f}, {f1['bracket'][1]:.6f}]; at s = 1/32 "
      f"new [{e1['bracket'][0]:.9f}, {e1['bracket'][1]:.9f}] two-run [{old1['bracket'][0]:.9f}, "
      f"{old1['bracket'][1]:.9f}] (four numbers agree to {a4:.1e}, ends {ab:.1e}); poor s widths "
      f"{width(poor[0]):.6f} / {width(poor[1]):.6f}; {r1['seconds']} s")

# ================================================================ 2. 3b, the HARD prestress: mean sigma_xx at the clamp
mx, vx = CB.omega_box(d, (2.4, 2.4, -1, 7.6, 7.6, 2.6))
sig_xx = CB.mean_stress_extractor("xx", E, nu, vx)
fx = {"label": "mean xx at the clamp", "omega": mx, "sigma": sig_xx}
S_XX = 0.025
r2 = CB.bracket_functionals(p, LOAD, [fx], s_values=[[S_XX]], log=quiet)
f2, e2 = r2["functionals"][0], r2["functionals"][0]["at_s"][0]
old2 = two_run(p, LOAD, fx, S_XX)
agree(e2, old2, "3b xx at the clamp, s = 0.025")
fe2 = (TF.solve_cases(d, [dict(LOAD, prestress={"omega": mx, "sigma": [[Fr(S_XX) * x for x in rw] for rw in sig_xx]})],
                      log=quiet)[0]["compliance_float"]
       - TF.solve_cases(d, [dict(LOAD, prestress={"omega": mx, "sigma": [[-Fr(S_XX) * x for x in rw] for rw in sig_xx]})],
                        log=quiet)[0]["compliance_float"]) / (4 * S_XX)
check(inside(f2, fe2) and inside(e2, fe2), f"3b xx: the float FE value {fe2:.5f} inside at s* and at s = 0.025")
check(width(f2) <= width(e2) * (1 + 1e-9), f"3b xx: s* = {f2['s']:.6g} not wider ({width(f2):.5f}) than s = 0.025 "
      f"({width(e2):.5f})")
print(f"MEASURED 3b xx (box n = 4, {f2['tets']} tets in omega): s* = {f2['s']:.6g} [{f2['bracket'][0]:.5f}, "
      f"{f2['bracket'][1]:.5f}] (width {width(f2):.5f}); s = 0.025 [{e2['bracket'][0]:.5f}, {e2['bracket'][1]:.5f}] "
      f"(two-run [{old2['bracket'][0]:.5f}, {old2['bracket'][1]:.5f}]); FE {fe2:.5f}")

# ================================================================ 3. 3c, linear extractors: membrane AND bending, ONE call
ey = [Fr(0), Fr(1), Fr(0)]
Pi_zz, _ = CB.tangent_projector([0.0, 0.0, 1.0], ey)
BEAM = {"F": (0.0, 500.0, 1000.0), "M": (10000.0, 0.0, 0.0), "label": "beam"}
EXACT = {"membrane": 10.0, "bending": float(Fr(6, 1000) * (Fr(10000) - 7 * Fr(500)))}           # 10 and 39
fun3 = []
for kind in ("membrane", "bending"):
    S0, S1 = CB.scl_extractor(kind, Pi_zz, ey, Fr(5), Fr(10), volw, E, nu)
    fun3.append({"label": kind, "omega": mask, "S0": S0, "S1": S1})
S3 = {"membrane": 0.03125, "bending": 0.25}
r3 = CB.bracket_functionals(p, BEAM, fun3, s_values=[[S3["membrane"]], [S3["bending"]]], log=quiet)
check(len(r3["functionals"]) == 2, "3c: membrane and bending from one call")
for fo in r3["functionals"]:
    kind = fo["label"]
    e3 = fo["at_s"][0]
    check(inside(fo, EXACT[kind]) and inside(e3, EXACT[kind]), f"3c {kind}: the exact {EXACT[kind]} inside at s* "
          f"({fo['bracket']}) and at s = {S3[kind]} ({e3['bracket']})")
    check(width(fo) <= width(e3) * (1 + 1e-9), f"3c {kind}: s* not wider than s = {S3[kind]}")
    old3 = two_run(p, BEAM, [f_ for f_ in fun3 if f_["label"] == kind][0], S3[kind])
    _, a4, ab = agree(e3, old3, f"3c {kind} at s = {S3[kind]}")
    print(f"MEASURED 3c {kind} (box n = 4): s* = {fo['s']:.6g} [{fo['bracket'][0]:.5f}, {fo['bracket'][1]:.5f}] "
          f"(width {100 * width(fo) / EXACT[kind]:.2f} % of {EXACT[kind]}); at s = {S3[kind]} [{e3['bracket'][0]:.5f}, "
          f"{e3['bracket'][1]:.5f}] vs two-run [{old3['bracket'][0]:.5f}, {old3['bracket'][1]:.5f}] ({a4:.1e} / "
          f"{ab:.1e}); CG {fo['cg_iterations']}")
print(f"MEASURED 3c both functionals in one call: {r3['seconds']} s (3 trace solves, 3 P1 solves)")

# ================================================================ 4. a REFINED deck: the prestress-only load is posed there
ru = RF.red_refine(d)
ru["refined_from"]["deck"] = p
q = os.path.join(os.path.dirname(p), "box_r1.deck.pkl")
with open(q, "wb") as fh:
    pickle.dump(ru, fh)
dr = TF.read_deck(q)
mr, vr = CB.children_of(dr, lambda co: CB.omega_box(co, LAYER))
check(vr == volw and int(mr.sum()) == 8 * 192, f"refined: omega = the children of the coarse layer ({int(mr.sum())} tets,"
      f" |omega| {float(vr)})")
ctx = TF.setup(dr, log=quiet)
try:
    Lp = TF.case_load(ctx, {"F": (0.0, 0.0, 0.0), "M": (0.0, 0.0, 0.0), "traction": False,
                            "prestress": {"omega": mr, "sigma": sig_zz}})
    posed = not Lp["fvec"].any() and Lp["ftot"].any()
except ValueError as ex:
    posed = False
    print("  refused:", ex)
check(posed, "refined: the prestress-only load (no traction) is posed")
try:
    TF.case_load(ctx, {"F": (0.0, 0.0, 500.0), "M": (0.0, 0.0, 0.0)})
    refused = False
except ValueError:
    refused = True
check(refused, "refined: a DIFFERENT traction is still refused")
try:
    TF.case_load(ctx, {"F": (0.0, 0.0, 500.0), "M": (0.0, 0.0, 0.0), "traction": False})
    refused0 = False
except ValueError:
    refused0 = True
check(refused0, "a load posed without traction but with F != 0 is refused (no silent zero)")
del ctx
sig_r = CB.mean_stress_extractor("zz", E, nu, vr)
fr_ = {"label": "mean zz (children)", "omega": mr, "sigma": sig_r}
r4 = CB.bracket_functionals(q, LOAD, [fr_], s_values=[[S_ZZ]], log=quiet)
f4, e4 = r4["functionals"][0], r4["functionals"][0]["at_s"][0]
check(inside(f4, 10.0) and inside(e4, 10.0), f"refined: the exact 10 inside ({f4['bracket']}, {e4['bracket']})")
check(max(f4["bracket"][0], f1["bracket"][0]) <= min(f4["bracket"][1], f1["bracket"][1]),
      "refined: the bracket overlaps the coarse one")
check(r4["compliance"][0] >= r1["compliance"][0] * (1 - 1e-9) and
      max(r4["compliance"][0], r1["compliance"][0]) <= min(r4["compliance"][1], r1["compliance"][1]),
      f"refined: the compliance of f overlaps the coarse one, its lower not lower ({r4['compliance']} vs "
      f"{r1['compliance']})")
old4 = two_run(q, LOAD, fr_, S_ZZ)
agree(e4, old4, "refined zz at s = 1/32")
print(f"MEASURED refined ({r4['tets']} tets): C(f) [{r4['compliance'][0]:.6f}, {r4['compliance'][1]:.6f}]; mean zz at s*"
      f" = {f4['s']:.6g} [{f4['bracket'][0]:.6f}, {f4['bracket'][1]:.6f}] (coarse [{f1['bracket'][0]:.6f}, "
      f"{f1['bracket'][1]:.6f}]); {r4['seconds']} s")

# ================================================================ 5. PLANTED errors — each must turn a check RED
# "caught" = what the checks above test: the agreement with the two-run bracket at the same s, the known value inside,
# the compliance brackets ordered
cases = [("3b zz", p, LOAD, [fz], S_ZZ, old1, 10.0), ("3b xx", p, LOAD, [fx], S_XX, old2, fe2),
         ("3c bending", p, BEAM, [fun3[1]], S3["bending"], two_run(p, BEAM, fun3[1], S3["bending"]), EXACT["bending"])]
for plant in ("gp_traction", "drop_xf", "vp_sign"):
    caught_all = []
    for nm, path, load, fun, s_, old, want in cases:
        w = CB.bracket_functionals(path, load, fun, s_values=[[s_]], log=quiet, planted=plant)["functionals"][0]
        ew = w["at_s"][0]
        agrees = agree(ew, old, None)[0]
        has = inside(ew, want) and inside(w, want)
        ordered = all(x["L_plus"] <= x["U_plus"] and x["L_minus"] <= x["U_minus"] for x in (w, ew))
        caught = not agrees or not has or not ordered
        caught_all.append(caught)
        print(f"  planted {plant}, {nm}: at s = {s_} [{ew['bracket'][0]:.5f}, {ew['bracket'][1]:.5f}] vs two-run "
              f"[{old['bracket'][0]:.5f}, {old['bracket'][1]:.5f}]; agrees {agrees}, known value inside {has}, "
              f"ordered {ordered} -> {'CAUGHT' if caught else 'NOT caught'}")
    check(all(caught_all), f"planted {plant}: caught on every case ({caught_all})")

print(f"{CHECKS - len(FAILS)}/{CHECKS} checks passed")
if FAILS:
    print(f"FUNCTIONALS RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"FUNCTIONALS GREEN ({CHECKS} checks)")
