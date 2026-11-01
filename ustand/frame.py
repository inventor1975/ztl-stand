"""A PLANE FRAME (an ANSYS input deck, BEAM3 elements) judged by ZTL zenergy (2026-11-01, the curator's plan: frames
after trusses, ZTL first).

A 2D Euler-Bernoulli beam element, nodes i, j, length L, direction (c, s), modulus E, area A, second moment I. Its
strain energy, in the element's own axes (axial u, transverse v, rotation th), is EXACTLY
    U = (E A / 2L)(u_j - u_i)^2 + (E I / 2L) [ (th_i - th_j)^2 + 3 (th_i + th_j - 2 (v_j - v_i)/L)^2 ]
(expand: 4 th_i^2 + 4 th_j^2 + 4 th_i th_j - 12 psi (th_i + th_j) + 12 psi^2, psi = (v_j - v_i)/L — the textbook
matrix (E I / L^3)[12 6L -12 6L; ...]). So the element stiffness is THREE rank-one terms that share ONE factor, E:
    (E A / L) a a^T,   (E I / L) b b^T,   (3 E I / L) c c^T
with a, b, c rational rows over the element's global displacements (u = c ux + s uy, v = -s ux + c uy). An element
with its modulus anywhere in E (1 +- t) is a part of three terms — the case lean/ZEnergy.lean's
`target_first_grouped` is for (ZTL), on top of ZNet's step 4.

    python3 -m ustand.frame deck.txt --tol 0.5% --req "U(12,Y) >= -0.0251"     a requirement
    python3 -m ustand.frame deck.txt --tol 0.5% --range "U(12,Y)"               the proved enclosure (not exact)
            U(node,X|Y) a displacement, ROT(node) a rotation
    python3 -m ustand.frame deck.txt --tol 0.5% --req "SIG(3) <= 235e6"         member stress, EN 1993-1-1 6.2.1(7):
            |sigma| at both extreme fibres of both ends of element 3 (needs the section height in R), on EN's global
            analysis: sway imperfection +-1/200 and second order by the proved alpha_cr (--first-order: without)
    python3 -m ustand.frame deck.txt --tol 0.5% --stability                     the critical load factor: a proved
            lower bound for every modulus in the box, a proved upper bound at the nominal moduli (a witness mode)
    python3 -m ustand.frame deck.txt --tol 0.5% --buckling 355e6 b [1.0]        EN 1993-1-1 6.3.1 for every compressed
            member, fy, curve a0|a|b|c|d, gamma_M1; N_cr,i = alpha_cr |N_Ed,i|; EARNED / REFUTED (nominal) / OPEN
    --jobs N   outputs spread over N processes (stresses, stability, buckling)

THE DECK (the subset read; anything else is REFUSED aloud):
    N, id, x, y                  a node
    E, i, j                      an element between nodes i and j (one material, one real constant)
    MP, EX, 1, value             Young's modulus (nominal)
    R, 1, area, izz[, height]    the section: area, second moment, and (for stresses) the height
    F, node, FX|FY|MZ, value     a nodal force or moment
    D, node, UX|UY|ROTZ, 0       a support (zero displacement or rotation)
    /PREP7, ET (BEAM3 / 3), MAT, REAL, TYPE, comments (!) — read and skipped.
Lengths must be rational (an irrational length is refused: the stiffness would not be exact).

WHAT IT DOES NOT DO (yet), said: the box path (zlin) is not wired for frames — a requirement the energy path cannot
decide comes back OPEN, not guessed; no shear deformation (Timoshenko); second order only by EN 5.2.2's amplification (alpha_cr >= 3;
below, OPEN — no geometrically nonlinear solve yet); gravity is taken along Y for the imperfection's equivalent
forces (5.3.2(7)); stability is LINEAR buckling (no imperfections, no plasticity); member buckling is 6.3.1 under axial
force only — the 6.3.3 bending-axial interaction, out-of-plane and lateral-torsional buckling are NOT checked.
The proved ranges are for the MODEL (the mesh): discretization error is not bounded (bench/stage0/plate_convergence).
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F

from . import bricks as B
from .spice import tolerance
from .truss import _num, _sqrt, _show


class FrameError(B.BrickError):
    pass


def read_deck(text):
    nodes, elems, loads, supports = {}, [], {}, set()
    ex = sec = None
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split("!")[0].strip()
        if not line or line.startswith("/"):
            continue
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())]
        cmd, where = f[0].upper(), f"line {ln}"
        if cmd == "N":
            nodes[int(f[1])] = (_num(f[2], where), _num(f[3], where) if len(f) > 3 and f[3] else F(0))
        elif cmd == "E":
            elems.append((int(f[1]), int(f[2])))
        elif cmd == "MP":
            if f[1].upper() != "EX":
                raise FrameError(f"{where}: MP {f[1]} — only EX is read")
            if ex is not None and _num(f[3], where) != ex:
                raise FrameError(f"{where}: a second material — one EX only (version 1)")
            ex = _num(f[3], where)
        elif cmd == "R":
            if len(f) < 4:
                raise FrameError(f"{where}: R needs the area and the second moment (R, 1, area, izz)")
            s = (_num(f[2], where), _num(f[3], where))
            if sec is not None and s != sec:
                raise FrameError(f"{where}: a second real constant — one section only (version 1)")
            sec = s
        elif cmd == "F":
            d = f[2].upper()
            if d not in ("FX", "FY", "MZ"):
                raise FrameError(f"{where}: load {f[2]} — FX, FY or MZ only")
            k = (int(f[1]), {"FX": "X", "FY": "Y", "MZ": "R"}[d])
            loads[k] = loads.get(k, F(0)) + _num(f[3], where)
        elif cmd == "D":
            d = f[2].upper()
            if d not in ("UX", "UY", "ROTZ"):
                raise FrameError(f"{where}: support {f[2]} — UX, UY or ROTZ only")
            if _num(f[3], where) != 0:
                raise FrameError(f"{where}: a prescribed nonzero displacement — not read (version 1)")
            supports.add((int(f[1]), {"UX": "X", "UY": "Y", "ROTZ": "R"}[d]))
        elif cmd == "ET":
            if f[2].upper() not in ("BEAM3", "3"):
                raise FrameError(f"{where}: element type {f[2]} — only BEAM3 (2D beam)")
        elif cmd in ("MAT", "REAL", "TYPE"):
            if len(f) > 1 and f[1] not in ("1", ""):
                raise FrameError(f"{where}: {cmd},{f[1]} — one material and one real constant only")
        else:
            raise FrameError(f"{where}: {f[0]} — not read (only N E MP R F D ET MAT REAL TYPE)")
    if not nodes or not elems:
        raise FrameError("no nodes or no elements")
    if ex is None or sec is None:
        raise FrameError("no MP,EX or no R (the modulus and the section are needed)")
    for i, j in elems:
        for n in (i, j):
            if n not in nodes:
                raise FrameError(f"element {i}-{j}: node {n} does not exist")
    return nodes, elems, loads, supports, ex, sec


def energy_system(text, tol):
    """K(p) = sum_e p_e (three rank-one terms of element e), p_e in [1 - t, 1 + t]; f the loads."""
    parts, f, dof, _, _ = energy_system_full(text, tol)
    return parts, f, dof


def read_height(text):
    """The section's HEIGHT, BEAM3's third real constant (R, 1, area, izz, height) — None if not given."""
    for raw in text.splitlines():
        line = raw.split("!")[0].strip()
        fl = [x.strip() for x in (line.split(",") if "," in line else line.split())]
        if fl and fl[0].upper() == "R" and len(fl) > 4 and fl[4]:
            return _num(fl[4], "R")
    return None


def energy_system_full(text, tol):
    """energy_system, plus per element its part index and rows (a, b, c) and length, and (E, A, I, h)."""
    nodes, elems, loads, supports, ex, (area, izz) = read_deck(text)
    t = F(0) if tol in (None, "0", 0) else tolerance(tol) if isinstance(tol, str) else F(tol)
    free = [(n, d) for n in sorted(nodes) for d in "XYR" if (n, d) not in supports]
    dof = {nd: k for k, nd in enumerate(free)}
    parts = []
    emap = {}
    for k, (i, j) in enumerate(elems, 1):
        dx, dy = nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1]
        L = _sqrt(dx * dx + dy * dy)
        if not L:
            raise FrameError(f"element {k} ({i}-{j}): its length is irrational or zero — not exact (version 1)")
        c, s = dx / L, dy / L

        def row(pairs):
            g = {}
            for (n, d), v in pairs:
                if v and (n, d) in dof:
                    g[dof[(n, d)]] = g.get(dof[(n, d)], F(0)) + v
            return g
        # u = c ux + s uy (axial), v = -s ux + c uy (transverse)
        a = row([((j, "X"), c), ((j, "Y"), s), ((i, "X"), -c), ((i, "Y"), -s)])
        b = row([((i, "R"), F(1)), ((j, "R"), F(-1))])
        cc = row([((i, "R"), F(1)), ((j, "R"), F(1)),
                  ((j, "X"), 2 * s / L), ((j, "Y"), -2 * c / L), ((i, "X"), -2 * s / L), ((i, "Y"), 2 * c / L)])
        emap[k] = {"part": len(parts), "a": a, "b": b, "c": cc, "L": L, "t": t}
        parts.append({"t": t, "terms": [(ex * area / L, a), (ex * izz / L, b), (3 * ex * izz / L, cc)]})
    f = [F(0)] * len(free)
    for (n, d), v in loads.items():
        if (n, d) in dof:
            f[dof[(n, d)]] += v
    return parts, f, dof, emap, (ex, area, izz, read_height(text))


# ----------------------------------------------------------------------------------------------------------------
# MEMBER STRESSES (2026-11-01). At an end of element k: N = (E A / L)(a.u) and the end moments
# M_i = (E I / L)((b + 3c).u), M_j = (E I / L)((-b + 3c).u) (the textbook 4th + 2th - 6psi: b = th_i - th_j,
# c = th_i + th_j - 2psi). An extreme fibre carries sigma = N/A +- M (h/2)/I = E p_k (g.u),
#   g = a/L +- (h/2)/L (+-b + 3c),
# an output scaled by the element's own factor — ZTL zenergy.certify_scaled. Both fibres at both ends are
# checked, so the sign convention of the moment does not matter. The check is EN 1993-1-1 6.2.1(7)'s elastic,
# conservative one: |sigma| <= fy / gamma_M0 at every fibre. NOT here: member buckling (6.3 needs buckling lengths
# from a stability analysis), shear, lateral-torsional buckling.

def fibre_vectors(emap, k, h):
    """The four fibre functionals of element k: (end, side, g) with sigma = E p_k (g.u)."""
    m = emap[k]
    L, a, b, c = m["L"], m["a"], m["b"], m["c"]
    out = []
    for end, sb in (("I", 1), ("J", -1)):
        for side, sg in (("TOP", 1), ("BOT", -1)):
            g = {}
            for i, v in a.items():
                g[i] = g.get(i, F(0)) + v / L
            for i, v in b.items():
                g[i] = g.get(i, F(0)) + sg * (h / 2) / L * sb * v
            for i, v in c.items():
                g[i] = g.get(i, F(0)) + sg * (h / 2) / L * 3 * v
            out.append((end, side, {i: v for i, v in g.items() if v}))
    return out


def fibre_ranges_many(text, tol, ks, ctx=None, jobs=1):
    """fibre_ranges for many elements at once: every fibre's output in ONE ZTL zenergy.certify_many call (the shared
    work once, the outputs over `jobs` processes) — results equal fibre_ranges' (2026-11-01)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof, emap, (ex, area, izz, h) = ctx or energy_system_full(text, tol)
    if h is None:
        raise FrameError("member stresses need the section height: R, 1, area, izz, height")
    n = len(dof)
    items, es = [], []
    for k in ks:
        if k not in emap:
            raise FrameError(f"SIG({k}): no element {k}")
        for end, side, g in fibre_vectors(emap, k, h):
            e = [F(0)] * n
            for i, v in g.items():
                e[i] = v
            items.append((k, end, side, e))
            if any(e):
                es.append(e)
    rs = iter(ZE.certify_many(parts, f, es, n, jobs=jobs))
    out = {k: [] for k in ks}
    for k, end, side, e in items:
        if not any(e):
            out[k].append({"end": end, "side": side, "lo": F(0), "hi": F(0), "nominal": F(0), "e": e, "sc": None})
            continue
        sc = ZE.scaled_from(next(rs), parts, emap[k]["part"])
        lo, hi = sorted([ex * sc["lo"], ex * sc["hi"]])
        out[k].append({"end": end, "side": side, "lo": lo, "hi": hi, "nominal": ex * sc["nominal"], "e": e, "sc": sc})
    return out


# ----------------------------------------------------------------------------------------------------------------
# STABILITY (2026-11-01): a PROVED lower bound on the elastic critical load factor, for every modulus in the box.
# The consistent geometric stiffness of a beam, G_e = int N_v'^T N_v' dx over Hermite cubics (local v, th):
#   (1/(30 L)) [[36, 3L, -36, 3L], [3L, 4L^2, -3L, -L^2], [-36, -3L, 36, -3L], [3L, -L^2, -3L, 4L^2]],
# is positive SEMIdefinite (a Gram matrix), and K_G = sum_e N_e G_e (N_e tension positive). If N_e(p) >= N_lo,e over
# the box (each a proved range: ZTL zenergy.certify_many on the axial outputs), then for lambda >= 0
#   K(p) + lambda K_G(N(p))  >=  (1 - T) K0 + lambda sum_e N_lo,e G_e        (Loewner: K(p) >= (1 - T) K0, G_e >= 0)
# so ONE matrix proved positive definite (ZTL zenergy.pd_ieee) proves lambda < lambda_cr at every p. Linear
# buckling (no imperfections, no plasticity); the load factor scales the given loads.

def _geo_entries(nodes_xy, i, j, L, c, s, dof):
    """G_e over global DOFs as {(row, col): value} (both triangles), the local v = -s ux + c uy."""
    G = [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L], [-36, -3 * L, 36, -3 * L],
         [3 * L, -L * L, -3 * L, 4 * L * L]]
    loc = [[((i, "X"), -s), ((i, "Y"), c)], [((i, "R"), F(1))], [((j, "X"), -s), ((j, "Y"), c)], [((j, "R"), F(1))]]
    out = {}
    for a in range(4):
        for b in range(4):
            if not G[a][b]:
                continue
            for (na, va) in loc[a]:
                for (nb, vb) in loc[b]:
                    if va and vb and na in dof and nb in dof:
                        key = (dof[na], dof[nb])
                        out[key] = out.get(key, F(0)) + F(G[a][b]) / (30 * L) * va * vb
    return out


def stability_lower(text, tol, jobs=1, rel=F(1, 1000)):
    """A proved lam_low with lam_low < lambda_cr for every modulus in the box; and the float estimate of the
    nominal lambda_cr for the reader. Bisection on lambda, every accepted step proved by pd_ieee. Why one matrix
    covers the whole box: ZTL lean/ZStability.lean `stability_lower` (zero axioms) -- with K_P, G_e PSD,
    p_P >= 1 - T and N_e >= N_lo,e, x'((1-T)K0 + lam sum N_lo G)x <= x'(K(p) + lam K_G(N(p)))x for every x."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    import numpy as np
    import scipy.sparse.linalg as sla
    nodes, elems, loads, supports, ex, (area, izz) = read_deck(text)
    parts, f, dof, emap, _ = energy_system_full(text, tol)
    n = len(dof)
    T = max((p["t"] for p in parts), default=F(0))
    # axial forces N_e = (E A / L) p_e (a.u): scaled outputs, all at once
    es, ks = [], []
    for k in emap:
        e = [F(0)] * n
        for i, v in emap[k]["a"].items():
            e[i] = v
        if any(e):
            es.append(e)
            ks.append(k)
    rs = ZE.certify_many(parts, f, es, n, jobs=jobs, scale=[emap[k]["part"] for k in ks])
    Nlo = {k: F(0) for k in emap}
    Nnom = {k: F(0) for k in emap}
    for k, sc in zip(ks, rs):
        fac = ex * area / emap[k]["L"]
        Nlo[k] = min(fac * sc["lo"], fac * sc["hi"])
        Nnom[k] = fac * sc["nominal"]
    if all(v >= 0 for v in Nlo.values()):
        # no member compressed anywhere in the box: K_G(N(p)) >= 0, so K(p) + lam K_G > 0 for every lam >= 0
        return {"lam_low": None, "why": "no compressed member: no buckling under these loads", "lam_est": None,
                "unknowns": n, "T": T, "Nlo": Nlo, "Nnom": Nnom}
    K0 = ZE.matrix(parts, n)                      # lower triangle
    Gsum, Gnom = {}, {}
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        dx, dy = nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1]
        ge = _geo_entries(nodes, i, j, L, dx / L, dy / L, dof)
        for (a, b), v in ge.items():
            if a >= b:
                Gsum[(a, b)] = Gsum.get((a, b), F(0)) + Nlo[k] * v
                Gnom[(a, b)] = Gnom.get((a, b), F(0)) + Nnom[k] * v
    # float estimate of the nominal lambda_cr: K0 v = -lam K_G v
    A = ZE._float_matrix(K0, n)
    Bm = ZE._float_matrix(Gnom, n)
    try:
        vals = sla.eigsh(-Bm, k=1, M=A, which="LA", return_eigenvectors=False, v0=np.ones(n))
        lam_est = float(1 / vals[0]) if vals[0] > 0 else None
    except Exception:
        lam_est = None
    def proved(lam):
        M = {key: (1 - T) * v for key, v in K0.items()}
        for key, v in Gsum.items():
            M[key] = M.get(key, F(0)) + lam * v
        Mf = ZE._float_matrix(M, n)
        try:
            mu = float(sla.eigsh(Mf, k=1, sigma=0, which="LM", return_eigenvectors=False, v0=np.ones(n))[0])
        except Exception:
            return False
        if mu <= 0:
            return False
        return ZE.pd_ieee(n, M, F(mu) * F(9, 10)) is not None
    if lam_est is None:
        return {"lam_low": None, "why": "no compressed member: no buckling under these loads", "lam_est": None}
    lo, hi = F(0), F(lam_est) * F(11, 10)
    start = F(lam_est) / 1000
    for _ in range(20):                           # a noisy estimate (members barely compressed): step down
        if proved(start):
            break
        hi, start = start, start / 10
    else:
        return {"lam_low": F(0), "lam_est": lam_est, "why": "not even a small factor proved"}
    lo = start
    for _ in range(40):
        mid = (lo + hi) / 2
        if proved(mid):
            lo = mid
        else:
            hi = mid
        if hi - lo <= rel * hi:
            break
    return {"lam_low": lo, "lam_est": lam_est, "unknowns": n, "T": T, "Nlo": Nlo, "Nnom": Nnom}


def stability_upper(text, tol="0"):
    """A proved UPPER bound on the critical load factor at the NOMINAL moduli, by a witness: the float buckling mode
    x (dyadic, exact from here on) with x'K0x + lam sum_e N_hi,e x'G_e x <= 0, N_hi,e >= N_e proved by one solve
    (zenergy.enclose_linear) and x'G_e x >= 0 — so K0 + lam K_G(N) is not positive definite and lambda_cr <= lam
    (ZTL lean/ZStability.lean `witness_upper`, zero axioms). Nominal only: the box's moduli are not used."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    import numpy as np
    import scipy.sparse.linalg as sla
    nodes, elems, loads, supports, ex, (area, izz) = read_deck(text)
    parts, f, dof, emap, _ = energy_system_full(text, tol)
    n = len(dof)
    nom = [{"t": 0, "terms": p["terms"]} for p in parts]
    ks = [k for k in emap if any(emap[k]["a"].values())]
    encl = ZE.enclose_linear(nom, f, n, [emap[k]["a"] for k in ks])
    Nlo, Nhi, Nmid, Ge = {}, {}, {}, {}
    for k, (lo, hi) in zip(ks, encl):
        fac = ex * area / emap[k]["L"]
        Nlo[k], Nhi[k], Nmid[k] = fac * lo, fac * hi, fac * (lo + hi) / 2
    K0 = ZE.matrix(nom, n)
    Gnom = {}
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        dx, dy = nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1]
        Ge[k] = _geo_entries(nodes, i, j, L, dx / L, dy / L, dof)
        for (a, b), v in Ge[k].items():
            if a >= b:
                Gnom[(a, b)] = Gnom.get((a, b), F(0)) + Nmid.get(k, F(0)) * v
    A = ZE._float_matrix(K0, n)
    Bm = ZE._float_matrix(Gnom, n)
    try:
        vals, vecs = sla.eigsh(-Bm, k=1, M=A, which="LA", v0=np.ones(n))
    except Exception:
        return {"lam_high": None, "why": "no buckling mode found"}
    if vals[0] <= 0:
        return {"lam_high": None, "why": "no compressed member: no buckling under these loads"}
    x = [F(float(v)) for v in vecs[:, 0]]
    qK = sum(a * b for a, b in zip(x, ZE._kmul(K0, x, n)))
    den = F(0)
    for k, G in Ge.items():
        if k not in Nhi:
            continue
        g = sum(v * x[a] * x[b] for (a, b), v in G.items())        # both triangles: the full form, >= 0
        den -= Nhi[k] * g
    if den <= 0:
        return {"lam_high": None, "why": "the witness does not load the mode in compression"}
    lam = qK / den                                       # x'K0x + lam sum N_hi g = 0 <= 0: not positive definite
    S = 1 << 64
    lam = F(-((-lam.numerator * S) // lam.denominator), S)  # rounded UP: still not PD there (form <= 0 beyond)
    return {"lam_high": lam, "lam_est": float(1 / vals[0]), "Nlo": Nlo, "Nhi": Nhi, "unknowns": n}


CURVES = {"a0": F(13, 100), "a": F(21, 100), "b": F(34, 100), "c": F(49, 100), "d": F(76, 100)}   # EN 1993-1-1 Table 6.1


def _curve_premises(a, lb0=F(1, 5)):
    """The premises of ZChi.chi_curves_monotone, checked exactly — the monotonicity the bounds rest on is a theorem
    only where these hold."""
    if not (a > 0 and lb0 >= 0 and (a + 4 * lb0) * lb0 <= 2):
        raise FrameError(f"imperfection factor {a}: outside ZChi's premises (0 < a, (a + 4 lb0) lb0 <= 2)")


def _sqrt_down(q, bits=64):
    from math import isqrt
    S = 1 << bits
    return F(isqrt(q.numerator * S * S // q.denominator), S)


def _g_lower(lb_lo, a):
    """A lower bound on g(lb) = chi(lb) lb^2 at any lb >= lb_lo (EN 1993-1-1 6.3.1.2: chi = 1/(Phi + sqrt(Phi^2 - lb^2)),
    Phi = (1 + a (lb - 0.2) + lb^2)/2; chi = 1 up to lb = 0.2). g is strictly increasing in lb: below 0.2 it is lb^2;
    above, g = Phi - sqrt(Phi^2 - lb^2) and g' > 0 <=> 2uw + w^2 > 4 lb^2 with u = lb^2 - 1 + a/5, w = 2 + a(lb - 2/5),
    which is a lb (2 lb (lb - 0.4) + 2 + a (lb - 0.4)) > 0. PROVED in ZTL lean/ZChi.lean `chi_curves_monotone`
    (zero axioms, 2026-11-01): g = chi lb^2 and R = 1/chi are the roots of t^2 - 2 Phi t + lb^2; g does not fall and
    chi does not rise for lb >= 0.2, given 0 < a, 0 <= lb0 and (a + 4 lb0) lb0 <= 2 (checked: _curve_premises).
    Also MEASURED on a 20000-point grid lb in (0, 6] for all five curves: every step positive."""
    if lb_lo <= F(1, 5):
        return lb_lo * lb_lo
    ph = (1 + a * (lb_lo - F(1, 5)) + lb_lo * lb_lo) / 2
    d = ph * ph - lb_lo * lb_lo
    S = 1 << 64
    from math import isqrt
    r = isqrt(d.numerator * S * S // d.denominator)
    up = F(r + 1, S)                               # sqrt(d) <= up
    return max(F(0), ph - up)


def _g_upper(lb_hi, a):
    """An upper bound on g(lb) at any lb <= lb_hi (g increasing; see _g_lower)."""
    if lb_hi <= F(1, 5):
        return lb_hi * lb_hi
    ph = (1 + a * (lb_hi - F(1, 5)) + lb_hi * lb_hi) / 2
    return ph - _sqrt_down(ph * ph - lb_hi * lb_hi)


def judge_buckling(text, tol, fy, curve, gamma_m1=F(1), jobs=1, phi=None):
    """judge_buckling_case on the EN global-analysis load cases: the deck plus the sway imperfection +-phi (5.3.2,
    phi0 = 1/200 bounds it), both directions (2026-11-01). REFUTED if a case is, EARNED if every case is."""
    phi = PHI0 if phi is None else phi
    signs = [1, -1] if with_imperfection(text, phi, 1) != text else [0]
    cases = []
    for sg in signs:
        r = judge_buckling_case(with_imperfection(text, phi, sg) if sg else text, tol, fy, curve, gamma_m1, jobs)
        r["imperfection"] = f"{'+' if sg > 0 else '-' if sg < 0 else ''}{phi if sg else 0}"
        cases.append(r)
    vs = [c["verdict"] for c in cases]
    return {"verdict": "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN",
            "path": cases[0].get("path"), "cases": cases,
            "not_checked": "6.3.3 bending-axial interaction; out-of-plane and lateral-torsional buckling"}


def judge_buckling_case(text, tol, fy, curve, gamma_m1=F(1), jobs=1):
    """EN 1993-1-1 6.3.1 flexural buckling of every compressed member, N_Ed <= chi A fy / gamma_M1, with the member's
    elastic critical force taken from the frame's critical factor, N_cr,i = alpha_cr |N_Ed,i| (lb_i^2 = A fy / N_cr,i).
    The check is gamma_M1 <= H = alpha_cr g(lb_i), g = chi lb^2; H grows with alpha_cr (dH/dalpha = -lb^3 chi'/2 >= 0)
    and falls with |N| (g increasing, lb falling in |N|), so the proved alpha_cr lower bound and the proved |N| upper
    bound give a proved lower bound on H for every modulus in the box. EARNED when every member clears it. REFUTED
    when a member fails at the NOMINAL moduli (a point of the box): H <= alpha_cr,hi g(lb_hi) with alpha_cr,hi
    from stability_upper's witness and |N| >= |N|_lo from one proved solve. OPEN otherwise. Axial force only: the
    bending interaction of 6.3.3 is NOT checked, nor out-of-plane or lateral-torsional buckling."""
    nodes, elems, loads, supports, ex, (area, izz) = read_deck(text)
    if curve not in CURVES:
        raise FrameError(f"{curve!r}: a buckling curve is one of {', '.join(CURVES)}")
    a = CURVES[curve]
    _curve_premises(a)
    st = stability_lower(text, tol, jobs=jobs)
    lam = st.get("lam_low")
    if st.get("lam_est") is None:
        return {"verdict": "EARNED", "why": "no compressed member under these loads", "members": []}
    su = stability_upper(text, "0")
    lam_hi = su.get("lam_high")
    rows, worst = [], F(0)
    for k in sorted(st["Nlo"]):
        nlo = st["Nlo"][k]
        if nlo >= 0:
            continue                                  # never compressed anywhere in the box
        nhi = -nlo                                    # |N| upper bound
        if not lam or lam <= 0:
            rows.append({"member": k, "N_max": _show(nhi, 1), "verdict": "OPEN"})
            continue
        lb_lo = _sqrt_down(area * fy / (lam * nhi))
        H = lam * _g_lower(lb_lo, a)
        u = gamma_m1 / H if H > 0 else None
        if u is not None:
            worst = max(worst, u)
        row = {"member": k, "N_max": _show(nhi, 1), "lambda_bar_min": _show(lb_lo, -1),
               "utilisation_max": _show(u, 1) if u is not None else None,
               "verdict": "EARNED" if u is not None and u <= 1 else "OPEN"}
        nn = su.get("Nhi", {}).get(k)                  # nominal N upper bound: compressed there if < 0
        if row["verdict"] == "OPEN" and lam_hi and nn is not None and nn < 0:
            lb_hi = _sqrt_down(area * fy / (lam_hi * -nn)) + F(1, 1 << 64)     # sqrt rounded up
            Hh = lam_hi * _g_upper(lb_hi, a)
            if gamma_m1 > Hh:
                row["verdict"] = "REFUTED"
                row["at_nominal_utilisation_min"] = _show(gamma_m1 / Hh, -1)
        rows.append(row)
    vs = [r["verdict"] for r in rows]
    return {"verdict": "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN",
            "alpha_cr_nominal_proved_upper": _show(lam_hi, 1) if lam_hi else None,
            "path": "EN 1993-1-1 6.3.1 with N_cr,i = alpha_cr |N_Ed,i|; alpha_cr and |N| proved over the box",
            "alpha_cr_proved_lower": _show(lam, -1) if lam else None, "alpha_cr_nominal_estimate": st.get("lam_est"),
            "utilisation_max": _show(worst, 1), "members": rows,
            "not_checked": "6.3.3 bending-axial interaction; out-of-plane and lateral-torsional buckling"}


def fibre_ranges(text, tol, k, ctx=None):
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof, emap, (ex, area, izz, h) = ctx or energy_system_full(text, tol)
    if h is None:
        raise FrameError("member stresses need the section height: R, 1, area, izz, height")
    if k not in emap:
        raise FrameError(f"SIG({k}): no element {k}")
    n = len(dof)
    res = []
    for end, side, g in fibre_vectors(emap, k, h):
        e = [F(0)] * n
        for i, v in g.items():
            e[i] = v
        if not any(e):
            res.append({"end": end, "side": side, "lo": F(0), "hi": F(0), "nominal": F(0), "e": e, "sc": None})
            continue
        sc = ZE.certify_scaled(parts, f, e, n, emap[k]["part"])
        lo, hi = sorted([ex * sc["lo"], ex * sc["hi"]])
        res.append({"end": end, "side": side, "lo": lo, "hi": hi, "nominal": ex * sc["nominal"], "e": e, "sc": sc})
    return res


PHI0 = F(1, 200)        # EN 1993-1-1 5.3.2(3): phi = phi0 alpha_h alpha_m, alpha_h, alpha_m <= 1 -> phi0 bounds it


def with_imperfection(text, phi, sign):
    """The deck plus EN 1993-1-1 5.3.2(7)'s equivalent horizontal forces for a global sway imperfection phi: at every
    node with a vertical load V, a horizontal sign * phi * |V| (gravity along Y; the whole structure tilted by phi)."""
    nodes, elems, loads, supports, ex, sec = read_deck(text)
    extra = [f"F, {nd}, FX, {sign * phi * abs(v)}" for (nd, d), v in sorted(loads.items()) if d == "Y" and v]
    return text.rstrip("\n") + "\n" + "\n".join(extra) + "\n" if extra else text


def judge_members(text, tol, checks, jobs=1, order=2, phi=PHI0):
    """Member stress checks |sigma| <= limit (EN 1993-1-1 6.2.1(7)) with the GLOBAL ANALYSIS EN asks for
    (2026-11-01, the curator's "максимальное устранение ошибок"): the loads plus the sway imperfection phi (5.3.2,
    both directions, phi0 = 1/200 bounds phi from above), and second-order effects by the proved critical factor:
      alpha_cr,low >= 10  first-order analysis is allowed (5.2.1(3)): the first-order verdicts stand, REFUTED too;
      3 <= alpha_cr,low < 10  every proved fibre range amplified by 1/(1 - 1/alpha_cr,low) (5.2.2(5B) amplifies the
            sway effects; amplifying ALL of sigma is on the safe side, and alpha_cr,low <= alpha_cr makes the factor an
            upper bound): EARNED when inside the limit; never REFUTED (sway and non-sway parts may have opposite signs
            at a fibre, so first-order failure does not prove second-order failure) — OPEN;
      alpha_cr,low < 3  the amplification is not allowed: OPEN, a second-order analysis is needed.
    order=1: the first-order check alone, no imperfection (the earlier behaviour)."""
    if order == 1:
        return _judge_members_1(text, tol, checks, jobs)
    signs = [1, -1] if with_imperfection(text, phi, 1) != text else [0]
    cases = []
    for sg in signs:
        deck = with_imperfection(text, phi, sg) if sg else text
        r1 = _judge_members_1(deck, tol, checks, jobs)
        st = stability_lower(deck, tol, jobs=jobs)
        lam = st.get("lam_low")
        none = st.get("lam_est") is None
        amp = F(1) if none else (1 / (1 - 1 / lam) if lam and lam >= 3 else None)
        mode = "no compression" if none else "first order allowed" if lam >= 10 else "amplified" if amp else \
            "not allowed"
        rows = []
        for row in r1["checks"]:
            lim = F(row["check"].split("<=")[1].strip())
            peak = max(max(abs(F(x.split()[0])) for x in fb["proved_range"]) for fb in row["fibres"])
            r = {"check": row["check"], "first_order": row["verdict"], "first_order_peak": _show(peak, 1)}
            if mode in ("no compression", "first order allowed"):
                r["verdict"] = row["verdict"]
            elif mode == "amplified":
                r["amplified_peak"] = _show(peak * amp, 1)
                r["verdict"] = "EARNED" if peak * amp <= lim else "OPEN"
            else:
                r["verdict"] = "OPEN"
            if "witness" in row:
                r["first_order_witness"] = row["witness"]
            rows.append(r)
        cases.append({"imperfection": f"{'+' if sg > 0 else '-' if sg < 0 else ''}{phi if sg else 0}",
                      "alpha_cr_proved_lower": _show(lam, -1) if lam is not None else None,
                      "second_order": mode, "amplification": _show(amp, 1) if amp else None, "checks": rows})
    vs = [r["verdict"] for c in cases for r in c["checks"]]
    verdict = "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN"
    return {"verdict": verdict, "path": "member stresses: zenergy.certify_scaled on every extreme fibre; EN global "
            "analysis: sway imperfection +-phi and second order by the proved alpha_cr", "cases": cases,
            "not_checked": "member buckling (use --buckling), 6.3.3 interaction"}


def _judge_members_1(text, tol, checks, jobs=1):
    """checks: [(k, limit)] — |sigma| <= limit at every extreme fibre of element k (EN 1993-1-1 6.2.1(7),
    limit = fy / gamma_M0). EARNED when every fibre's proved range is inside [-limit, limit]; REFUTED when a
    fibre's witness vertex (solved exactly, or its floating enclosure) is wholly outside; OPEN otherwise."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    ctx = energy_system_full(text, tol)
    parts, f, dof, emap, (ex, area, izz, h) = ctx
    n = len(dof)
    rows = []
    allfr = fibre_ranges_many(text, tol, [k for k, _ in checks], ctx, jobs)
    for k, lim in checks:
        fr = allfr[k]
        ok = all(-lim <= r["lo"] and r["hi"] <= lim for r in fr)
        row = {"check": f"|SIG({k})| <= {lim}", "fibres": [{"end": r["end"], "side": r["side"],
               "nominal": _show(r["nominal"]), "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)]} for r in fr]}
        if ok:
            row["verdict"] = "EARNED"
        else:
            row["verdict"] = "OPEN"
            worst = max((r for r in fr if r["sc"] is not None), key=lambda r: abs(r["nominal"]), default=None)
            if worst is not None:
                up = worst["nominal"] >= 0
                pk = emap[k]["part"]
                sl = worst["sc"]["base"]["slopes"]
                # push the bracket outward; the element's own factor up (|sigma| grows with p_k for this sign)
                ps = [1 + (pp["t"] if (s_ > 0) == up and s_ != 0 else -pp["t"] if s_ != 0 else 0)
                      for pp, s_ in zip(parts, sl)]
                ps[pk] = 1 + parts[pk]["t"]
                if n <= ZE.EXACT_UP_TO:
                    wl = wh = ZE.value_at(parts, f, worst["e"], n, ps)
                else:
                    wl, wh = ZE.value_enclosure_fp(parts, f, worst["e"], n, ps)
                lo_, hi_ = sorted([ex * ps[pk] * wl, ex * ps[pk] * wh])
                row["witness"] = {"end": worst["end"], "side": worst["side"], "value": _show(hi_ if up else lo_)}
                if (lo_ > lim) if up else (hi_ < -lim):
                    row["verdict"] = "REFUTED"
        rows.append(row)
    vs = [r["verdict"] for r in rows]
    verdict = "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN"
    return {"verdict": verdict, "path": "member stresses: zenergy.certify_scaled on every extreme fibre",
            "checks": rows, "unknowns": n}


def _target(text):
    import re
    m = re.match(r"^\s*(?:U\(\s*(\d+)\s*,\s*([XYxy])\s*\)|ROT\(\s*(\d+)\s*\))\s*$", text)
    if not m:
        raise FrameError(f"{text!r}: a target is U(node,X), U(node,Y) or ROT(node)")
    return (int(m.group(1)), m.group(2).upper()) if m.group(1) else (int(m.group(3)), "R")


def _req(text):
    import re
    m = re.match(r"^\s*((?:U|ROT)\([^)]*\))\s*(<=|>=)\s*(\S+)\s*$", text)
    if not m:
        raise FrameError(f"{text!r}: a requirement is U(node,X|Y) or ROT(node), <= or >=, a value")
    n, d = _target(m.group(1))
    return n, d, m.group(2), _num(m.group(3), text)


def _name(n, d):
    return f"ROT({n})" if d == "R" else f"U({n},{d})"


def judge(text, tol, requirements):
    from . import judge_ztl  # noqa: F401  (puts ZTL on the path)
    import zenergy as ZE
    parts, f, dof = energy_system(text, tol)
    n = len(dof)
    rows = []
    for (nd, d, op, v) in requirements:
        if (nd, d) not in dof:
            raise FrameError(f"{_name(nd, d)}: not a free displacement of this frame")
        e = [F(0)] * n
        e[dof[(nd, d)]] = F(1)
        r = ZE.certify(parts, f, e, n)       # exact solves up to ZE.EXACT_UP_TO unknowns, the floating path above
        row = {"requirement": f"{_name(nd, d)} {op} {v}", "nominal": _show(r["nominal"]),
               "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)],
               "first_order": _show(r["first"]), "rest": _show(r["rest"])}
        if (r["hi"] <= v) if op == "<=" else (r["lo"] >= v):
            row["verdict"] = "EARNED"
        else:
            up = op == "<="
            ps = [1 + (p["t"] if (sl > 0) == up and sl != 0 else -p["t"] if sl != 0 else 0)
                  for p, sl in zip(parts, r["slopes"])]
            if n <= ZE.EXACT_UP_TO:
                w = wl = wh = ZE.value_at(parts, f, e, n, ps)
            else:                                     # the floating path at the vertex: its whole enclosure must cross
                wl, wh = ZE.value_enclosure_fp(parts, f, e, n, ps)
                w = wh if up else wl
            row["witness_value"] = _show(w)
            row["verdict"] = "REFUTED" if ((wl > v) if up else (wh < v)) else "OPEN"
        rows.append(row)
    vs = [r["verdict"] for r in rows]
    verdict = "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN"
    return {"verdict": verdict, "path": "energy norm (ZTL zenergy): first order exact + a proved rest",
            "requirements": rows, "unknowns": n, "elements": len(parts),
            "checked_by": "ZTL zenergy: exact solves up to ZTL zenergy.EXACT_UP_TO unknowns (120; residual checked); above them float solves with "
                          "exact residuals and lambda_min(K0) proved by a floating Cholesky — PREMISE: IEEE 754 "
                          "binary64 and LAPACK (Higham Thm 10.3, cited, not in Lean; ZTL KNOWN-LIMITS.md); the "
                          "bound's algebra is ZTL lean/ZNet.lean step 4 with lean/ZEnergy.lean target_first_grouped "
                          "(zero axioms); the floating path's error assembly is on paper (Lean next)"}


def range_of(text, tol, target):
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    parts, f, dof = energy_system(text, tol)
    nd, d = _target(target)
    e = [F(0)] * len(dof)
    e[dof[(nd, d)]] = F(1)
    r = ZE.certify(parts, f, e, len(dof))
    return {"target": target, "nominal": _show(r["nominal"]), "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)],
            "note": "an enclosure (first order exact + a proved rest), not the exact range"}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    try:
        text = open(argv[0], encoding="utf-8").read()
        tol = argv[argv.index("--tol") + 1] if "--tol" in argv else "0"
        import re as _re
        if "--stability" in argv:                     # a proved lower bound on the critical load factor
            jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
            r = stability_lower(text, tol, jobs=jobs)
            ru = stability_upper(text, "0")
            print(json.dumps({"lambda_cr_proved_lower": _show(r["lam_low"], -1) if r.get("lam_low") is not None
                              else None, "lambda_cr_nominal_estimate": r.get("lam_est"),
                              "lambda_cr_nominal_proved_upper": _show(ru["lam_high"], 1) if ru.get("lam_high")
                              else None,
                              "note": "linear buckling; the lower bound holds for every modulus in the box, the upper one at the "
                                      "nominal moduli (a witness mode); no imperfections, no plasticity",
                              **({"why": r["why"]} if "why" in r else {})}, indent=1, ensure_ascii=False))
            return 0
        if "--buckling" in argv:                      # EN 6.3.1 per member: --buckling fy curve [gamma_M1]
            i = argv.index("--buckling")
            fy = _num(argv[i + 1], "fy")
            curve = argv[i + 2]
            gm1 = _num(argv[i + 3], "gamma_M1") if len(argv) > i + 3 and not argv[i + 3].startswith("--") else F(1)
            jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
            print(json.dumps(judge_buckling(text, tol, fy, curve, gm1, jobs=jobs), indent=1, ensure_ascii=False))
            return 0
        raw = [argv[i + 1] for i, a in enumerate(argv) if a == "--req"]
        sig = [x for x in raw if _re.match(r"^\s*SIG\(", x, _re.I)]
        if sig:                                       # member stress checks: SIG(k) <= limit
            checks = []
            for x in sig:
                m = _re.match(r"^\s*SIG\(\s*(\d+)\s*\)\s*<=\s*(\S+)\s*$", x, _re.I)
                if not m:
                    raise FrameError(f"{x!r}: a member check is SIG(element) <= limit (|sigma| at every fibre)")
                checks.append((int(m.group(1)), _num(m.group(2), x)))
            jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
            order = 1 if "--first-order" in argv else 2
            print(json.dumps(judge_members(text, tol, checks, jobs=jobs, order=order), indent=1, ensure_ascii=False))
            return 0
        reqs = [_req(x) for x in raw]
        ranges = [argv[i + 1] for i, a in enumerate(argv) if a == "--range"]
        out = {t: range_of(text, tol, t) for t in ranges} if ranges else judge(text, tol, reqs)
    except (B.BrickError, OSError, ValueError, IndexError) as e:
        out = {"verdict": "BRICK ERROR", "why": f"{e}"}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
