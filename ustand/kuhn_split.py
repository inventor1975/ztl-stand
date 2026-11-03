"""The ALFELD-split stress element on the six Kuhn tetrahedra (2026-11-03; DESIGN-3D.md, track 3, the exact lower
bound). On a tetrahedron split at its barycentre into 4 sub-tetrahedra, the symmetric stresses that are linear and
divergence-free on each sub-tetrahedron, with the normal traction continuous across the 6 inner faces and LINEAR on
the 4 outer faces, form a space of dimension 30, and the outer trace map is a bijection onto the balanced linear face
tractions (MEASURED by exact rank; asserted again here on every type). A single polynomial on the whole tetrahedron
reaches only 21 of the 30 at degree 1, 2 and 3.

Per Kuhn type (conduction3d.PERMS order; vertices p0 = 0, p1 = e_a, p2 = e_a + e_b, p3 = (1, 1, 1)), EXACT rationals:
  faces[f]  the outer face opposite local vertex f: its three local vertices (sorted) and its OUTWARD integer area
            normal n2 = (B - A) x (C - A) (|n2| = twice the area);
  g         the face data, 36 numbers: for f = 0..3, for its vertices in order, the vector tau(p_v) n2 (x, y, z);
  BAL       6 x 36: the tet's balance — force (1/6) sum g, moment about p0 (1/24) sum_ij (1 + delta_ij) x_i x g_j
            (a linear traction on a triangle); a stress of the element space has BAL g = 0;
  S1, S2    36 x 36: for balanced g, int tau:tau and int (tr tau)^2 over the tetrahedron of the unique element stress
            with that face data — the compliance energy (1/E)((1 + nu) S1 - nu S2).
Generated with sympy and cached as JSON beside this file (python3 -m ustand.kuhn_split rebuilds it)."""
from __future__ import annotations

import json
import os
import sys
from fractions import Fraction as F

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "kuhn_split.json")
VO = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]


def _build_type(perm):
    import sympy as sp
    x, y, z = sp.symbols("x y z")
    X = (x, y, z)
    s_, t_ = sp.symbols("s t")
    e = [sp.Matrix([1 if q == a else 0 for q in range(3)]) for a in range(3)]
    a, b, c = perm
    P = [sp.zeros(3, 1), e[a], e[a] + e[b], e[a] + e[b] + e[c]]
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
                eqs.append(d)                                  # linear T: div is a constant
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
    N = sp.Matrix.hstack(*E.nullspace())
    faces, trace = [], []
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        A, B, C = (P[v] for v in vs)
        n2 = (B - A).cross(C - A)
        if n2.dot(P[f] - A) > 0:
            n2 = -n2
        faces.append({"verts": vs, "n2": [int(q) for q in n2]})
        for v in vs:
            tv = (Ts[f] * n2).subs({x: P[v][0], y: P[v][1], z: P[v][2]})
            for i in range(3):
                trace.append(sp.expand(tv[i]))
    Tm = sp.Matrix([[sp.diff(q, cc) for cc in cs] for q in trace])
    TN = Tm * N
    assert N.shape[1] == 30 and TN.rank() == 30, (N.shape, TN.rank())
    L = (TN.T * TN).inv() * TN.T                             # a left inverse of TN on its image
    R = N * L                                                # 96 x 36: face data -> coefficients
    # balance: force (1/6) sum g, moment (1/24) sum (1 + d_ij) x_i x g_j over each face's vertices
    BAL = sp.zeros(6, 36)
    for f in range(4):
        vs = faces[f]["verts"]
        for jv, v in enumerate(vs):
            for comp in range(3):
                col = f * 9 + jv * 3 + comp
                BAL[comp, col] += sp.Rational(1, 6)
                g = sp.zeros(3, 1)
                g[comp] = 1
                for iv, w in enumerate(vs):
                    BAL[3:6, col] += sp.Rational(1 + (iv == jv), 24) * P[w].cross(g)
    assert (BAL * TN).is_zero_matrix
    # compliance forms over the 4 sub-tetrahedra (exact monomial integrals by an affine map)
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
    S1 = R.T * q1 * R
    S2 = R.T * q2 * R
    fr = lambda M: [[str(sp.Rational(v)) for v in M.row(i)] for i in range(M.rows)]
    return {"perm": list(perm), "faces": faces, "BAL": fr(BAL), "S1": fr(S1), "S2": fr(S2)}


def build():
    from .conduction3d import PERMS
    data = [_build_type(p) for p in PERMS]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as fh:
        json.dump(data, fh)
    return data


_DATA = None


def load():
    """[per Kuhn type] {"faces", "BAL", "S1", "S2"} with Fraction matrices."""
    global _DATA
    if _DATA is None:
        if not os.path.exists(CACHE):
            build()
        raw = json.load(open(CACHE))
        _DATA = [{"perm": t["perm"], "faces": t["faces"],
                  **{k: [[F(v) for v in row] for row in t[k]] for k in ("BAL", "S1", "S2")}} for t in raw]
    return _DATA


if __name__ == "__main__":
    import time
    t0 = time.time()
    d = build()
    print(f"built {len(d)} Kuhn types in {time.time() - t0:.0f} s -> {CACHE}")
    sys.exit(0)
