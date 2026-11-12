# -*- coding: utf-8 -*-
"""The P2 lower side (ustand.tetfea2, 2026-11-12): v quadratic on the deck's own tets. Run: python3 tests/test_p2.py

Checks:
  boxes n = 3, 4, a red-refined and a graded box (cadbracket.bracket(lower="p2")): the P2 lower bound >= the P1 one and
    <= the proved upper bound; the gaps P1 vs P2 MEASURED;
  a(v, v): the errfloat bound >= the exact Fraction and within 1e-10 of it; the exact-integer bound >= the exact;
  PINNED to the proved P1 code — a P1 field embedded in P2 (midpoints = the means of the ends):
    a_upper_exact2 == tetfea.a_upper_exact BIT FOR BIT; the prestress work (3b constant, 3c linear) == tetfea's EXACTLY;
    the traction work == tetfea.traction_work_exact EXACTLY for a flux q whose P1 consistent loads are exact integers;
  INDEPENDENT quadratures for a genuinely quadratic v (the solved field): a(v, v) by the 4-point degree-2 rule, the
    traction work by the 7-point degree-5 triangle rule, the 3c prestress by the 4-point rule — in floats, to 1e-9;
  Galerkin: the proved W^2 / a_up equals the float f . u of the P2 solve to 1e-9 (the float stiffness and loads are a
    third, separate code path);
  the support faces: every vertex and midpoint dof zero (tetfea2.check_admissible);
  level 3d with P2 on the box n = 4: the exact mean sigma_zz = 10 inside, sigma_m = 10 and sigma_b = 39 inside, each
    bracket not wider than with P1;
  PLANTED (tetfea2._PLANTED) — each must turn a check RED: "a_weight" (1/24 for 1/20 in a(v, v), both routes),
    "free_midpoint" (one support-face midpoint left free), "traction_p1" (the P1 traction formula on a P2 field).
"""
import os
import pickle
import sys
import tempfile
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetfea as TF, tetfea2 as T2, refine as RF, cadbracket as CB, tetmesh as TM      # noqa: E402

CHECKS, FAILS = 0, []
S = TF.S
quiet = lambda m: None


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


def load_box_deck():
    """box_deck of tests/test_prestress.py, read from its source (importing that module would run it)"""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_prestress.py")).read()
    ns = {"os": os, "tempfile": tempfile}
    exec(src[src.index("def f8(x):"):src.index("def n2out(P, f):")], ns)
    return ns["box_deck"]


box_deck = load_box_deck()


def rel(a, b):
    return abs(float(a) - float(b)) / max(abs(float(a)), abs(float(b)), 1e-300)


# ------------------------------------------------------------------------------------------------ independent rules
HAMMER_A, HAMMER_B = 0.5854101966249685, 0.1381966011250105
TET4 = [[HAMMER_A if i == j else HAMMER_B for i in range(4)] for j in range(4)]          # weights 1/4 each
# the 7-point degree-5 triangle rule (Radon / Dunavant), weights relative to the area
_s15 = np.sqrt(15.0)
_a1, _b1 = (9 - 2 * _s15) / 21, (6 + _s15) / 21
_a2, _b2 = (9 + 2 * _s15) / 21, (6 - _s15) / 21
_w1, _w2 = (155 + _s15) / 1200, (155 - _s15) / 1200
TRI7 = ([(1 / 3, 1 / 3, 1 / 3, 9 / 40)]
        + [p + (_w1,) for p in ((_a1, _b1, _b1), (_b1, _a1, _b1), (_b1, _b1, _a1))]
        + [p + (_w2,) for p in ((_a2, _b2, _b2), (_b2, _a2, _b2), (_b2, _b2, _a2))])


def grad_at(ctx, V, lam):
    """grad v (nt, 3, 3) at the barycentric point lam (4,) of every tet, from the shape functions directly"""
    g = ctx["grads"]
    Vn = np.asarray(V, float).reshape(-1, 3) / 2.0 ** S
    nodes = np.concatenate([ctx["T"], ctx["nv"] + ctx["te"]], axis=1)
    G = np.zeros((len(g), 3, 3))
    for a in range(4):
        G += np.einsum("nc,nb->ncb", Vn[nodes[:, a]], (4 * lam[a] - 1) * g[:, a])
    for e, (i, j) in enumerate(T2.LE):
        G += np.einsum("nc,nb->ncb", Vn[nodes[:, 4 + e]], 4 * (lam[j] * g[:, i] + lam[i] * g[:, j]))
    return G


def a_quadrature(ctx, V):
    mu, lam = float(ctx["mu"]), float(ctx["lam"])
    tot = 0.0
    for pt in TET4:
        G = grad_at(ctx, V, pt)
        eps = 0.5 * (G + np.transpose(G, (0, 2, 1)))
        dens = 2 * mu * (eps * eps).sum(axis=(1, 2)) + lam * np.trace(eps, axis1=1, axis2=2) ** 2
        tot += 0.25 * float((ctx["vol"] * dens).sum())
    return tot


def prestress_quadrature(ctx, pre, om, V):
    S0 = np.array([[float(x) for x in r] for r in pre["S0"]])
    S1 = np.array([[[float(x) for x in c] for c in r] for r in pre["S1"]])
    tot = 0.0
    for pt in TET4:
        G = grad_at(ctx, V, pt)[om]
        x = np.einsum("k,nkr->nr", np.array(pt), ctx["P"][om])
        sg = S0[None] + np.einsum("ijk,nk->nij", S1, x)
        tot += 0.25 * float((ctx["vol"][om] * np.einsum("ncb,ncb->n", G, sg)).sum())
    return tot


def traction_quadrature(ctx, q, V):
    X, Fm, fk, nv = ctx["X"], ctx["F"], ctx["fedge"], ctx["nv"]
    Vn = np.asarray(V, float).reshape(-1, 3) / 2.0 ** S
    lf = np.where(np.abs(q).reshape(len(q), -1).max(axis=1) > 0)[0]
    tot = 0.0
    for f in lf:
        a, b, c = Fm[f]
        A = 0.5 * np.linalg.norm(np.cross(X[b] - X[a], X[c] - X[a]))
        t_nodes = q[f] / (2 * A)
        vv = Vn[[a, b, c]]
        ve = Vn[nv + fk[f]]
        for l0, l1, l2, w in TRI7:
            L = (l0, l1, l2)
            t = sum(L[p] * t_nodes[p] for p in range(3))
            v = sum(L[i] * (2 * L[i] - 1) * vv[i] for i in range(3)) \
                + sum(4 * L[i] * L[j] * ve[e] for e, (i, j) in enumerate(T2.FE))
            tot += A * w * float(t @ v)
    return tot


# ------------------------------------------------------------------------------------------------ the deck family
def graded_box():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_refine.py")).read()
    ns = {"os": os, "tempfile": tempfile}
    exec(src[src.index("def f8(x):"):src.index("def vol6(P):")], ns)
    p = ns["box_deck"](n=4)
    d = TF.read_deck(p)
    marked = []
    for t in d["tets"]:
        P = np.array([[float(TF._nas(x)) for x in d["grids"][n]] for n in t])
        marked.append(bool(np.linalg.norm(P.mean(0) - np.array((5.0, 5.0, 8.5))) < 3.2))
    r = RF.graded_refine(d, np.array(marked))
    r["refined_from"]["deck"] = p
    q = os.path.join(os.path.dirname(p), "box_g1.deck.pkl")
    with open(q, "wb") as fh:
        pickle.dump(r, fh)
    return q


def red_box(n=3):
    p = box_deck(n=n)
    r = RF.red_refine(TF.read_deck(p))
    r["refined_from"]["deck"] = p
    q = os.path.join(os.path.dirname(p), f"box{n}_r1.deck.pkl")
    with open(q, "wb") as fh:
        pickle.dump(r, fh)
    return q


def probe(path, record=None, label=""):
    """every check of one deck; -> {check name: bool} (for the planted runs)"""
    res = {}
    d = TF.read_deck(path)
    b = CB.bracket(path, 1, log=quiet, lower="p2")
    p1lo, p2lo, up = b["p2"]["p1_lower"], b["compliance"][0], b["compliance"][1]
    res["p2 >= p1"] = p2lo >= p1lo * (1 - 1e-9)
    res["p2 <= upper"] = p2lo <= up
    if record is not None:
        record.append((label, p1lo, p2lo, up, b["p2"]["dof"], b["p2"]["cg_iterations"], b["tets"]))
    # the field itself, posed here again (the same q the bracket used: tetfea2.traction_flux, asserted in 3d)
    ctx = T2.setup2(d, log=quiet)
    L = T2.case_load2(ctx, 1)
    u, V, rs = T2.case_field2(ctx, L["ftot"], tol=1e-10, log=quiet)
    try:
        T2.check_admissible(ctx, V)
        res["admissible"] = True
    except ValueError:
        res["admissible"] = False
    # an INDEPENDENT admissibility look: the support faces from the deck's own RBE2/SPC and tetmesh, not ctx's mask
    sf = np.where(ctx["kind_s"] == 1)[0]
    Vr = V.reshape(-1, 3)
    edge_of = {tuple(e): i for i, e in enumerate(ctx["edges"].tolist())}
    zero = all(not Vr[int(x)].any() for x in ctx["F"][sf].ravel())
    zero &= all(not Vr[ctx["nv"] + edge_of[tuple(sorted((int(ctx["F"][f, i]), int(ctx["F"][f, j]))))]].any()
                for f in sf for i, j in T2.FE)
    res["support faces zero (independent)"] = bool(zero)
    ae = T2.a_exact2(ctx, V) if len(ctx["tets"]) <= 4000 else None
    af = T2.a_upper_float2(ctx, V)
    ax = T2.a_upper_exact2(ctx, V)
    if ae is not None:
        res["errfloat >= exact, close"] = Fr(af) >= ae and rel(af, ae) < 1e-10
        res["exact-integer >= exact, close"] = Fr(ax) >= ae and rel(ax, ae) < 1e-10
    aq = a_quadrature(ctx, V)
    res["a(v,v) = 4-point quadrature"] = rel(af, aq) < 1e-9
    W = T2.traction_work2(ctx, L["q"], V)
    Wq = traction_quadrature(ctx, L["q"], V)
    res["f(v) = 7-point quadrature"] = rel(W, Wq) < 1e-9
    gal = float(W) ** 2 / af
    cf = float(L["ftot"] @ u)
    res["Galerkin: W^2/a = f.u"] = rel(gal, cf) < 1e-8
    return res, dict(ctx=ctx, V=V, u=u, L=L, af=af, ae=ae, aq=aq, W=W, Wq=Wq, gal=gal, cf=cf, b=b)


# ================================================================ 1. boxes: P1 <= P2 <= upper, and every check
record = []
decks = [("box n=3", box_deck(n=3)), ("box n=4", box_deck(n=4)), ("red-refined box n=3", red_box(3)),
         ("graded box n=4", graded_box())]
keep = {}
for nm, path in decks:
    res, info = probe(path, record, nm)
    keep[nm] = (path, info)
    for k_, ok in res.items():
        check(ok, f"{nm}: {k_}")
    print(f"  {nm}: a errfloat {info['af']!r}, exact {float(info['ae']) if info['ae'] is not None else None!r}, "
          f"4-pt {info['aq']!r}; f(v) {float(info['W'])!r} vs 7-pt {info['Wq']!r}; W^2/a {info['gal']!r} vs f.u "
          f"{info['cf']!r}")
for nm, p1, p2, up, dof, cg, nt in record:
    print(f"MEASURED {nm} ({nt} tets, P2 {dof} dof, {cg} AMG-CG): P1 [{p1:.6f}, {up:.6f}] gap {100 * (up / p1 - 1):.2f} %;"
          f" P2 [{p2:.6f}, {up:.6f}] gap {100 * (up / p2 - 1):.2f} %")

# ================================================================ 2. pinned to the proved P1 code: P1 fields embedded
path, info = keep["box n=4"]
d = TF.read_deck(path)
ctx2 = info["ctx"]
ctx1 = TF.setup(d, log=quiet)
L1 = TF.case_load(ctx1, 1)
u1, _, _ = TF.case_field(ctx1, L1["ftot"], tol=1e-10, log=quiet)
vi = [2 * int(round(x * 2 ** (S - 1))) for x in u1]                  # even: the midpoint means are integers
for i in ctx1["fixed"]:
    vi[3 * i] = vi[3 * i + 1] = vi[3 * i + 2] = 0
V = T2.embed_p1(ctx2, vi)
a1x = TF.a_upper_exact(ctx1["XI"], ctx1["tets"], vi, ctx1["mu"], ctx1["lam"], ctx1["k"])
a2x = T2.a_upper_exact2(ctx2, V)
check(a2x == a1x, f"embedded P1: a_upper_exact2 == tetfea.a_upper_exact bit for bit ({a2x!r} vs {a1x!r})")
a1f = TF.a_upper_float(ctx1["XI"], ctx1["tets"], vi, ctx1["mu"], ctx1["lam"], ctx1["k"], Xf=ctx1["X"])
a2f = T2.a_upper_float2(ctx2, V)
check(rel(a1f, a2f) < 1e-10, f"embedded P1: the two float bounds agree ({a2f!r} vs {a1f!r})")
LAYER = (-1, -1, 2.4, 11, 11, 7.6)
mask, volw = CB.omega_box(d, LAYER)
E, nu = d["mat"][0], d["mat"][1]
pre_c = {"omega": mask, "sigma": CB.mean_stress_extractor("zz", E, nu, volw)}
ey = [Fr(0), Fr(1), Fr(0)]
Pi_zz, _ = CB.tangent_projector([0.0, 0.0, 1.0], ey)
S0, S1 = CB.scl_extractor("bending", Pi_zz, ey, Fr(5), Fr(10), volw, E, nu)
pre_l = {"omega": mask, "S0": S0, "S1": S1}
for nm, pre in (("3b constant", pre_c), ("3c linear", pre_l)):
    w1 = TF.prestress_work_of(ctx1, pre, mask, vi)
    w2 = T2.prestress_work2(ctx2, pre, mask, V)
    check(w1 == w2, f"embedded P1: the {nm} prestress work equals tetfea's EXACTLY ({float(w2)!r} vs {float(w1)!r})")
# the traction: a flux q with exact integer P1 consistent loads (q in multiples of 24)
rng = np.random.default_rng(7)
qs = np.zeros_like(info["L"]["q"])
lf = np.where(np.abs(info["L"]["q"]).reshape(len(qs), -1).max(axis=1) > 0)[0]
qs[lf] = 24.0 * rng.integers(-50, 50, size=(len(lf), 3, 3))
fv1 = np.zeros(ctx1["ndof"])
for f in lf:
    for i in range(3):
        for p_ in range(3):
            fv1[3 * int(ctx2["F"][f, i]):3 * int(ctx2["F"][f, i]) + 3] += qs[f, p_] * (2 if i == p_ else 1) / 24
w1 = TF.traction_work_exact(fv1, vi)
w2 = T2.traction_work2(ctx2, qs, V)
check(w1 == w2, f"embedded P1: the traction work equals tetfea.traction_work_exact EXACTLY ({float(w2)!r} vs "
      f"{float(w1)!r})")
# the real load: the P1 lower side's traction (consistent loads = f_RBE3) vs t_q (the upper side's) — MEASURED
w1r = TF.traction_work_exact(L1["fvec"], vi)
w2r = T2.traction_work2(ctx2, info["L"]["q"], V)
print(f"MEASURED box n=4, one P1 field: f(v) against the P1 lower side's traction {float(w1r)!r}, against t_q (the "
      f"upper side's) {float(w2r)!r}: relative {rel(w1r, w2r):.2e}")
check(rel(w1r, w2r) < 1e-10, "the two tractions' works agree to 1e-10 on a P1 field (t_q = M_s^-1 f up to the float "
      "solve)")
# the float P2 stiffness on an embedded field = the P1 energy (the solver's matrix is the right one)
uu = np.asarray(V, float) / 2.0 ** S
Kf2 = ctx2.get("Kf")
if Kf2 is not None:
    e2 = float(uu[ctx2["free"]] @ (Kf2 @ uu[ctx2["free"]]))
    check(rel(e2, a2f) < 1e-10, f"the float P2 stiffness gives the P1 energy on an embedded field ({e2!r} vs {a2f!r})")
# a prestress-only P2 field (genuinely quadratic): its 3c work = the 4-point quadrature
Lp = T2.case_load2(ctx2, {"F": (0, 0, 0), "M": (0, 0, 0), "traction": False, "prestress": pre_l})
_, Vp, _ = T2.case_field2(ctx2, Lp["ftot"], tol=1e-10, log=quiet)
wp = T2.prestress_work2(ctx2, pre_l, mask, Vp)
wq = prestress_quadrature(ctx2, pre_l, mask, Vp)
check(rel(wp, wq) < 1e-9, f"3c prestress work of a P2 field = the 4-point quadrature ({float(wp)!r} vs {wq!r})")
Lc = T2.case_load2(ctx2, {"F": (0, 0, 0), "M": (0, 0, 0), "traction": False, "prestress": pre_c})
_, Vc, _ = T2.case_field2(ctx2, Lc["ftot"], tol=1e-10, log=quiet)
wc = T2.prestress_work2(ctx2, pre_c, mask, Vc)
S0c = [[x for x in r] for r in pre_c["sigma"]]
wcq = prestress_quadrature(ctx2, {"S0": S0c, "S1": [[[0, 0, 0]] * 3] * 3}, mask, Vc)
check(rel(wc, wcq) < 1e-9, f"3b prestress work of a P2 field = the 4-point quadrature ({float(wc)!r} vs {wcq!r})")

# ================================================================ 3. level 3d with P2 (box n = 4)
LOAD = {"F": (0.0, 0.0, 1000.0), "M": (0.0, 0.0, 0.0), "label": "pull"}
fz = {"label": "mean zz", "omega": mask, "sigma": pre_c["sigma"]}
# the solves to 1e-8 on both sides of the comparison: on this box P1 already holds the prestress-only solution (the
# layer is mesh-aligned), so its w_p is solver error only, and at the default 1e-4 the comparison measures the CG
# tolerance, not the space (MEASURED: P1 width 1e-6, P2 1.2e-4 for mean zz at 1e-4)
TOL3 = 1e-8
r1 = CB.bracket_functionals(path, LOAD, [fz], log=quiet, lower="p1", lower_tol=TOL3)["functionals"][0]
r2 = CB.bracket_functionals(path, LOAD, [fz], log=quiet, lower="p2", lower_tol=TOL3)
r2d = CB.bracket_functionals(path, LOAD, [fz], log=quiet, lower="p2")["functionals"][0]
check(r2d["bracket"][0] <= 10.0 <= r2d["bracket"][1], f"3d P2 at the default tolerance: 10 inside {r2d['bracket']}")
print(f"MEASURED 3d mean zz P2 at the default lower_tol 1e-4: [{r2d['bracket'][0]:.6f}, {r2d['bracket'][1]:.6f}]")
f2 = r2["functionals"][0]
w_ = lambda r: r["bracket"][1] - r["bracket"][0]
check(f2["bracket"][0] <= 10.0 <= f2["bracket"][1], f"3d P2: the exact mean zz 10 inside {f2['bracket']}")
check(w_(f2) <= w_(r1) * (1 + 1e-9), f"3d P2: not wider than P1 ({w_(f2):.6f} vs {w_(r1):.6f})")
print(f"MEASURED 3d mean zz (box n = 4): P1 [{r1['bracket'][0]:.6f}, {r1['bracket'][1]:.6f}] width {w_(r1):.6f}; "
      f"P2 [{f2['bracket'][0]:.6f}, {f2['bracket'][1]:.6f}] width {w_(f2):.6f}; C(f) P2 {r2['compliance']}")
BEAM = {"F": (0.0, 500.0, 1000.0), "M": (10000.0, 0.0, 0.0), "label": "beam"}
EXACT = {"membrane": 10.0, "bending": float(Fr(6, 1000) * (Fr(10000) - 7 * Fr(500)))}
fun3 = []
for kind in ("membrane", "bending"):
    S0k, S1k = CB.scl_extractor(kind, Pi_zz, ey, Fr(5), Fr(10), volw, E, nu)
    fun3.append({"label": kind, "omega": mask, "S0": S0k, "S1": S1k})
b1 = CB.bracket_functionals(path, BEAM, fun3, log=quiet, lower="p1", lower_tol=TOL3)
b2 = CB.bracket_functionals(path, BEAM, fun3, log=quiet, lower="p2", lower_tol=TOL3)
for o1, o2 in zip(b1["functionals"], b2["functionals"]):
    k_ = o2["label"]
    check(o2["bracket"][0] <= EXACT[k_] <= o2["bracket"][1], f"3d P2 {k_}: the exact {EXACT[k_]} inside {o2['bracket']}")
    check(w_(o2) <= w_(o1) * (1 + 1e-9), f"3d P2 {k_}: not wider than P1 ({w_(o2):.5f} vs {w_(o1):.5f})")
    print(f"MEASURED 3d {k_} (box n = 4): P1 [{o1['bracket'][0]:.5f}, {o1['bracket'][1]:.5f}] width {w_(o1):.5f}; P2 "
          f"[{o2['bracket'][0]:.5f}, {o2['bracket'][1]:.5f}] width {w_(o2):.5f}")

# ================================================================ 4. PLANTED errors
for plant in ("a_weight", "free_midpoint", "traction_p1"):
    T2._PLANTED = plant
    caught = []
    try:
        res, _ = probe(keep["box n=3"][0])
        caught += [k_ for k_, ok in res.items() if not ok]
    except ValueError as ex:
        caught.append(f"refused: {ex}")
    # the P1-pinning checks under the plant
    c2 = T2.setup2(d, log=quiet, solver=False)
    Vb = T2.embed_p1(c2, vi)
    if T2.a_upper_exact2(c2, Vb) != a1x:
        caught.append("embedded a == P1")
    if T2.traction_work2(c2, qs, Vb) != TF.traction_work_exact(fv1, vi):
        caught.append("embedded traction == P1")
    T2._PLANTED = None
    print(f"  planted {plant}: caught by {caught if caught else 'NOTHING'}")
    check(len(caught) > 0, f"planted {plant}: caught")

print(f"{CHECKS - len(FAILS)}/{CHECKS} checks passed")
if FAILS:
    print(f"P2 RED ({len(FAILS)} of {CHECKS})")
    sys.exit(1)
print(f"P2 GREEN ({CHECKS} checks)")
