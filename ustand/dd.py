# -*- coding: utf-8 -*-
"""
dd — the COARSE balance of a domain decomposition, EXACT (2026-11-10, CAD/FEA level 2b at scale).

A subdomain that touches no support face must be balanced by its boundary data alone: the resultant force and moment
of the fluxes on its boundary faces (interface fluxes as seen from it, the load, free faces = 0) must vanish — else
no equilibrated stress exists inside it. The resultant of a LINEAR flux q (3 vertices x 3, q = tau n2, n2 the face's
oriented area normal) on a face depends on the face alone:
    force  = (1/6) sum_v q_v,        moment about the origin = (1/24) sum_ij (1 + d_ij) x_i x q_j
(the same rule as alfeld.balance). The push: a spanning forest of the SUBDOMAIN graph, roots at subdomains with a
support; leaves first, each subdomain's imbalance cancelled by the least-norm EXACT change of the fluxes on its
interface with its parent (a 6 x 9m system solved through its 6 x 6 Gram matrix in Fractions).
"""
from __future__ import annotations

from collections import deque
from fractions import Fraction as Fr

import numpy as np


def face_map(Xq, Fv):
    """The exact 6 x 9 map: a face's flux (3 vertices x 3, in the face's vertex order) -> (force, moment)."""
    P = [Xq[int(v)] for v in Fv]
    A = [[Fr(0)] * 9 for _ in range(6)]
    for j in range(3):
        w = [sum(Fr(1 + (i == j), 24) * P[i][k] for i in range(3)) for k in range(3)]
        b = 3 * j
        A[0][b] = A[1][b + 1] = A[2][b + 2] = Fr(1, 6)
        A[4][b], A[5][b] = w[2], -w[1]
        A[3][b + 1], A[5][b + 1] = -w[2], w[0]
        A[3][b + 2], A[4][b + 2] = w[1], -w[0]
    return A


def _apply(A, q):
    flat = [x for row in q for x in row]
    return [sum(a * b for a, b in zip(row, flat) if a and b) for row in A]


def _solve6(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = next(i for i in range(c, n) if M[i][c] != 0)
        M[c], M[piv] = M[piv], M[c]
        for i in range(n):
            if i != c and M[i][c] != 0:
                f = M[i][c] / M[c][c]
                M[i] = [a - f * bb for a, bb in zip(M[i], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def coarse_balance(Xq, F, owner, kind, sid, q):
    """Xq: exact coordinates; F, owner, kind: tetmesh; sid: subdomain per tet; q: {face: 3x3 Fractions} for every
    interface, loaded and free face (owner 0's orientation). Modifies q on interface faces so that every subdomain
    without a support face is EXACTLY balanced. -> (q, report)."""
    nS = int(sid.max()) + 1
    o0, o1 = owner[:, 0], owner[:, 1]
    s0 = sid[o0]
    s1 = np.where(o1 >= 0, sid[np.maximum(o1, 0)], -1)
    iface = np.where((o1 >= 0) & (s0 != s1))[0]
    support = np.zeros(nS, bool)
    for f in np.where(kind == 1)[0]:
        support[s0[f]] = True
    maps = {}

    def fmap(f):
        if f not in maps:
            maps[f] = face_map(Xq, F[f])
        return maps[f]
    # the faces of each subdomain's boundary with the sign as seen from it (+1 if it owns side 0)
    bfaces = {s: [] for s in range(nS)}
    for f in iface:
        bfaces[int(s0[f])].append((int(f), 1))
        bfaces[int(s1[f])].append((int(f), -1))
    for f in np.where((o1 < 0) & (kind != 1))[0]:            # loaded and free faces
        bfaces[int(s0[f])].append((int(f), 1))

    def imbalance(s):
        r = [Fr(0)] * 6
        for f, sg in bfaces[s]:
            fr = _apply(fmap(f), q[f])
            r = [a + sg * b for a, b in zip(r, fr)]
        return r
    pairs = {}
    for f in iface:
        a, b = int(s0[f]), int(s1[f])
        pairs.setdefault(frozenset((a, b)), []).append(int(f))
    adj = {s: [] for s in range(nS)}
    for pr in pairs:
        a, b = tuple(pr)
        adj[a].append(b)
        adj[b].append(a)
    parent, dq, order = {}, deque(), []
    for s in range(nS):
        if support[s]:
            parent[s] = None
            dq.append(s)
    while dq:
        s = dq.popleft()
        order.append(s)
        for c in adj[s]:
            if c not in parent:
                parent[c] = s
                dq.append(c)
    unreached = [s for s in range(nS) if s not in parent]
    for s in reversed(order):
        p = parent[s]
        if p is None:
            continue
        r = imbalance(s)
        if all(x == 0 for x in r):
            continue
        cols = []                                             # (face, position, comp, sign-as-seen-from-s, column)
        for f in pairs[frozenset((s, p))]:
            sg = 1 if int(s0[f]) == s else -1
            A = fmap(f)
            for k in range(9):
                cols.append((f, k // 3, k % 3, [sg * A[i][k] for i in range(6)]))
        G = [[sum(c[3][i] * c[3][j] for c in cols) for j in range(6)] for i in range(6)]
        y = _solve6(G, [-x for x in r])
        for f, pos, comp, col in cols:
            # col already carries the sign as seen from s: the least-norm change of q itself is col . y (the same
            # double-sign slip as the morning's box prototype: caught here by the unbalanced count, fixed)
            q[f][pos][comp] += sum(col[i] * y[i] for i in range(6))
    left = [s for s in range(nS) if not support[s] and any(x != 0 for x in imbalance(s))]
    return q, {"subdomains": nS, "with_support": int(support.sum()), "interfaces": len(pairs),
               "interface_faces": int(len(iface)), "floating_unbalanced_after": left, "unreached": unreached}
