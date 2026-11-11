# -*- coding: utf-8 -*-
"""
alfeld — the Alfeld-split stress element on ANY tetrahedron, by the double Piola map (2026-11-10, CAD/FEA level 2b).

kuhn_split.py builds the element (piecewise-linear symmetric divergence-free stresses on the 4 barycentric sub-tets,
normal traction continuous inside, linear on the outer faces; dimension 30; the outer trace a bijection onto the
BALANCED linear face tractions) with sympy for the 6 Kuhn shapes. A CAD mesh has a different shape per tet. Here the
element is built ONCE on the reference tet P^ = (0, e1, e2, e3) and carried to a tet P = B P^ + b by
    tau(x) = (1 / det B) B s^(x^) B^T          (symmetric; div tau = (1/det B) B div^ s^ = 0)
— CHECKED exactly onto the directly built element on 20 random tets (research/cad/alfeld_piola_check.py).

FACE DATA (as kuhn_split): face f is opposite local vertex f, its vertices sorted, n2 its OUTWARD area normal
(|n2| = twice the area); g = 36 numbers, for f = 0..3, for its vertices in order, tau(p_v) n2 (x, y, z).
Under the map the outward area normal is n2 = |det B| B^-T n2^, so tau n2 = sign(det B) B s^ n2^:
    the reference face data  g^ = sign(det B) B^-1 g  (each vertex's 3-vector).
ENERGY: int_T tau:tau dx = (1/|det B|) int_T^ |B s^ B^T|^2 dx^, and the same for (tr tau)^2 — s^ linear on each
reference sub-tet, the integrand of degree 2: EXACT with the rational rule on a tet of volume V,
    int f = V [ -(1/20) sum_vertices f + (1/5) sum_edge-midpoints f ]       (exact for degree <= 2).
BALANCE (physical, as kuhn_split): force (1/6) sum g; moment about the origin (1/24) sum_ij (1 + d_ij) x_i x g_j over
each face's vertices i, j. An element stress exists for g iff g is balanced.
"""
from __future__ import annotations

import json
import os
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "alfeld_ref.json")
VO = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]


def build_on(P):
    """sympy: the element on the tet with vertices P (4 sympy 3-vectors). -> dict with R (96 x 36: face data ->
    coefficients, valid for balanced g), faces, BAL (6 x 36), S1, S2 (36 x 36: int tau:tau, int (tr tau)^2)."""
    import sympy as sp
    from sympy.polys.matrices import DomainMatrix
    x, y, z = sp.symbols("x y z")
    X = (x, y, z)
    s_, t_ = sp.symbols("s t")
    bc = (P[0] + P[1] + P[2] + P[3]) / 4
    mons = [sp.Integer(1), x, y, z]
    cs = sp.symbols("c0:96")
    Ts = []
    for si in range(4):
        T = sp.zeros(3, 3)
        for p, (i, j) in enumerate(VO):
            ex = sum(cs[(si * 6 + p) * 4 + m] * mons[m] for m in range(4))
            T[i, j] = ex
            T[j, i] = ex
        Ts.append(T)
    eqs = []
    for T in Ts:
        for i in range(3):
            d = sp.expand(sum(sp.diff(T[i, j], X[j]) for j in range(3)))
            if d != 0:
                eqs.append(d)
    for f in range(4):
        for g in range(f + 1, 4):
            v1, v2 = [v for v in range(4) if v not in (f, g)]
            A, B, C = bc, P[v1], P[v2]
            n = (B - A).cross(C - A)
            pt = A + s_ * (B - A) + t_ * (C - A)
            d = (Ts[f] * n - Ts[g] * n).subs({x: pt[0], y: pt[1], z: pt[2]})
            for i in range(3):
                ex = sp.expand(d[i])
                if ex != 0:
                    eqs += sp.Poly(ex, s_, t_).coeffs()
    E = sp.Matrix([[sp.diff(q, cc) for cc in cs] for q in eqs])
    N = DomainMatrix.from_Matrix(E).convert_to(sp.QQ).nullspace().to_Matrix().T
    faces, trace = [], []
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        A, B, C = (P[v] for v in vs)
        n2 = (B - A).cross(C - A)
        if n2.dot(P[f] - A) > 0:
            n2 = -n2
        faces.append({"verts": vs, "n2": [sp.Rational(q) for q in n2]})
        for v in vs:
            tv = (Ts[f] * n2).subs({x: P[v][0], y: P[v][1], z: P[v][2]})
            for i in range(3):
                trace.append(sp.expand(tv[i]))
    Tm = sp.Matrix([[sp.diff(q, cc) for cc in cs] for q in trace])
    TN = Tm * N
    assert N.shape[1] == 30 and DomainMatrix.from_Matrix(TN).convert_to(sp.QQ).rank() == 30
    L = (TN.T * TN).inv() * TN.T
    R = N * L
    BAL = sp.zeros(6, 36)
    for f in range(4):
        vs = faces[f]["verts"]
        for jv, v in enumerate(vs):
            for comp in range(3):
                col = f * 9 + jv * 3 + comp
                BAL[comp, col] += sp.Rational(1, 6)
                gg = sp.zeros(3, 1)
                gg[comp] = 1
                for iv, w in enumerate(vs):
                    BAL[3:6, col] += sp.Rational(1 + (iv == jv), 24) * P[w].cross(gg)
    assert (BAL * TN).is_zero_matrix

    def integ(expr, V0, V1, V2, V3):
        u, v, w = sp.symbols("u v w")
        J = sp.Matrix.hstack(V1 - V0, V2 - V0, V3 - V0)
        pt = V0 + J * sp.Matrix([u, v, w])
        ex = sp.expand(expr.subs({x: pt[0], y: pt[1], z: pt[2]}))
        val = sp.integrate(sp.integrate(sp.integrate(ex, (w, 0, 1 - u - v)), (v, 0, 1 - u)), (u, 0, 1))
        return val * abs(J.det())
    q1, q2 = sp.zeros(96, 96), sp.zeros(96, 96)
    for si in range(4):
        vs = [v for v in range(4) if v != si]
        T = Ts[si]
        tt = sum(T[i, j] ** 2 for i in range(3) for j in range(3))
        tr2 = (T[0, 0] + T[1, 1] + T[2, 2]) ** 2
        for form, Q in ((tt, q1), (tr2, q2)):
            val = integ(form, bc, P[vs[0]], P[vs[1]], P[vs[2]])
            poly = sp.Poly(sp.expand(val), *cs)
            for mon, coef in zip(poly.monoms(), poly.coeffs()):
                idx = [k for k, pw in enumerate(mon) for _ in range(pw)]
                if len(idx) == 2:
                    i, j = idx
                    if i == j:
                        Q[i, i] += coef
                    else:
                        Q[i, j] += coef / 2
                        Q[j, i] += coef / 2
    return {"R": R, "faces": faces, "BAL": BAL, "S1": R.T * q1 * R, "S2": R.T * q2 * R}


# ------------------------------------------------------------------------------------------------ the reference
def _quad_points():
    """For each reference sub-tet (barycentre + the face opposite vertex si): its 10 points (4 vertices, 6 edge
    midpoints) and rational weights (-1/20, 1/5); the sub-tet volume is 1/24."""
    P = [(Fr(0), Fr(0), Fr(0)), (Fr(1), Fr(0), Fr(0)), (Fr(0), Fr(1), Fr(0)), (Fr(0), Fr(0), Fr(1))]
    bc = tuple(sum(p[k] for p in P) / 4 for k in range(3))
    out = []
    for si in range(4):
        V = [bc] + [P[v] for v in range(4) if v != si]
        pts = [(v, Fr(-1, 20)) for v in V]
        for a in range(4):
            for b in range(a + 1, 4):
                pts.append((tuple((V[a][k] + V[b][k]) / 2 for k in range(3)), Fr(1, 5)))
        out.append(pts)
    return out


def reference():
    """-> {"R": 96 x 36 Fractions, "faces": [...], "EVAL": [4 sub-tets][10 points] -> (weight, 6 x 36 Fractions:
    the stress components VO at that point as a linear map of the reference face data)}. Cached as JSON."""
    if os.path.exists(CACHE):
        raw = json.load(open(CACHE))
        R = [[Fr(v) for v in row] for row in raw["R"]]
        faces = raw["faces"]
    else:
        import sympy as sp
        e = [sp.Matrix([1 if q == a else 0 for q in range(3)]) for a in range(3)]
        d = build_on([sp.zeros(3, 1), e[0], e[1], e[2]])
        R = [[Fr(str(d["R"][i, j])) for j in range(36)] for i in range(96)]
        faces = [{"verts": f["verts"], "n2": [str(q) for q in f["n2"]]} for f in d["faces"]]
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump({"R": [[str(v) for v in row] for row in R], "faces": faces}, open(CACHE, "w"))
    ev = []
    for si, pts in enumerate(_quad_points()):
        rows = []
        for (px, py, pz), w in pts:
            mon = (1, px, py, pz)
            M = [[sum(mon[m] * R[(si * 6 + p) * 4 + m][j] for m in range(4)) for j in range(36)] for p in range(6)]
            rows.append((w, M))
        ev.append(rows)
    return {"R": R, "faces": faces, "EVAL": ev}


_REF = None


def ref():
    global _REF
    if _REF is None:
        _REF = reference()
    return _REF


def _inv3(B):
    a, b, c = B[0]
    d, e, f = B[1]
    g, h, i = B[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    adj = [[e * i - f * h, c * h - b * i, b * f - c * e],
           [f * g - d * i, a * i - c * g, c * d - a * f],
           [d * h - e * g, b * g - a * h, a * e - b * d]]
    return det, [[adj[r][k] / det for k in range(3)] for r in range(3)]


def energy(P, g):
    """Exact: (int tau:tau, int (tr tau)^2) of the element stress with face data g (36 Fractions, BALANCED) on the tet
    P (4 points, Fractions), by the double Piola map from the reference."""
    r = ref()
    B = [[P[k + 1][row] - P[0][row] for k in range(3)] for row in range(3)]
    det, Bi = _inv3(B)
    sg = 1 if det > 0 else -1
    gh = []
    for vtx in range(12):
        gv = g[3 * vtx:3 * vtx + 3]
        gh += [sg * sum(Bi[a][b] * gv[b] for b in range(3)) for a in range(3)]
    tt = tr2 = Fr(0)
    for si in range(4):
        for w, M in r["EVAL"][si]:
            s = [sum(M[p][j] * gh[j] for j in range(36) if gh[j]) for p in range(6)]
            S = [[s[0], s[3], s[4]], [s[3], s[1], s[5]], [s[4], s[5], s[2]]]
            BS = [[sum(B[a][k] * S[k][l] for k in range(3)) for l in range(3)] for a in range(3)]
            T = [[sum(BS[a][l] * B[c][l] for l in range(3)) for c in range(3)] for a in range(3)]   # B S B^T
            tt += w * sum(T[a][c] * T[a][c] for a in range(3) for c in range(3))
            tr2 += w * (T[0][0] + T[1][1] + T[2][2]) ** 2
    scale = Fr(1, 24) / abs(det)
    return tt * scale, tr2 * scale


def balance(P, g):
    """(force, moment about the origin) of the face data g on the tet P — zero iff an element stress exists."""
    F = [Fr(0)] * 3
    Mo = [Fr(0)] * 3
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        for jv in range(3):
            gj = g[f * 9 + jv * 3:f * 9 + jv * 3 + 3]
            for c in range(3):
                F[c] += gj[c] / 6
            for iv, w in enumerate(vs):
                x = P[w]
                cr = (x[1] * gj[2] - x[2] * gj[1], x[2] * gj[0] - x[0] * gj[2], x[0] * gj[1] - x[1] * gj[0])
                k = Fr(1 + (iv == jv), 24)
                for c in range(3):
                    Mo[c] += k * cr[c]
    return F, Mo


# ------------------------------------------------------------------------------------------------ vectorised forms
_FREF = None


def _float_ref():
    """The reference element's quadrature maps as float arrays: W (40,), MQ (40, 6, 12, 3) — the stress components
    VO at each point as a linear map of the reference face data (12 vertex blocks x 3)."""
    global _FREF
    if _FREF is None:
        import numpy as np
        r = ref()
        W, MQ = [], []
        for si in range(4):
            for w, M in r["EVAL"][si]:
                W.append(float(w))
                MQ.append(np.array([[float(v) for v in row] for row in M]).reshape(6, 12, 3))
        _FREF = (np.array(W), np.stack(MQ))
    return _FREF


_HCONST = None


def _hconst():
    """H[p, p'] = sum_q w_q Mq[p]^T Mq[p'] (36 x 36 each): the quadrature folded once, in the REFERENCE face data."""
    global _HCONST
    if _HCONST is None:
        import numpy as np
        W, MQ = _float_ref()
        M = MQ.reshape(len(W), 6, 36)
        _HCONST = np.einsum("q,qpj,qrk->prjk", W, M, M)
    return _HCONST


def float_forms(P):
    """FLOAT element forms for many tets at once (only to CHOOSE the fluxes; the bound is evaluated exactly).
    P: (N, 4, 3). -> Q1, Q2 (N, 36, 36): int tau:tau and int (tr tau)^2 as quadratic forms of the face data g;
    BAL (N, 6, 36): force (1/6 sum g) and moment about the origin (1/24 sum (1 + d_ij) x_i x g_j).
    FAST FORM (2026-11-10): tau = B s^ B^T / det gives |tau|^2 = tr(S C S C) / det^2 and tr tau = tr(S C) / det with
    C = B^T B — the geometry enters through C only. So Q^_k = sum_pp' K_k(C)[p, p'] H[p, p'] with the quadrature
    folded into H once, and Q = sc G^T Q^ G, G = blockdiag(sign(det) B^-1)."""
    import numpy as np
    P = np.asarray(P, dtype=float)
    N = len(P)
    B = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=2)       # columns
    det = np.linalg.det(B)
    sBi = np.linalg.inv(B) * np.sign(det)[:, None, None]
    C = np.einsum("nki,nkj->nij", B, B)
    Eb = np.zeros((6, 3, 3))
    for p, (i, j) in enumerate(VO):
        Eb[p, i, j] = 1
        Eb[p, j, i] = 1
    EC = np.einsum("pij,njk->npik", Eb, C)                                               # E_p C
    K1 = np.einsum("npij,nqji->npq", EC, EC)                                             # tr(E_p C E_q C)
    t = np.einsum("npii->np", EC)                                                        # tr(E_p C)
    K2 = t[:, :, None] * t[:, None, :]
    H = _hconst().reshape(36, 1296)
    Q1h = (K1.reshape(N, 36) @ H).reshape(N, 12, 3, 12, 3)
    Q2h = (K2.reshape(N, 36) @ H).reshape(N, 12, 3, 12, 3)
    sc = (1 / 24) / np.abs(det)
    Q1 = np.einsum("nki,nvkwl,nlj->nviwj", sBi, Q1h, sBi).reshape(N, 36, 36) * sc[:, None, None]
    Q2 = np.einsum("nki,nvkwl,nlj->nviwj", sBi, Q2h, sBi).reshape(N, 36, 36) * sc[:, None, None]
    BAL = np.zeros((N, 6, 36))
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        for jv in range(3):
            for comp in range(3):
                col = f * 9 + jv * 3 + comp
                BAL[:, comp, col] = 1 / 6
                e = np.zeros(3)
                e[comp] = 1
                for iv, wv in enumerate(vs):
                    BAL[:, 3:, col] += (1 + (iv == jv)) / 24 * np.cross(P[:, wv], e)
    return Q1, Q2, BAL



def bal_matrix(P):
    """The exact 6 x 36 balance map of the tet P (rows: force x y z, moment about the origin x y z) — the same as
    `balance` column by column, built directly (2026-11-10: 36 calls of `balance` per tet were the finisher's cost)."""
    from fractions import Fraction as Fr
    A = [[Fr(0)] * 36 for _ in range(6)]
    sixth = Fr(1, 6)
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        for jv in range(3):
            # sum_iv (1 + d) / 24 * x_iv  (a weighted point), then  w x e_comp
            w = [sum(Fr(1 + (iv == jv), 24) * P[vv][k] for iv, vv in enumerate(vs)) for k in range(3)]
            base = f * 9 + jv * 3
            A[0][base] = A[1][base + 1] = A[2][base + 2] = sixth
            # w x e0 = (0, w2, -w1); w x e1 = (-w2, 0, w0); w x e2 = (w1, -w0, 0)
            A[4][base], A[5][base] = w[2], -w[1]
            A[3][base + 1], A[5][base + 1] = -w[2], w[0]
            A[3][base + 2], A[4][base + 2] = w[1], -w[0]
    return A


def energy_upper_ev(P, g, E, nu, return_terms=False):
    """A PROVED UPPER bound on sum over tets of the compliance energy (1/E)((1 + nu) int tau:tau - nu int (tr tau)^2),
    VECTORISED with errfloat (2026-11-10: the exact Fractions took > 35 min for 82k tets with 366-bit fluxes).
    P: (N, 4, 3) the exact coordinates (Fractions or decimals -> rounded once), g: (N, 36) the exact face data
    (Fractions -> rounded once). Same formulas as `energy`: the double Piola map, the rational degree-2 rule; every
    rounding carried by errfloat.Ev. E, nu: Fractions. -> float upper bound (and per-tet Ev if return_terms)."""
    import numpy as np
    from .errfloat import Ev
    Pv = np.array([[[float(c) for c in p] for p in tet] for tet in P])
    gv = np.array([[float(x) for x in row] for row in g])
    return energy_upper_ev_g(Pv, Ev.rounded(gv), E, nu, return_terms=return_terms)


def energy_upper_ev_g(Pv, ge, E, nu, return_terms=False):
    """energy_upper_ev with the face data given as an errfloat.Ev (level 3d, 2026-11-12): ge (N, 36) carries its own
    proved error, e.g. Ev.rounded(g_f) + Ev.exact(s) * Ev.rounded(g_p) for the combined field of the load f + s p —
    the error of the combination is carried, nothing is kept in Fractions. Pv (N, 4, 3): the exact coordinates
    rounded ONCE to binary64 (float(Fraction) is correctly rounded; Ev.rounded claims exactly that). The arithmetic is
    energy_upper_ev's, unchanged (energy_upper_ev calls this). -> float upper bound (and per-tet Ev if return_terms)."""
    import numpy as np
    from fractions import Fraction as Fr
    from .errfloat import Ev
    Pv = np.asarray(Pv, dtype=np.float64)
    Pe = Ev.rounded(Pv)
    B = [[Pe[:, k + 1, r] - Pe[:, 0, r] for k in range(3)] for r in range(3)]        # B[r][k] = column k, row r
    a = B
    adj = [[a[1][1] * a[2][2] - a[1][2] * a[2][1], a[0][2] * a[2][1] - a[0][1] * a[2][2], a[0][1] * a[1][2] - a[0][2] * a[1][1]],
           [a[1][2] * a[2][0] - a[1][0] * a[2][2], a[0][0] * a[2][2] - a[0][2] * a[2][0], a[0][2] * a[1][0] - a[0][0] * a[1][2]],
           [a[1][0] * a[2][1] - a[1][1] * a[2][0], a[0][1] * a[2][0] - a[0][0] * a[2][1], a[0][0] * a[1][1] - a[0][1] * a[1][0]]]
    det = a[0][0] * adj[0][0] + a[0][1] * adj[1][0] + a[0][2] * adj[2][0]
    if not (np.abs(det.v) > det.e).all():
        raise ZeroDivisionError("a tet whose determinant's sign is not certain")
    sg = np.sign(det.v)
    Bi = [[(adj[i][j] / det) * Ev.exact(sg) for j in range(3)] for i in range(3)]    # sign(det) B^-1
    # reference face data per vertex block
    gh = [None] * 36
    for vtx in range(12):
        for i in range(3):
            acc = Bi[i][0] * ge[:, 3 * vtx]
            acc = acc + Bi[i][1] * ge[:, 3 * vtx + 1]
            acc = acc + Bi[i][2] * ge[:, 3 * vtx + 2]
            gh[3 * vtx + i] = acc
    r = ref()
    tt = Ev.exact(np.zeros(len(Pv)))
    tr2 = Ev.exact(np.zeros(len(Pv)))
    for si in range(4):
        for w, M in r["EVAL"][si]:
            s = []
            for p in range(6):
                acc = None
                for j in range(36):
                    if M[p][j] == 0:
                        continue
                    term = gh[j] * Ev.rounded(float(M[p][j])) if Fr(float(M[p][j])) != M[p][j] else gh[j] * float(M[p][j])
                    acc = term if acc is None else acc + term
                s.append(acc if acc is not None else Ev.exact(np.zeros(len(Pv))))
            S = [[s[0], s[3], s[4]], [s[3], s[1], s[5]], [s[4], s[5], s[2]]]
            BS = [[B[aa][0] * S[0][l] + B[aa][1] * S[1][l] + B[aa][2] * S[2][l] for l in range(3)] for aa in range(3)]
            T = [[BS[aa][0] * B[c][0] + BS[aa][1] * B[c][1] + BS[aa][2] * B[c][2] for c in range(3)] for aa in range(3)]
            f1 = None
            for aa in range(3):
                for c in range(3):
                    t2 = T[aa][c].sq()
                    f1 = t2 if f1 is None else f1 + t2
            f2 = (T[0][0] + T[1][1] + T[2][2]).sq()
            wv = Ev.rounded(float(w)) if Fr(float(w)) != w else Ev.exact(float(w))
            tt = tt + wv * f1
            tr2 = tr2 + wv * f2
    absdet = Ev(np.abs(det.v), det.e)
    scale = Ev.rounded(1 / 24) / absdet
    Ef, nuf = Fr(E), Fr(nu)
    c1 = Ev.rounded(float((1 + nuf) / Ef)) if Fr(float((1 + nuf) / Ef)) != (1 + nuf) / Ef else Ev.exact(float((1 + nuf) / Ef))
    c2 = Ev.rounded(float(nuf / Ef)) if Fr(float(nuf / Ef)) != nuf / Ef else Ev.exact(float(nuf / Ef))
    per = (c1 * tt - c2 * tr2) * scale
    tot = per.sum()
    up = float(tot.upper())
    return (up, per) if return_terms else up


def moments(P, g):
    """INDEPENDENT exact check (tests only): (int_T tau_ij, int_T tau_ij x_k) of the element stress itself, by the
    sub-tet quadrature (10 points, exact to degree 2; tau is piecewise linear, tau x_k quadratic). The physical stress
    at a point is B S B^T / det (the double Piola map; energy() squares it, so its sign is moot there)."""
    r = ref()
    B = [[P[k + 1][row] - P[0][row] for k in range(3)] for row in range(3)]
    det, Bi = _inv3(B)
    sg = 1 if det > 0 else -1
    gh = []
    for vtx in range(12):
        gv = g[3 * vtx:3 * vtx + 3]
        gh += [sg * sum(Bi[a][b] * gv[b] for b in range(3)) for a in range(3)]
    m0 = [[Fr(0)] * 3 for _ in range(3)]
    m1 = [[[Fr(0)] * 3 for _ in range(3)] for _ in range(3)]
    for si, pts in enumerate(_quad_points()):
        for (w, M), (xi, _w2) in zip(r["EVAL"][si], pts):
            s = [sum(M[p][j] * gh[j] for j in range(36) if gh[j]) for p in range(6)]
            S = [[s[0], s[3], s[4]], [s[3], s[1], s[5]], [s[4], s[5], s[2]]]
            BS = [[sum(B[a][k] * S[k][l] for k in range(3)) for l in range(3)] for a in range(3)]
            T = [[sum(BS[a][l] * B[c][l] for l in range(3)) for c in range(3)] for a in range(3)]
            x = [P[0][k] + sum(B[k][q] * xi[q] for q in range(3)) for k in range(3)]
            for i in range(3):
                for j in range(3):
                    m0[i][j] += w * T[i][j]
                    for k in range(3):
                        m1[i][j][k] += w * T[i][j] * x[k]
    # weights sum to 1 per sub-tet; a sub-tet's physical volume is |det|/24; tau = T/|det| -> factor 1/24
    # the sign: tau = T / det (signed). MEASURED 2026-11-11: with T / |det| the zeroth moment disagreed with the
    # boundary formula exactly on a tet with det < 0 and agreed on one with det > 0
    return ([[sg * m0[i][j] / 24 for j in range(3)] for i in range(3)],
            [[[sg * m1[i][j][k] / 24 for k in range(3)] for j in range(3)] for i in range(3)])
