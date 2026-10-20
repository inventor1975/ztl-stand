"""THE SEARCH for a network certificate (ustand/znet.py checks it exactly; this file is trusted for nothing).

Per round, at the centre of the round's box, floating point (scipy, sparse): the node potentials y, the reverse
field z of the target branch, and an approximate lowest eigenvector w of L0 (inverse iteration) — each rounded to
integers over a common power-of-two denominator. The round's pinning is then done by znet itself (exactly), so the
search and the check walk the same boxes. It stops when a round pins nothing, or after ROUNDS.
"""
from __future__ import annotations

from fractions import Fraction as F

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import splu

from . import znet as Z

ROUNDS = 8
BITS = 60


def _laplacian(net, g):
    m = len(net.free)
    rows, cols, vals = [], [], []
    for j in net.res:
        u, v = net.edges[j]
        gj = float(g[j])
        for x, y_ in ((u, v), (v, u)):
            if x in net.idx:
                rows.append(net.idx[x]); cols.append(net.idx[x]); vals.append(gj)
                if y_ in net.idx:
                    rows.append(net.idx[x]); cols.append(net.idx[y_]); vals.append(-gj)
    return sp.csc_matrix((vals, (rows, cols)), shape=(m, m))


def _ints(x):
    return {"den": str(1 << BITS), "v": [str(int(round(float(v) * (1 << BITS)))) for v in x]}


def _round_data(net, gl, gh, V, k):
    g0 = [(a + b) / 2 for a, b in zip(gl, gh)]
    L = _laplacian(net, g0)
    lu = splu(L)
    c = np.array([float(x) for x in net.rhs_source(g0, V)])
    s = np.array([float(x) for x in net.unit(k)])
    y, z = lu.solve(c), lu.solve(s)
    w = np.ones(len(net.free))
    for _ in range(30):                          # inverse iteration: the lowest eigenvector (positive: M-matrix)
        w = lu.solve(w)
        w = w / np.max(np.abs(w))
    w = np.abs(w) + 1e-9
    return {"y": _ints(y), "z": _ints(z), "w": _ints(w)}


SPLIT_DEPTH = 10
GAP = F(1, 100)            # cut further while the bound is more than 1 % above a value found inside the box


def _float_current(net, g, V, k):
    L = _laplacian(net, g)
    x = splu(L).solve(np.array([float(c) for c in net.rhs_source(g, V)]))
    p = [0.0] * net.n
    p[net.a] = float(V)
    for node, i in net.idx.items():
        p[node] = x[i]
    if isinstance(k, tuple):                     # a potential target (network v2): x_p - x_q
        return p[k[1]] - p[k[2]]
    u, v = net.edges[k]
    return float(g[k]) * (p[u] - p[v])


def _ascent(net, glo, ghi, V, k, direction):
    """A value direction * I_k really takes in the box (a lower end for the max): coordinate ascent over corners."""
    g = [(a + b) / 2 for a, b in zip(glo, ghi)]
    best = direction * _float_current(net, g, V, k)
    for _ in range(3):
        for j in net.res:
            if glo[j] == ghi[j]:
                continue
            for end in (glo[j], ghi[j]):
                g2 = list(g); g2[j] = end
                v = direction * _float_current(net, g2, V, k)
                if v > best:
                    best, g = v, g2
    return best


def search(net, glo, ghi, V, k, direction, depth=SPLIT_DEPTH):
    """A certificate for max over the box of direction * I_k, and the bound it gives — cutting the box where the
    rounds leave the bound well above a value the ascent finds inside — or (None, why)."""
    glo, ghi = [F(x) for x in glo], [F(x) for x in ghi]
    cert, U = _search_rounds(net, glo, ghi, V, k, direction)
    if cert is None:
        return cert, U
    low = _ascent(net, glo, ghi, V, k, direction)
    if depth <= 0 or float(U) - low <= float(GAP) * abs(low):
        return cert, U
    free = [j for j in net.res if glo[j] < ghi[j]]
    if not free:
        return cert, U
    j = max(free, key=lambda i: (ghi[i] - glo[i]) / ghi[i])
    at = (glo[j] + ghi[j]) / 2
    lo_hi, hi_lo = list(ghi), list(glo)
    lo_hi[j], hi_lo[j] = at, at
    a, Ua = search(net, glo, lo_hi, V, k, direction, depth - 1)
    b, Ub = search(net, hi_lo, ghi, V, k, direction, depth - 1)
    if a is None or b is None:
        return cert, U
    if max(Ua, Ub) >= U:
        return cert, U
    return {"split": j, "at": f"{at.numerator}/{at.denominator}", "lo": a, "hi": b}, max(Ua, Ub)


def _search_rounds(net, glo, ghi, V, k, direction):
    glo, ghi = [F(x) for x in glo], [F(x) for x in ghi]
    gl, gh = list(glo), list(ghi)
    rounds = []
    for _ in range(ROUNDS):
        rd = _round_data(net, gl, gh, V, k)
        rounds.append(rd)
        enc = Z.round_enclose(net, gl, gh, V, k, Z._vec(rd["y"]), Z._vec(rd["z"]), Z._vec(rd["w"]))
        if isinstance(enc, str):
            return None, enc
        gl2, gh2, pinned = Z.pin(net, gl, gh, glo, ghi, k, direction, enc)
        if pinned == 0:
            break
        gl, gh = gl2, gh2
    else:
        rounds.append(_round_data(net, gl, gh, V, k))   # the final reading on the last pinned box
    cert = {"rounds": rounds}
    # the bound this certificate gives: replayed by the kernel itself with an unbounded claim
    ok = Z.check(net, glo, ghi, V, k, direction, F(10) ** 30, cert)
    return (cert, ok[1]) if ok[0] else (None, ok[1])


def grid(R, C):
    """An R x C grid of branches; the source from the top-left node to the bottom-right one (the circuit stand's
    test networks)."""
    node = lambda r, c: r * C + c
    edges = []
    for r in range(R):
        for c in range(C):
            if c + 1 < C:
                edges.append((node(r, c), node(r, c + 1)))
            if r + 1 < R:
                edges.append((node(r, c), node(r + 1, c)))
    edges.append((node(0, 0), node(R - 1, C - 1)))
    return Z.Net(R * C, edges, len(edges) - 1)
