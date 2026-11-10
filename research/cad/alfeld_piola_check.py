# -*- coding: utf-8 -*-
"""CHECK, exactly, that the double Piola map carries the Alfeld-split stress element of one tetrahedron onto the
element of ANY other (CAD/FEA level 2b, 2026-11-10). For a reference tet P^ and a random rational tet P = B P^ + b:
  (1) build the element DIRECTLY on P (as kuhn_split._build_type does on Kuhn tets): piecewise-linear symmetric
      stresses on the 4 barycentric sub-tets, divergence-free, normal traction continuous across the 6 inner faces;
  (2) map the reference element's 30 basis fields: tau(x) = (1/det B) B s^(B^-1 (x - b)) B^T on each sub-tet;
  (3) assert: the mapped fields lie in the direct space (rank of the union = 30) and are independent (rank 30) —
      the map is onto the element — and the outer trace of the direct element has rank 30 (the bijection).
Run: python3 research/cad/alfeld_piola_check.py [n_tets]"""
import random
import sys
import time

import sympy as sp
from sympy.polys.matrices import DomainMatrix

def _dm(M):
    return DomainMatrix.from_Matrix(M).convert_to(sp.QQ)


def _null(M):
    """exact nullspace over QQ (DomainMatrix: much faster than Matrix.nullspace) -> sympy Matrix, columns"""
    N = _dm(M).nullspace()                      # rows are basis vectors
    return N.to_Matrix().T


def _rank(M):
    return _dm(M).rank()

x, y, z = sp.symbols("x y z")
X = (x, y, z)
VO = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]


def element(P):
    """-> (N: 96 x 30 basis of coefficient vectors, Ts: the 4 symbolic sub-tet stresses, cs)."""
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
    N = _null(E)
    # outer trace rank
    trace = []
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        A, B, C = (P[v] for v in vs)
        n2 = (B - A).cross(C - A)
        for v in vs:
            tv = (Ts[f] * n2).subs({x: P[v][0], y: P[v][1], z: P[v][2]})
            trace += [sp.expand(tv[i]) for i in range(3)]
    Tm = sp.Matrix([[sp.diff(q, cc) for cc in cs] for q in trace])
    return N, Ts, cs, _rank(Tm * N)


def coeffs_of(Tlist):
    """4 sub-tet linear symmetric fields -> the 96-vector in the element's coefficient order."""
    out = []
    for T in Tlist:
        for (i, j) in VO:
            p = sp.Poly(sp.expand(T[i, j]), x, y, z)
            out += [p.coeff_monomial(1), p.coeff_monomial(x), p.coeff_monomial(y), p.coeff_monomial(z)]
    return sp.Matrix(out)


def main(n):
    e = [sp.Matrix([1 if q == a else 0 for q in range(3)]) for a in range(3)]
    Ph = [sp.zeros(3, 1), e[0], e[1], e[2]]
    t0 = time.time()
    Nh, Tsh, csh, rh = element(Ph)
    assert Nh.shape[1] == 30 and rh == 30, (Nh.shape, rh)
    print(f"reference element: dimension {Nh.shape[1]}, trace rank {rh} ({time.time() - t0:.0f} s)", flush=True)
    rnd = random.Random(20261110)
    for k in range(n):
        while True:
            P = [sp.Matrix([sp.Rational(rnd.randint(-40, 40), rnd.randint(1, 9)) for _ in range(3)]) for _ in range(4)]
            Bm = sp.Matrix.hstack(P[1] - P[0], P[2] - P[0], P[3] - P[0])
            if Bm.det() != 0:
                break
        b = P[0]
        N, Ts, cs, r = element(P)
        Binv = Bm.inv()
        xh = Binv * (sp.Matrix(X) - b)
        mapped = []
        for col in range(30):
            sub = dict(zip(csh, Nh[:, col]))
            Tl = []
            for si in range(4):
                Th = Tsh[si].subs(sub).subs({x: xh[0], y: xh[1], z: xh[2]}, simultaneous=True)
                Tl.append((Bm * Th * Bm.T) / Bm.det())
            mapped.append(coeffs_of(Tl))
        M = sp.Matrix.hstack(*mapped)
        rm, ru = _rank(M), _rank(sp.Matrix.hstack(N, M))
        ok = (N.shape[1] == 30 and r == 30 and rm == 30 and ru == 30)
        print(f"tet {k}: det B = {Bm.det()}, direct dim {N.shape[1]}, trace rank {r}, mapped rank {rm}, "
              f"union rank {ru} -> {'OK' if ok else 'FAIL'} ({time.time() - t0:.0f} s)", flush=True)
        if not ok:
            print("ALFELD PIOLA RED")
            sys.exit(1)
    print(f"ALFELD PIOLA GREEN ({n} random tets)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
