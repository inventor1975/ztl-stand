# -*- coding: utf-8 -*-
"""
cadbracket — a PROVED two-sided bracket on a solid part's compliance, from its FEA deck (2026-11-10, CAD/FEA).

    python3 -m ustand.cadbracket part.fem [--subcase N] [--d-max D] [--d-min D] [--E-range LO:HI] [--E-ground credit]

  LOWER: ustand.tetfea (minimum potential energy; P1 on the deck's tets; the bound evaluated with every rounding
         bounded) — C >= f(v)^2 / a(v, v).
  UPPER: ustand.equil.choose (the Alfeld stress, hybridized: per-tet KKT + an SPD trace system, AMG + CG) CHOOSES an
         equilibrated field; ustand.equil.finish makes it EXACTLY admissible (exact fluxes per face, the forest push);
         ustand.alfeld.energy_upper_ev bounds its compliance energy (binary64, every rounding carried) — C <= ||tau||^2.
  Then d = C / |F| (the load's work-conjugate displacement; a rotation C / |M| for a pure moment) in [d_lo, d_hi],
  and, with a requirement, ustand.cadstiff's verdict by ZTL's judge (E with its ground).
Premises (said in the output): the deck's tets ARE the part (its sha256); linear isotropic elasticity; supports =
RBE2 spiders to SPC'd nodes (u = 0 there); the load = the traction whose consistent nodal loads are the RBE3
distribution of the subcase's FORCE / MOMENT.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time

import numpy as np

from . import tetfea as TF, tetmesh as TM, equil as EQ, alfeld as AL


def _trim():
    """hand freed heap back to the OS (glibc keeps it otherwise: the lower bound's assembled K and AMG, freed, still
    counted against the cap — 148 peaked at 16.5 GB of an 18 GB cap, 2026-11-10)"""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:
        pass


def bracket(path, subcase=1, log=print, cg_tol=1e-8, matfree=None, zdtype=None, dump_g=None, dump_eta=None,
            smoother="jacobi"):
    from fractions import Fraction as Fr
    t0 = time.time()
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    d = TF.read_deck(path)
    lo = TF.solve_cases(d, [subcase], tol=1e-4, log=lambda s: None, return_u=dump_eta is not None)[0]
    log(f"lower (2a): C >= {lo['compliance_lower_proved']:.6f}; {time.time() - t0:.0f} s")
    _trim()
    ids = sorted(d["grids"])
    idx = {n: i for i, n in enumerate(ids)}
    Xq = [tuple(TF._nas(x) for x in d["grids"][n]) for n in ids]
    X = np.array([[float(c) for c in p] for p in Xq])
    T = np.array([[idx[n] for n in t] for t in d["tets"]])
    F, own, lf, tf = TM.faces(T)
    fixed = {idx[n] for ind, deps in d["rbe2"] for n in deps if d["spc"].get(ind, "").startswith("123")}
    Fv, Mv = tuple(lo["F"]), tuple(lo["M"])
    trc = d.get("traction")
    if trc is not None:
        # a REFINED deck (ustand.refine): the traction itself is given (the coarse deck's, linear per coarse face);
        # tetfea already refused any other load on it
        kind = TM.classify(F, own, fixed, {idx[n] for n in trc["nodal"]})
        tr = {idx[n]: np.asarray(v, float) for n, v in trc["nodal"].items()}
    else:
        ref, _, rn = d["rbe3"][0]
        kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
        xyz = {n: list(X[idx[n]]) for n in rn + [ref]}
        fl = TF.rbe3_loads(xyz, ref, rn, Fv, Mv)
        tr, res, lost = TM.rbe3_traction(X, F, kind, {idx[n]: fl[i] for i, n in enumerate(rn)})
        if lost:
            raise ValueError(f"{len(lost)} RBE3 nodal forces on nodes of no loaded face: the load is not a traction "
                             f"here")
    A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    n2 = np.linalg.norm(np.cross(B - A, C - A), axis=1)
    q = np.zeros((len(F), 3, 3))
    for fid in np.where(kind == 2)[0]:
        for p_ in range(3):
            q[fid, p_] = tr[int(F[fid, p_])] * n2[fid]
    E, nu = d["mat"][0], d["mat"][1]
    # level 3b: a prestress in the load (subcase = {"F", "M", "prestress": {"omega", "sigma"}}). The upper side keeps
    # tau' admissible for the traction alone and adds p = sig_e chi_omega analytically (equil: "level 3b"); the choice
    # minimises ||tau' + p||^2 through the linear term lin.
    pre = subcase.get("prestress") if isinstance(subcase, dict) else None
    lin = om = None
    if pre is not None:
        om = np.asarray(pre["omega"], bool)
        lin = np.zeros((len(T), 36))
        if "S1" in pre:                             # level 3c: a LINEAR extractor sig_e(x) = S0 + S1 . x
            lin[om] = EQ.extractor_linear_b_float(X[T[om]], pre["S0"], pre["S1"], float(E), float(nu))
        else:
            sgf = [[float(x) for x in row] for row in pre["sigma"]]
            lin[om] = EQ.prestress_linear_float(X[T[om]], sgf, float(E), float(nu))
    g, e_float, info = EQ.choose(X, T, F, own, tf, kind, float(E), float(nu), q, direct=False, tol=cg_tol,
                                 log=lambda m: log(m), zdtype=np.float64 if zdtype is None else zdtype,
                                 matfree=(len(T) > 100000) if matfree is None else matfree, lin=lin, smoother=smoother)
    if pre is not None:
        if "S1" in pre:
            self_f = EQ.extractor_linear_self_float(X[T[om]], pre["S0"], pre["S1"], float(E), float(nu))
        else:
            sg_ = np.array(sgf)
            As_ = ((1 + float(nu)) * sg_ - float(nu) * np.trace(sg_) * np.eye(3)) / float(E)
            P_ = X[T[om]]
            vol_ = np.abs(np.linalg.det(np.stack([P_[:, 1] - P_[:, 0], P_[:, 2] - P_[:, 0], P_[:, 3] - P_[:, 0]],
                                                 2))) / 6
            self_f = float(vol_.sum() * (sg_ * As_).sum())
        e_float = e_float + 2 * float((lin[om] * g[om]).sum()) + self_f
    log(f"upper choice (float): {e_float:.6f}; {time.time() - t0:.0f} s")
    if dump_g:                                      # the float choice, saved to profile the exact finish alone
        np.save(dump_g, g)
    qp = {int(f): [[Fr(float(q[f, p_, c])) for c in range(3)] for p_ in range(3)] for f in np.where(kind == 2)[0]}
    qp.update({int(f): [[Fr(0)] * 3 for _ in range(3)] for f in np.where(kind == 3)[0]})
    qd, bad, _, bits = EQ.finish(Xq, T, F, own, tf, kind, g, qp, fixed_faces=set(qp))
    if bad:
        raise RuntimeError(f"{bad} tets left unbalanced by the exact push — no upper bound")
    log(f"exact push: 0 unbalanced, denominators <= {bits} bits; {time.time() - t0:.0f} s")
    pos, sgn = EQ.slot_maps(T, F, own, tf)
    Ps, gs = [], []
    for t in range(len(T)):
        out = []
        for f in range(4):
            qq = qd[int(tf[t, f])]
            s_ = int(sgn[t, f])
            for jv in range(3):
                r = qq[int(pos[t, f, jv])]
                out += [r[0] * s_, r[1] * s_, r[2] * s_]
        Ps.append([list(Xq[v]) for v in T[t]])
        gs.append(out)
    if dump_eta is not None:
        up, per_ev = AL.energy_upper_ev(Ps, gs, E, nu, return_terms=True)
    else:
        up = AL.energy_upper_ev(Ps, gs, E, nu)
    pre_out = None
    if pre is not None:
        # ||tau' + p||^2 = ||tau'||^2 + sum over omega (2 b_T . g_T + |T| sig : A sig) — the extra terms EXACT
        cross = self_ = Fr(0)
        linear = "S1" in pre
        for t in np.where(om)[0]:
            if linear:
                bT = EQ.extractor_linear_b(Ps[t], pre["S0"], pre["S1"], E, nu)
                self_ += EQ.extractor_linear_self(Ps[t], pre["S0"], pre["S1"], E, nu)
            else:
                bT = EQ.prestress_linear(Ps[t], pre["sigma"], E, nu)
                self_ += EQ.prestress_self(Ps[t], pre["sigma"], E, nu)
            cross += 2 * sum(x * y for x, y in zip(bT, gs[t]))
        extra = cross + self_
        up = math.nextafter(float(Fr(up) + extra), math.inf)
        pre_out = {"tets": int(om.sum()), "extra_exact": float(extra), "cross_exact": float(cross),
                   "self_exact": float(self_)}
        if linear:
            pre_out["S0"] = [[float(x) for x in row] for row in pre["S0"]]
            pre_out["S1"] = [[[float(x) for x in c] for c in row] for row in pre["S1"]]
            pre_out["extractor"] = pre.get("label", "linear")
        else:
            pre_out["sigma_e"] = [[float(x) for x in row] for row in pre["sigma"]]
        log(f"prestress: {int(om.sum())} tets, exact extra {float(extra):.6f}; upper {up:.6f}")
    Fn, Mn = math.sqrt(sum(x * x for x in Fv)), math.sqrt(sum(x * x for x in Mv))
    c_lo, c_hi = lo["compliance_lower_proved"], up
    w = Fn if Fn and not Mn else (Mn if Mn and not Fn else None)
    U_ = 2.0 ** -53
    if pre is not None:
        w = None                                    # a traction + prestress load has no single work-conjugate
    out = {"deck": path, "sha256": sha, "subcase": lo["subcase"], "label": lo["label"], "F": Fv, "M": Mv,
            "tets": int(len(T)), "E": float(E), "nu": float(nu),
            "compliance": [c_lo, c_hi], "gap": c_hi / c_lo - 1,
            "work_conjugate": ([c_lo / w * (1 - 2 * U_), c_hi / w * (1 + 2 * U_)] if w else None),
            "work_conjugate_is": ("displacement along F (mm)" if Fn and not Mn else "rotation about M (rad)"
                                  if Mn and not Fn else None),
            "upper_float_choice": e_float, "push_bits": bits, "seconds": round(time.time() - t0, 1),
            "rests_on": [f"the deck {path} (sha256 {sha[:16]}…): its tets ARE the part — EARNED IF STABLE on it",
                         "linear isotropic elasticity", "supports: RBE2 spiders to SPC'd nodes (u = 0)",
                         "the load: the traction whose consistent nodal loads are the RBE3 distribution"]}
    if trc is not None:
        rf = d.get("refined_from", {})
        out["refined_from"] = {k: v for k, v in rf.items() if k != "nodal"}
        out["rests_on"][0] = (f"a red refinement (ustand.refine) of {rf.get('deck', '?')} (sha256 "
                              f"{str(rf.get('sha256', '?'))[:16]}…): the same faceted part, its tets subdivided 1:8")
        out["rests_on"][3] = ("the load: the coarse deck's traction (linear per coarse loaded face, its nodal values "
                              "M_s t = f_RBE3), given at the fine nodes")
    if pre_out is not None:
        out["prestress"] = pre_out
        out["rests_on"].append("plus the prestress load int_omega eps(v) : sig_e (omega = the selected tets)")
    if dump_eta is not None:
        Gf = np.array([[float(x) for x in row] for row in gs])
        eta, info_eta = eta_indicator(X, T, Gf, per_ev.v, lo["u"], float(E), float(nu), pre=pre, om=om)
        info_eta["gap"] = c_hi - c_lo
        out["eta"] = info_eta
        if dump_eta == "return":
            out["_eta_array"] = eta
            # the indicator's inputs, for tests that plant a wrong tau into eta_indicator itself
            out["_eta_parts"] = {"X": X, "T": T, "G": Gf, "energy": np.asarray(per_ev.v, float), "u": lo["u"],
                                 "E": float(E), "nu": float(nu), "pre": pre, "om": om}
        else:
            np.save(dump_eta, eta)
        log(f"indicator: sum eta^2 = {info_eta['sum']:.6f} vs the gap {c_hi - c_lo:.6f} (hypercircle "
            f"{info_eta['hypercircle']:.6f})")
    return out


def _down(x):
    """the largest binary64 <= the exact rational x"""
    from fractions import Fraction as Fr
    y = float(x)
    return math.nextafter(y, -math.inf) if Fr(y) > x else y


def _up(x):
    """the smallest binary64 >= the exact rational x"""
    from fractions import Fraction as Fr
    y = float(x)
    return math.nextafter(y, math.inf) if Fr(y) < x else y


def _face_data(qd, nf, T, tf, pos, sgn, rows_for=()):
    """The per-tet face data (nt, 36) of the exact fluxes qd, ROUNDED once to binary64 (float(Fraction) is correctly
    rounded, and the sign flip is exact: the same numbers energy_upper_ev makes of bracket's Fraction lists), plus the
    exact Fraction rows of the tets in rows_for (only those: omega's tets, for X = sum b_T . g_T)."""
    Qf = np.zeros((nf, 3, 3))
    for fid, qq in qd.items():
        for p_ in range(3):
            for c in range(3):
                Qf[fid, p_, c] = float(qq[p_][c])
    G = np.empty((len(T), 36))
    for f in range(4):
        for jv in range(3):
            G[:, f * 9 + jv * 3:f * 9 + jv * 3 + 3] = sgn[:, f, None] * Qf[tf[:, f], pos[:, f, jv]]
    rows = {}
    for t in rows_for:
        t = int(t)
        out = []
        for f in range(4):
            qq = qd[int(tf[t, f])]
            s_ = int(sgn[t, f])
            for jv in range(3):
                r = qq[int(pos[t, f, jv])]
                out += [r[0] * s_, r[1] * s_, r[2] * s_]
        rows[t] = out
    return G, rows


def bracket_functionals(path, subcase=1, functionals=(), s_values=None, log=print, cg_tol=1e-8, matfree=None,
                        zdtype=None, smoother="jacobi", lower_tol=1e-4, planted=None):
    """LEVEL 3d (2026-11-12): brackets of stress functionals l_p(u) with ONE solve per load and ONE per functional.
    research/cad/PLAN-level3.md, "Level 3d — one solve per load, one per functional".

    subcase: the load f (a deck subcase or {"F", "M", "label"}, no prestress). functionals: a list of
    {"label", "omega": bool mask, "sigma": 3 x 3} (3b, a constant extractor) or {"label", "omega", "S0", "S1"} (3c, a
    linear one), all EXACT and UNSCALED. s_values: None, or per functional a list of explicit s (> 0, binary64) to
    evaluate in addition to s* = sqrt(w_f / w_p).
    Fields, once each: lower — v_f (the P1 field of f), v_p (of p alone, no traction); upper — g_f (choose with the
    traction, lin = 0; the exact finish), g_p (choose with ZERO traction and lin = b_p; the exact finish with zero
    prescribed flux). For a dyadic s:
        L(s) = W^2 / a_up(v, v),  v = round(v_f + s v_p) (any integer field is admissible), W = f(v) + s l_p(v) exact;
        U(s) = energy_upper_ev_g(Ev.rounded(g_f) + Ev.exact(s) Ev.rounded(g_p)) + 2 s X_f + 2 s^2 X_p + s^2 self,
               X_f = sum_omega b_T . g_f,T, X_p = sum_omega b_T . g_p,T, self = sum_omega |T| sig_e : A sig_e (exact);
        (L(s) - U(-s)) / (4 s) <= l_p(u) <= (U(s) - L(-s)) / (4 s), in exact rationals, rounded outward.
    planted (tests only): "gp_traction" — g_p chosen and finished with the traction left on; "drop_xf" — X_f = 0;
    "vp_sign" — v = v_f - s v_p."""
    from fractions import Fraction as Fr
    from .errfloat import Ev
    t0 = time.time()
    quiet = lambda m: None
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    d = TF.read_deck(path)
    functionals = list(functionals)
    if not functionals:
        raise ValueError("no functional given")
    if isinstance(subcase, dict) and subcase.get("prestress") is not None:
        raise ValueError("the load f carries no prestress here: the functionals are given separately")
    E, nu = d["mat"][0], d["mat"][1]
    # ---------------------------------------------------------------- the lower side: one P1 solve per field
    ctx = TF.setup(d, log=quiet)
    Lf = TF.case_load(ctx, subcase)
    ts = time.time()
    _, vi_f, res_f = TF.case_field(ctx, Lf["ftot"], tol=lower_tol, log=quiet)
    fvec = Lf["fvec"]
    low_f, _, _, _, _ = TF.lower_bound(ctx, vi_f, fvec)
    L_f = _down(low_f)
    log(f"lower field f: {len(res_f)} AMG-CG iterations, C(f) >= {L_f:.6f}; {time.time() - t0:.0f} s")
    timing = {"lower_f": round(time.time() - ts, 1)}
    fields = []
    for i, fn in enumerate(functionals):
        pre = {k_: v_ for k_, v_ in fn.items() if k_ in ("sigma", "S0", "S1")}
        pre["omega"] = np.asarray(fn["omega"], bool)
        Lp = TF.case_load(ctx, {"F": (0.0, 0.0, 0.0), "M": (0.0, 0.0, 0.0), "traction": False, "prestress": pre})
        ts = time.time()
        _, vi_p, res_p = TF.case_field(ctx, Lp["ftot"], tol=lower_tol, log=quiet)
        low_p, _, _, _, _ = TF.lower_bound(ctx, vi_p, None, pre, pre["omega"], t_scale=0)
        fields.append({"label": fn.get("label", f"functional {i}"), "pre": pre, "om": pre["omega"], "vi_p": vi_p,
                       "L_p": _down(low_p), "cg_lower": len(res_p), "sec_lower": round(time.time() - ts, 1)})
        log(f"lower field p[{fields[-1]['label']}]: {len(res_p)} AMG-CG iterations, C(p) >= {fields[-1]['L_p']:.6f}; "
            f"{time.time() - t0:.0f} s")
    for key in ("ml", "grads", "P", "vol"):          # the stiffness's AMG is not needed for the evaluations
        ctx.pop(key, None)
    _trim()
    # ---------------------------------------------------------------- the upper side: one trace solve per field
    ids = sorted(d["grids"])
    idx = {n: i for i, n in enumerate(ids)}
    Xq = [tuple(TF._nas(x) for x in d["grids"][n]) for n in ids]
    X = np.array([[float(c) for c in p] for p in Xq])
    T = np.array([[idx[n] for n in t] for t in d["tets"]])
    F, own, lf, tf = TM.faces(T)
    fixed = {idx[n] for ind, deps in d["rbe2"] for n in deps if d["spc"].get(ind, "").startswith("123")}
    trc = d.get("traction")
    if trc is not None:
        kind = TM.classify(F, own, fixed, {idx[n] for n in trc["nodal"]})
        tr = {idx[n]: np.asarray(v, float) for n, v in trc["nodal"].items()}
    else:
        ref, _, rn = d["rbe3"][0]
        kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
        xyz = {n: list(X[idx[n]]) for n in rn + [ref]}
        fl = TF.rbe3_loads(xyz, ref, rn, tuple(Lf["F"]), tuple(Lf["M"]))
        tr, res, lost = TM.rbe3_traction(X, F, kind, {idx[n]: fl[i] for i, n in enumerate(rn)})
        if lost:
            raise ValueError(f"{len(lost)} RBE3 nodal forces on nodes of no loaded face: the load is not a traction "
                             f"here")
    A_, B_, C_ = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    n2 = np.linalg.norm(np.cross(B_ - A_, C_ - A_), axis=1)
    q = np.zeros((len(F), 3, 3))
    for fid in np.where(kind == 2)[0]:
        for p_ in range(3):
            q[fid, p_] = tr[int(F[fid, p_])] * n2[fid]
    pos, sgn = EQ.slot_maps(T, F, own, tf)
    Pv = X[T]                                       # the exact coordinates rounded once (as energy_upper_ev does)
    mf = (len(T) > 100000) if matfree is None else matfree
    zd = np.float64 if zdtype is None else zdtype
    # the exact b_T and self_T on each omega (Fractions, only omega's tets)
    for fd in fields:
        pre, om = fd["pre"], fd["om"]
        lin = np.zeros((len(T), 36))
        bT, self_ = {}, Fr(0)
        for t in np.where(om)[0]:
            Pt = [list(Xq[v]) for v in T[t]]
            if "S1" in pre:
                bT[int(t)] = EQ.extractor_linear_b(Pt, pre["S0"], pre["S1"], E, nu)
                self_ += EQ.extractor_linear_self(Pt, pre["S0"], pre["S1"], E, nu)
            else:
                bT[int(t)] = EQ.prestress_linear(Pt, pre["sigma"], E, nu)
                self_ += EQ.prestress_self(Pt, pre["sigma"], E, nu)
        if "S1" in pre:
            lin[om] = EQ.extractor_linear_b_float(X[T[om]], pre["S0"], pre["S1"], float(E), float(nu))
        else:
            lin[om] = EQ.prestress_linear_float(X[T[om]], [[float(x) for x in r] for r in pre["sigma"]], float(E),
                                                float(nu))
        fd["bT"], fd["self"], fd["lin"] = bT, self_, lin
    omega_all = sorted({t for fd in fields for t in fd["bT"]})

    def field(qflux, lin, what):
        ts_ = time.time()
        g, e_float, info = EQ.choose(X, T, F, own, tf, kind, float(E), float(nu), qflux, direct=False, tol=cg_tol,
                                     log=lambda m: log(m), zdtype=zd, matfree=mf, lin=lin, smoother=smoother)
        qp = {int(f): [[Fr(float(qflux[f, p_, c])) for c in range(3)] for p_ in range(3)] for f in np.where(kind == 2)[0]}
        qp.update({int(f): [[Fr(0)] * 3 for _ in range(3)] for f in np.where(kind == 3)[0]})
        qd, bad, _, bits = EQ.finish(Xq, T, F, own, tf, kind, g, qp, fixed_faces=set(qp))
        del g
        if bad:
            raise RuntimeError(f"{what}: {bad} tets left unbalanced by the exact push — no upper bound")
        G, rows = _face_data(qd, len(F), T, tf, pos, sgn, omega_all)
        del qd
        _trim()
        log(f"upper field {what}: choice (float) {e_float:.6f}, CG {info.get('cg_iterations')}, push bits {bits}; "
            f"{time.time() - t0:.0f} s")
        return G, rows, {"cg_iterations": info.get("cg_iterations"), "push_bits": bits, "float_energy": e_float,
                         "seconds": round(time.time() - ts_, 1)}

    def Xof(fd, rows):
        return sum((sum(x * y for x, y in zip(b, rows[t])) for t, b in fd["bT"].items()), Fr(0))

    G_f, rows, info_f = field(q, None, "f")
    for fd in fields:
        fd["X_f"] = Fr(0) if planted == "drop_xf" else Xof(fd, rows)
    del rows
    U_f = AL.energy_upper_ev_g(Pv, Ev.rounded(G_f), E, nu)
    log(f"compliance of f: [{L_f:.6f}, {U_f:.6f}]; {time.time() - t0:.0f} s")
    zero_q = q if planted == "gp_traction" else np.zeros_like(q)
    for fd in fields:
        G_p, rows, fd["info_upper"] = field(zero_q, fd["lin"], f"p[{fd['label']}]")
        fd["X_p"] = Xof(fd, rows)
        del rows
        fd["G_p"] = G_p
        up_p = AL.energy_upper_ev_g(Pv, Ev.rounded(G_p), E, nu)
        fd["U_p"] = _up(Fr(up_p) + 2 * fd["X_p"] + fd["self"])
        fd.pop("lin")
    # ---------------------------------------------------------------- the evaluations at s
    ge_f = Ev.rounded(G_f)

    def L_at(fd, s):
        m_, den = s.as_integer_ratio()                # den a power of two
        sg = -1 if planted == "vp_sign" else 1
        N = [a * den + sg * m_ * b for a, b in zip(vi_f, fd["vi_p"])]           # exact: den (v_f + s v_p) 2^S
        # any integer field zero on the supports is admissible and the bound is homogeneous of degree 0 in v: scale
        # the combination down by 2^e so a_upper_float's integers stay < 2^51 (a large s: s v_p >> v_f)
        e = max(0, (max(abs(x) for x in N) // den).bit_length() - 49)
        dd = den << e
        v = [(x + dd // 2) // dd for x in N]
        low, W, fv, fp, a_up = TF.lower_bound(ctx, v, fvec, fd["pre"], fd["om"], t_scale=1, p_scale=Fr(s))
        return _down(low)

    def U_at(fd, s):
        sf = Fr(s)
        up = AL.energy_upper_ev_g(Pv, ge_f + Ev.exact(np.float64(s)) * Ev.rounded(fd["G_p"]), E, nu)
        return _up(Fr(up) + 2 * sf * fd["X_f"] + 2 * sf * sf * fd["X_p"] + sf * sf * fd["self"])

    def at(fd, s):
        s = float(s)
        if not s > 0:
            raise ValueError("s must be > 0")
        Lp_, Lm_, Up_, Um_ = L_at(fd, s), L_at(fd, -s), U_at(fd, s), U_at(fd, -s)
        sf = Fr(s)
        lo = (Fr(Lp_) - Fr(Um_)) / (4 * sf)
        hi = (Fr(Up_) - Fr(Lm_)) / (4 * sf)
        return {"s": s, "bracket": [_down(lo), _up(hi)], "L_plus": Lp_, "L_minus": Lm_, "U_plus": Up_,
                "U_minus": Um_, "compliance_plus": [Lp_, Up_], "compliance_minus": [Lm_, Um_]}

    out_f = []
    w_f = U_f - L_f
    for i, fd in enumerate(fields):
        ts = time.time()
        w_p = fd["U_p"] - fd["L_p"]
        s_star = float(math.sqrt(w_f / w_p)) if w_p > 0 and w_f > 0 else 1.0
        r = at(fd, s_star)
        extra = [at(fd, s) for s in (s_values[i] if s_values else [])]
        sec_eval = round(time.time() - ts, 1)
        lab = fd["label"]
        log(f"{lab}: s* = {s_star:.6g}, l_p(u) in [{r['bracket'][0]:.6f}, {r['bracket'][1]:.6f}]" +
            "".join(f"; at s = {e['s']}: [{e['bracket'][0]:.6f}, {e['bracket'][1]:.6f}]" for e in extra) +
            f"; {time.time() - t0:.0f} s")
        pre = fd["pre"]
        o = {"label": lab, "bracket": r["bracket"], "s": s_star, "s_rule": "s* = sqrt(w_f / w_p) from the float widths",
             "L_plus": r["L_plus"], "L_minus": r["L_minus"], "U_plus": r["U_plus"], "U_minus": r["U_minus"],
             "at_s": extra, "p_alone_compliance": [fd["L_p"], fd["U_p"]], "w_f": w_f, "w_p": w_p,
             "tets": int(fd["om"].sum()), "X_f": float(fd["X_f"]), "X_p": float(fd["X_p"]),
             "self": float(fd["self"]),
             "cg_iterations": {"lower_p1_amg": fd["cg_lower"], "upper_trace": fd["info_upper"]["cg_iterations"]},
             "push_bits": fd["info_upper"]["push_bits"],
             "seconds": {"lower_field": fd["sec_lower"], "upper_field": fd["info_upper"]["seconds"],
                         "evaluations": sec_eval}}
        if "S1" in pre:
            o["S0"] = [[float(x) for x in rw] for rw in pre["S0"]]
            o["S1"] = [[[float(x) for x in c] for c in rw] for rw in pre["S1"]]
        else:
            o["sigma_e"] = [[float(x) for x in rw] for rw in pre["sigma"]]
        out_f.append(o)
    out = {"deck": path, "sha256": sha, "level": "3d: one solve per load, one per functional",
           "subcase": subcase if not isinstance(subcase, dict) else {k_: v_ for k_, v_ in subcase.items()},
           "F": tuple(Lf["F"]), "M": tuple(Lf["M"]), "tets": int(len(T)), "E": float(E), "nu": float(nu),
           "compliance": [L_f, U_f], "gap": U_f / L_f - 1,
           "cg_iterations_f": {"lower_p1_amg": len(res_f), "upper_trace": info_f["cg_iterations"]},
           "push_bits_f": info_f["push_bits"],
           "seconds_f": {"lower_field": timing["lower_f"], "upper_field": info_f["seconds"]},
           "functionals": out_f, "seconds": round(time.time() - t0, 1),
           "rests_on": [f"the deck {path} (sha256 {sha[:16]}…): its tets ARE the part — EARNED IF STABLE on it",
                        "linear isotropic elasticity", "supports: RBE2 spiders to SPC'd nodes (u = 0)",
                        ("the load: the traction whose consistent nodal loads are the RBE3 distribution"
                         if trc is None else "the load: the coarse deck's traction, given at the fine nodes"),
                        "each functional l_p(v) = int_omega eps(v) : sig_e (omega = the selected tets), by "
                        "polarization of C(f + s p) and C(f - s p)"]}
    if planted:
        out["PLANTED"] = planted
    return out


def eta_indicator(X, T, G, energy_T, u, E, nu, pre=None, om=None):
    """The per-tet HYPERCIRCLE indicator (float; it only CHOOSES a mesh, no bound rests on it), 2026-11-11.
    For tau admissible for the load l and a kinematic field alpha*u, Prager-Synge gives, with alpha = l(u)/a(u, u):
        sum_T || tau - alpha C eps(u) ||^2_{A,T} = ||tau||^2_A - l(u)^2 / a(u, u)  (= upper - lower when the lower is
    the Rayleigh quotient of u). Per tet, with sigma_u = C eps(u) constant on a P1 tet and div tau' = 0 inside T:
        eta_T^2 = ||tau_T||^2 - 2 alpha int_T tau : eps(u) + alpha^2 |T| eps : C eps,
        int_T tau' = boundary moments of the face data (mean_stress_integral's weights), tau = tau' + p on omega
        (p the 3b prestress or the 3c linear extractor): ||tau'+p||^2_T = ||tau'||^2_T + 2 b_T . g_T + self_T,
        int_T p : eps = eps : |T| p(centroid).
    X (nv,3), T (nt,4), G (nt,36) the EXACT face data (as floats), energy_T (nt) ||tau'||^2_{A,T}, u (nv,3) the P1
    solution of the same load. -> (eta^2 (nt), info)"""
    P = X[T]
    D = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=2)
    Di = np.linalg.inv(D)
    gr = np.concatenate([-Di.sum(axis=1, keepdims=True), Di], axis=1)          # (n, 4, 3) grad of barycentrics
    vol = np.abs(np.linalg.det(D)) / 6
    Gu = np.einsum("nia,nib->nab", u[T], gr)
    eps = 0.5 * (Gu + Gu.transpose(0, 2, 1))
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    sig = 2 * mu * eps + lam * np.trace(eps, axis1=1, axis2=2)[:, None, None] * np.eye(3)
    a_T = vol * np.einsum("nij,nij->n", sig, eps)
    # int_T tau'_ij = sum over the 12 slots s = (f, jv) of g[s, i] w[s, j], w = sum_u (1 + d_uv)/24 x_u
    It = np.zeros((len(T), 3, 3))
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        for jv in range(3):
            w = sum((2 if iv == jv else 1) * P[:, vv] for iv, vv in enumerate(vs)) / 24          # (n, 3)
            s = f * 3 + jv
            It += G[:, 3 * s:3 * s + 3, None] * w[:, None, :]
    l_T = np.einsum("nij,nij->n", It, eps)
    tau2 = np.asarray(energy_T, float).copy()
    if pre is not None:
        omi = np.where(np.asarray(om, bool))[0]
        Po = P[omi]
        if "S1" in pre:
            S0 = np.array([[float(x) for x in r] for r in pre["S0"]])
            S1 = np.array([[[float(x) for x in c] for c in r] for r in pre["S1"]])
            b = EQ.extractor_linear_b_float(Po, pre["S0"], pre["S1"], E, nu)
            c = Po.mean(axis=1)
            pc = S0[None] + np.einsum("ijk,nk->nij", S1, c)                      # p at the centroid
            Af = lambda s_: ((1 + nu) * s_ - nu * np.trace(s_) * np.eye(3)) / E
            B0 = Af(S0)
            B1 = np.stack([Af(S1[:, :, k]) for k in range(3)], axis=2)
            sx = Po.sum(axis=1)
            Q = vol[omi, None, None] * (np.einsum("nak,nal->nkl", Po, Po) + sx[:, :, None] * sx[:, None, :]) / 20
            d0 = float((S0 * B0).sum())
            d1 = np.einsum("ij,ijk->k", S0, B1) + np.einsum("ijk,ij->k", S1, B0)
            d2 = np.einsum("ijk,ijl->kl", S1, B1)
            self_T = vol[omi] * d0 + vol[omi] * (c @ d1) + np.einsum("kl,nkl->n", d2, Q)
        else:
            sg = np.array([[float(x) for x in r] for r in pre["sigma"]])
            b = EQ.prestress_linear_float(Po, sg, E, nu)
            pc = np.broadcast_to(sg, (len(omi), 3, 3))
            As = ((1 + nu) * sg - nu * np.trace(sg) * np.eye(3)) / E
            self_T = vol[omi] * float((sg * As).sum())
        tau2[omi] += 2 * np.einsum("ni,ni->n", b, G[omi]) + self_T
        l_T[omi] += vol[omi] * np.einsum("nij,nij->n", pc, eps[omi])
    l_, a_ = float(l_T.sum()), float(a_T.sum())
    alpha = l_ / a_
    eta = tau2 - 2 * alpha * l_T + alpha ** 2 * a_T
    info = {"sum": float(eta.sum()), "hypercircle": float(tau2.sum()) - l_ * l_ / a_, "alpha": alpha,
            "negative_tets": int((eta < 0).sum()), "min": float(eta.min())}
    return eta, info


def doerfler(eta, theta=0.5):
    """The smallest set of tets carrying the fraction theta of sum eta (largest first) -> bool mask."""
    eta = np.maximum(np.asarray(eta, float), 0.0)
    o = np.argsort(-eta)
    cum = np.cumsum(eta[o])
    k = int(np.searchsorted(cum, theta * cum[-1])) + 1
    m = np.zeros(len(eta), bool)
    m[o[:k]] = True
    return m


_COMP = {"xx": (0, 0), "yy": (1, 1), "zz": (2, 2), "xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}


def omega_children(deck, box):
    """omega on a red-refined deck (ustand.refine) = the 8 children of every COARSE tet the box selects. red_refine
    appends the children of coarse tet i as fine tets 8i .. 8i+7, so the fine mask is the coarse one repeated 8 times,
    and |omega| is the coarse |omega| exactly (the children fill the parent). Found 2026-11-11: a centroid test on
    the fine tets picked 11612 tets / 581.07 mm^3 against 8 x 1458 / 589.12, so the two means were of different
    regions. -> (fine mask, |omega| exact)."""
    return children_of(deck, lambda coarse: omega_box(coarse, box))


def children_of(deck, select):
    """The fine omega of a red-refined deck = the 8 children of each coarse tet that select(coarse deck) -> (mask,
    |omega|) chooses; |omega| is the coarse one exactly. Used for the 3b box and the 3c SCL slab alike."""
    rf = deck.get("refined_from") or {}
    if "deck" not in rf:
        raise ValueError("--omega-children needs a deck made by ustand.refine (refined_from.deck)")
    coarse = TF.read_deck(rf["deck"])
    cmask, vol = select(coarse)
    par = deck.get("parent")
    if par is not None:
        # every fine tet carries its ROOT coarse tet (uniform red: 8i..8i+7; graded red-green: any number, >= 1)
        if len(par) != len(deck["tets"]) or max(par) >= len(coarse["tets"]):
            raise ValueError("the refined deck's parent map does not fit its coarse deck")
        return np.asarray(cmask, bool)[np.asarray(par)], vol
    if 8 * len(coarse["tets"]) != len(deck["tets"]):
        raise ValueError("the refined deck does not have 8 children per coarse tet")
    return np.repeat(cmask, 8), vol


def omega_box(deck, box):
    """omega = the deck's tets whose CENTROID lies strictly inside the box (x0, y0, z0, x1, y1, z1); exact decimals.
    -> (mask over the deck's tets, |omega| exact)."""
    from fractions import Fraction as Fr
    g = deck["grids"]
    lo, hi = [Fr(str(x)) for x in box[:3]], [Fr(str(x)) for x in box[3:]]
    mask, vol = [], Fr(0)
    for t in deck["tets"]:
        P = [[TF._nas(x) for x in g[n]] for n in t]
        c = [sum(p[k] for p in P) / 4 for k in range(3)]
        inside = all(lo[k] < c[k] < hi[k] for k in range(3))
        mask.append(inside)
        if inside:
            vol += EQ.tet_volume(P)
    return np.array(mask, bool), vol


def mean_stress_extractor(comp, E, nu, vol):
    """sig_e with int_omega eps(u) : sig_e = (1 / |omega|) int_omega sigma(u)_comp: sig_e = C : Pi / |omega|,
    Pi the unit tensor of the component (sym for a shear), C = 2 mu I + lam 1 (x) 1. Exact (Fractions)."""
    i, j = _COMP[comp]
    Pi = [[0] * 3 for _ in range(3)]
    if i == j:
        Pi[i][i] = 1
    else:
        Pi[i][j] = Pi[j][i] = type(E)(1, 2)
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    tr = Pi[0][0] + Pi[1][1] + Pi[2][2]
    return [[(2 * mu * Pi[a][b] + (lam * tr if a == b else 0)) / vol for b in range(3)] for a in range(3)]


# ------------------------------------------------------------------------------------------------ level 3c: SCL
# Membrane and bending on a stress classification line (ASME VIII-2 5-A style), certified over a thin SLAB omega, not a
# line: omega = the tets whose centroid lies within the wall (|x.n - c| < t_w / 2) and within R of the line p + s n.
# sigma_m = (1 / |omega|) int_omega sigma_tt,   sigma_b = 6 / (t_w |omega|) int_omega sigma_tt (x.n - c)
# (= the line formulas (1/t) int sigma dz and (6/t^2) int sigma z dz averaged over the patch, A_perp := |omega| / t_w).
# n is an EXACTLY unit rational vector; Pi = t' t'^T / |t'|^2 with t' = u - (u.n) n, exactly perpendicular to n.
def rational_unit(v, den=10 ** 6):
    """an exactly unit rational vector near the float direction v (inverse stereographic map of a rational point)"""
    from fractions import Fraction as Fr
    v = np.asarray(v, float)
    v = v / np.linalg.norm(v)
    flip = v[2] < 0
    w = -v if flip else v
    a, b = Fr(round(w[0] / (1 + w[2]) * den), den), Fr(round(w[1] / (1 + w[2]) * den), den)
    q = 1 + a * a + b * b
    n = [2 * a / q, 2 * b / q, (1 - a * a - b * b) / q]
    assert sum(x * x for x in n) == 1
    return [-x for x in n] if flip else n


def tangent_projector(u, n, den=10 ** 6):
    """Pi = t' t'^T / |t'|^2, t' = u - (u.n) n with u the float direction rounded to den: exact, t' . n = 0 exactly"""
    from fractions import Fraction as Fr
    uq = [Fr(round(float(x) * den), den) for x in u]
    un = sum(uq[i] * n[i] for i in range(3))
    tp = [uq[i] - un * n[i] for i in range(3)]
    nn = sum(x * x for x in tp)
    return [[tp[i] * tp[j] / nn for j in range(3)] for i in range(3)], tp


def wall_chord(deck, p, ndir=4000):
    """FLOAT (choosing only): the shortest chord through p to the mesh boundary over ndir directions of a hemisphere
    -> (unit direction, length, the two hit points)."""
    ids = sorted(deck["grids"])
    idx = {n: i for i, n in enumerate(ids)}
    X = np.array([[float(TF._nas(c)) for c in deck["grids"][n]] for n in ids])
    T = np.array([[idx[n] for n in t] for t in deck["tets"]])
    F, own, lf, tf = TM.faces(T)
    bnd = F[own[:, 1] < 0]
    A, B, C = X[bnd[:, 0]], X[bnd[:, 1]], X[bnd[:, 2]]
    e1, e2 = B - A, C - A
    p = np.asarray(p, float)
    k = np.arange(ndir) + 0.5
    zc = k / ndir                                   # hemisphere z in (0, 1], Fibonacci spiral
    ph = np.pi * (1 + 5 ** 0.5) * k
    D = np.stack([np.sqrt(1 - zc * zc) * np.cos(ph), np.sqrt(1 - zc * zc) * np.sin(ph), zc], 1)
    best = (np.inf, None, None, None)
    s = p - A
    q = np.cross(s, e1)
    for d in D:
        hits = []
        for sg in (1.0, -1.0):
            dd = sg * d
            h = np.cross(dd, e2)
            a = (e1 * h).sum(1)
            ok = np.abs(a) > 1e-14
            f = np.where(ok, 1.0 / np.where(ok, a, 1.0), 0.0)
            uu = f * (s * h).sum(1)
            vv = f * (q @ dd)
            tt = f * (e2 * q).sum(1)
            m = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (tt > 1e-9)
            hits.append(tt[m].min() if m.any() else np.inf)
        L = hits[0] + hits[1]
        if L < best[0]:
            best = (L, d, p + hits[0] * d, p - hits[1] * d)
    return best[1], best[0], best[2], best[3]


def omega_slab(deck, p, n, c, tw, R):
    """omega = tets with the centroid at |x.n - c| < tw / 2 and within R of the line p + s n (float test: omega is a
    DEFINITION, the chosen set); -> (mask, |omega| EXACT)."""
    from fractions import Fraction as Fr
    g = deck["grids"]
    nf = np.array([float(x) for x in n])
    pf = np.asarray([float(x) for x in p], float)
    mask, vol = [], Fr(0)
    for t in deck["tets"]:
        Pq = [[TF._nas(x) for x in g[q]] for q in t]
        cf = np.array([float(sum(P_[k] for P_ in Pq) / 4) for k in range(3)])
        dn = float(cf @ nf) - float(c)
        lat = (cf - pf) - ((cf - pf) @ nf) * nf
        inside = abs(dn) < float(tw) / 2 and float(np.linalg.norm(lat)) < float(R)
        mask.append(inside)
        if inside:
            vol += EQ.tet_volume(Pq)
    return np.array(mask, bool), vol


def scl_extractor(kind, Pi, n, c, tw, vol, E, nu):
    """(S0, S1) of the linear extractor (exact): membrane sigma_e = C:Pi / |omega|; bending
    sigma_e(x) = 6 / (tw |omega|) C:Pi (x.n - c)."""
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    tr = Pi[0][0] + Pi[1][1] + Pi[2][2]
    CP = [[2 * mu * Pi[a][b] + (lam * tr if a == b else 0) for b in range(3)] for a in range(3)]
    z3 = [[[0 * CP[0][0]] * 3 for _ in range(3)] for _ in range(3)]
    if kind == "membrane":
        return [[x / vol for x in r] for r in CP], z3
    if kind == "bending":
        kap = 6 / (tw * vol)
        S0 = [[-c * kap * x for x in r] for r in CP]
        S1 = [[[kap * CP[i][j] * n[k] for k in range(3)] for j in range(3)] for i in range(3)]
        return S0, S1
    raise ValueError(kind)


def subcase_load(deck, n):
    """the RBE3 resultant (F, M) of a deck subcase, as tetfea reads it"""
    lid = int(deck["subcases"][n]["LOAD"])
    F, M = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    if lid in deck["force"]:
        _, sc, v = deck["force"][lid]
        F = tuple(float(sc * x) for x in v)
    if lid in deck["moment"]:
        _, sc, v = deck["moment"][lid]
        M = tuple(float(sc * x) for x in v)
    return F, M


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="ustand.cadbracket")
    ap.add_argument("deck")
    ap.add_argument("--subcase", type=int, default=1)
    ap.add_argument("--load", help="an explicit RBE3 resultant 'Fx,Fy,Fz,Mx,My,Mz' on the deck's RBE3 instead of a "
                    "subcase (level 3a: combinations f +- s g for polarization)")
    ap.add_argument("--d-max", type=float)
    ap.add_argument("--d-min", type=float)
    ap.add_argument("--E-range")
    ap.add_argument("--E-ground", default="credit")
    ap.add_argument("--matfree", choices=("auto", "yes", "no"), default="auto",
                    help="the trace system: never assembled (yes), assembled + AMG (no), by size (auto: > 1e5 tets)")
    ap.add_argument("--smoother", choices=("jacobi", "schwarz"), default="jacobi",
                    help="matrix-free CG local smoother: 9x9 face-block Jacobi (default) or tet-patch additive Schwarz "
                         "(MEASURED -20 %% CG time on a graded 131k deck, no gain on the coarse 631; never touches the bound)")
    ap.add_argument("--zdtype", choices=("auto", "32", "64"), default="auto",
                    help="the local inverse blocks Z: float64 (auto) or float32 — float32 stays VALID but loose: MEASURED "
                         "2026-11-10, its choice drifts and the exact push inflates the bound (631: 45677 -> 61518; "
                         "40: 31382 -> 44812)")
    ap.add_argument("--dump-g", help="save the float choice g (nt x 36) to this .npy (to profile the finish alone)")
    ap.add_argument("--dump-eta", help="save the per-tet hypercircle indicator eta^2 (nt) to this .npy (only to CHOOSE a mesh; the bounds are unchanged)")
    ap.add_argument("--omega-box", help="level 3b: the region omega = tets with the centroid inside "
                    "'x0,y0,z0,x1,y1,z1'; with --mean-stress adds the prestress load s * l_p to the traction")
    ap.add_argument("--omega-children", action="store_true", help="level 3b/3c on a REFINED deck: omega (box or SCL slab) = the children "
                    "of the COARSE deck's box selection (the same region, the same exact volume), not a new centroid "
                    "test on the fine tets")
    ap.add_argument("--mean-stress", choices=sorted(_COMP), action="append", help="level 3b: l_p(u) = the mean of "
                    "this stress component over omega (repeatable with --functionals)")
    ap.add_argument("--prestress-scale", default="1", help="level 3b: s (exact decimal, signed) in f + s l_p; "
                    "polarization needs the runs with +s and -s")
    ap.add_argument("--scl", help="level 3c: a JSON spec {point, n: [3 exact strings, exactly unit], u: [3 floats, the "
                    "tangent direction], c, tw, R} (from the SCL pilot); with --scl-kind adds s * l_p, l_p = sigma_m "
                    "or sigma_b of sigma_tt on the slab")
    ap.add_argument("--scl-kind", choices=("membrane", "bending"), action="append",
                    help="repeatable with --functionals: --scl-kind membrane --scl-kind bending")
    ap.add_argument("--functionals", action="store_true", help="level 3d: ONE solve for the load and ONE per "
                    "functional (every --mean-stress on --omega-box and every --scl-kind on --scl), the fields combined; "
                    "s chosen after the solves (s* = sqrt(w_f / w_p)); --prestress-scale is not used")
    ap.add_argument("--s", help="level 3d: explicit s values to evaluate in addition to s*: 'a,b,..' one per "
                    "functional (in the order mean stresses, then SCL kinds), or one value for all")
    a = ap.parse_args(argv)
    if a.functionals:
        return _main_functionals(a, ap)
    for nm in ("mean_stress", "scl_kind"):
        vals = getattr(a, nm)
        if vals and len(vals) > 1:
            ap.error(f"several --{nm.replace('_', '-')} need --functionals (level 3d)")
        setattr(a, nm, vals[0] if vals else None)
    mf = {"auto": None, "yes": True, "no": False}[a.matfree]
    zd = {"auto": None, "32": np.float32, "64": np.float64}[a.zdtype]
    sub = a.subcase
    if a.load:
        v = [float(x) for x in a.load.split(",")]
        sub = {"F": v[:3], "M": v[3:6], "label": f"load {a.load}"}
    if a.omega_box or a.mean_stress:
        from fractions import Fraction as Fr
        if not (a.omega_box and a.mean_stress):
            ap.error("--omega-box and --mean-stress go together")
        dk = TF.read_deck(a.deck)
        if not isinstance(sub, dict):
            Fd, Md = subcase_load(dk, sub)
            sub = {"F": Fd, "M": Md, "label": f"subcase {sub}"}
        box = [float(x) for x in a.omega_box.split(",")]
        if a.omega_children:
            mask, vol = omega_children(dk, box)
        else:
            mask, vol = omega_box(dk, box)
        if not mask.any():
            ap.error("omega is empty")
        s = Fr(a.prestress_scale)
        sig = mean_stress_extractor(a.mean_stress, dk["mat"][0], dk["mat"][1], vol)
        sub["prestress"] = {"omega": mask, "sigma": [[s * x for x in row] for row in sig]}
        sub["label"] += f" + {a.prestress_scale} * mean {a.mean_stress} over {int(mask.sum())} tets"
    if a.scl or a.scl_kind:
        from fractions import Fraction as Fr
        if not (a.scl and a.scl_kind):
            ap.error("--scl and --scl-kind go together")
        spec = json.load(open(a.scl))
        dk = TF.read_deck(a.deck)
        if not isinstance(sub, dict):
            Fd, Md = subcase_load(dk, sub)
            sub = {"F": Fd, "M": Md, "label": f"subcase {sub}"}
        n = [Fr(x) for x in spec["n"]]
        if sum(x * x for x in n) != 1:
            ap.error("--scl: n must be EXACTLY unit (use rational_unit)")
        Pi, tp = tangent_projector(spec["u"], n)
        c, tw = Fr(spec["c"]), Fr(spec["tw"])
        if a.omega_children:
            mask, vol = children_of(dk, lambda coarse: omega_slab(coarse, spec["point"], n, c, tw, Fr(spec["R"])))
        else:
            mask, vol = omega_slab(dk, spec["point"], n, c, tw, Fr(spec["R"]))
        if not mask.any():
            ap.error("omega is empty")
        S0, S1 = scl_extractor(a.scl_kind, Pi, n, c, tw, vol, dk["mat"][0], dk["mat"][1])
        s = Fr(a.prestress_scale)
        sub["prestress"] = {"omega": mask, "S0": [[s * x for x in r] for r in S0],
                            "S1": [[[s * x for x in cc] for cc in r] for r in S1], "label": a.scl_kind}
        sub["label"] += (f" + {a.prestress_scale} * sigma_{a.scl_kind[0]} of sigma_tt on the SCL slab "
                         f"({int(mask.sum())} tets, |omega| {float(vol):.6f})")
    r = bracket(a.deck, sub, log=lambda s: print(s, file=sys.stderr, flush=True), matfree=mf, zdtype=zd, dump_g=a.dump_g, dump_eta=a.dump_eta,
                smoother=a.smoother)
    if (a.d_max is not None or a.d_min is not None) and r["work_conjugate"]:
        from . import cadstiff as CS
        Er = tuple(float(x) for x in a.E_range.split(":")) if a.E_range else (r["E"], r["E"])
        v = CS.judge(r["work_conjugate"][0], r["work_conjugate"][1], r["E"], Er, a.E_ground, a.d_max, a.d_min,
                     rests_on=r["rests_on"])
        r["requirement"] = {k: v[k] for k in ("d_bracket_over_E", "verdicts")}
    print(json.dumps(r, indent=1, default=str))



def _main_functionals(a, ap):
    """the CLI of level 3d: build the UNSCALED functionals from the 3b / 3c flags and call bracket_functionals"""
    from fractions import Fraction as Fr
    if a.prestress_scale != "1":
        ap.error("--functionals chooses s itself; give explicit values with --s, not --prestress-scale")
    if a.dump_g or a.dump_eta or a.d_max is not None or a.d_min is not None:
        ap.error("--dump-g / --dump-eta / --d-max / --d-min stay on the two-run path (no --functionals)")
    mf = {"auto": None, "yes": True, "no": False}[a.matfree]
    zd = {"auto": None, "32": np.float32, "64": np.float64}[a.zdtype]
    dk = TF.read_deck(a.deck)
    sub = a.subcase
    if a.load:
        v = [float(x) for x in a.load.split(",")]
        sub = {"F": v[:3], "M": v[3:6], "label": f"load {a.load}"}
    funs = []
    if a.omega_box or a.mean_stress:
        if not (a.omega_box and a.mean_stress):
            ap.error("--omega-box and --mean-stress go together")
        box = [float(x) for x in a.omega_box.split(",")]
        mask, vol = omega_children(dk, box) if a.omega_children else omega_box(dk, box)
        if not mask.any():
            ap.error("omega is empty")
        for comp in a.mean_stress:
            funs.append({"label": f"mean {comp} over {int(mask.sum())} tets", "omega": mask,
                         "sigma": mean_stress_extractor(comp, dk["mat"][0], dk["mat"][1], vol)})
    if a.scl or a.scl_kind:
        if not (a.scl and a.scl_kind):
            ap.error("--scl and --scl-kind go together")
        spec = json.load(open(a.scl))
        n = [Fr(x) for x in spec["n"]]
        if sum(x * x for x in n) != 1:
            ap.error("--scl: n must be EXACTLY unit (use rational_unit)")
        Pi, tp = tangent_projector(spec["u"], n)
        c, tw = Fr(spec["c"]), Fr(spec["tw"])
        if a.omega_children:
            mask, vol = children_of(dk, lambda coarse: omega_slab(coarse, spec["point"], n, c, tw, Fr(spec["R"])))
        else:
            mask, vol = omega_slab(dk, spec["point"], n, c, tw, Fr(spec["R"]))
        if not mask.any():
            ap.error("omega is empty")
        for kind in a.scl_kind:
            S0, S1 = scl_extractor(kind, Pi, n, c, tw, vol, dk["mat"][0], dk["mat"][1])
            funs.append({"label": kind, "omega": mask, "S0": S0, "S1": S1,
                         "describe": f"sigma_{kind[0]} of sigma_tt on the SCL slab ({int(mask.sum())} tets, "
                                     f"|omega| {float(vol):.6f})"})
    if not funs:
        ap.error("--functionals needs --omega-box/--mean-stress and/or --scl/--scl-kind")
    sv = None
    if a.s:
        vals = [float(x) for x in a.s.split(",")]
        if len(vals) == 1:
            vals = vals * len(funs)
        if len(vals) != len(funs):
            ap.error(f"--s: {len(vals)} values for {len(funs)} functionals")
        sv = [[x] for x in vals]
    del dk
    r = bracket_functionals(a.deck, sub, funs, s_values=sv, log=lambda s: print(s, file=sys.stderr, flush=True),
                            matfree=mf, zdtype=zd, smoother=a.smoother)
    for fo, fn in zip(r["functionals"], funs):
        if "describe" in fn:
            fo["describe"] = fn["describe"]
    print(json.dumps(r, indent=1, default=str))

if __name__ == "__main__":
    main(sys.argv[1:])


def _grow(mask, owner, layers):
    """the tets within `layers` face-steps of the masked ones"""
    o0, o1 = owner[:, 0], owner[:, 1]
    inner = o1 >= 0
    m = mask.copy()
    for _ in range(layers):
        a, b = o0[inner], o1[inner]
        add = np.zeros_like(m)
        add[b[m[a]]] = True
        add[a[m[b]]] = True
        m |= add
    return m


def _overlap_fluxes(X, T, F, own, lf, kind, sid, qf_rough, q_load, E, nu, layers, log):
    """Interface fluxes from OVERLAPPING solves: each subdomain grown by `layers` face-steps, the rough (P1) fluxes on
    the grown domain's cut, its float imbalance removed by a least-norm change on that cut, the hybridized choice on
    it; an interface face's flux = the average of the two adjacent tets' data, over the (two) grown solves that
    contain it as an interior face."""
    from . import dd as DD
    nS = int(sid.max()) + 1
    acc = np.zeros((len(F), 3, 3))
    cnt = np.zeros(len(F))
    s0 = sid[own[:, 0]]
    s1 = np.where(own[:, 1] >= 0, sid[np.maximum(own[:, 1], 0)], -1)
    ifm = (own[:, 1] >= 0) & (s0 != s1)
    gkey = {tuple(int(v) for v in F[f]): f for f in range(len(F))}
    Xq_f = [tuple(float(c) for c in p) for p in X]
    for s in range(nS):
        m = _grow(sid == s, own, layers)
        Ts = T[m]
        tet_ids = np.where(m)[0]
        Fs, ows, lfs, tfs = TM.faces(Ts)
        gf = np.array([gkey[tuple(int(v) for v in Fs[f])] for f in range(len(Fs))])
        same = tet_ids[ows[:, 0]] == own[gf, 0]
        kind_s = kind[gf].copy()
        cut = (ows[:, 1] < 0) & (own[gf, 1] >= 0)                # boundary of the grown domain inside the part
        kind_s[cut] = 3
        qpres = np.zeros((len(Fs), 3, 3))
        sg = np.where(same, 1.0, -1.0)[:, None, None]
        qpres[cut] = (qf_rough[gf] * sg)[cut]
        for f in np.where(kind_s == 2)[0]:
            qpres[f] = q_load[gf[f]] * sg[f]
        # a grown domain with no support: remove its float imbalance on the cut (least norm)
        if not (kind_s == 1).any():
            rows, r = [], np.zeros(6)
            for f in np.where((kind_s == 3) | (kind_s == 2))[0]:
                A = np.array([[float(x) for x in row] for row in DD.face_map(Xq_f, Fs[f])])
                r += A @ qpres[f].ravel()
                if cut[f]:
                    rows.append((f, A))
            G = sum(A @ A.T for _, A in rows)
            y = np.linalg.solve(G, -r)
            for f, A in rows:
                qpres[f] += (A.T @ y).reshape(3, 3)
        g, e_f, info = EQ.choose(X, Ts, Fs, ows, tfs, kind_s, E, nu, qpres, tol=1e-8)
        qloc, _, _ = EQ.face_flux_float(Ts, Fs, ows, tfs, g)
        inner_if = (ows[:, 1] >= 0) & ifm[gf]
        acc[gf[inner_if]] += (qloc * sg)[inner_if]
        cnt[gf[inner_if]] += 1
        log(f"  overlap solve {s}: {len(Ts)} tets ({int(m.sum() - (sid == s).sum())} in the layer), float {e_f:.3f}")
    out = qf_rough.copy()
    have = cnt > 0
    out[have] = acc[have] / cnt[have][:, None, None]
    return out, int((ifm & ~have).sum())


def upper_dd(path, subcase=1, size=12000, log=print, cg_tol=1e-8, merge=200, overlap=0):
    """The 2b UPPER bound by DOMAIN DECOMPOSITION (for parts too large for one hybridized system): interface fluxes
    from the P1 stress, the EXACT coarse balance (dd.coarse_balance), then per subdomain the hybridized choice with
    its interface faces prescribed, the exact push, the rigorous energy; the sum is the bound."""
    from fractions import Fraction as Fr
    from . import dd as DD
    t0 = time.time()
    d = TF.read_deck(path)
    ids = sorted(d["grids"])
    idx = {n: i for i, n in enumerate(ids)}
    Xq = [tuple(TF._nas(x) for x in d["grids"][n]) for n in ids]
    X = np.array([[float(c) for c in p] for p in Xq])
    T = np.array([[idx[n] for n in t] for t in d["tets"]])
    F, own, lf, tf = TM.faces(T)
    fixed = {idx[n] for ind, deps in d["rbe2"] for n in deps if d["spc"].get(ind, "").startswith("123")}
    ref, _, rn = d["rbe3"][0]
    kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
    E, nu = d["mat"][0], d["mat"][1]
    lo = TF.solve_cases(d, [subcase], tol=1e-6, log=lambda s: None, return_u=True)[0]
    sig = TM.p1_stress(X, T, lo["u"], float(E), float(nu))
    sid = TM.connected_subdomains(TM.partition(X[T].mean(axis=1), size), own)
    if merge:
        sid = TM.connected_subdomains(TM.merge_small(sid, own, merge), own)
    s0 = sid[own[:, 0]]
    s1 = np.where(own[:, 1] >= 0, sid[np.maximum(own[:, 1], 0)], -1)
    ifm = (own[:, 1] >= 0) & (s0 != s1)
    qf = TM.interface_flux(X, T, F, own, lf, sig, (own[:, 1] >= 0) | ifm)     # rough fluxes on every inner face
    xyz = {n: list(X[idx[n]]) for n in rn + [ref]}
    fl = TF.rbe3_loads(xyz, ref, rn, tuple(lo["F"]), tuple(lo["M"]))
    tr, res, lost = TM.rbe3_traction(X, F, kind, {idx[n]: fl[i] for i, n in enumerate(rn)})
    A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    n2 = np.linalg.norm(np.cross(B - A, C - A), axis=1)
    if overlap:
        q_load = np.zeros((len(F), 3, 3))
        for f in np.where(kind == 2)[0]:
            q_load[f] = [tr[int(F[f, p_])] * n2[f] for p_ in range(3)]
        qf, missing = _overlap_fluxes(X, T, F, own, lf, kind, sid, qf, q_load, float(E), float(nu), overlap, log)
        log(f"overlap fluxes: {missing} interface faces without an overlap estimate; {time.time() - t0:.0f} s")
    q = {int(f): [[Fr(float(qf[f, p_, c])) for c in range(3)] for p_ in range(3)] for f in np.where(ifm)[0]}
    for f in np.where(kind == 2)[0]:
        q[int(f)] = [[Fr(float(tr[int(F[f, p_])][c] * n2[f])) for c in range(3)] for p_ in range(3)]
    for f in np.where(kind == 3)[0]:
        q[int(f)] = [[Fr(0)] * 3 for _ in range(3)]
    q, rep = DD.coarse_balance(Xq, F, own, kind, sid, q)
    if rep["floating_unbalanced_after"] or rep["unreached"]:
        raise RuntimeError(f"coarse balance failed: {rep}")
    log(f"coarse balance: {rep}; {time.time() - t0:.0f} s")
    gkey = {tuple(int(v) for v in F[f]): f for f in range(len(F))}
    total = 0.0
    worst_bits = 0
    for s in range(int(sid.max()) + 1):
        Ts = T[sid == s]
        Fs, ows, lfs, tfs = TM.faces(Ts)
        gf = np.array([gkey[tuple(int(v) for v in Fs[f])] for f in range(len(Fs))])
        # local owner 0 vs global owner 0: the same tet? (a sign for the oriented flux)
        tet_ids = np.where(sid == s)[0]
        same = tet_ids[ows[:, 0]] == own[gf, 0]
        kind_s = kind[gf].copy()
        iface_s = ifm[gf]
        kind_s[iface_s] = 3                                   # a prescribed boundary face of the subdomain
        qpres = np.zeros((len(Fs), 3, 3))
        qexact = {}
        for f in np.where(kind_s != 0)[0]:
            G = int(gf[f])
            if kind_s[f] == 1:
                continue
            sg = 1 if same[f] else -1
            qexact[int(f)] = [[sg * x for x in row] for row in q[G]]
            qpres[f] = [[float(x) for x in row] for row in qexact[int(f)]]
        g, e_f, info = EQ.choose(X, Ts, Fs, ows, tfs, kind_s, float(E), float(nu), qpres, tol=cg_tol)
        qd, bad, _, bits = EQ.finish(Xq, Ts, Fs, ows, tfs, kind_s, g, qexact, fixed_faces=set(qexact))
        if bad:
            raise RuntimeError(f"subdomain {s}: {bad} tets unbalanced after the push")
        worst_bits = max(worst_bits, bits)
        pos, sgn = EQ.slot_maps(Ts, Fs, ows, tfs)
        Ps, gs = [], []
        for t in range(len(Ts)):
            out = []
            for f in range(4):
                qq = qd[int(tfs[t, f])]
                s_ = int(sgn[t, f])
                for jv in range(3):
                    r = qq[int(pos[t, f, jv])]
                    out += [r[0] * s_, r[1] * s_, r[2] * s_]
            Ps.append([list(Xq[v]) for v in Ts[t]])
            gs.append(out)
        up_s = AL.energy_upper_ev(Ps, gs, E, nu)
        total = math.nextafter(total + up_s, math.inf)
        log(f"subdomain {s}: {len(Ts)} tets, float {e_f:.4f}, proved {up_s:.4f}, bits {bits}; {time.time() - t0:.0f} s")
    return {"upper_dd": total, "lower": lo["compliance_lower_proved"], "subdomains": int(sid.max()) + 1,
            "coarse": rep, "bits": worst_bits, "seconds": round(time.time() - t0, 1)}
