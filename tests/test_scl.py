# -*- coding: utf-8 -*-
"""Level 3c (2026-11-11): a LINEAR extractor sig_e(x) = S0 + S1 . x in both bounds; membrane and bending of a stress
on a section (ASME-style), certified by polarization. Run: python3 -m tests.test_scl

The KNOWN answer: the box of test_prestress clamped at z = 0, loaded on top through the RBE3 by F_z and a couple M_x.
On every section z = z0 above the clamp, equilibrium of the part above gives EXACTLY (continuum, whatever the clamp
does): int sigma_zz dA = F_z and int sigma_zz (y - 5) dA = M_x - (12 - z0) F_y (the force acts at (5, 5, 12)). The
lateral F_y is NEEDED: without it the permutation term of the moment formula sums to EXACTLY zero over a full layer
(it is -1/2 kappa int_d(omega) t_y z^2, and the section shear resultant is F_y). MEASURED 2026-11-11 with F_y = 0:
the planted no-permutation bracket equalled the right one to every digit. omega = the whole layer 2.5 < z < 7.5 (|omega| = 500, the "wall" = the full depth 0 < y < 10,
t_w = 10, c = 5, n = e_y, t = e_z):
    sigma_m = (1/|omega|) int sigma_zz = F_z / 100,
    sigma_b = 6 / (t_w |omega|) int sigma_zz (y - 5) = 0.006 (M_x - 7 F_y)   (7 = the layer's mean arm 12 - z0)."""
# The default lower side became P2 on 2026-11-12; this file tests the P1 path, so it asks for lower="p1" explicitly.
import os
import random
import sys
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetfea as TF, equil as EQ, alfeld as AL, cadbracket as CB          # noqa: E402
from tests.test_prestress import box_deck                                             # noqa: E402  (runs its checks)

CHECKS, FAILS = 0, []


def check(cond, what):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILS.append(what)
        print(f"FAIL: {what}")


def rnd_sym(r):
    s = [[Fr(r.randint(-5, 5), r.randint(1, 3)) for _ in range(3)] for _ in range(3)]
    return [[(s[i][j] + s[j][i]) / 2 for j in range(3)] for i in range(3)]


# ---- 1. the upper side's algebra, EXACT, against the element's OWN moments (the Alfeld quadrature, independent of the
#         boundary formula): b . g = int_T (A sig_e(x)) : tau', and the self term against the same quadrature
r = random.Random(5)
E0, nu0 = Fr(113800), Fr(342, 1000)
for trial in range(3):
    P = [[Fr(r.randint(-9, 9), r.randint(1, 5)) for _ in range(3)] for _ in range(4)]
    rr = [Fr(r.randint(-20, 20)) for _ in range(36)]
    B = AL.bal_matrix(P)
    G = [[sum(B[i][k] * B[j][k] for k in range(36)) for j in range(6)] for i in range(6)]
    y = EQ._solve6(G, [sum(B[i][k] * rr[k] for k in range(36)) for i in range(6)])
    g = [rr[k] - sum(B[i][k] * y[i] for i in range(6)) for k in range(36)]
    S0 = rnd_sym(r)
    cols = [rnd_sym(r) for _ in range(3)]
    S1 = [[[cols[k][i][j] for k in range(3)] for j in range(3)] for i in range(3)]
    B0, B1 = EQ._apply_A_lin(S0, S1, E0, nu0)
    m0, m1 = AL.moments(P, g)
    want = sum(B0[i][j] * m0[i][j] for i in range(3) for j in range(3)) + \
        sum(B1[i][j][k] * m1[i][j][k] for i in range(3) for j in range(3) for k in range(3))
    got = sum(x * y_ for x, y_ in zip(EQ.extractor_linear_b(P, S0, S1, E0, nu0), g))
    check(got == want, f"random tet {trial}: b . g = int_T A sig_e(x) : tau' EXACTLY (vs the element's own moments)")
    EQ.PLANT_NO_PERMUTATION = True
    bad = sum(x * y_ for x, y_ in zip(EQ.extractor_linear_b(P, S0, S1, E0, nu0), g))
    EQ.PLANT_NO_PERMUTATION = False
    check(bad != want, f"random tet {trial}: planted — the moment formula WITHOUT the permutation term is wrong")
    # the self term by the sub-tet quadrature (exact to degree 2)
    Bm = [[P[k + 1][row] - P[0][row] for k in range(3)] for row in range(3)]
    det, _ = AL._inv3(Bm)
    q = Fr(0)
    for pts in AL._quad_points():
        for xi, w in pts:
            x = [P[0][k] + sum(Bm[k][j] * xi[j] for j in range(3)) for k in range(3)]
            se = EQ.extractor_at(S0, S1, x)
            As = EQ.compliance_apply(se, E0, nu0)
            q += w * sum(se[i][j] * As[i][j] for i in range(3) for j in range(3))
    q = q * abs(det) / 24
    check(EQ.extractor_linear_self(P, S0, S1, E0, nu0) == q, f"random tet {trial}: the self term EXACTLY")
    # float b = exact b
    bf = EQ.extractor_linear_b_float(np.array([[[float(c) for c in p] for p in P]]), S0, S1, float(E0), float(nu0))[0]
    check(np.allclose(bf, [float(x) for x in EQ.extractor_linear_b(P, S0, S1, E0, nu0)], rtol=1e-11, atol=1e-14),
          f"random tet {trial}: the float b equals the exact b")
    sf = EQ.extractor_linear_self_float(np.array([[[float(c) for c in p] for p in P]]), S0, S1, float(E0), float(nu0))
    check(abs(sf - float(q)) <= 1e-10 * abs(float(q)), f"random tet {trial}: the float self term equals the exact")

# ---- 2. the lower side, EXACT for a globally linear v = G x: l_p(v) = sym(G) : (S0 |omega| + S1 . int_omega x),
#         int over the middle layer of x = |omega| (5, 5, 5)
p4 = box_deck(n=4)
d4 = TF.read_deck(p4)
ids = sorted(d4["grids"])
idx = {n: i for i, n in enumerate(ids)}
dec = {n: tuple(TF._nas(x) for x in d4["grids"][n]) for n in ids}
k = 4
XI = [tuple(int(x * 10 ** k) for x in dec[n]) for n in ids]
tets = [tuple(idx[n] for n in t) for t in d4["tets"]]
Gm = [[3, -1, 2], [5, 4, -7], [1, 6, 2]]
vi = [int(sum(Gm[c][b] * dec[n][b] for b in range(3)) * 2 ** TF.S) for n in ids for c in range(3)]
mask, volw = CB.omega_box(d4, (-1, -1, 2.4, 11, 11, 7.6))
S0 = rnd_sym(r)
cols = [rnd_sym(r) for _ in range(3)]
S1 = [[[cols[kk][i][j] for kk in range(3)] for j in range(3)] for i in range(3)]
sig_per = {}
for t in np.where(mask)[0]:
    cq = [Fr(sum(XI[q][rr_] for q in tets[int(t)]), 4 * 10 ** k) for rr_ in range(3)]
    sig_per[int(t)] = EQ.extractor_at(S0, S1, cq)
lp = TF.prestress_work_exact(XI, tets, vi, np.where(mask)[0], None, k, sig_per=sig_per)
mid = EQ.extractor_at(S0, S1, [Fr(5)] * 3)
want = volw * sum(mid[a][b] * Fr(Gm[a][b] + Gm[b][a], 2) for a in range(3) for b in range(3))
check(lp == want, f"l_p(G x) for the LINEAR extractor exactly ({float(lp)} vs {float(want)})")

# ---- 3. the beam: membrane and bending of sigma_zz on the middle layer contain the exact 10 and 60
Fz, Mx, Fy = 1000.0, 10000.0, 500.0
ez = [Fr(0), Fr(0), Fr(1)]
ey = [Fr(0), Fr(1), Fr(0)]
Pi_zz, tp = CB.tangent_projector([0.0, 0.0, 1.0], ey)
check(Pi_zz == [[0, 0, 0], [0, 0, 0], [0, 0, 1]] and tp[1] == 0, "Pi = e_z e_z, t . n = 0 exactly")
quiet = lambda m: None
EXACT = {"membrane": Fr(10), "bending": Fr(6, 1000) * (Fr(10000) - 7 * Fr(500))}       # 10 and 39
results = {}


def run(n_, kind, c_=Fr(5), plant_self=False):
    p_ = box_deck(n=n_)
    d_ = TF.read_deck(p_)
    m_, v_ = CB.omega_box(d_, (-1, -1, 2.4, 11, 11, 7.6))
    S0_, S1_ = CB.scl_extractor(kind, Pi_zz, ey, c_, Fr(10), v_, d_["mat"][0], d_["mat"][1])

    def ld(sv, pre=True):
        dd = {"F": (0.0, Fy, Fz), "M": (Mx, 0.0, 0.0), "label": "t"}
        if pre:
            dd["prestress"] = {"omega": m_, "S0": [[sv * x for x in rw] for rw in S0_],
                               "S1": [[[sv * x for x in cc] for cc in rw] for rw in S1_]}
        return dd
    cf = TF.solve_cases(d_, [ld(0, False)], log=quiet)[0]["compliance_float"]
    cp = TF.solve_cases(d_, [{"F": (0.0, 0.0, 0.0), "M": (0.0, 0.0, 0.0), "label": "p",
                              "prestress": ld(1)["prestress"]}], log=quiet)[0]["compliance_float"]
    s_ = Fr(round(float(np.sqrt(cf / cp)), 4)).limit_denominator(10000)
    bp, bm = CB.bracket(p_, ld(s_), log=quiet, lower="p1"), CB.bracket(p_, ld(-s_), log=quiet, lower="p1")
    Pl, Ph = (Fr(x) for x in bp["compliance"])
    Ml, Mh = (Fr(x) for x in bm["compliance"])
    if plant_self:
        Ph, Mh = Ph - Fr(bp["prestress"]["self_exact"]), Mh - Fr(bm["prestress"]["self_exact"])
    fe = (TF.solve_cases(d_, [ld(s_)], log=quiet)[0]["compliance_float"]
          - TF.solve_cases(d_, [ld(-s_)], log=quiet)[0]["compliance_float"]) / (4 * float(s_))
    return {"lo": (Pl - Mh) / (4 * s_), "hi": (Ph - Ml) / (4 * s_), "s": s_, "P": (Pl, Ph), "M": (Ml, Mh),
            "fe": fe, "tets": len(d_["tets"])}


for n_ in (4, 8):
    for kind in ("membrane", "bending"):
        R_ = run(n_, kind)
        results[n_, kind] = R_
        ex = EXACT[kind]
        check(R_["P"][0] <= R_["P"][1] and R_["M"][0] <= R_["M"][1], f"n = {n_} {kind}: both compliance brackets ordered")
        check(R_["lo"] <= ex <= R_["hi"], f"n = {n_} {kind}: [{float(R_['lo']):.4f}, {float(R_['hi']):.4f}] contains "
              f"the exact {float(ex)}")
        check(float(R_["lo"]) <= R_["fe"] <= float(R_["hi"]), f"n = {n_} {kind}: the float FE value {R_['fe']:.4f} inside")
        print(f"MEASURED n = {n_} ({R_['tets']} tets) {kind}: s = {R_['s']}, [{float(R_['lo']):.5f}, "
              f"{float(R_['hi']):.5f}] (width {100 * float((R_['hi'] - R_['lo']) / ex):.2f} % of {float(ex)}), "
              f"FE {R_['fe']:.5f}")
for kind in ("membrane", "bending"):
    a4, b4 = results[4, kind]["lo"], results[4, kind]["hi"]
    a8, b8 = results[8, kind]["lo"], results[8, kind]["hi"]
    check(b8 - a8 <= b4 - a4, f"{kind}: the finer mesh gives the narrower (or equal) bracket "
          f"({float(b4 - a4):.5f} -> {float(b8 - a8):.5f})")

# ---- 4. PLANTED errors on the beam (bending, the case that needs the permutation term)
# (a) the moment formula WITHOUT the permutation term (choice and exact cross term both): caught = the exact 60 falls
#     outside the "interval", or a compliance "bracket" inverts
caught = []
for n_ in (4, 8):
    EQ.PLANT_NO_PERMUTATION = True
    try:
        W = run(n_, "bending")
    finally:
        EQ.PLANT_NO_PERMUTATION = False
    cw = not (W["lo"] <= EXACT["bending"] <= W["hi"]) or W["P"][1] < W["P"][0] or W["M"][1] < W["M"][0]
    caught.append(cw)
    print(f"  planted no-permutation, n = {n_}: [{float(W['lo']):.4f}, {float(W['hi']):.4f}], "
          f"C+ [{float(W['P'][0]):.4f}, {float(W['P'][1]):.4f}], C- [{float(W['M'][0]):.4f}, {float(W['M'][1]):.4f}]"
          f" -> {'CAUGHT' if cw else 'not caught'}")
check(all(caught), f"planted (a): the moment formula without the permutation term is caught on the beam ({caught})")
# (b) the self term dropped on the upper side: the "upper" falls under the proved lower on at least one sign
for n_ in (4, 8):
    W = run(n_, "bending", plant_self=True)
    cw = W["P"][1] < W["P"][0] or W["M"][1] < W["M"][0] or not (W["lo"] <= EXACT["bending"] <= W["hi"])
    check(cw, f"planted (b), n = {n_}: dropping the self term is caught")
# (c) the wrong sign of c (c = -5): a VALID bracket of a DIFFERENT quantity (exact 6/(5000) int sigma_zz (y + 5) =
#     39 + 6 / (10 * 500) * 10 * int_omega sigma_zz = 39 + 0.0012 * 10 * 5 F_z = 99); it must refute the claim 39
W = run(8, "bending", c_=Fr(-5))
check(not (W["lo"] <= EXACT["bending"] <= W["hi"]) and W["lo"] <= 99 <= W["hi"],
      f"planted (c): c = -5 brackets 99 ([{float(W['lo']):.4f}, {float(W['hi']):.4f}]) and refutes 39")

print(f"{CHECKS - len(FAILS)}/{CHECKS} checks passed")
if FAILS:
    sys.exit(1)
print("SCL GREEN")
