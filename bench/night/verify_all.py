"""THE NIGHT BATTERY (2026-11-01, the curator: "на ночь запустить серию тестов, что бы все проверить, что только
можно"). Randomised cross-checks of every proved bound against an INDEPENDENT answer — float P-delta on a fine mesh
(8 elements per member), closed forms, exact solves — counting violations (must be 0); then the same checks with a
bound deliberately broken (MUTATION) — they must find violations, or the check proves nothing.

    PYTHONPATH=. python3 bench/night/verify_all.py [--jobs 22] [--scale 1] [--only A,B,...]

  A  beam-columns (random P, q, end moments, 1/2/4 elements): physical second-order stress and deflection bounds vs
     the fine-mesh float solution
  B  random frames (storeys, bays, lateral/vertical loads, transverse member loads on beams, tol 0 or 0.5 %):
     second-order member stresses and roof sway vs the fine-mesh float P-delta at the nominal moduli
  C  random frames: the continuum's proved lambda_cr lower bound <= the fine-mesh float lambda_cr
  D  random trusses: second-order displacement bounds vs float P-delta (bars straight: the same model)
  E  ZTL zenergy.certify_general on random second-order systems: every vertex / interior point / D inside
  F  plates: hypercircle brackets of a coarse and a 4x finer mesh must overlap, lower <= upper
  M  mutations of A/B: the interior and the end-moment corrections dropped (the old "ends only" check that once read
     325 MPa for 337.67); A-MUTG: the end moment's geometric part N (G u) dropped (the K_E-row moment fixed
     2026-11-02); B-MUTG the same on frames — violations EXPECTED, or the check cannot see a broken bound.
     MEASURED 2026-11-02: B-MUT (ends only) was NOT visible on these random frames (0 of 2085) while the member-load
     correction was global; the 22 it "caught" before that were an artefact of the old reference, which shared the
     K_E-row moment. With the correction PER MEMBER (same day) the brackets are narrow enough: B-MUT 10, B-MUTG 176
     (was 13) of x1.
  G  random SPACE frames (2026-11-02) vs bench/night/frame3d_ref.py, an independent numpy FE: first order at the
     nodes, second-order displacements, member stresses and end moments both sides, the stability bracket; loads
     scaled to lambda_ref in [1.3, 3]. G-MUTG3 drops frame3d's geometric stiffness, G-MUTM3 the end moment's N (G u).
  H  2D frames with AXIAL member loads on the columns (2026-11-02): lambda_low <= lambda_fine <= lambda_high;
     H-MUTA restores the old witness (N_mean G for a linear N — a false upper bound for a self-weight column).
  I  one member's lateral-torsional / torsional critical factor (ustand.ltb, 2026-11-02) vs bench/night/ltb_ref.py:
     the lower bound over a box below the fine mesh at points inside it, the witness above; I-MUTL drops the
     continuum correction.
  J  second-order member STRESSES with an AXIAL member load (2026-11-03): one random column vs a solve_bvp continuum
     reference, end moments both sides and |sigma| from above; J-MUTA: the geometric moment with N_mid G.
  A and B also check BOTH SIDES since 2026-11-02 (B: the 8-element mesh's end moments, with the geometric part): every proved end-moment interval must contain an INDEPENDENT numpy FE
     reference (K_E - P G rows, 64 elements) — the old stress check shared the stand's K_E-row formula
Writes bench/night/REPORT.json and REPORT.md.
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")      # one BLAS thread per process (2026-11-02: 22 processes x BLAS threads put the
                                        # load average at 323 and the suite's timed tests over their limit)
import json
import math
import multiprocessing as mp
import pathlib
import random
import sys
import time
from fractions import Fraction as F

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench/night"))

from ustand import frame as FRM  # noqa: E402
from ustand import judge_ztl  # noqa: E402,F401
import zenergy as ZE  # noqa: E402

E0, A0_, I0, H0 = 210e9, 0.01, 8e-5, 0.2


def float_second_order(deck):
    """Float P-delta (axial forces from first order) of a frame deck: per element its max fibre |sigma| at the ends
    (with the member-load inner solution added), and every free nodal displacement."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    nodes, elems, loads, supports, ex, (area, izz) = FRM.read_deck(deck)
    parts, f, dof, emap, (_, _, _, h) = FRM.energy_system_full(deck, "0")
    n = len(dof)
    K0 = ZE._float_matrix(ZE.matrix(parts, n), n)
    fv = np.array([float(x) for x in f])
    u1 = sla.spsolve(K0.tocsc(), fv)
    N = {k: float(ex * area / emap[k]["L"]) * sum(float(v) * u1[i] for i, v in emap[k]["a"].items()) for k in emap}
    rr, cc, dd = [], [], []
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        c, s_ = (nodes[j][0] - nodes[i][0]) / L, (nodes[j][1] - nodes[i][1]) / L
        for (a, b), v in FRM._geo_entries(nodes, i, j, L, c, s_, dof).items():
            rr.append(a); cc.append(b); dd.append(N[k] * float(v))
    u = sla.spsolve((K0 + sp.csr_matrix((dd, (rr, cc)), shape=(n, n))).tocsc(), fv)
    qd = FRM.read_qloads(deck)
    sig, MOM = {}, {}
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        c, s_ = (nodes[j][0] - nodes[i][0]) / L, (nodes[j][1] - nodes[i][1]) / L
        Gl = [[F(v) / (30 * L) for v in r] for r in [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                                       [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]]]
        # the end moment's geometric part (2026-11-02): + N (G u)_th at I, - N (G u)_th at J — the reference used to
        # share the stand's K_E-row formula
        dM = {"I": N[k] * sum(float(v) * u[ii] for ii, v in FRM._glob(i, j, c, s_, dof, Gl[1]).items()),
              "J": -N[k] * sum(float(v) * u[ii] for ii, v in FRM._glob(i, j, c, s_, dof, Gl[3]).items())}
        best = 0.0
        for end, side, g in FRM.fibre_vectors(emap, k, h):
            b = float(FRM._bubble(qd, k, end, side, area, izz, h)[0]) if h else 0.0
            dm = dM[end] * (1 if side == "TOP" else -1) * float(h / 2 / izz) if h else 0.0
            best = max(best, abs(float(ex) * sum(float(v) * u[ii] for ii, v in g.items()) + b + dm))
        sig[k] = best
        # the end moments themselves, in the stand's convention (+(K_E + N G) row at I, -row at J, + the member
        # load's clamped end moment -w L^2/12): the two-sided reference (2026-11-02)
        m_ = emap[k]
        mb = -float(qd[k][1]) * float(L) ** 2 / 12 if k in qd else 0.0
        for end, sb in (("I", 1), ("J", -1)):
            mv = 0.0
            for ii, v in m_["b"].items():
                mv += float(izz / L * v) * u[ii]
            for ii, v in m_["c"].items():
                mv += float(izz / L * 3 * sb * v) * u[ii]
            MOM[(k, end)] = float(ex) * mv + dM[end] + mb
    disp = {nd: float(u[i]) for nd, i in dof.items()}
    _LAST_MOM.clear(); _LAST_MOM.update(MOM)
    return sig, disp, N


_LAST_MOM = {}          # float_second_order's end moments of its last call (the two-sided frame check)


def ref_end_moments(L, P, q, M1, M2, nfine=64):
    """An INDEPENDENT reference for the beam-column's internal end moments (2026-11-02): a numpy Hermite FE with the
    geometric matrix (K_E - P G), consistent loads, nfine elements; the end moment of an element is the
    ((K_E - P G) u_e - f_e) row — at its I end +row th_i, at its J end -row th_j (the stand's sign convention). The
    sweep A used to compare stresses from the SAME K_E-row formula as the stand, which hid the missing N (G u) term."""
    import numpy as np
    h = L / nfine
    EI = 210e9 * 8e-5
    ke = EI / h ** 3 * np.array([[12, 6 * h, -12, 6 * h], [6 * h, 4 * h * h, -6 * h, 2 * h * h],
                                 [-12, -6 * h, 12, -6 * h], [6 * h, 2 * h * h, -6 * h, 4 * h * h]])
    kg = P / (30 * h) * np.array([[36, 3 * h, -36, 3 * h], [3 * h, 4 * h * h, -3 * h, -h * h],
                                  [-36, -3 * h, 36, -3 * h], [3 * h, -h * h, -3 * h, 4 * h * h]])
    fe = q * np.array([h / 2, h * h / 12, h / 2, -h * h / 12])
    nd = 2 * (nfine + 1)
    K = np.zeros((nd, nd)); f = np.zeros(nd)
    for e in range(nfine):
        ix = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        K[np.ix_(ix, ix)] += ke - kg
        f[ix] += fe
    f[1] += M1; f[2 * nfine + 1] += M2
    free = [i for i in range(nd) if i not in (0, 2 * nfine)]
    u = np.zeros(nd)
    u[free] = np.linalg.solve(K[np.ix_(free, free)], f[free])
    MI, MJ = {}, {}
    for e in range(nfine):
        ix = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        r = (ke - kg) @ u[ix] - fe
        MI[e] = r[1]
        MJ[e + 1] = -r[3]
    return MI, MJ, h


def beam_column_case(seed):
    rng = random.Random(seed)
    L = rng.choice([2, 3, 4, 5, 6])
    Pe = math.pi ** 2 * E0 * I0 / L ** 2
    P = int(Pe * rng.uniform(0, 0.6))
    q = rng.choice([0, 1]) * rng.randint(-20000, 20000)
    M1, M2 = rng.randint(-50000, 50000), rng.randint(-50000, 50000)
    nsub = rng.choice([1, 2, 4])
    deck = "\n".join(["ET, 1, BEAM3", "MP, EX, 1, 210e9", "R, 1, 0.01, 8e-5, 0.2", "N, 1, 0, 0", f"N, 2, {L}, 0",
                      "E, 1, 2", "D, 1, UX, 0", "D, 1, UY, 0", "D, 2, UY, 0", f"F, 2, FX, -{P}", f"F, 1, MZ, {M1}",
                      f"F, 2, MZ, {M2}"] + ([f"QLOAD, 1, FY, {q}"] if q else []))
    d = FRM.subdivide(deck, nsub)
    r = FRM.second_order_case(d, "0", [(k, F(10) ** 15) for k in range(1, nsub + 1)])
    if not r.get("checks"):
        return {"checked": 0, "skipped": 1, "why": r.get("why")}
    fine_sig, _, _ = float_second_order(FRM.subdivide(deck, 64))
    ref = max(fine_sig.values())
    MI0, MJ0, _ = ref_end_moments(L, P, q, M1, M2)
    ref = max(ref, P / 0.01 + max(max(abs(v) for v in MI0.values()), max(abs(v) for v in MJ0.values())) / (8e-5 / 0.1))
    bound = max(float(F(c["sigma_abs_max"].split()[0])) for c in r["checks"])
    bad = ref > bound * (1 + 1e-9) + 1.0
    # BOTH SIDES (2026-11-02): every proved end-moment interval must CONTAIN the independent reference
    MI, MJ, h = ref_end_moments(L, P, q, M1, M2)
    per = 64 // nsub
    mref = max(max(abs(v) for v in MI.values()), max(abs(v) for v in MJ.values()), 1.0)
    tol = 1e-4 * mref + 1.0
    n_m, bad_m, ex_m = 0, 0, None
    for c in r["checks"]:
        k = int(c["check"].split("(")[1].split(")")[0])
        for end, refv in (("I", MI[(k - 1) * per]), ("J", MJ[k * per])):
            lo_, hi_ = (float(F(x.split()[0])) for x in c["M_ends"][end])
            n_m += 1
            if not (lo_ - tol <= refv <= hi_ + tol):
                bad_m += 1
                ex_m = ex_m or {"seed": seed, "elem": k, "end": end, "ref": refv, "proved": [lo_, hi_]}
    return {"checked": 1 + n_m, "violations": int(bad) + bad_m, "example": (None if not bad else
            {"seed": seed, "L": L, "P": P, "q": q, "M": [M1, M2], "nsub": nsub, "ref": ref, "bound": bound}) or ex_m}


def random_frame(rng, with_q=True):
    ns, nb = rng.randint(2, 6), rng.randint(1, 4)
    nid = lambda f_, c_: f_ * (nb + 1) + c_ + 1
    H, B = rng.choice([3, 4]), rng.choice([4, 5, 6])
    L_ = ["/PREP7", "ET, 1, BEAM3", "MP, EX, 1, 210e9", "R, 1, 0.01, 8e-5, 0.2"]
    for f_ in range(ns + 1):
        for c_ in range(nb + 1):
            L_.append(f"N, {nid(f_, c_)}, {B * c_}, {H * f_}")
    el = []
    for f_ in range(ns):
        for c_ in range(nb + 1):
            el.append((nid(f_, c_), nid(f_ + 1, c_)))
    beams = []
    for f_ in range(1, ns + 1):
        for c_ in range(nb):
            el.append((nid(f_, c_), nid(f_, c_ + 1)))
            beams.append(len(el))
    L_ += [f"E, {a}, {b}" for a, b in el]
    for c_ in range(nb + 1):
        L_ += [f"D, {nid(0, c_)}, UX, 0", f"D, {nid(0, c_)}, UY, 0", f"D, {nid(0, c_)}, ROTZ, 0"]
    scale = rng.choice([1, 2, 4, 8])
    for f_ in range(1, ns + 1):
        L_.append(f"F, {nid(f_, 0)}, FX, {rng.randint(0, 15000) * scale}")
        for c_ in range(nb + 1):
            L_.append(f"F, {nid(f_, c_)}, FY, -{rng.randint(5000, 30000) * scale}")
    if with_q:
        for k in beams:
            if rng.random() < 0.5:
                L_.append(f"QLOAD, {k}, FY, -{rng.randint(2000, 15000) * scale}")
    return "\n".join(L_), len(el), nid(ns, 0)


def frame_case(seed):
    rng = random.Random(seed)
    deck, ne, roof = random_frame(rng)
    tol = rng.choice(["0", "0.5%"])
    checks = [(k, F(10) ** 15) for k in range(1, ne + 1)]
    try:
        r = FRM.second_order_case(deck, tol, checks, disp=[(roof, "X")])
    except Exception as ex_:
        return {"checked": 0, "skipped": 1, "why": f"{type(ex_).__name__}: {ex_}"[:200]}
    if not r.get("checks"):
        return {"checked": 0, "skipped": 1, "why": r.get("why")}
    fine_sig, fine_disp, _ = float_second_order(FRM.subdivide(deck, 8))
    fmom = dict(_LAST_MOM)
    viol, n_chk, ex_ = 0, 0, None
    # BOTH SIDES (2026-11-02): the proved end-moment intervals must contain the fine mesh's end moments (the coarse
    # element k is fine elements 8(k-1)+1 .. 8k); tolerance MEASURED on the fixed code (see the commit)
    for c in r["checks"]:
        k = int(c["check"].split("(")[1].split(")")[0])
        mk = max(abs(fmom[(8 * (k - 1) + 1, "I")]), abs(fmom[(8 * k, "J")]), 1.0)
        for end, refv in (("I", fmom[(8 * (k - 1) + 1, "I")]), ("J", fmom[(8 * k, "J")])):
            lo_, hi_ = (float(F(x.split()[0])) for x in c["M_ends"][end])
            n_chk += 1
            tol_m = MOM_TOL * mk + 1.0
            if not (lo_ - tol_m <= refv <= hi_ + tol_m):
                viol += 1
                ex_ = ex_ or {"seed": seed, "member": k, "end": end, "ref": refv, "proved": [lo_, hi_]}
            DIST.append(max(0.0, lo_ - refv, refv - hi_) / mk)
    for c in r["checks"]:
        k = int(c["check"].split("(")[1].split(")")[0])
        ref = max(fine_sig[8 * (k - 1) + q] for q in range(1, 9))
        b = float(F(c["sigma_abs_max"].split()[0]))
        n_chk += 1
        if ref > b * (1 + 1e-9) + 1.0:
            viol += 1
            ex_ = ex_ or {"seed": seed, "member": k, "ref": ref, "bound": b}
    lo, hi = (float(x) for x in r["disp"][("U", roof, "X")])
    n_chk += 1
    d_ref = fine_disp[(roof, "X")]
    if not (lo - 1e-12 - 1e-9 * abs(d_ref) <= d_ref <= hi + 1e-12 + 1e-9 * abs(d_ref)):
        viol += 1
        ex_ = ex_ or {"seed": seed, "roof": [lo, hi], "ref": d_ref}
    return {"checked": n_chk, "violations": viol, "example": ex_}


def random_space_frame(rng, scale=None):
    """storeys x bays in X x bays in Y, columns (THETA 0 or 90) and beams in X and Y, two sections, vertical + lateral
    nodal loads, transverse QLOAD on some beams; fixed bases. scale multiplies every load (integer loads: a float scale
    is rounded per load)."""
    ns, bx, by = rng.randint(1, 3), rng.randint(1, 2), rng.randint(1, 2)
    H, B, C = rng.choice([3, 4]), rng.choice([4, 5, 6]), rng.choice([3, 4, 5])
    nid = lambda f_, a_, b_: f_ * (bx + 1) * (by + 1) + b_ * (bx + 1) + a_ + 1
    th = rng.choice([0, 90])
    L_ = ["ET, 1, BEAM4", "MP, EX, 1, 210e9", "MP, PRXY, 1, 0.3",
          f"R, 1, 0.006, {rng.choice([4, 6, 8])}e-5, {rng.choice([1, 2, 3])}e-5, 0.2, 0.2, {th}, 0, 5e-6",
          f"R, 2, 0.004, {rng.choice([3, 5])}e-5, 1e-5, 0.24, 0.12, 0, 0, 2e-6"]
    for f_ in range(ns + 1):
        for b_ in range(by + 1):
            for a_ in range(bx + 1):
                L_.append(f"N, {nid(f_, a_, b_)}, {B * a_}, {C * b_}, {H * f_}")
    el, beams = [], []
    for f_ in range(ns):
        for b_ in range(by + 1):
            for a_ in range(bx + 1):
                el.append((nid(f_, a_, b_), nid(f_ + 1, a_, b_), 1))
    for f_ in range(1, ns + 1):
        for b_ in range(by + 1):
            for a_ in range(bx):
                el.append((nid(f_, a_, b_), nid(f_, a_ + 1, b_), 2)); beams.append(len(el))
        for a_ in range(bx + 1):
            for b_ in range(by):
                el.append((nid(f_, a_, b_), nid(f_, a_, b_ + 1), 2)); beams.append(len(el))
    for k, (a, b, r_) in enumerate(el, 1):
        L_ += [f"REAL, {r_}", f"E, {a}, {b}"]
    for b_ in range(by + 1):
        for a_ in range(bx + 1):
            L_.append(f"D, {nid(0, a_, b_)}, ALL, 0")
    scale = rng.choice([1, 2, 4, 8]) if scale is None else scale
    for f_ in range(1, ns + 1):
        L_.append(f"F, {nid(f_, 0, 0)}, FX, {round(rng.randint(0, 8000) * scale)}")
        L_.append(f"F, {nid(f_, 0, 0)}, FY, {round(rng.randint(0, 8000) * scale)}")
        for b_ in range(by + 1):
            for a_ in range(bx + 1):
                L_.append(f"F, {nid(f_, a_, b_)}, FZ, -{round(rng.randint(5000, 30000) * scale)}")
    for k in beams:
        if rng.random() < 0.4:
            L_.append(f"QLOAD, {k}, FZ, -{round(rng.randint(1000, 8000) * scale)}")
    return "\n".join(L_), nid(ns, bx, by)


def space_frame_case(seed):
    """sweep G (2026-11-02): ustand.frame3d against bench/night/frame3d_ref.py — an independent numpy space-frame FE
    (12 x 12 Przemieniecki beam + consistent geometric matrix, 8 elements per member). First order at the nodes
    (tight), second-order displacement brackets and per-member max|sigma| brackets BOTH SIDES (lo <= ref <= hi),
    the stability bracket lambda_low <= lambda_ref(4 el.) and lambda_ref <= lambda_high (1e-9)."""
    import frame3d_ref as RF
    from ustand import frame3d as F3
    # the loads scaled to a target lambda_ref in [1.3, 3]: far from buckling the geometric part of the end moment
    # (2-3 %) hides inside the proved interval (~25 % wide) and the G-MUTM3 sabotage is invisible (MEASURED 2026-11-02)
    deck, top = random_space_frame(random.Random(seed), 1)
    nodes, elems, loads, supports, props = F3.read_deck(deck)
    lam1 = RF.solve(nodes, elems, props, {k: v for k, v in loads["BASE"].items() if not isinstance(k[0], tuple)},
                    supports, F3._qloads(deck).get("BASE", {}), m=4, buckling=True)
    rng = random.Random(seed + 7)
    deck, top = random_space_frame(random.Random(seed), lam1 / rng.uniform(1.3, 3.0) if lam1 else 1)
    tol = rng.choice(["0", "0.5%"])
    nodes, elems, loads, supports, props = F3.read_deck(deck)
    ld = loads["BASE"]
    nl = {k: v for k, v in ld.items() if not isinstance(k[0], tuple)}
    ql = F3._qloads(deck).get("BASE", {})
    T = [f"U({top},X)", f"U({top},Y)", f"U({top},Z)", f"U({top},RZ)"]
    viol, n_chk, ex_ = 0, 0, None
    r1 = RF.solve(nodes, elems, props, nl, supports, ql)
    for t in T:
        nd, dd = F3._target(t)
        r = F3.range_of(deck, tol, t)
        lo, hi, ref = float(r["lo"]), float(r["hi"]), r1[(nd, dd)]
        n_chk += 1
        slack = 1e-9 * max(abs(ref), abs(lo), abs(hi)) + 1e-15
        if not (lo - slack <= ref <= hi + slack):
            viol += 1
            ex_ = ex_ or {"seed": seed, "first": t, "proved": [lo, hi], "ref": ref}
    st = F3.stability_lower(deck, tol)
    lam_ref = RF.solve(nodes, elems, props, nl, supports, ql, m=4, buckling=True)
    if lam_ref is not None and st.get("lam_low") is not None:
        n_chk += 1
        if float(st["lam_low"]) > lam_ref * (1 + 1e-9):
            viol += 1
            ex_ = ex_ or {"seed": seed, "lam_low": float(st["lam_low"]), "ref": lam_ref}
        if tol == "0":
            su = F3.stability_upper(deck)
            if su.get("lam_high") is not None:
                n_chk += 1
                if float(su["lam_high"]) < lam_ref * (1 - 1e-9):
                    viol += 1
                    ex_ = ex_ or {"seed": seed, "lam_high": float(su["lam_high"]), "ref": lam_ref}
    if lam_ref is None or lam_ref <= 1.2:
        return {"checked": n_chk, "violations": viol, "example": ex_, "why": f"lambda_ref {lam_ref}: no 2nd order"}
    r2 = F3.second_order_disp(deck, tol, T)["BASE"]
    if r2.get("verdict") == "OPEN":
        return {"checked": n_chk, "violations": viol, "example": ex_, "skipped": 1, "why": r2["why"]}
    u2, fr = RF.solve(nodes, elems, props, nl, supports, ql, m=8, second=True, forces=True)
    for t in T:
        nd, dd = F3._target(t)
        lo, hi = float(r2[t][0]), float(r2[t][1])
        ref = u2[(nd, dd)]
        n_chk += 1
        slack = 1e-9 * max(abs(ref), abs(lo), abs(hi)) + 1e-15
        if not (lo - slack <= ref <= hi + slack):
            viol += 1
            ex_ = ex_ or {"seed": seed, "second": t, "proved": [lo, hi], "ref": ref}
    rs = F3.second_order_stress(deck, tol, 10 ** 12)
    for row in rs.get("members", []):
        k = row["element"]
        p = props[k]
        sig = max(abs(N) / float(p.area) + max(abs(a), abs(b)) * float(p.tky) / 2 / float(p.izz)
                  + max(abs(c), abs(d)) * float(p.tkz) / 2 / float(p.iyy) for (N, a, b, c, d) in fr[k])
        lo, hi = (float(F(x.split()[0])) for x in row["sigma_abs"])
        n_chk += 1
        if not (lo * (1 - 1e-6) - 1.0 <= sig <= hi * (1 + 1e-6) + 1.0):
            viol += 1
            ex_ = ex_ or {"seed": seed, "member": k, "sigma": [lo, sig, hi]}
        DIST3.append((hi - lo) / max(sig, 1.0))
        # BOTH SIDES on the end moments (the stress bracket is too wide to see a dropped N (G u)): the stand's end
        # moments are the internal moment, Przemieniecki's J-end force is its negative
        f0, f1 = fr[k][0], fr[k][-1]
        ref_m = {("y", "I"): f0[1], ("y", "J"): -f1[2], ("z", "I"): f0[3], ("z", "J"): -f1[4]}
        mk = max(abs(v) for v in ref_m.values()) + 1.0
        for (pl, e_), rv in ref_m.items():
            a_, b_ = (float(F(x.split()[0])) for x in row["M_ends"][pl][e_])
            n_chk += 1
            if not (a_ - MOM_TOL * mk - 1.0 <= rv <= b_ + MOM_TOL * mk + 1.0):
                viol += 1
                ex_ = ex_ or {"seed": seed, "member": k, "end": pl + e_, "proved": [a_, b_], "ref": rv}
    return {"checked": n_chk, "violations": viol, "example": ex_}


DIST3 = []


def stability_case(seed):
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    rng = random.Random(seed)
    deck, ne, roof = random_frame(rng, with_q=rng.random() < 0.5)
    st = FRM.stability_lower(deck, "0")
    if st.get("lam_low") is None or not st.get("lam_est"):
        return {"checked": 0, "skipped": 1}
    fine = FRM.subdivide(deck, 8)
    nodes, elems, loads, supports, ex, (area, izz) = FRM.read_deck(fine)
    parts, f, dof, emap, _ = FRM.energy_system_full(fine, "0")
    n = len(dof)
    K0 = ZE._float_matrix(ZE.matrix(parts, n), n)
    u1 = sla.spsolve(K0.tocsc(), np.array([float(x) for x in f]))
    qd = FRM.read_qloads(fine)
    rr, cc, dd = [], [], []
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        c, s_ = (nodes[j][0] - nodes[i][0]) / L, (nodes[j][1] - nodes[i][1]) / L
        N = float(ex * area / L) * sum(float(v) * u1[i_] for i_, v in emap[k]["a"].items())
        for (a, b), v in FRM._geo_entries(nodes, i, j, L, c, s_, dof).items():
            rr.append(a); cc.append(b); dd.append(N * float(v))
    G = sp.csr_matrix((dd, (rr, cc)), shape=(n, n))
    lam_fine = float(1 / sla.eigsh(-G, k=1, M=K0, which="LA", return_eigenvectors=False, v0=np.ones(n))[0])
    lo = float(st["lam_low"])
    bad = lo > lam_fine * (1 + 1e-6)
    return {"checked": 1, "violations": int(bad), "example": None if not bad else {"seed": seed, "lo": lo, "fine": lam_fine}}


def axial_case(seed):
    """sweep H (2026-11-02): 2D frames with AXIAL member loads on the columns (down: self-weight; up: a pull) —
    lambda_low <= lambda_fine <= lambda_high, the fine mesh 16 elements per member with each sub-element's N at its
    middle (the linear N's own variation O(h^2): tolerance 1e-3). H-MUTA: the stability witness with N_mean G."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    rng = random.Random(seed)
    if rng.random() < 1 / 3:
        # a single column (the path's own case): fixed base, tip load, self-weight or a pull, 1-4 elements
        Lc, me = rng.choice([3, 4, 6]), rng.choice([1, 2, 4])
        top = "" if rng.random() < 0.5 else "D, 2, UX, 0\n"
        deck = (f"ET, 1, BEAM3\nMP, EX, 1, 210e9\nR, 1, 0.01, 8e-5, 0.2\nN, 1, 0, 0\nN, 2, 0, {Lc}\nE, 1, 2\n"
                f"D, 1, UX, 0\nD, 1, UY, 0\nD, 1, ROTZ, 0\n{top}F, 2, FY, -{rng.randint(0, 200) * 1000}\nF, 2, FX, 1\n"
                f"QLOAD, 1, FY, {rng.choice([-1, 1]) * rng.randint(10, 300) * 1000}")
        if me > 1:
            deck = FRM.subdivide(deck, me)
        return _axial_check(seed, deck)
    deck, ne, roof = random_frame(rng, with_q=rng.random() < 0.5)
    if rng.random() < 0.5:                       # the member loads alone carry the columns (self-weight-like)
        deck = "\n".join(ln for ln in deck.splitlines() if not (ln.startswith("F,") and "FY" in ln))
    nd_, el_ = FRM.read_deck(deck)[:2]
    cols = [k for k, (i, j) in enumerate(el_, 1) if nd_[i][0] == nd_[j][0]]
    for k in cols:
        if rng.random() < 0.7:
            deck += f"\nQLOAD, {k}, FY, {rng.choice([-1, 1]) * rng.randint(2000, 40000) * rng.choice([1, 4])}"
    return _axial_check(seed, deck)


def _axial_check(seed, deck):
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    st = FRM.stability_lower(deck, "0")
    su = FRM.stability_upper(deck)
    if st.get("lam_low") is None:
        return {"checked": 0, "skipped": 1, "why": st.get("why")}
    fine = FRM.subdivide(deck, 16)
    nodes, elems, loads, supports, ex, (area, izz) = FRM.read_deck(fine)
    parts, f, dof, emap, _ = FRM.energy_system_full(fine, "0")
    n = len(dof)
    K0 = ZE._float_matrix(ZE.matrix(parts, n), n)
    u1 = sla.spsolve(K0.tocsc(), np.array([float(x) for x in f]))
    rr, cc, dd = [], [], []
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        c, s_ = (nodes[j][0] - nodes[i][0]) / L, (nodes[j][1] - nodes[i][1]) / L
        N = float(ex * area / L) * sum(float(v) * u1[i_] for i_, v in emap[k]["a"].items())
        for (a, b), v in FRM._geo_entries(nodes, i, j, L, c, s_, dof).items():
            rr.append(a); cc.append(b); dd.append(N * float(v))
    G = sp.csr_matrix((dd, (rr, cc)), shape=(n, n))
    try:
        mu = float(sla.eigsh(-G, k=1, M=K0, which="LA", return_eigenvectors=False, v0=np.ones(n))[0])
    except Exception as ex_:
        return {"checked": 0, "skipped": 1, "why": f"fine eigsh: {ex_}"[:120]}
    if mu <= 0:
        return {"checked": 0, "skipped": 1, "why": "the fine mesh has no buckling mode"}
    lam_fine = 1 / mu
    lo, hi = float(st["lam_low"]), su.get("lam_high")
    viol, n_chk, ex_ = 0, 1, None
    if lo > lam_fine * (1 + 1e-3):
        viol += 1
        ex_ = {"seed": seed, "lo": lo, "fine": lam_fine}
    if hi is not None:
        n_chk += 1
        if float(hi) < lam_fine * (1 - 1e-3):
            viol += 1
            ex_ = ex_ or {"seed": seed, "hi": float(hi), "fine": lam_fine}
    return {"checked": n_chk, "violations": viol, "example": ex_}


def axial_stress_case(seed):
    """sweep J (2026-11-03): second-order member STRESSES with an AXIAL member load (frame.second_order_case) on one
    random column, vertical, 1/2/4/8 elements: a cantilever (tip loads H, P) or a pinned member (end moments M_a,
    M_b, top load P); the axial load down (self-weight) or up (a pull); half the cases a transverse load q_x too. Reference: scipy solve_bvp on the continuum,
    nothing shared — theta' = M/EI, M' = C + N theta, C' = q_v (= -q_x), v' = theta, N(x) = F_y + q_y (L - x) (tension +; the
    nodal moments enter as M(0) = -M_a, M(L) = M_b). Both sides: every proved end-moment interval holds the reference
    (one global sign for the member), every proved |sigma| bound is not below the reference's max over its element.
    J-MUTA: the end moment's geometric part with N_mid G (not N_a G_a + N_b G_b)."""
    import numpy as np
    from scipy.integrate import solve_bvp
    rng = random.Random(seed)
    Lc, ne = rng.choice([2, 3, 4, 6]), rng.choice([1, 2, 4, 8])
    E, A, I, h = 210e9, 0.01, 8e-5, 0.2
    EI = E * I
    qy = rng.choice([-1, -1, 1]) * rng.randint(5, 250) * 1000
    P = rng.randint(0, 600) * 1000
    cant = rng.random() < 0.5
    H = rng.randint(1, 40) * 1000 if cant else 0
    Ma = 0 if cant else rng.choice([-1, 1]) * rng.randint(5, 60) * 1000
    Mb = 0 if cant else rng.choice([-1, 1]) * rng.randint(0, 60) * 1000
    qx = rng.choice([-1, 1]) * rng.randint(1, 30) * 1000 if rng.random() < 0.5 else 0   # a transverse load too
    deck = (f"ET, 1, BEAM3\nMP, EX, 1, 210e9\nR, 1, {A}, {I}, {h}\nN, 1, 0, 0\nN, 2, 0, {Lc}\nE, 1, 2\n"
            + ("D, 1, UX, 0\nD, 1, UY, 0\nD, 1, ROTZ, 0\n" if cant else "D, 1, UX, 0\nD, 1, UY, 0\nD, 2, UX, 0\n")
            + f"F, 2, FY, -{P}\n" + (f"F, 2, FX, {H}\n" if H else "")
            + (f"F, 1, MZ, {Ma}\n" if Ma else "") + (f"F, 2, MZ, {Mb}\n" if Mb else "") + f"QLOAD, 1, FY, {qy}"
            + (f"\nQLOAD, 1, FX, {qx}" if qx else ""))
    if ne > 1:
        deck = FRM.subdivide(deck, ne)
    r = FRM.second_order_case(deck, "0", [(k + 1, F(10) ** 12) for k in range(ne)])
    if not r.get("checks"):
        return {"checked": 0, "skipped": 1, "why": (r.get("why") or "")[:100]}
    Nf = lambda x: -P + qy * (Lc - x)
    def f(x, y):
        return np.vstack([y[1], y[2] / EI, y[3] + Nf(x) * y[1], 0 * y[3] - qx])   # C' = q_v, v = -u_x
    if cant:
        bc = lambda ya, yb: np.array([ya[0], ya[1], yb[2], yb[3] - H])
    else:
        bc = lambda ya, yb: np.array([ya[0], yb[0], ya[2] + Ma, yb[2] - Mb])
    x0 = np.linspace(0, Lc, 4001)
    sol = solve_bvp(f, bc, x0, np.zeros((4, x0.size)), tol=1e-9, max_nodes=1000000)
    if not sol.success:                          # a linear problem: retry looser before skipping (named)
        sol = solve_bvp(f, bc, x0, np.zeros((4, x0.size)), tol=1e-7, max_nodes=1000000)
    if not sol.success:
        return {"checked": 0, "skipped": 1, "why": "reference bvp did not converge"}
    xx = np.linspace(0, Lc, 20001)
    M = sol.sol(xx)[2]
    sig = np.abs(Nf(xx)) / A + np.abs(M) / (I / (h / 2))
    mref = max(np.abs(M).max(), 1.0)
    viol, n_chk, ex_ = 0, 0, None
    best = None
    for sg in (1, -1):                          # one global sign for the member's end moments
        bad = []
        for k, c in enumerate(r["checks"]):
            for e_, xe in (("I", Lc * k / ne), ("J", Lc * (k + 1) / ne)):
                m = sg * float(sol.sol(xe)[2])
                lo, hi = (float(F(v.split()[0])) for v in c["M_ends"][e_])
                if not (lo - 1e-6 * mref <= m <= hi + 1e-6 * mref) and not (lo - 1e-6 * mref <= -m <= hi + 1e-6 * mref):
                    bad.append((k + 1, e_, m, lo, hi))
        if best is None or len(bad) < len(best):
            best = bad
    n_chk += 2 * ne
    if best:
        viol += len(best)
        ex_ = {"seed": seed, "moment": best[0]}
    for k, c in enumerate(r["checks"]):
        hi = float(F(c["sigma_abs_max"].split()[0]))
        seg = (xx >= Lc * k / ne - 1e-12) & (xx <= Lc * (k + 1) / ne + 1e-12)
        n_chk += 1
        if hi < sig[seg].max() * (1 - 1e-6):
            viol += 1
            ex_ = ex_ or {"seed": seed, "elem": k + 1, "sigma_bound": hi, "ref": float(sig[seg].max())}
    return {"checked": n_chk, "violations": viol, "example": ex_}


def ltb_case(seed):
    """sweep I (2026-11-02): ustand.ltb's member critical factor against bench/night/ltb_ref.py (Gauss-quadrature
    Hermite elements, 96 per member, nothing shared): random doubly symmetric sections (I_w = 0 sometimes), spans,
    end moments, member-load parabolas, compressions; the lower bound over a BOX of moments and axial forces must stay
    below the reference at random points inside it, the upper witness (point boxes) above. I-MUT drops the continuum
    correction (two sub-elements, where the Hermite model alone is measurably above the continuum)."""
    import ltb_ref as RL
    from ustand import ltb as LTB
    rng = random.Random(seed)
    mutated = bool(LTB._MUTANT)
    L = F(rng.randint(3, 10))
    E = F(210 * 10 ** 9); G = E / F(26, 10)
    Iz = F(rng.randint(2, 40), 10 ** 6); Iy = Iz * rng.randint(3, 15); A = F(rng.randint(3, 15), 1000)
    J = F(rng.randint(5, 50), 10 ** 8); Iw = F(0) if rng.random() < 0.2 else F(rng.randint(1, 30), 10 ** 8)
    sec = (E * Iz, G * J, E * Iw, (Iy + Iz) / A)
    Mc = 10 ** 5
    MA, MB = F(rng.randint(-Mc, Mc)), F(rng.randint(-Mc, Mc))
    kap = F(rng.choice([0, rng.randint(-Mc, Mc)]))
    Ne = float(E * Iz) * 9.8696 / float(L) ** 2
    N = F(-int(rng.uniform(0, 0.5) * Ne)) if rng.random() < 0.7 else F(0)
    box = rng.random() < 0.4
    r = F(rng.randint(0, Mc // 20)) if box else F(0)
    rn = F(int(abs(N) / 20)) if box else F(0)
    m = 2 if mutated else rng.choice([2, 4, 8])
    lo = LTB.alpha_lower(L, sec, (N - rn, min(N + rn, F(0))), (MA - r, MA + r), (MB - r, MB + r), kap, m=m,
                         rel=F(1, 10 ** 5))
    viol, n_chk, ex_ = 0, 0, None
    pts = [(MA, MB, N)] + [(MA + r * F(rng.uniform(-1, 1)), MB + r * F(rng.uniform(-1, 1)),
                            min(N + rn * F(rng.uniform(-1, 1)), F(0))) for _ in range(3 if box else 0)]
    for a_, b_, n_ in pts:
        ref = RL.alpha(float(L), *(float(x) for x in sec), float(a_), float(b_), float(kap), float(n_))
        if ref is None or lo is None:
            continue
        n_chk += 1
        if float(lo) > ref * (1 + 1e-6):
            viol += 1
            ex_ = ex_ or {"seed": seed, "lo": float(lo), "ref": ref, "m": m}
    if not box and not mutated:
        hi = LTB.alpha_upper(L, sec, MA, MB, kap, N, m=8)
        ref = RL.alpha(float(L), *(float(x) for x in sec), float(MA), float(MB), float(kap), float(N))
        if hi is not None and ref is not None:
            n_chk += 1
            if float(hi) < ref * (1 - 1e-4):          # the fine mesh is itself an upper approximation (1e-4)
                viol += 1
                ex_ = ex_ or {"seed": seed, "hi": float(hi), "ref": ref}
    return {"checked": n_chk, "violations": viol, "example": ex_}


def truss_case(seed):
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    from ustand import truss as TR
    rng = random.Random(seed)
    nf = rng.randint(2, 8)
    L_ = ["/PREP7", "ET, 1, LINK1", "MP, EX, 1, 200e9", "R, 1, 0.002"]
    nid = lambda f_, c_: 2 * f_ + c_ + 1
    for f_ in range(nf + 1):
        for c_ in range(2):
            L_.append(f"N, {nid(f_, c_)}, {3 * c_}, {4 * f_}")
    bars = []
    for f_ in range(nf):
        diag = (nid(f_, 0), nid(f_ + 1, 1)) if rng.random() < .5 else (nid(f_, 1), nid(f_ + 1, 0))
        bars += [(nid(f_, 0), nid(f_ + 1, 0)), (nid(f_, 1), nid(f_ + 1, 1)), (nid(f_ + 1, 0), nid(f_ + 1, 1)), diag]
    bars = [b for b in dict.fromkeys(tuple(sorted(b)) for b in bars) if b[0] != b[1]]
    L_ += [f"E, {a}, {b}" for a, b in bars]
    L_ += [f"D, {nid(0, c_)}, UX, 0" for c_ in range(2)] + [f"D, {nid(0, c_)}, UY, 0" for c_ in range(2)]
    top = nid(nf, 0)
    L_ += [f"F, {top}, FX, {rng.randint(1000, 50000)}", f"F, {top}, FY, -{rng.randint(10000, 400000)}",
           f"F, {nid(nf, 1)}, FY, -{rng.randint(10000, 400000)}"]
    deck = "\n".join(L_)
    try:
        so = TR.second_order(deck, "0", [(top, "X")])
    except Exception as ex_:
        return {"checked": 0, "skipped": 1, "why": str(ex_)[:120]}
    nodes, bars_, forces, supports, ex, area = TR.read_deck(deck)
    parts, f, dof = TR.energy_system(deck, "0")
    n = len(dof)
    K0 = ZE._float_matrix(ZE.matrix(parts, n), n)
    fv = np.array([float(x) for x in f])
    u1 = sla.spsolve(K0.tocsc(), fv)
    rr, cc, dd = [], [], []
    for (a, b), p in zip(bars_, parts):
        w, g = p["terms"][0]
        N = float(w) * sum(float(v) * u1[i] for i, v in g.items())
        dx, dy = nodes[b][0] - nodes[a][0], nodes[b][1] - nodes[a][1]
        L = math.hypot(float(dx), float(dy))
        c, s_ = float(dx) / L, float(dy) / L
        h = {}
        for nd, sg in ((b, 1), (a, -1)):
            for d, comp in (("X", -s_), ("Y", c)):
                if (nd, d) in dof and comp:
                    h[dof[(nd, d)]] = h.get(dof[(nd, d)], 0.0) + sg * comp
        for i, gi in h.items():
            for j, gj in h.items():
                rr.append(i); cc.append(j); dd.append(N / L * gi * gj)
    u = sla.spsolve((K0 + sp.csr_matrix((dd, (rr, cc)), shape=(n, n))).tocsc(), fv)
    ref = u[dof[(top, "X")]]
    lo, hi = (float(x) for x in so[(top, "X")])
    bad = not (lo - 1e-12 - 1e-9 * abs(ref) <= ref <= hi + 1e-12 + 1e-9 * abs(ref))
    return {"checked": 1, "violations": int(bad), "example": None if not bad else {"seed": seed, "ref": ref, "lo": lo, "hi": hi}}


def general_case(seed):
    import itertools
    rng = random.Random(seed)
    n = rng.randint(3, 7)
    def rpart(m):
        out = []
        for _ in range(m):
            idx = rng.sample(range(n), rng.randint(1, min(3, n)))
            out.append((F(rng.randint(1, 9), rng.randint(1, 4)), {i: F(rng.randint(-3, 3) or 1) for i in idx}))
        return out
    Kp = [rpart(2) for _ in range(rng.randint(2, 5))]
    Gp = [rpart(1) for _ in range(rng.randint(1, 4))]
    A0 = ZE.matrix([{"t": 0, "terms": t} for t in Kp], n)
    for t_ in Gp:
        n0 = F(-rng.randint(0, 3), 10)
        for key, v in ZE.matrix([{"t": 0, "terms": t_}], n).items():
            A0[key] = A0.get(key, F(0)) + n0 * v
    parts = [{"t": F(rng.choice([1, 3, 5]), 100), "terms": t} for t in Kp] + \
            [{"t": F(rng.randint(0, 3), 100), "terms": t} for t in Gp]
    Ct = [(w / 50, g) for w, g in rpart(1)]
    f = [F(rng.randint(-5, 5)) for _ in range(n)]
    e = [F(rng.randint(-3, 3)) for _ in range(n)]
    try:
        r = ZE.certify_general(A0, parts, Ct, f, e, n)
    except ArithmeticError:
        return {"checked": 0, "skipped": 1}
    Cm = ZE.matrix([{"t": 0, "terms": Ct}], n)
    Pm = [ZE.matrix([{"t": 0, "terms": p["terms"]}], n) for p in parts]
    pts = [([s_ * p["t"] for s_, p in zip(sg, parts)], df) for sg in itertools.islice(
        itertools.product((-1, 1), repeat=len(parts)), 64) for df in (F(0), F(1))]
    pts += [([p["t"] * F(rng.randint(-100, 100), 100) for p in parts], F(rng.randint(0, 100), 100)) for _ in range(20)]
    viol = 0
    for ds, df in pts:
        A = dict(A0)
        for d, P in zip(ds, Pm):
            for key, v in P.items():
                A[key] = A.get(key, F(0)) + d * v
        for key, v in Cm.items():
            A[key] = A.get(key, F(0)) - df * v
        try:
            L, dd = ZE.ldl(n, A)
        except ValueError:
            viol += 1
            continue
        val = sum(a * b for a, b in zip(e, ZE.solve(L, dd, f)))
        viol += not (r["lo"] <= val <= r["hi"])
    return {"checked": len(pts), "violations": viol, "example": None if not viol else {"seed": seed}}


def plate_case(seed):
    import subprocess
    from ustand import hypercircle as HC
    rng = random.Random(seed)
    k = rng.choice([1, 2])
    aspect = rng.choice([2, 3, 4])
    load = rng.choice(["shear", "tension"])
    def deck(kk):
        return subprocess.run([sys.executable, str(ROOT / "examples/plate/gen_plate.py"), str(aspect * kk), str(kk),
                               "--load", load, "--h", str(F(1, kk))], capture_output=True, text=True, check=True).stdout
    try:
        a = HC.compliance_bounds(deck(k))
        b = HC.compliance_bounds(deck(4 * k))
    except Exception as ex_:
        return {"checked": 0, "skipped": 1, "why": str(ex_)[:120]}
    bad = not (a["lower"] <= a["upper"] and b["lower"] <= b["upper"] and a["lower"] <= b["upper"] and b["lower"] <= a["upper"])
    return {"checked": 1, "violations": int(bad), "example": None if not bad else {"seed": seed}}


def mutate(kind=True):
    """Break the second-order stress bound the way it once was broken: the member's interior and the continuum's
    end-moment corrections dropped ("ends only, Hermite moments" — 325 instead of 337.67 MPa on a beam-column); or
    (kind "geo") the end moment's geometric part N (G u) dropped (the K_E-row moment fixed on 2026-11-02); "geo3" /
    "geom3" the same breaks in ustand.frame3d (the whole geometric stiffness / the moment's N (G u))."""
    if kind == "axial":
        FRM._MUTANT["axial_mean"] = True
        return FRM._MUTANT.clear
    if kind == "axialm":
        FRM._MUTANT["axial_const_moment"] = True
        return FRM._MUTANT.clear
    if kind == "ltb":
        from ustand import ltb as LTB
        LTB._MUTANT["no_corr"] = True
        return LTB._MUTANT.clear
    if kind in ("geo3", "geom3"):
        from ustand import frame3d as F3
        F3._MUTANT["no_geo" if kind == "geo3" else "no_geo_moment"] = True
        return F3._MUTANT.clear
    if kind == "geo":
        FRM._MUTANT["no_geo_moment"] = True
    else:
        FRM._MUTANT["ends_only"] = True
    def restore():
        FRM._MUTANT.clear()
    return restore


MOM_TOL = 1e-3          # relative to the member's end moments; MEASURED 2026-11-02 on the fixed code: 0 excess in 1954 checks (40 frames); the no-G mutation exceeds by up to 4.6 %
DIST = []


SWEEPS = {"A": (beam_column_case, 400), "B": (frame_case, 120), "C": (stability_case, 120), "D": (truss_case, 200),
          "E": (general_case, 600), "F": (plate_case, 24), "G": (space_frame_case, 60), "H": (axial_case, 120), "I": (ltb_case, 150),
          "J": (axial_stress_case, 150)}


def _run(args):
    key, seed, mutated = args
    restore = mutate(mutated) if mutated else None
    fn = SWEEPS[key][0]
    t0 = time.time()
    try:
        r = fn(seed)
    except Exception as ex_:
        r = {"checked": 0, "errors": 1, "why": f"{type(ex_).__name__}: {ex_}"[:200], "seed": seed}
    finally:
        if restore:
            restore()
    r["seconds"] = time.time() - t0
    tag = {"geo": "-MUTG", "geo3": "-MUTG3", "geom3": "-MUTM3", "axial": "-MUTA", "ltb": "-MUTL", "axialm": "-MUTA"}.get(
        mutated, "-MUT" if mutated else "")
    return key + tag, r


def main(argv):
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 22
    scale = float(argv[argv.index("--scale") + 1]) if "--scale" in argv else 1.0
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else list(SWEEPS) + ["M"]
    tasks = []
    for key, (fn, count) in SWEEPS.items():
        if key in only:
            tasks += [(key, 1000 + s, False) for s in range(int(count * scale))]
    if "M" in only:
        tasks += [("A", 900000 + s, True) for s in range(int(200 * scale))]
        tasks += [("B", 900000 + s, True) for s in range(int(30 * scale))]
        tasks += [("A", 950000 + s, "geo") for s in range(int(200 * scale))]
        tasks += [("B", 950000 + s, "geo") for s in range(int(30 * scale))]
        tasks += [("G", 960000 + s, "geo3") for s in range(int(20 * scale))]
        tasks += [("G", 970000 + s, "geom3") for s in range(int(20 * scale))]
        tasks += [("H", 980000 + s, "axial") for s in range(int(60 * scale))]
        tasks += [("I", 990000 + s, "ltb") for s in range(int(60 * scale))]
        tasks += [("J", 991000 + s, "axialm") for s in range(int(60 * scale))]
    random.Random(7).shuffle(tasks)
    t0 = time.time()
    agg = {}
    with mp.get_context("fork").Pool(jobs) as pool:
        for i, (key, r) in enumerate(pool.imap_unordered(_run, tasks, chunksize=1), 1):
            a = agg.setdefault(key, {"cases": 0, "checked": 0, "violations": 0, "skipped": 0, "errors": 0,
                                     "seconds": 0.0, "examples": [], "why": []})
            a["cases"] += 1
            for fld in ("checked", "violations", "skipped", "errors"):
                a[fld] += r.get(fld, 0)
            a["seconds"] += r["seconds"]
            if r.get("example") and len(a["examples"]) < 5:
                a["examples"].append(r["example"])
            if r.get("why") and len(a["why"]) < 5:
                a["why"].append(r["why"])
            if i % 50 == 0:
                print(f"{i}/{len(tasks)} done, {time.time() - t0:.0f} s", flush=True)
    out = ROOT / "bench/night"
    (out / "REPORT.json").write_text(json.dumps(agg, indent=1, default=str))
    lines = ["# Night battery report", "", f"wall {time.time() - t0:.0f} s, {jobs} processes", "",
             "| sweep | cases | checked | violations | skipped | errors | cpu s |", "|---|---|---|---|---|---|---|"]
    for key in sorted(agg):
        a = agg[key]
        lines.append(f"| {key} | {a['cases']} | {a['checked']} | {a['violations']} | {a['skipped']} | {a['errors']} | "
                     f"{a['seconds']:.0f} |")
    lines += ["", "Violations must be 0 in A-F and > 0 in the -MUT rows (the check can see a broken bound).", ""]
    for key in sorted(agg):
        if agg[key]["examples"] or agg[key]["why"]:
            lines.append(f"- {key}: examples {agg[key]['examples'][:3]}; notes {agg[key]['why'][:3]}")
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
