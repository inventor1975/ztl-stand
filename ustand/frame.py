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
    python3 -m ustand.frame deck.txt --tol 0.5% --interaction 355e6 b [1.0]     EN 1993-1-1 6.3.3 (6.61), Annex B,
            in-plane: every compressed member (a chain of collinear elements between joints); out-of-plane restraint
            and section class 1-3 ASSUMED and said
    --jobs N   outputs spread over N processes (stresses, stability, buckling, interaction)

THE DECK (the subset read; anything else is REFUSED aloud):
    N, id, x, y                  a node
    E, i, j                      an element between nodes i and j (one material, one real constant)
    MP, EX, 1, value             Young's modulus (nominal)
    R, 1, area, izz[, height]    the section: area, second moment, and (for stresses) the height
    F, node, FX|FY|MZ, value     a nodal force or moment
    QLOAD, elem, FX|FY, q        a uniform load per unit LENGTH of the element, in a global direction (the stand's
                                 own command; ANSYS's SFBEAM is refused). Exact: consistent nodal loads + the inner
                                 solution (stresses and moments along the element, the peak found inside)
    D, node, UX|UY|ROTZ, 0       a support (zero displacement or rotation)
    /PREP7, ET (BEAM3 / 3), MAT, REAL, TYPE, comments (!) — read and skipped.
Lengths must be rational (an irrational length is refused: the stiffness would not be exact).

WHAT IT DOES NOT DO (yet), said: the box path (zlin) is not wired for frames — a requirement the energy path cannot
decide comes back OPEN, not guessed; no shear deformation (Timoshenko); second order only by EN 5.2.2's amplification (alpha_cr >= 3;
below, OPEN — no geometrically nonlinear solve yet); gravity is taken along Y for the imperfection's equivalent
forces (5.3.2(7)); stability is LINEAR buckling of the Euler-Bernoulli CONTINUUM (each member's
inner deflection bounded by its clamped Euler load; no imperfections, no plasticity); member buckling: 6.3.1 (axial) and 6.3.3
(6.61) in-plane interaction; out-of-plane and lateral-torsional buckling are NOT checked (no out-of-plane data).
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


SCOPE_BEAM = {"scope": "FRAME (Euler-Bernoulli members)",
              "scope_note": "proved for the frame in Euler-Bernoulli beam theory: the Hermite element is exact for "
                            "nodal loads in statics, and buckling carries each member's continuum correction. Not "
                            "covered: shear deformation, joint flexibility, imperfections beyond EN's phi, plasticity."}


def _qload_lines(text):
    """QLOAD, elem, FX|FY, q — a uniform load per unit LENGTH of the element, in a global direction (the stand's own
    command, 2026-11-01: ANSYS's SFBEAM is face-and-sign dependent; a silent sign error is worse than a refusal)."""
    out = []
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split("!")[0].strip()
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())] if line else []
        if f and f[0].upper() == "QLOAD":
            if len(f) != 4 or f[2].upper() not in ("FX", "FY"):
                raise FrameError(f"line {ln}: QLOAD, elem, FX|FY, q (per unit length, global direction)")
            out.append((int(f[1]), f[2].upper()[1], _num(f[3], f"line {ln}")))
    return out


def read_qloads(text):
    """{element: (a, w, L)}: the element's uniform load per length resolved along it (a, local x) and across it
    (w, local y = (-s, c)), and its length."""
    nodes, elems, loads, supports, ex, sec = read_deck(text)
    out = {}
    for k, d, q in _qload_lines(text):
        i, j = elems[k - 1]
        dx, dy = nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1]
        L = _sqrt(dx * dx + dy * dy)
        c, s_ = dx / L, dy / L
        qx, qy = (q, F(0)) if d == "X" else (F(0), q)
        a0, w0, _ = out.get(k, (F(0), F(0), L))
        out[k] = (a0 + qx * c + qy * s_, w0 - qx * s_ + qy * c, L)
    return out


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
        elif cmd == "QLOAD":
            continue                                   # read below (_qload_lines): its consistent nodal loads
        elif cmd == "SFBEAM":
            raise FrameError(f"{where}: SFBEAM is not read (its face and sign conventions are easy to get silently "
                             f"wrong) — write QLOAD, elem, FX|FY, q (per unit length, global direction)")
        else:
            raise FrameError(f"{where}: {f[0]} — not read (only N E MP R F D ET MAT REAL TYPE QLOAD)")
    if not nodes or not elems:
        raise FrameError("no nodes or no elements")
    if ex is None or sec is None:
        raise FrameError("no MP,EX or no R (the modulus and the section are needed)")
    for i, j in elems:
        for n in (i, j):
            if n not in nodes:
                raise FrameError(f"element {i}-{j}: node {n} does not exist")
    # member loads: their CONSISTENT nodal loads (Hermite: exact at the nodes for an Euler-Bernoulli member):
    # the resultant split in halves, and +-w L^2/12 end moments (w across the element, local y = (-s, c))
    for k, d, q in _qload_lines(text):
        if not 1 <= k <= len(elems):
            raise FrameError(f"QLOAD on element {k}: no such element")
        i, j = elems[k - 1]
        dx, dy = nodes[j][0] - nodes[i][0], nodes[j][1] - nodes[i][1]
        L = _sqrt(dx * dx + dy * dy)
        if not L:
            raise FrameError(f"QLOAD on element {k}: its length is irrational — not exact")
        c, s_ = dx / L, dy / L
        qx, qy = (q, F(0)) if d == "X" else (F(0), q)
        w = -qx * s_ + qy * c
        for n, mz in ((i, w * L * L / 12), (j, -w * L * L / 12)):
            for key, v in (((n, "X"), qx * L / 2), ((n, "Y"), qy * L / 2), ((n, "R"), mz)):
                if v:
                    loads[key] = loads.get(key, F(0)) + v
    return nodes, elems, loads, supports, ex, sec


def subdivide(text, n):
    """The deck with every element split into n equal elements (new nodes at rational points; loads, supports, the
    section and the material unchanged). Each original element k becomes elements n(k-1)+1 .. nk (2026-11-01: the
    Hermite beam is exact for nodal loads in statics, NOT for buckling — measured with this)."""
    if n == 1:
        return text
    nodes, elems, loads, supports, ex, sec = read_deck(text)
    keep = [ln for ln in text.splitlines()
            if not ln.split("!")[0].strip().upper().startswith(("E,", "E ", "QLOAD"))]
    keep += [f"QLOAD, {n * (k - 1) + m}, F{d}, {q}" for k, d, q in _qload_lines(text) for m in range(1, n + 1)]
    nxt = max(nodes) + 1
    out_e = []
    for (i, j) in elems:
        chain = [i]
        for k in range(1, n):
            x = nodes[i][0] + (nodes[j][0] - nodes[i][0]) * F(k, n)
            y = nodes[i][1] + (nodes[j][1] - nodes[i][1]) * F(k, n)
            keep.append(f"N, {nxt}, {x}, {y}")
            chain.append(nxt)
            nxt += 1
        chain.append(j)
        out_e += [f"E, {a}, {b}" for a, b in zip(chain, chain[1:])]
    return "\n".join(keep + out_e) + "\n"


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
    # TOP = the physical fibre at local +y at BOTH ends (2026-11-01: the J end used to carry the opposite label —
    # harmless for |sigma| checks, wrong for curvature signs): sigma_top = N/A + M/W with M = E I/L (b + 3c).u at I
    # and E I/L (b - 3c).u at J (one sign convention: single curvature = same sign at both ends)
    for end, sb in (("I", 1), ("J", -1)):
        for side, sg in (("TOP", 1), ("BOT", -1)):
            g = {}
            for i, v in a.items():
                g[i] = g.get(i, F(0)) + v / L
            for i, v in b.items():
                g[i] = g.get(i, F(0)) + sg * (h / 2) / L * v
            for i, v in c.items():
                g[i] = g.get(i, F(0)) + sg * (h / 2) / L * 3 * sb * v
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
    qd = read_qloads(text)
    for k, end, side, e in items:
        bub, kap = _bubble(qd, k, end, side, area, izz, h)
        if not any(e):
            out[k].append({"end": end, "side": side, "lo": bub, "hi": bub, "nominal": bub, "e": e, "sc": None,
                           "bub": bub, "kappa": kap})
            continue
        sc = ZE.scaled_from(next(rs), parts, emap[k]["part"])
        lo, hi = sorted([ex * sc["lo"], ex * sc["hi"]])
        out[k].append({"end": end, "side": side, "lo": lo + bub, "hi": hi + bub, "nominal": ex * sc["nominal"] + bub,
                       "e": e, "sc": sc, "bub": bub, "kappa": kap})
    return out


def _bubble(qd, k, end, side, area, izz, h):
    """A member load's exact INNER solution (it vanishes, with its slope, at both nodes): at an end fibre its stress
    (added to the Hermite part), and kappa, the fibre's parabola across the element: sigma(s) = linear between the
    ends + kappa s (1 - s). Axial load a: N_b = a (L - 2x)/2 (linear); transverse w: M_b = w (6x^2 - 6Lx + L^2)/12,
    top fibre (local +y) -M_b (h/2)/I. kappa_top = w L^2 (h/2)/(2 I), kappa_bot = -kappa_top."""
    if k not in qd:
        return F(0), F(0)
    a, w, L = qd[k]
    s_ = F(0) if end == "I" else F(1)
    sg = 1 if side == "TOP" else -1
    axial = a * L * (1 - 2 * s_) / (2 * area)
    bend = -sg * (h / 2) * w * L * L * (6 * s_ * s_ - 6 * s_ + 1) / (12 * izz)
    return axial + bend, sg * w * L * L * (h / 2) / (2 * izz)


def _side_peak(Ar, Br, kappa):
    """max over s in [0, 1] of |sigma(s)|, sigma between (1-s) A_lo + s B_lo + kappa s(1-s) and the same with the highs
    (A, B the end ranges): each envelope a parabola — its ends and, inside, its vertex."""
    best = F(0)
    for a_, b_ in ((Ar[0], Br[0]), (Ar[1], Br[1])):
        cands = [F(0), F(1)]
        if kappa:
            sv = (kappa + b_ - a_) / (2 * kappa)
            if 0 < sv < 1:
                cands.append(sv)
        for s_ in cands:
            best = max(best, abs((1 - s_) * a_ + s_ * b_ + kappa * s_ * (1 - s_)))
    return best


# ----------------------------------------------------------------------------------------------------------------
# STABILITY (2026-11-01): a PROVED lower bound on the elastic critical load factor, for every modulus in the box.
# The consistent geometric stiffness of a beam, G_e = int N_v'^T N_v' dx over Hermite cubics (local v, th):
#   (1/(30 L)) [[36, 3L, -36, 3L], [3L, 4L^2, -3L, -L^2], [-36, -3L, 36, -3L], [3L, -L^2, -3L, 4L^2]],
# is positive SEMIdefinite (a Gram matrix), and K_G = sum_e N_e G_e (N_e tension positive). If N_e(p) >= N_lo,e over
# the box (each a proved range: ZTL zenergy.certify_many on the axial outputs), then for lambda >= 0
#   K(p) + lambda K_G(N(p))  >=  (1 - T) K0 + lambda sum_e N_lo,e G_e        (Loewner: K(p) >= (1 - T) K0, G_e >= 0)
# so ONE matrix proved positive definite (ZTL zenergy.pd_ieee) proves lambda < lambda_cr at every p. Linear
# buckling (no imperfections, no plasticity); the load factor scales the given loads.

def _geo_split(L):
    """The consistent geometric stiffness for a LINEAR axial force N(x) = N_a (1 - s) + N_b s: N_a G_a + N_b G_b,
    G_a = int (1 - s) N'^T N' dx, G_b = int s N'^T N' dx (Hermite cubics, exact rationals; G_a + G_b = G)."""
    # N_i'(s) as polynomial coefficients in s (d/dx = (1/L) d/ds)
    d = [[F(0), F(-6) / L, F(6) / L], [F(1), F(-4), F(3)], [F(0), F(6) / L, F(-6) / L], [F(0), F(-2), F(3)]]
    def mul(p, q):
        r = [F(0)] * (len(p) + len(q) - 1)
        for i, a in enumerate(p):
            for j, b in enumerate(q):
                r[i + j] += a * b
        return r
    integ = lambda p: sum(c / (i + 1) for i, c in enumerate(p))
    Ga = [[L * integ(mul(mul(d[i], d[j]), [F(1), F(-1)])) for j in range(4)] for i in range(4)]
    Gb = [[L * integ(mul(mul(d[i], d[j]), [F(0), F(1)])) for j in range(4)] for i in range(4)]
    return Ga, Gb


PI2_LO = F(98695, 10000)          # < pi^2 = 9.8696044...: the continuum correction is conservative with it


def _beam_form(i, j, c, s, dof, Gl):
    """A local 4 x 4 form over (v_i, th_i, v_j, th_j) on the global DOFs, lower triangle (a >= b)."""
    loc = [[((i, "X"), -s), ((i, "Y"), c)], [((i, "R"), F(1))], [((j, "X"), -s), ((j, "Y"), c)], [((j, "R"), F(1))]]
    out = {}
    for a in range(4):
        for b in range(4):
            if not Gl[a][b]:
                continue
            for (na, va) in loc[a]:
                for (nb, vb) in loc[b]:
                    if va and vb and na in dof and nb in dof:
                        key = (dof[na], dof[nb])
                        if key[0] >= key[1]:
                            out[key] = out.get(key, F(0)) + Gl[a][b] * va * vb
    return out


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


_STAB = {}
_MUTANT = {}       # TEST-ONLY sabotage switches (bench/night/verify_all.py's mutation runs); empty = the real bounds


def stability_lower(text, tol, jobs=1, rel=F(1, 1000), model="continuum"):
    """Cached: the same deck, tolerance, precision and model give the same proved result (the float steps are
    deterministic, eigsh starts from ones) — the second-order checks ask for it again and again."""
    key = (text, str(tol), rel, model)
    if key not in _STAB:
        _STAB[key] = _stability_lower(text, tol, jobs, rel, model)
    return _STAB[key]


def _stability_lower(text, tol, jobs=1, rel=F(1, 1000), model="continuum"):
    """A proved lam_low with lam_low < lambda_cr for every modulus in the box — of the CONTINUUM frame (Euler-Bernoulli
    members), not of its Hermite model (model="continuum", the default since 2026-11-01; model="fe" is the model's
    own, which one element per member can put ABOVE the true load); and the float estimate of the nominal
    lambda_cr for the reader. Bisection on lambda, every accepted step proved by pd_ieee. Why one matrix
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
    Nhi = {k: F(0) for k in emap}
    Nnom = {k: F(0) for k in emap}
    for k, sc in zip(ks, rs):
        fac = ex * area / emap[k]["L"]
        Nlo[k] = min(fac * sc["lo"], fac * sc["hi"])
        Nhi[k] = max(fac * sc["lo"], fac * sc["hi"])
        Nnom[k] = fac * sc["nominal"]
    Nnodes_lo = dict(Nlo)
    qax = {}
    for k, (a_, w_, L_) in read_qloads(text).items():
        # an axial member load: N(x) = N_nodes + a (L - 2x)/2 — the whole element's range
        Nlo[k] = Nlo.get(k, F(0)) - abs(a_) * L_ / 2
        Nhi[k] = Nhi.get(k, F(0)) + abs(a_) * L_ / 2
        if a_:
            qax[k] = a_ * L_ / 2
    if all(v >= 0 for v in Nlo.values()):
        # no member compressed anywhere in the box: K_G(N(p)) >= 0, so K(p) + lam K_G > 0 for every lam >= 0
        return {"lam_low": None, "why": "no compressed member: no buckling under these loads", "lam_est": None,
                "unknowns": n, "T": T, "Nlo": Nlo, "Nhi": Nhi, "Nnom": Nnom}
    K0 = ZE.matrix(parts, n)                      # lower triangle
    # THE CONTINUUM, not the Hermite model (2026-11-01, MEASURED: one element per member put the FE "lower bound"
    # 0.72 % ABOVE Euler's exact load). Inside a member w = w_H + eta (eta, eta' = 0 at both ends); EI int w_H" eta"
    # = 0 (w_H is cubic); int eta'^2 <= (L/2pi)^2 int eta"^2 (the clamped member's Euler load) — so, as forms,
    #   compression P:  K_exact(-P) >= K_E - P G - P^2 k/(1 - P k) Q,   k = L^2/(4 pi^2 E I),  Q = G - b b^T/L,
    #   tension N:      K_exact(N)  >= K_E + N b b^T / L,
    # b = (-1, 0, 1, 0) on (v_i, th_i, v_j, th_j) (Q = int (w_H' - mean)^2). pi^2 from below, E at (1 - T) E0.
    # The algebra: ZTL lean/ZHypercircle.lean `beam_correction` (zero axioms); the Poincare inequality: a premise.
    Elo = (1 - T) * ex
    Gl, Ql, Bl, kk, Gal, Gbl = {}, {}, {}, {}, {}, {}
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        c_, s_ = (nodes[j][0] - nodes[i][0]) / L, (nodes[j][1] - nodes[i][1]) / L
        Gloc = [[F(v) / (30 * L) for v in r] for r in [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                                        [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]]]
        Bloc = [[F(v) / L for v in r] for r in [[1, 0, -1, 0], [0, 0, 0, 0], [-1, 0, 1, 0], [0, 0, 0, 0]]]
        Qloc = [[Gloc[a][b] - Bloc[a][b] for b in range(4)] for a in range(4)]
        Gl[k], Bl[k], Ql[k] = (_beam_form(i, j, c_, s_, dof, X) for X in (Gloc, Bloc, Qloc))
        kk[k] = L * L / (4 * PI2_LO * Elo * izz)
        if k in qax:
            Ga_, Gb_ = _geo_split(L)
            Gal[k], Gbl[k] = _beam_form(i, j, c_, s_, dof, Ga_), _beam_form(i, j, c_, s_, dof, Gb_)
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
        if model == "fe":
            for key, v in Gsum.items():
                M[key] = M.get(key, F(0)) + lam * v
        else:
            for k in Gl:
                if k in qax and Nlo[k] < 0:
                    # LINEAR N along the element (an axial member load): the geometric part exactly split,
                    # N_a = N_nodes + aL/2 at I, N_b = N_nodes - aL/2 at J, each from below; the continuum
                    # correction with the largest compression and G (not Q: the mean trick needs constant N)
                    Na, Nb = Nnodes_lo.get(k, F(0)) + qax[k], Nnodes_lo.get(k, F(0)) - qax[k]
                    P = -lam * Nlo[k]
                    if P * kk[k] >= 1:
                        return False
                    cq = P * P * kk[k] / (1 - P * kk[k])
                    for key, v in Gal[k].items():
                        M[key] = M.get(key, F(0)) + lam * Na * v
                    for key, v in Gbl[k].items():
                        M[key] = M.get(key, F(0)) + lam * Nb * v
                    for key, v in Gl[k].items():
                        M[key] = M.get(key, F(0)) - cq * v
                elif Nlo[k] < 0:
                    P = -lam * Nlo[k]
                    if P * kk[k] >= 1:
                        return False                  # the member itself could buckle between its nodes: subdivide
                    cq = P * P * kk[k] / (1 - P * kk[k])
                    for key, v in Gl[k].items():
                        M[key] = M.get(key, F(0)) - P * v
                    for key, v in Ql[k].items():
                        M[key] = M.get(key, F(0)) - cq * v
                elif Nlo[k] > 0:
                    for key, v in Bl[k].items():
                        M[key] = M.get(key, F(0)) + lam * Nlo[k] * v
        Mf = ZE._float_matrix(M, n)
        try:
            mu = float(sla.eigsh(Mf, k=1, sigma=0, which="LM", return_eigenvectors=False, v0=np.ones(n))[0])
        except Exception:
            return False
        if mu <= 0:
            return False
        return ZE.pd_ieee(n, M, F(mu) * F(9, 10)) is not None
    if lam_est is None:
        return {"lam_low": None, "why": "no compressed member: no buckling under these loads", "lam_est": None,
                "unknowns": n, "T": T, "Nlo": Nlo, "Nhi": Nhi, "Nnom": Nnom}
    lo, hi = F(0), F(lam_est) * F(11, 10)
    start = F(lam_est) / 1000
    for _ in range(20):                           # a noisy estimate (members barely compressed): step down
        if proved(start):
            break
        hi, start = start, start / 10
    else:
        return {"lam_low": F(0), "lam_est": lam_est, "why": "not even a small factor proved", "unknowns": n, "T": T,
                "Nlo": Nlo, "Nhi": Nhi, "Nnom": Nnom}
    lo = start
    for _ in range(40):
        mid = (lo + hi) / 2
        if proved(mid):
            lo = mid
        else:
            hi = mid
        if hi - lo <= rel * hi:
            break
    return {"lam_low": lo, "lam_est": lam_est, "unknowns": n, "T": T, "Nlo": Nlo, "Nhi": Nhi, "Nnom": Nnom}


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
    return {**SCOPE_BEAM, "verdict": "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN",
            "path": cases[0].get("path"), "cases": cases,
            "not_checked": "6.3.3 bending-axial interaction HERE (run --interaction); out-of-plane and lateral-torsional buckling"}


def judge_buckling_case(text, tol, fy, curve, gamma_m1=F(1), jobs=1):
    """EN 1993-1-1 6.3.1 flexural buckling of every compressed member, N_Ed <= chi A fy / gamma_M1, with the member's
    elastic critical force taken from the frame's critical factor, N_cr,i = alpha_cr |N_Ed,i| (lb_i^2 = A fy / N_cr,i).
    The check is gamma_M1 <= H = alpha_cr g(lb_i), g = chi lb^2; H grows with alpha_cr (dH/dalpha = -lb^3 chi'/2 >= 0)
    and falls with |N| (g increasing, lb falling in |N|), so the proved alpha_cr lower bound and the proved |N| upper
    bound give a proved lower bound on H for every modulus in the box. EARNED when every member clears it. REFUTED
    when a member fails at the NOMINAL moduli (a point of the box): H <= alpha_cr,hi g(lb_hi) with alpha_cr,hi
    from stability_upper's witness and |N| >= |N|_lo from one proved solve. OPEN otherwise. Axial force only: the
    bending interaction of 6.3.3 is judge_interaction's; out-of-plane and lateral-torsional buckling are not checked."""
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
    return {**SCOPE_BEAM, "verdict": "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN",
            "alpha_cr_nominal_proved_upper": _show(lam_hi, 1) if lam_hi else None,
            "path": "EN 1993-1-1 6.3.1 with N_cr,i = alpha_cr |N_Ed,i|; alpha_cr and |N| proved over the box",
            "alpha_cr_proved_lower": _show(lam, -1) if lam else None, "alpha_cr_nominal_estimate": st.get("lam_est"),
            "utilisation_max": _show(worst, 1), "members": rows,
            "not_checked": "6.3.3 bending-axial interaction HERE (run --interaction); out-of-plane and lateral-torsional buckling"}


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


def _psd_terms(Ml):
    """A symmetric positive SEMIdefinite 4 x 4 (exact) as rank-one terms [(d, l)], d > 0 — LDL^T with zero pivots
    skipped (their column must then vanish); checked to reproduce Ml exactly."""
    n = 4
    A = [list(r) for r in Ml]
    out = []
    for j in range(n):
        d = A[j][j]
        if d < 0:
            raise FrameError("internal: a local form is not PSD")
        if d == 0:
            if any(A[i][j] for i in range(n)):
                raise FrameError("internal: a zero pivot with a nonzero column (not PSD)")
            continue
        l = [A[i][j] / d if i >= j else F(0) for i in range(n)]
        out.append((d, l))
        for a in range(n):
            for b in range(n):
                A[a][b] -= d * l[a] * l[b]
    for a in range(n):
        for b in range(n):
            if sum(d * l[a] * l[b] for d, l in out) != Ml[a][b]:
                raise FrameError("internal: the rank-one terms do not reproduce the local form")
    return out


def _glob(i, j, c, s, dof, l):
    """A local (v_i, th_i, v_j, th_j) vector on the global DOFs (v = -s ux + c uy)."""
    g = {}
    for (nd, v) in (((i, "X"), -s * l[0]), ((i, "Y"), c * l[0]), ((i, "R"), l[1]),
                    ((j, "X"), -s * l[2]), ((j, "Y"), c * l[2]), ((j, "R"), l[3])):
        if v and nd in dof:
            g[dof[nd]] = g.get(dof[nd], F(0)) + v
    return {k: v for k, v in g.items() if v}


def second_order_case(text, tol, checks, jobs=1, disp=(), at=None):
    """PHYSICAL SECOND ORDER (2026-11-01, the curator's "(а)"): member stresses of the frame under its loads, with
    every modulus in the box, in second-order theory with the axial forces of the first-order analysis (a NAMED
    model premise; MEASURED on the 12x6 frame: iterating N moves the result by 0.02 %), each member the Euler-
    Bernoulli CONTINUUM. The system (K(p) + K_G(N) - D) u = f is ZTL zenergy.certify_general's:
      A0 = K0 + sum_e N_mid,e G_e;  parts: each element's stiffness, radius t; each G_e, radius (N_hi - N_lo)/2;
      D in [0, C], C = sum_e max(P_hi^2 k/(1 - P_hi k), N_hi+) Q_e (the continuum correction, both signs of N);
    theta proved, first order exact per part, the rest theta^2/(1 - theta). Requires the proved alpha_cr > 1.
    sigma = E p_k (g.u): the element's own factor taken as an interval (no correlation kept: safe).
    LEAN (ZTL lean/ZHypercircle.lean, zero axioms): |Delta(w,w)| <= M(w,w) <= theta A0(w,w) gives `rest_bound`'s
    hypotheses with t = theta; `perturb_identity` / `perturb_split` the first order + rest; `cs_weak` the D term."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    nodes, elems, loads, supports, ex, (area, izz) = read_deck(text)
    qd = read_qloads(text)
    if any(a_ for a_, w_, L_ in qd.values()):
        return {"verdict": "OPEN", "why": "an AXIAL member load (QLOAD along an element) in second order: not yet "
                                          "(N varies along the member) — first order and EN's method judge it",
                "checks": [], "disp": {}}
    st = stability_lower(text, tol, jobs=jobs)
    parts, f, dof, emap, (_, _, _, h) = energy_system_full(text, tol)
    if h is None and checks:
        raise FrameError("member stresses need the section height: R, 1, area, izz, height")
    n = len(dof)
    T = max((p["t"] for p in parts), default=F(0))
    lam = st.get("lam_low")
    if st.get("lam_est") is not None and (lam is None or lam <= 1):
        return {"verdict": "OPEN", "why": f"the critical factor is not proved above 1 (proved {lam}): the frame may "
                                          f"buckle under these loads", "checks": []}
    Nlo, Nhi = st["Nlo"], st["Nhi"]
    if at is not None:
        # ONE POINT of the box (a witness): every modulus fixed at p = at; the axial forces there enclosed (exact
        # solve up to EXACT_UP_TO unknowns, the floating path's enclosure above); D in [0, C] stays unknown
        parts = [{"t": F(0), "terms": [(F(w) * pp, g) for w, g in p_["terms"]]} for p_, pp in zip(parts, at)]
        T = F(0)
        Nlo, Nhi = {}, {}
        for k in emap:
            e = [F(0)] * n
            for i_, v in emap[k]["a"].items():
                e[i_] = v
            if not any(e):
                Nlo[k] = Nhi[k] = F(0)
                continue
            if n <= ZE.EXACT_UP_TO:
                a_ = b_ = ZE.value_at(parts, f, e, n, [F(1)] * len(parts))
            else:
                a_, b_ = ZE.value_enclosure_fp(parts, f, e, n, [F(1)] * len(parts))
            fac = ex * area / emap[k]["L"]
            Nlo[k], Nhi[k] = min(fac * a_, fac * b_), max(fac * a_, fac * b_)
    A0 = ZE.matrix(parts, n)
    gparts, cterms, cqd = [], [], {}
    Elo = (1 - T) * ex
    for k, (i, j) in enumerate(elems, 1):
        L = emap[k]["L"]
        c_, s_ = (nodes[j][0] - nodes[i][0]) / L, (nodes[j][1] - nodes[i][1]) / L
        Gloc = [[F(v) / (30 * L) for v in r] for r in [[36, 3 * L, -36, 3 * L], [3 * L, 4 * L * L, -3 * L, -L * L],
                                                        [-36, -3 * L, 36, -3 * L], [3 * L, -L * L, -3 * L, 4 * L * L]]]
        Bloc = [[F(v) / L for v in r] for r in [[1, 0, -1, 0], [0, 0, 0, 0], [-1, 0, 1, 0], [0, 0, 0, 0]]]
        Qloc = [[Gloc[a][b] - Bloc[a][b] for b in range(4)] for a in range(4)]
        Gt = [(d, _glob(i, j, c_, s_, dof, l)) for d, l in _psd_terms(Gloc)]
        Gt = [(d, g) for d, g in Gt if g]
        mid = (Nlo.get(k, F(0)) + Nhi.get(k, F(0))) / 2
        rad = (Nhi.get(k, F(0)) - Nlo.get(k, F(0))) / 2
        for d, g in Gt:
            items = list(g.items())
            for a, ga in items:
                for b, gb in items:
                    if a >= b:
                        A0[(a, b)] = A0.get((a, b), F(0)) + mid * d * ga * gb
        if rad and Gt:
            gparts.append({"t": rad, "terms": Gt})
        P = max(F(0), -Nlo.get(k, F(0)))
        kk = L * L / (4 * PI2_LO * Elo * izz)
        if P * kk >= 1:
            return {"verdict": "OPEN", "why": f"element {k} could buckle between its nodes: subdivide", "checks": []}
        cq = max(P * P * kk / (1 - P * kk), max(F(0), Nhi.get(k, F(0))))
        cqd[k] = cq
        if cq:
            for d, l in _psd_terms(Qloc):
                g = _glob(i, j, c_, s_, dof, l)
                if g:
                    cterms.append((cq * d, g))
    # outputs per checked element: N = E p (A/L) a.u, M_I, M_J = E p (I/L)(+-b + 3c).u (top fibre: N/A + M/W);
    # and f.u (the energy bound for the end moments' continuum correction)
    es, items = [], []
    def vec(g):
        e = [F(0)] * n
        for i_, v in g.items():
            e[i_] = v
        return e
    for kchk, lim in checks:
        m = emap[kchk]
        es.append(vec({i_: area / m["L"] * v for i_, v in m["a"].items()})); items.append((kchk, "N"))
        for end, sb in (("I", 1), ("J", -1)):
            g = {}
            for i_, v in m["b"].items():
                g[i_] = g.get(i_, F(0)) + izz / m["L"] * v
            for i_, v in m["c"].items():
                g[i_] = g.get(i_, F(0)) + izz / m["L"] * 3 * sb * v
            es.append(vec(g)); items.append((kchk, end))
    for (nd, d) in disp:                              # nodal displacements (second order, the continuum frame)
        es.append(vec({dof[(nd, d)]: F(1)})); items.append((("U", nd, d), "U"))
    es.append(list(f)); items.append((None, "f"))
    rs = ZE.certify_general_many(A0, parts + gparts, cterms, f, es, n)
    theta = rs[0]["theta"]
    # TRANSVERSE MEMBER LOADS in second order (2026-11-01, v2): inside a member the load couples to the nodal motion
    # through the condensed inner field — a load correction g with |g.d| <= sum_e ||d||_{C_e} r_e,
    #   r_e^2 = sup_eta (int q eta)^2 / a(eta, eta) <= q^2 L^5 / (720 E I (1 - P k))   (eta, eta' = 0 at both ends;
    #   L^5/720: the clamped beam's compliance under a uniform load; a(eta) >= (1 - P k) E I |eta''|^2, Poincare);
    # its response on any output: |e.u_g| <= ||y||_C R <= sqrt(theta) ||y||_A0 /(1 - theta) R, R = sqrt(sum r_e^2)
    Elo2 = (1 - T) * ex
    re2 = {}
    for k, (a_, w_, L_) in qd.items():
        if w_:
            P_ = max(F(0), -Nlo.get(k, F(0)))
            kk_ = L_ * L_ / (4 * PI2_LO * Elo2 * izz)
            re2[k] = w_ * w_ * L_ ** 5 / (720 * Elo2 * izz * (1 - P_ * kk_))
    Rq = ZE._sqrt_up(sum(re2.values())) if re2 else F(0)
    if Rq:
        sth = ZE._sqrt_up(theta)
        for r in rs:
            extra = sth * (r["ny_t"] + r["ey"]) / (1 - theta) * Rq
            r["lo"] -= extra
            r["hi"] += extra
    dranges = {key: (r["lo"], r["hi"]) for (key, what), r in zip(items, rs) if what == "U"}
    fu_hi = rs[-1]["hi"]
    unC = ZE._sqrt_up(theta * max(fu_hi, F(0)) / (1 - theta))     # ||u||_C <= sqrt(theta) ||u||_A0, A >= (1-theta)A0
    rng = {}
    for (kchk, what), r in zip(items, rs):
        if kchk is not None and what != "U":
            rng[(kchk, what)] = (min(ex * (1 - T) * r["lo"], ex * (1 + T) * r["lo"]),
                                 max(ex * (1 - T) * r["hi"], ex * (1 + T) * r["hi"]))
    W = izz / (h / 2) if h else None
    out = []
    for kchk, lim in checks:
        L = emap[kchk]["L"]
        Nl, Nh = rng[(kchk, "N")]
        cth = ZE._sqrt_up(cqd.get(kchk, F(0)) * 4 * L / 30)
        corr = cth * unC                                          # |e_theta' D_e u| <= sqrt(C_e,thth) ||u||_C
        if kchk in re2:                                           # the member load's own end-moment correction
            corr += cth * ZE._sqrt_up(re2[kchk])
        mb = -qd[kchk][1] * L * L / 12 if kchk in qd else F(0)     # the P = 0 inner solution's end moment (both ends)
        Ml = {e_: (rng[(kchk, e_)][0] + mb - corr, rng[(kchk, e_)][1] + mb + corr) for e_ in ("I", "J")}
        mend = max(max(abs(a_), abs(b_)) for a_, b_ in Ml.values())
        # interior: M'' + k^2 M = 0 in a compressed member (k^2 = P/EI); max |M| <= m (1 + psi)/(2 cos^2 phi),
        # phi = kL/2, and NO interior maximum when psi <= cos(2 phi) (>= 1 - 2 phi^2); in tension none at all
        P = max(F(0), -Nl)
        interior = "none (tension)" if P == 0 else None
        mint = mend
        wq = qd[kchk][1] if kchk in qd else F(0)
        if wq:
            # a transversely loaded member: M = M_lin + m, m'' +- k^2 m = -q -+ k^2 M_lin, m = 0 at the ends; the
            # Dirichlet Green function is positive, its integral <= (L^2/8)/(1 - k^2 L^2/8) in compression
            # (sec phi - 1 <= (phi^2/2)/(1 - phi^2/2)), <= L^2/8 in tension
            if P:
                k2 = P / ((1 - T) * ex * izz)
                if k2 * L * L / 8 >= 1:
                    return {"verdict": "OPEN", "why": f"element {kchk}: too slender between its nodes (subdivide)",
                            "checks": []}
                mint = mend + (abs(wq) + k2 * mend) * (L * L / 8) / (1 - k2 * L * L / 8)
            if Nh > 0:                                          # tension possible too (a range through zero: both)
                kt = Nh / ((1 - T) * ex * izz)
                mint = max(mint, mend + (abs(wq) + kt * mend) * L * L / 8)
            interior = "bounded (member load: the Dirichlet Green function's bound)"
        elif P:
            phi2 = L * L * P / (4 * (1 - T) * ex * izz)
            (al, ah), (bl, bh) = Ml["I"], Ml["J"]
            if (al > 0 and bh < 0) or (ah < 0 and bl > 0):
                psi = F(0)                                         # opposite signs: psi <= 0
            elif (al > 0 and bl > 0) or (ah < 0 and bh < 0):
                A_ = (min(abs(al), abs(ah)), max(abs(al), abs(ah)))
                B_ = (min(abs(bl), abs(bh)), max(abs(bl), abs(bh)))
                psi = min(F(1), min(A_[1], B_[1]) / max(A_[0], B_[0]))
            else:
                psi = F(1)
            if psi <= 1 - 2 * phi2:
                interior = "none (psi <= cos 2phi)"
            elif phi2 < 2:
                c_lo = 1 - phi2 / 2                         # cos phi >= 1 - phi^2/2
                b1 = mend * (1 + psi) / (2 * c_lo * c_lo)
                # tighter: an interior extremum of A cos + B sin is sqrt(A^2 + B^2), A = (M0 + ML)/(2 cos phi),
                # B = (ML - M0)/(2 sin phi); sin phi >= phi (1 - phi^2/6) with phi from below
                ph_lo = _sqrt_down(phi2)
                s_lo = ph_lo * (1 - ph_lo * ph_lo / 6)
                (al, ah), (bl, bh) = Ml["I"], Ml["J"]
                msum = max(abs(al + bl), abs(ah + bh), abs(al + bh), abs(ah + bl))
                mdif = max(abs(bh - al), abs(ah - bl))
                b2 = ZE._sqrt_up((msum / (2 * c_lo)) ** 2 + (mdif / (2 * s_lo)) ** 2) if s_lo > 0 else b1
                mint = max(mend, min(b1, b2))
                interior = "bounded (beam-column: min of m(1+psi)/(2cos^2 phi) and sqrt(A^2 + B^2))"
            else:
                return {"verdict": "OPEN", "why": f"element {kchk}: too slender between its nodes (subdivide)",
                        "checks": []}
        if _MUTANT.get("ends_only"):                   # sabotage: the old "ends only, Hermite moments" check
            mint = max(max(abs(a_ + corr), abs(b_ - corr)) for a_, b_ in Ml.values())
        hi_abs = max(abs(Nl), abs(Nh)) / area + mint / W
        # REFUTED: an end fibre beyond the limit for every point of the box (independent intervals: safe)
        bad = False
        for e_ in ("I", "J"):
            ml, mh = Ml[e_]
            top = (Nl / area + ml / W, Nh / area + mh / W)
            bot = (Nl / area - mh / W, Nh / area - ml / W)
            bad |= any(lo_ > lim or hi_ < -lim for lo_, hi_ in (top, bot))
        out.append({"check": f"|SIG({kchk})| <= {lim}", "sigma_abs_max": _show(hi_abs, 1),
                    "N_range": [_show(Nl, -1), _show(Nh, 1)],
                    "M_ends": {e_: [_show(a_, -1), _show(b_, 1)] for e_, (a_, b_) in Ml.items()},
                    "end_moment_correction": _show(corr, 1), "interior": interior, "theta": _show(theta, 1),
                    "verdict": "EARNED" if hi_abs <= lim else "REFUTED" if bad else "OPEN"})
    vs = [r["verdict"] for r in out]
    return {"verdict": "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN",
            "checks": out, "alpha_cr_proved_lower": _show(lam, -1) if lam else None, "disp": dranges}


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
            peak = max(max(max(abs(F(x.split()[0])) for x in fb["proved_range"]) for fb in row["fibres"]),
                       F(row.get("peak_along_element", "0").split()[0]))
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
    verdict_en = "REFUTED" if "REFUTED" in vs else "EARNED" if all(v == "EARNED" for v in vs) else "OPEN"
    # THE PHYSICAL VERDICT (the curator's "(а)", 2026-11-01): second-order theory itself, proved
    phys = []
    for sg in signs:
        deck = with_imperfection(text, phi, sg) if sg else text
        try:
            pc = second_order_case(deck, tol, checks, jobs=jobs)
        except (ArithmeticError, FrameError) as ex_:
            pc = {"verdict": "OPEN", "why": str(ex_), "checks": []}
        pc["imperfection"] = f"{'+' if sg > 0 else '-' if sg < 0 else ''}{phi if sg else 0}"
        phys.append(pc)
    pv = [c["verdict"] for c in phys]
    verdict = "REFUTED" if "REFUTED" in pv else "EARNED" if all(v == "EARNED" for v in pv) else "OPEN"
    return {**SCOPE_BEAM, "verdict": verdict, "verdict_en_method": verdict_en, "second_order_cases": phys,
            "verdict_note": "verdict: second-order theory (axial forces from the first-order analysis, a named "
                            "premise), every member the Euler-Bernoulli continuum, proved by ZTL "
                            "zenergy.certify_general; verdict_en_method: EN 5.2.2(5B)'s amplification (the code's "
                            "approximation), the 'cases' below",
            "path": "member stresses: zenergy.certify_scaled on every extreme fibre; EN global "
            "analysis: sway imperfection +-phi and second order by the proved alpha_cr", "cases": cases,
            "second_order_note": "EN 5.2.2(5B)'s amplification is the CODE's approximation of second-order theory: "
                                 "MEASURED 2026-11-01 (12x6 frame, loads x5/x10/x12) it falls short of linear P-delta "
                                 "in 6 of 156 members by up to 0.6/1.4/1.8 % — compliant with EN, not a physical "
                                 "second-order bound",
            "not_checked": "member buckling (use --buckling), 6.3.3 interaction"}


def members(text):
    """MEMBERS for EN's member checks: maximal chains of collinear elements whose inner nodes join exactly two
    elements and carry no support (an element alone is a member). [(element ids in order)]."""
    nodes, elems, loads, supports, ex, sec = read_deck(text)
    at = {}
    for k, (i, j) in enumerate(elems, 1):
        at.setdefault(i, []).append(k)
        at.setdefault(j, []).append(k)
    sup = {n for (n, _) in supports}
    def inner(n):
        if n in sup or len(at[n]) != 2:
            return False
        (i1, j1), (i2, j2) = (elems[at[n][0] - 1], elems[at[n][1] - 1])
        a = [p for p in (i1, j1) if p != n][0]
        b = [p for p in (i2, j2) if p != n][0]
        (xa, ya), (xn, yn), (xb, yb) = nodes[a], nodes[n], nodes[b]
        return (xn - xa) * (yb - yn) - (yn - ya) * (xb - xn) == 0 and (xn - xa) * (xb - xn) + (yn - ya) * (yb - yn) > 0
    seen, out = set(), []
    for k in range(1, len(elems) + 1):
        if k in seen:
            continue
        chain = [k]
        seen.add(k)
        for direction in (0, 1):
            cur = k
            end = elems[k - 1][1 - direction] if direction == 0 else elems[k - 1][0]
            end = elems[k - 1][1] if direction == 0 else elems[k - 1][0]
            while inner(end):
                nxt = [e for e in at[end] if e != cur][0]
                if nxt in seen:
                    break
                seen.add(nxt)
                chain = chain + [nxt] if direction == 0 else [nxt] + chain
                i2, j2 = elems[nxt - 1]
                end = j2 if i2 == end else i2
                cur = nxt
        out.append(chain)
    return out


def _cmy_upper(ends):
    """An upper bound on EN 1993-1-1 Table B.3's C_my for a member of ONE element (the moment linear between its
    ends), from the proved end-moment ranges [[lo, hi] at I, [lo, hi] at J] (same-sign = single curvature):
    max(0.9, 0.6 + 0.4 psi_max) — 0.9 covers a sway buckling mode. psi_max <= 0 when the ends are proved of opposite
    sign; else psi = |small|/|large| <= min(the highs)/max(the lows), at most 1. Anything unproved: 1."""
    if not ends or len(ends) != 2:
        return F(1)
    (al, ah), (bl, bh) = ends
    if (al > 0 and bh < 0) or (ah < 0 and bl > 0):
        psi = F(0)
    elif (al > 0 and bl > 0) or (ah < 0 and bh < 0):
        A = (min(abs(al), abs(ah)), max(abs(al), abs(ah)))
        B = (min(abs(bl), abs(bh)), max(abs(bl), abs(bh)))
        psi = min(F(1), min(A[1], B[1]) / max(A[0], B[0]))
    else:
        psi = F(1)
    return max(F(9, 10), F(3, 5) + F(2, 5) * psi)


def judge_interaction_case(text, tol, fy, curve, gamma_m1=F(1), jobs=1):
    """EN 1993-1-1 6.3.3, formula (6.61), Annex B (Method 2), IN-PLANE, for every compressed member (one load case).
    ASSUMED (said in the output): the member is restrained out of plane (no flexural buckling about z, no
    lateral-torsional buckling: chi_z = chi_LT = 1 — then (6.62) is milder than (6.61)); the section is class 1-3, its
    resistance taken ELASTIC (M_Rk = W_el fy, W_el = I/(h/2): safe for class 1-2). Bounds, each proved over the box:
      n = N_Ed/(chi_y N_Rk/gamma_M1) <= gamma_M1/H  (H = alpha_cr g(lb) as in judge_buckling, N_cr = alpha_cr N_Ed);
      k_yy <= C_my (1 + 0.6 n)  (Table B.1's cap); C_my: one-element members from the proved end-moment signs and
      ratio (_cmy_upper, >= 0.9 for a sway mode), longer members 1 (Table B.3's largest);
      M_y,Ed <= the largest proved |M| at the member's element ends (nodal loads: the moment is linear in each element).
    EARNED when n + k_yy M gamma_M1/M_Rk <= 1; OPEN otherwise (no refutation)."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    nodes, elems, loads, supports, ex, (area, izz) = read_deck(text)
    if curve not in CURVES:
        raise FrameError(f"{curve!r}: a buckling curve is one of {', '.join(CURVES)}")
    a = CURVES[curve]
    _curve_premises(a)
    ctx = energy_system_full(text, tol)
    parts, f, dof, emap, (_, _, _, h) = ctx
    if h is None:
        raise FrameError("the interaction check needs the section height: R, 1, area, izz, height")
    n = len(dof)
    st = stability_lower(text, tol, jobs=jobs)
    lam = st.get("lam_low")
    if st.get("lam_est") is None or lam is None:
        return {"verdict": "EARNED", "why": "no compressed member under these loads", "members": []}
    # end moments M = E p (I/L)(+-b + 3c).u at both ends of every element: scaled outputs, all at once
    es, keys = [], []
    for k in emap:
        m = emap[k]
        for end, sb in (("I", 1), ("J", -1)):
            g = {}
            for i, v in m["b"].items():
                g[i] = g.get(i, F(0)) + izz / m["L"] * v
            for i, v in m["c"].items():
                g[i] = g.get(i, F(0)) + izz / m["L"] * 3 * sb * v
            e = [F(0)] * n
            for i, v in g.items():
                e[i] = v
            if any(e):
                es.append(e)
                keys.append(k)
    rs = ZE.certify_many(parts, f, es, n, jobs=jobs, scale=[emap[k]["part"] for k in keys])
    Mmax, Mend = {}, {}
    qd = read_qloads(text)
    Wel_ = izz / (h / 2)
    for k, r in zip(keys, rs):
        end = "I" if len(Mend.get(k, [])) == 0 else "J"
        bub = _bubble(qd, k, end, "TOP", area, izz, h)[0] * Wel_ if k in qd else F(0)
        if k in qd:                                     # the bending part only: the axial part is not a moment
            a_, w_, L_ = qd[k]
            bub -= a_ * L_ * (1 if end == "I" else -1) / (2 * area) * Wel_
        Mend.setdefault(k, []).append(sorted([ex * r["lo"] + bub, ex * r["hi"] + bub]))
    for k in Mend:
        if len(Mend[k]) == 2:
            kap = _bubble(qd, k, "I", "TOP", area, izz, h)[1] * Wel_ if k in qd else F(0)
            Mmax[k] = _side_peak(Mend[k][0], Mend[k][1], kap)
        else:
            Mmax[k] = max(max(abs(x) for x in m_) for m_ in Mend[k])
    Wel = izz / (h / 2)
    MRk = Wel * fy
    rows = []
    for mem in members(text):
        nlo = min(st["Nlo"].get(k, F(0)) for k in mem)
        if nlo >= 0:
            continue
        N = -nlo
        lb_lo = _sqrt_down(area * fy / (lam * N))
        H = lam * _g_lower(lb_lo, a)
        if H <= 0:
            rows.append({"member": mem, "verdict": "OPEN", "why": "no positive buckling resistance proved"})
            continue
        nn = gamma_m1 / H
        M = max(Mmax.get(k, F(0)) for k in mem)
        Cmy = _cmy_upper(Mend.get(mem[0])) if len(mem) == 1 and not any(k in qd for k in mem) else F(1)
        kyy = Cmy * (1 + F(3, 5) * nn)
        U = nn + kyy * M * gamma_m1 / MRk
        rows.append({"member": mem, "N_Ed_max": _show(N, 1), "M_Ed_max": _show(M, 1), "n_max": _show(nn, 1),
                     "C_my": _show(Cmy, 1),
                     "k_yy_max": _show(kyy, 1), "utilisation_max": _show(U, 1),
                     "verdict": "EARNED" if U <= 1 else "OPEN"})
    vs = [r["verdict"] for r in rows]
    return {"verdict": "EARNED" if all(v == "EARNED" for v in vs) else "OPEN", "members": rows,
            "alpha_cr_proved_lower": _show(lam, -1)}


def judge_interaction(text, tol, fy, curve, gamma_m1=F(1), jobs=1, phi=None):
    """judge_interaction_case on EN's global-analysis load cases (sway imperfection +-phi, both ways)."""
    phi = PHI0 if phi is None else phi
    signs = [1, -1] if with_imperfection(text, phi, 1) != text else [0]
    cases = []
    for sg in signs:
        r = judge_interaction_case(with_imperfection(text, phi, sg) if sg else text, tol, fy, curve, gamma_m1, jobs)
        r["imperfection"] = f"{'+' if sg > 0 else '-' if sg < 0 else ''}{phi if sg else 0}"
        cases.append(r)
    vs = [c["verdict"] for c in cases]
    return {**SCOPE_BEAM, "verdict": "EARNED" if all(v == "EARNED" for v in vs) else "OPEN",
            "path": "EN 1993-1-1 6.3.3 (6.61), Annex B, in-plane; N_cr,i = alpha_cr N_Ed,i; first-order moments with "
                    "the sway imperfection", "cases": cases,
            "assumed": "members restrained out of plane (chi_z = chi_LT = 1); section class 1-3 with ELASTIC "
                       "resistance; C_my from the proved end moments (>= 0.9, sway), 1 for multi-element members",
            "not_checked": "out-of-plane and lateral-torsional buckling (need out-of-plane data); class 4 sections"}


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
        inner = F(0)
        for side in ("TOP", "BOT"):
            A_ = next(r for r in fr if r["end"] == "I" and r["side"] == side)
            B_ = next(r for r in fr if r["end"] == "J" and r["side"] == side)
            inner = max(inner, _side_peak((A_["lo"], A_["hi"]), (B_["lo"], B_["hi"]), A_["kappa"]))
        ok = ok and inner <= lim
        row = {"check": f"|SIG({k})| <= {lim}", "fibres": [{"end": r["end"], "side": r["side"],
               "nominal": _show(r["nominal"]), "proved_range": [_show(r["lo"], -1), _show(r["hi"], 1)]} for r in fr],
               "peak_along_element": _show(inner, 1)}
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
                lo_, hi_ = sorted([ex * ps[pk] * wl + worst["bub"], ex * ps[pk] * wh + worst["bub"]])
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
            row["_vertex"] = ps
            row["verdict"] = "REFUTED" if ((wl > v) if up else (wh < v)) else "OPEN"
        rows.append(row)
    vs = [r["verdict"] for r in rows]
    verdict1 = "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN"
    # THE PHYSICAL VERDICT (2026-11-01): the displacements in second-order theory (axial forces of the first-order
    # analysis, a named premise), every member the Euler-Bernoulli continuum — compression makes them LARGER than
    # first order says. No imperfection here (the deck's loads as given).
    try:
        so = second_order_case(text, tol, [], disp=[(nd, d) for (nd, d, op, v) in requirements])
    except (ArithmeticError, FrameError) as ex_:
        so = {"verdict": "OPEN", "why": str(ex_), "disp": {}}
    pv = []
    for row, (nd, d, op, v) in zip(rows, requirements):
        rr = so.get("disp", {}).get(("U", nd, d))
        if rr is None:
            row["second_order"] = {"verdict": "OPEN", "why": so.get("why", "not proved")}
            pv.append("OPEN")
            continue
        lo2, hi2 = rr
        vv = "EARNED" if ((hi2 <= v) if op == "<=" else (lo2 >= v)) else \
            "REFUTED" if ((lo2 > v) if op == "<=" else (hi2 < v)) else "OPEN"
        row["second_order"] = {"proved_range": [_show(lo2, -1), _show(hi2, 1)], "verdict": vv}
        if vv == "OPEN" and row.get("_vertex") is not None:
            # the physical WITNESS: the first-order vertex p, second order there with D in [0, C] unknown
            try:
                sw = second_order_case(text, tol, [], disp=[(nd, d)], at=row["_vertex"])
                wr = sw.get("disp", {}).get(("U", nd, d))
            except (ArithmeticError, FrameError):
                wr = None
            if wr is not None:
                wl2, wh2 = wr
                row["second_order"]["witness_range"] = [_show(wl2, -1), _show(wh2, 1)]
                if (wl2 > v) if op == "<=" else (wh2 < v):
                    vv = "REFUTED"
                    row["second_order"]["verdict"] = vv
        pv.append(vv)
    verdict = "REFUTED" if "REFUTED" in pv else "EARNED" if all(x == "EARNED" for x in pv) else "OPEN"
    for row in rows:
        row.pop("_vertex", None)
    return {**SCOPE_BEAM, "verdict": verdict, "verdict_first_order": verdict1,
            "verdict_note": "verdict: second-order theory of the continuum frame (ZTL zenergy.certify_general); "
                            "verdict_first_order: first-order (each row's proved_range)",
            "path": "energy norm (ZTL zenergy): first order exact + a proved rest",
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
        if "--interaction" in argv:                   # EN 6.3.3 (6.61), in-plane: --interaction fy curve [gamma_M1]
            i = argv.index("--interaction")
            fy = _num(argv[i + 1], "fy")
            curve = argv[i + 2]
            gm1 = _num(argv[i + 3], "gamma_M1") if len(argv) > i + 3 and not argv[i + 3].startswith("--") else F(1)
            jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
            print(json.dumps(judge_interaction(text, tol, fy, curve, gm1, jobs=jobs), indent=1, ensure_ascii=False))
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
