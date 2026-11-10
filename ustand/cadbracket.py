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


def bracket(path, subcase=1, log=print, cg_tol=1e-8, matfree=None, zdtype=None, dump_g=None):
    from fractions import Fraction as Fr
    t0 = time.time()
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    d = TF.read_deck(path)
    lo = TF.solve_cases(d, [subcase], tol=1e-4, log=lambda s: None)[0]
    log(f"lower (2a): C >= {lo['compliance_lower_proved']:.6f}; {time.time() - t0:.0f} s")
    _trim()
    ids = sorted(d["grids"])
    idx = {n: i for i, n in enumerate(ids)}
    Xq = [tuple(TF._nas(x) for x in d["grids"][n]) for n in ids]
    X = np.array([[float(c) for c in p] for p in Xq])
    T = np.array([[idx[n] for n in t] for t in d["tets"]])
    F, own, lf, tf = TM.faces(T)
    fixed = {idx[n] for ind, deps in d["rbe2"] for n in deps if d["spc"].get(ind, "").startswith("123")}
    ref, _, rn = d["rbe3"][0]
    kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
    Fv, Mv = tuple(lo["F"]), tuple(lo["M"])
    xyz = {n: list(X[idx[n]]) for n in rn + [ref]}
    fl = TF.rbe3_loads(xyz, ref, rn, Fv, Mv)
    tr, res, lost = TM.rbe3_traction(X, F, kind, {idx[n]: fl[i] for i, n in enumerate(rn)})
    if lost:
        raise ValueError(f"{len(lost)} RBE3 nodal forces on nodes of no loaded face: the load is not a traction here")
    A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    n2 = np.linalg.norm(np.cross(B - A, C - A), axis=1)
    q = np.zeros((len(F), 3, 3))
    for fid in np.where(kind == 2)[0]:
        for p_ in range(3):
            q[fid, p_] = tr[int(F[fid, p_])] * n2[fid]
    E, nu = d["mat"][0], d["mat"][1]
    g, e_float, info = EQ.choose(X, T, F, own, tf, kind, float(E), float(nu), q, direct=False, tol=cg_tol,
                                 log=lambda m: log(m), zdtype=np.float64 if zdtype is None else zdtype,
                                 matfree=(len(T) > 100000) if matfree is None else matfree)
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
    up = AL.energy_upper_ev(Ps, gs, E, nu)
    Fn, Mn = math.sqrt(sum(x * x for x in Fv)), math.sqrt(sum(x * x for x in Mv))
    c_lo, c_hi = lo["compliance_lower_proved"], up
    w = Fn if Fn and not Mn else (Mn if Mn and not Fn else None)
    U_ = 2.0 ** -53
    return {"deck": path, "sha256": sha, "subcase": subcase, "label": lo["label"], "F": Fv, "M": Mv,
            "tets": int(len(T)), "E": float(E), "nu": float(nu),
            "compliance": [c_lo, c_hi], "gap": c_hi / c_lo - 1,
            "work_conjugate": ([c_lo / w * (1 - 2 * U_), c_hi / w * (1 + 2 * U_)] if w else None),
            "work_conjugate_is": ("displacement along F (mm)" if Fn and not Mn else "rotation about M (rad)"
                                  if Mn and not Fn else None),
            "upper_float_choice": e_float, "push_bits": bits, "seconds": round(time.time() - t0, 1),
            "rests_on": [f"the deck {path} (sha256 {sha[:16]}…): its tets ARE the part — EARNED IF STABLE on it",
                         "linear isotropic elasticity", "supports: RBE2 spiders to SPC'd nodes (u = 0)",
                         "the load: the traction whose consistent nodal loads are the RBE3 distribution"]}


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
    ap.add_argument("--zdtype", choices=("auto", "32", "64"), default="auto",
                    help="the local inverse blocks Z: float64 (auto) or float32 — float32 stays VALID but loose: MEASURED "
                         "2026-11-10, its choice drifts and the exact push inflates the bound (631: 45677 -> 61518; "
                         "40: 31382 -> 44812)")
    ap.add_argument("--dump-g", help="save the float choice g (nt x 36) to this .npy (to profile the finish alone)")
    a = ap.parse_args(argv)
    mf = {"auto": None, "yes": True, "no": False}[a.matfree]
    zd = {"auto": None, "32": np.float32, "64": np.float64}[a.zdtype]
    sub = a.subcase
    if a.load:
        v = [float(x) for x in a.load.split(",")]
        sub = {"F": v[:3], "M": v[3:6], "label": f"load {a.load}"}
    r = bracket(a.deck, sub, log=lambda s: print(s, file=sys.stderr, flush=True), matfree=mf, zdtype=zd, dump_g=a.dump_g)
    if (a.d_max is not None or a.d_min is not None) and r["work_conjugate"]:
        from . import cadstiff as CS
        Er = tuple(float(x) for x in a.E_range.split(":")) if a.E_range else (r["E"], r["E"])
        v = CS.judge(r["work_conjugate"][0], r["work_conjugate"][1], r["E"], Er, a.E_ground, a.d_max, a.d_min,
                     rests_on=r["rests_on"])
        r["requirement"] = {k: v[k] for k in ("d_bracket_over_E", "verdicts")}
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
