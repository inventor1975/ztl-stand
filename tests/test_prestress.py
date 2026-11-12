# -*- coding: utf-8 -*-
"""Level 3b (2026-11-11): a PRESTRESS load l_p(v) = int_omega eps(v) : sig_e in both bounds, and the mean stress over a
region certified by polarization. Run: python3 -m tests.test_prestress

The KNOWN answer: a box clamped at z = 0, pulled at z = L by a force F_z (any distribution), omega = a whole layer
of cells between two node planes. By equilibrium of the part above any section, int_section sigma_zz dA = F_z, so the
mean of sigma_zz over the layer is F_z / A EXACTLY for the continuum solution — whatever the clamp does to the field
(nu = 0.3: the field is NOT uniform). The polarized bracket must contain it; planted errors must break it."""
# The default lower side became P2 on 2026-11-12; this file tests the P1 path, so it asks for lower="p1" explicitly.
import os
import sys
import tempfile
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ustand import tetfea as TF, equil as EQ, alfeld as AL, cadbracket as CB          # noqa: E402

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
    """the cube of tests/test_tetfea.py (n^3 cells, 6 Kuhn tets each; bottom tied by RBE2 to an SPC'd node; top loaded
    by an RBE3) — a copy: importing that test module would run it"""
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


def n2out(P, f):
    vs = [v for v in range(4) if v != f]
    a, b, c = (P[v] for v in vs)
    u = [b[i] - a[i] for i in range(3)]
    w = [c[i] - a[i] for i in range(3)]
    n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
    if sum(n[i] * (P[f][i] - a[i]) for i in range(3)) > 0:
        n = [-x for x in n]
    return n


# ---- 1. the upper side's algebra, EXACT on random tets: ||tau' + sig||^2 = ||tau'||^2 + 2 b . g + |T| sig : A sig
import random                                                                     # noqa: E402
random.seed(2)
E0, nu0 = Fr(113800), Fr(342, 1000)


def compl(P, g):
    tt, tr2 = AL.energy(P, g)
    return ((1 + nu0) * tt - nu0 * tr2) / E0


for trial in range(3):
    P = [[Fr(random.randint(-9, 9), random.randint(1, 5)) for _ in range(3)] for _ in range(4)]
    r = [Fr(random.randint(-20, 20)) for _ in range(36)]
    B = AL.bal_matrix(P)
    G = [[sum(B[i][k] * B[j][k] for k in range(36)) for j in range(6)] for i in range(6)]
    y = EQ._solve6(G, [sum(B[i][k] * r[k] for k in range(36)) for i in range(6)])
    g = [r[k] - sum(B[i][k] * y[i] for i in range(6)) for k in range(36)]          # a random BALANCED g
    s = [[Fr(random.randint(-5, 5)) for _ in range(3)] for _ in range(3)]
    s = [[(s[i][j] + s[j][i]) / 2 for j in range(3)] for i in range(3)]
    gs = []
    for f in range(4):
        nn = n2out(P, f)
        for jv in range(3):
            gs += [sum(s[i][k] * nn[k] for k in range(3)) for i in range(3)]       # the constant stress's data
    lhs = compl(P, [a + b for a, b in zip(g, gs)])
    rhs = compl(P, g) + 2 * sum(x * y for x, y in zip(EQ.prestress_linear(P, s, E0, nu0), g)) \
        + EQ.prestress_self(P, s, E0, nu0)
    check(lhs == rhs, f"random tet {trial}: ||tau' + sig||^2 = ||tau'||^2 + 2 b.g + |T| sig:A sig EXACTLY")
    # the mean-stress identity on the constant field itself
    M = EQ.mean_stress_integral(P, gs)
    V = EQ.tet_volume(P)
    check(all(M[i][j] == V * s[i][j] for i in range(3) for j in range(3)), f"random tet {trial}: int_T sig = |T| sig")
# float b = exact b
bf = EQ.prestress_linear_float(np.array([[[float(c) for c in p] for p in P]]), [[float(x) for x in r_] for r_ in s],
                               float(E0), float(nu0))[0]
be = [float(x) for x in EQ.prestress_linear(P, s, E0, nu0)]
check(np.allclose(bf, be, rtol=1e-12, atol=1e-15), "the float b equals the exact b")

# ---- 2. the lower side's functional, EXACT: for a GLOBALLY LINEAR v = G x, l_p(v) = |omega| sig : sym(G)
p = box_deck(n=4)
deck = TF.read_deck(p)
ids = sorted(deck["grids"])
idx = {n: i for i, n in enumerate(ids)}
dec = {n: tuple(TF._nas(x) for x in deck["grids"][n]) for n in ids}
k = 4
XI = [tuple(int(x * 10 ** k) for x in dec[n]) for n in ids]
check(all((x * 10 ** k).denominator == 1 for n in ids for x in dec[n]), "box coordinates are exact over 10^4")
tets = [tuple(idx[n] for n in t) for t in deck["tets"]]
Gm = [[3, -1, 2], [5, 4, -7], [1, 6, 2]]                    # v = G x, in integers over 2^S (S = TF.S)
vi = []
for n in ids:
    x = dec[n]
    for c in range(3):
        vi.append(int(sum(Gm[c][b] * x[b] for b in range(3)) * 2 ** TF.S))     # exact: x * 2^S is an integer? check
check(all(Fr(vi[3 * i + c]) == sum(Gm[c][b] * dec[n][b] for b in range(3)) * 2 ** TF.S
          for i, n in enumerate(ids) for c in range(3)), "the linear v is exactly representable")
mask, volw = CB.omega_box(deck, (-1, -1, 2.4, 11, 11, 7.6))
check(int(mask.sum()) == 192 and volw == 500,
      f"omega = the two middle layers (2.5 < z < 7.5): 192 tets, |omega| = 500 ({int(mask.sum())}, {float(volw)})")
sig = [[Fr(2), Fr(1, 3), Fr(-1)], [Fr(1, 3), Fr(5), Fr(0)], [Fr(-1), Fr(0), Fr(7, 2)]]
lp = TF.prestress_work_exact(XI, tets, vi, np.where(mask)[0], sig, k)
want = volw * sum(sig[a][b] * Fr(Gm[a][b] + Gm[b][a], 2) for a in range(3) for b in range(3))
check(lp == want, f"l_p(G x) = |omega| sig : sym(G) exactly ({float(lp)} vs {float(want)})")

# ---- 3. the mean sigma_zz over the middle layer: the polarized bracket contains F_z / A = 10 EXACTLY
E, nu = deck["mat"][0], deck["mat"][1]
sig_e = CB.mean_stress_extractor("zz", E, nu, volw)
Fz = (0.0, 0.0, 1000.0)


def load(sv, prestress=True):
    dd = {"F": Fz, "M": (0.0, 0.0, 0.0), "label": "t"}
    if prestress:
        dd["prestress"] = {"omega": mask, "sigma": [[sv * x for x in row] for row in sig_e]}
    return dd


# s balancing the two loads' compliances (floats only choose s; any s > 0 is valid)
cf = TF.solve_cases(deck, [load(0, False)], log=lambda m: None)[0]["compliance_float"]
cp = TF.solve_cases(deck, [{"F": (0.0, 0.0, 0.0), "M": (0.0, 0.0, 0.0), "label": "p",
                            "prestress": {"omega": mask, "sigma": sig_e}}], log=lambda m: None)[0]["compliance_float"]
s = Fr(round(float(np.sqrt(cf / cp)), 3)).limit_denominator(1000)
quiet = lambda m: None
rp = CB.bracket(p, load(s), log=quiet, lower="p1")
rm = CB.bracket(p, load(-s), log=quiet, lower="p1")
plo, phi = (Fr(x) for x in rp["compliance"])
mlo, mhi = (Fr(x) for x in rm["compliance"])
lo, hi = (plo - mhi) / (4 * s), (phi - mlo) / (4 * s)
exact = Fr(1000) / 100
check(plo <= phi and mlo <= mhi, f"each compliance bracket is ordered: [{float(plo)}, {float(phi)}], "
      f"[{float(mlo)}, {float(mhi)}]")
for r_, nm in ((rp, "+s"), (rm, "-s")):
    lo_f = TF.solve_cases(deck, [load(s if nm == "+s" else -s)], log=quiet)[0]["compliance_float"]
    check(r_["compliance"][0] <= lo_f * (1 + 1e-9) <= r_["compliance"][1] * (1 + 2e-9),
          f"{nm}: lower <= the float FE compliance <= upper ({r_['compliance']} vs {lo_f})")
check(lo <= exact <= hi, f"mean sigma_zz over the layer in [{float(lo):.6f}, {float(hi):.6f}] contains F/A = 10")
width = float((hi - lo) / exact)
print(f"MEASURED: s = {s}, C(f+sp) in [{float(plo):.6f}, {float(phi):.6f}], C(f-sp) in [{float(mlo):.6f}, "
      f"{float(mhi):.6f}]; mean sigma_zz in [{float(lo):.6f}, {float(hi):.6f}] (width {100 * width:.2f} % of 10)")

# ---- 4. PLANTED errors — the bracket must catch them
# (a) upper side WITHOUT the prestress (tau' taken as admissible for f + s l_p, the extra terms dropped): the "upper"
#     falls under the proved lower for +s — a contradiction
up_wrong = rp["compliance"][1] - rp["prestress"]["extra_exact"]
um_wrong = rm["compliance"][1] - rm["prestress"]["extra_exact"]
check(up_wrong < rp["compliance"][0] or um_wrong < rm["compliance"][0],
      f"planted (a): dropping the prestress terms on the upper side is caught ({up_wrong} < {rp['compliance'][0]} or "
      f"{um_wrong} < {rm['compliance'][0]})")
# (b) lower side with the WRONG functional (the extractor of the mean sigma_xx in place of sigma_zz, the upper side
#     right): the polarized interval no longer contains 10, or a compliance bracket inverts
sig_x = CB.mean_stress_extractor("xx", E, nu, volw)
wrong = []
for sv in (s, -s):
    dd = {"F": Fz, "M": (0.0, 0.0, 0.0), "label": "w",
          "prestress": {"omega": mask, "sigma": [[sv * x for x in row] for row in sig_x]}}
    wrong.append(Fr(TF.solve_cases(deck, [dd], tol=1e-4, log=quiet)[0]["compliance_lower_proved"]))
lo_w, hi_w = (wrong[0] - mhi) / (4 * s), (phi - wrong[1]) / (4 * s)
caught_b = not (lo_w <= exact <= hi_w) or wrong[0] > phi or wrong[1] > mhi
check(caught_b, f"planted (b): the wrong lower functional is caught (interval [{float(lo_w):.4f}, {float(hi_w):.4f}],"
      f" lower {float(wrong[0]):.4f} vs upper {float(phi):.4f})")
# (c) the target itself wrong by 10 %: 11 is OUTSIDE the proved interval (the bracket is not wide enough to hide it)
check(not (lo <= Fr(11) <= hi) and not (lo <= Fr(9) <= hi), "a claim of 9 or 11 is refuted by the bracket")
# WHY section 3 is easy (MEASURED 2026-11-11, n = 4, s = 0.031 .. 0.248): the gaps of C(f +- s p) are 0.06055 for
# every s — the prestress part adds NO gap. For the zz extractor on a full layer the prestress solution is u_z
# piecewise linear in z (the layer strained, tau' = 0): exactly P1 and exactly admissible. So section 3 checks the
# plumbing against an exact value, and section 5 checks a case where the prestress itself is hard.

# ---- 5. a NON-trivial prestress: mean sigma_xx over a block at the clamp (the clamp holds back the Poisson
# contraction). No closed form; the checks: the float FE value inside, the brackets on two meshes overlap (both hold
# the same continuum value), the prestress now adds a gap, a planted error on the upper side is caught.
res5 = {}
for n5 in (4, 8):
    p5 = box_deck(n=n5)
    d5 = TF.read_deck(p5)
    m5, v5 = CB.omega_box(d5, (2.4, 2.4, -1, 7.6, 7.6, 2.6))
    check(v5 == Fr(25) * Fr(5, 2), f"n = {n5}: omega = the block (2.5, 7.5)^2 x (0, 2.5) at the clamp, |omega| = 62.5")
    sx = CB.mean_stress_extractor("xx", d5["mat"][0], d5["mat"][1], v5)

    def ld(sv, pre=True):
        dd = {"F": Fz, "M": (0.0, 0.0, 0.0), "label": "t"}
        if pre:
            dd["prestress"] = {"omega": m5, "sigma": [[sv * x for x in row] for row in sx]}
        return dd
    c_f = TF.solve_cases(d5, [ld(0, False)], log=quiet)[0]["compliance_float"]
    c_p = TF.solve_cases(d5, [{"F": (0.0, 0.0, 0.0), "M": (0.0, 0.0, 0.0), "label": "p",
                               "prestress": {"omega": m5, "sigma": sx}}], log=quiet)[0]["compliance_float"]
    s5 = Fr(round(float(np.sqrt(c_f / c_p)), 4)).limit_denominator(10000)
    b_p, b_m = CB.bracket(p5, ld(s5), log=quiet, lower="p1"), CB.bracket(p5, ld(-s5), log=quiet, lower="p1")
    b_0 = CB.bracket(p5, ld(0, False), log=quiet, lower="p1")
    Pl, Ph = (Fr(x) for x in b_p["compliance"])
    Ml, Mh = (Fr(x) for x in b_m["compliance"])
    l5, h5 = (Pl - Mh) / (4 * s5), (Ph - Ml) / (4 * s5)
    fe = (TF.solve_cases(d5, [ld(s5)], log=quiet)[0]["compliance_float"]
          - TF.solve_cases(d5, [ld(-s5)], log=quiet)[0]["compliance_float"]) / (4 * float(s5))
    check(float(l5) <= fe <= float(h5), f"n = {n5}: the float FE mean sigma_xx {fe:.5f} in [{float(l5):.5f}, "
          f"{float(h5):.5f}]")
    gap0 = b_0["compliance"][1] - b_0["compliance"][0]
    check((Ph - Pl) > Fr(gap0) * Fr(11, 10), f"n = {n5}: the prestress adds a gap ({float(Ph - Pl):.5f} vs the "
          f"traction's {gap0:.5f})")
    # planted (a) here: dropping BOTH terms is not caught (MEASURED: the cross term is NEGATIVE here, tau' works
    # against p, so the "upper" without it is larger, i.e. still above — unsound in principle, invisible in fact).
    # What makes an upper too SMALL is what a bracket can catch: drop the self term |T| sig : A sig (> 0).
    uw = b_p["compliance"][1] - b_p["prestress"]["self_exact"]
    mw = b_m["compliance"][1] - b_m["prestress"]["self_exact"]
    check(uw < b_p["compliance"][0] and mw < b_m["compliance"][0],
          f"n = {n5}: planted (a'): dropping the self term is caught on both signs ({uw:.5f} < "
          f"{b_p['compliance'][0]:.5f}; {mw:.5f} < {b_m['compliance'][0]:.5f})")
    print(f"  n = {n5}: cross {b_p['prestress']['cross_exact']:.5f} / {b_m['prestress']['cross_exact']:.5f}, self "
          f"{b_p['prestress']['self_exact']:.5f}")
    res5[n5] = (l5, h5)
    print(f"MEASURED n = {n5} ({len(d5['tets'])} tets, omega {int(m5.sum())}): s = {s5}, mean sigma_xx in "
          f"[{float(l5):.5f}, {float(h5):.5f}] (width {float(h5 - l5):.5f}), FE {fe:.5f}; gaps {float(Ph - Pl):.5f} "
          f"{float(Mh - Ml):.5f} vs traction {gap0:.5f}")
(a4, b4), (a8, b8) = res5[4], res5[8]
check(max(a4, a8) <= min(b4, b8), f"the n = 4 and n = 8 brackets overlap ([{float(a4):.5f}, {float(b4):.5f}] and "
      f"[{float(a8):.5f}, {float(b8):.5f}])")
check(b8 - a8 < b4 - a4, "the finer mesh gives the narrower bracket")

print(f"{CHECKS - len(FAILS)}/{CHECKS} checks passed")
if FAILS:
    sys.exit(1)
