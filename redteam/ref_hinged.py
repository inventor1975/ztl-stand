"""An independent straight-member reference with HINGES (redteam): one straight member of length L, cut into n Hermite
elements, ends: 'fixed' (v = th = 0), 'pin' (v = 0, th free), 'free'. Second order with a constant compression P
(tension negative), lateral point loads at given positions; also the linear buckling factor. numpy only."""
import numpy as np
import scipy.linalg as la


def _mats(EI, l):
    k = EI / l**3 * np.array([[12, 6*l, -12, 6*l], [6*l, 4*l*l, -6*l, 2*l*l], [-12, -6*l, 12, -6*l], [6*l, 2*l*l, -6*l, 4*l*l]])
    g = 1 / (30*l) * np.array([[36, 3*l, -36, 3*l], [3*l, 4*l*l, -3*l, -l*l], [-36, -3*l, 36, -3*l], [3*l, -l*l, -3*l, 4*l*l]])
    return k, g


def assemble(EI, L, n):
    N = 2 * (n + 1)
    K, G = np.zeros((N, N)), np.zeros((N, N))
    for e in range(n):
        k, g = _mats(EI, L / n)
        ix = [2*e, 2*e+1, 2*e+2, 2*e+3]
        K[np.ix_(ix, ix)] += k
        G[np.ix_(ix, ix)] += g
    return K, G


def _free(n, ends):
    fixed = set()
    for node, kind in ((0, ends[0]), (n, ends[1])):
        if kind in ("fixed", "pin"):
            fixed.add(2*node)
        if kind == "fixed":
            fixed.add(2*node + 1)
    return [d for d in range(2*(n+1)) if d not in fixed]


def buckling(EI, L, ends, n=200):
    K, G = assemble(EI, L, n)
    fr = _free(n, ends)
    w = la.eigh(K[np.ix_(fr, fr)], G[np.ix_(fr, fr)], eigvals_only=True)
    return float(w[w > 0].min())                         # the critical compression P_cr


def second_order(EI, L, ends, P, point_loads, n=400):
    """point_loads: [(x, Q)] lateral; returns the lateral displacement at every node (x, v)."""
    K, G = assemble(EI, L, n)
    f = np.zeros(2*(n+1))
    for x, Q in point_loads:
        f[2*int(round(x / L * n))] += Q
    fr = _free(n, ends)
    v = np.zeros(2*(n+1))
    v[fr] = np.linalg.solve(K[np.ix_(fr, fr)] - P * G[np.ix_(fr, fr)], f[fr])
    return np.linspace(0, L, n+1), v[0::2]
