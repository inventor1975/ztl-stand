"""An INDEPENDENT float reference for one member's lateral-torsional / torsional buckling (2026-11-02, the night
battery's sweep I): Vlasov's energy (E I v''^2 + G J phi'^2 + E I_w phi''^2; N (v'^2 + i0^2 phi'^2) + 2 M phi v''),
Hermite elements integrated by 12-point Gauss quadrature (ustand/ltb.py integrates polynomials exactly — nothing
shared), forks (v = phi = 0 at both ends), m elements, the lowest positive lambda of the generalized problem."""
import numpy as np
import scipy.linalg as sla

_gx, _gw = np.polynomial.legendre.leggauss(12)
_gx, _gw = (_gx + 1) / 2, _gw / 2


def _shp(s, h):
    N = np.array([1 - 3 * s ** 2 + 2 * s ** 3, h * (s - 2 * s ** 2 + s ** 3), 3 * s ** 2 - 2 * s ** 3, h * (-s ** 2 + s ** 3)])
    dN = np.array([-6 * s + 6 * s ** 2, h * (1 - 4 * s + 3 * s ** 2), 6 * s - 6 * s ** 2, h * (-2 * s + 3 * s ** 2)]) / h
    ddN = np.array([-6 + 12 * s, h * (-4 + 6 * s), 6 - 12 * s, h * (-2 + 6 * s)]) / h ** 2
    return N, dN, ddN


def alpha(L, EI, GJ, EIw, i02, MA, MB, kap, N, m=96):
    h = L / m
    nd = 4 * (m + 1)
    K0, K1 = np.zeros((nd, nd)), np.zeros((nd, nd))
    for e in range(m):
        k0, k1 = np.zeros((8, 8)), np.zeros((8, 8))
        for s, w in zip(_gx, _gw):
            Nn, dN, ddN = _shp(s, h)
            xi = (e + s) / m
            M = (1 - xi) * MA + xi * MB + kap * xi * (1 - xi)
            k0[:4, :4] += w * h * EI * np.outer(ddN, ddN)
            k0[4:, 4:] += w * h * (GJ * np.outer(dN, dN) + EIw * np.outer(ddN, ddN))
            k1[:4, :4] += w * h * N * np.outer(dN, dN)
            k1[4:, 4:] += w * h * N * i02 * np.outer(dN, dN)
            k1[4:, :4] += w * h * M * np.outer(Nn, ddN)
            k1[:4, 4:] += w * h * M * np.outer(ddN, Nn)
        dof = [4 * e, 4 * e + 1, 4 * e + 4, 4 * e + 5, 4 * e + 2, 4 * e + 3, 4 * e + 6, 4 * e + 7]
        K0[np.ix_(dof, dof)] += k0
        K1[np.ix_(dof, dof)] += k1
    free = [q for q in range(nd) if q not in (0, 2, nd - 4, nd - 2)]
    v = sla.eigh(-K1[np.ix_(free, free)], K0[np.ix_(free, free)], eigvals_only=True)
    return 1 / v.max() if v.max() > 0 else None
