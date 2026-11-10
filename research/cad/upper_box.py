# -*- coding: utf-8 -*-
"""CAD/FEA level 2b, step 3 PROTOTYPE (2026-11-10): an EXACTLY admissible equilibrated stress on a tet mesh, and the
complementary-energy UPPER bound on the compliance, on a box where the truth is known.

The box [0,L]^3, n^3 cubes x 6 Kuhn tets; u = 0 on z = 0; a uniform traction (0, 0, p) on z = L; the other faces free;
E, nu = 0. With nu = 0 the exact solution is u = (0, 0, p z / E): the compliance C = (p L^2)^2 L / (E L^2) = p^2 L^3 / E.
P1 reproduces it (the lower bound of 2a is exact) and the constant stress p e_z e_z is in the Alfeld space (the upper
bound is exact) — so both must equal p^2 L^3 / E.

Unknowns: per mesh face, a linear 'flux' q(p_v) = tau(p_v) n2_ref at its 3 vertices (n2_ref: the first tet's outward
area normal); a tet's face data g = sign * q (sign -1 for the second tet). Free faces q = 0; loaded faces q = t |n2|;
supported faces q free (reactions). A float KKT (minimise the compliance energy subject to every tet's balance)
CHOOSES q; an EXACT push over a spanning forest (leaves first, roots at supported faces) cancels each tet's residual
on its parent face (least-norm, exact rationals); then the energy is evaluated exactly (alfeld.energy)."""
import os
import sys
import time
from collections import deque
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import alfeld as AL          # noqa: E402


def box(n, L):
    h = Fr(L, n)
    nid = lambda i, j, k: i + (n + 1) * (j + (n + 1) * k)
    X = [(i * h, j * h, k * h) for k in range(n + 1) for j in range(n + 1) for i in range(n + 1)]
    perms = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
    T = []
    for k in range(n):
        for j in range(n):
            for i in range(n):
                for p in perms:
                    pt, path = [i, j, k], [nid(i, j, k)]
                    for ax in p:
                        pt[ax] += 1
                        path.append(nid(*pt))
                    T.append(tuple(path))
    return X, T


def faces_of(T):
    F = {}
    for t, tet in enumerate(T):
        for f in range(4):
            key = tuple(sorted(tet[v] for v in range(4) if v != f))
            F.setdefault(key, []).append((t, f))
    return F


def float_mats(P):
    """36 x 36 float forms Q1 (int tau:tau) and Q2 (int (tr tau)^2) of the element on P, and the 6 x 36 balance."""
    r = AL.ref()
    Pf = np.array([[float(c) for c in p] for p in P])
    B = np.stack([Pf[1] - Pf[0], Pf[2] - Pf[0], Pf[3] - Pf[0]], axis=1)
    det = np.linalg.det(B)
    Bi = np.linalg.inv(B)
    G = np.kron(np.eye(12), np.sign(det) * Bi)                      # g -> g^
    Q1 = np.zeros((36, 36))
    Q2 = np.zeros((36, 36))
    for si in range(4):
        for w, M in r["EVAL"][si]:
            Mf = np.array([[float(v) for v in row] for row in M]) @ G   # 6 x 36: s^ components
            # T = B S B^T, S from the 6 components; build the 9 x 36 map
            Lm = np.zeros((9, 36))
            for col in range(36):
                s = Mf[:, col]
                S = np.array([[s[0], s[3], s[4]], [s[3], s[1], s[5]], [s[4], s[5], s[2]]])
                Lm[:, col] = (B @ S @ B.T).ravel()
            tr = Lm[0] + Lm[4] + Lm[8]
            Q1 += float(w) * Lm.T @ Lm
            Q2 += float(w) * np.outer(tr, tr)
    sc = 1 / 24 / abs(det)
    BAL = np.zeros((6, 36))
    for col in range(36):
        e = [Fr(0)] * 36
        e[col] = Fr(1)
        Fv, Mv = AL.balance(P, e)
        BAL[:, col] = [float(v) for v in Fv + Mv]
    return Q1 * sc, Q2 * sc, BAL


def run(n=2, L=10, p=3, E=1000, nu=Fr(0)):
    t0 = time.time()
    X, T = box(n, L)
    F = faces_of(T)
    keys = list(F)
    kidx = {k: i for i, k in enumerate(keys)}
    support = {k for k in keys if len(F[k]) == 1 and all(X[v][2] == 0 for v in k)}
    loaded = {k for k in keys if len(F[k]) == 1 and all(X[v][2] == L for v in k)}
    free = {k for k in keys if len(F[k]) == 1 and k not in support and k not in loaded}
    # per tet: face slot -> (global face, sign, the local-vertex -> global-vertex order of its 3 data blocks)
    slots = []
    for t, tet in enumerate(T):
        s = []
        for f in range(4):
            key = tuple(sorted(tet[v] for v in range(4) if v != f))
            first = F[key][0] == (t, f)
            vs = [tet[v] for v in range(4) if v != f]          # local sorted order -> global ids
            s.append((key, 1 if first else -1, vs))
        slots.append(s)
    # the load flux on loaded faces: t = (0, 0, p) uniform; |n2| = twice the area
    def n2_out(t, f):
        tet = T[t]
        vs = [tet[v] for v in range(4) if v != f]
        A, B, C = (np.array([float(c) for c in X[v]]) for v in vs)
        n = np.cross(B - A, C - A)
        if n @ (np.array([float(c) for c in X[tet[f]]]) - A) > 0:
            n = -n
        return n
    qload = {}
    for k in loaded:
        t, f = F[k][0]
        area2 = Fr(str(np.linalg.norm(n2_out(t, f))))          # exact for axis-aligned faces of a rational box
        qload[k] = {v: (Fr(0), Fr(0), p * area2) for v in k}
    # unknown dofs: interior + support faces, 9 each (per vertex of the face key, 3 comps)
    unk = [k for k in keys if len(F[k]) == 2 or k in support]
    uidx = {k: i for i, k in enumerate(unk)}
    nq = 9 * len(unk)
    mats = [float_mats([X[v] for v in tet]) for tet in T]
    comp = lambda Q1, Q2: ((1 + nu) * Q1 - nu * Q2) / E
    # assemble: g_t = S_t q + gl_t
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    H = sp.lil_matrix((nq, nq))
    h = np.zeros(nq)
    A = sp.lil_matrix((6 * len(T), nq))
    b = np.zeros(6 * len(T))
    for t in range(len(T)):
        Q = comp(*mats[t][:2])
        BAL = mats[t][2]
        cols, gl = [], np.zeros(36)
        Smap = np.zeros((36, nq))
        for f, (key, sg, vs) in enumerate(slots[t]):
            for jv, v in enumerate(vs):
                for c in range(3):
                    row = f * 9 + jv * 3 + c
                    if key in uidx:
                        pos = 9 * uidx[key] + 3 * list(key).index(v) + c
                        Smap[row, pos] = sg
                    elif key in qload:
                        gl[row] = sg * float(qload[key][v][c])
        nzc = np.nonzero(Smap.any(axis=0))[0]
        Sm = Smap[:, nzc]
        Hl = Sm.T @ Q @ Sm
        for a_, ia in enumerate(nzc):
            h[ia] += (Sm.T @ Q @ gl)[a_]
            for b_, ib in enumerate(nzc):
                H[ia, ib] += Hl[a_, b_]
        Al = BAL @ Sm
        for r_ in range(6):
            for a_, ia in enumerate(nzc):
                A[6 * t + r_, ia] = Al[r_, a_]
            b[6 * t + r_] = -(BAL @ gl)[r_]
    H, A = H.tocsr(), A.tocsr()
    K = sp.bmat([[H + 1e-12 * sp.eye(nq), A.T], [A, None]]).tocsc()
    rhs = np.concatenate([-h, b])
    sol = spl.lsqr(K, rhs, atol=1e-15, btol=1e-15, iter_lim=200000)[0] if False else spl.spsolve(K, rhs)
    q = sol[:nq]
    print(f"float KKT: {nq} unknowns, {6 * len(T)} balances, max residual {np.abs(A @ q - b).max():.2e} "
          f"({time.time() - t0:.1f} s)", flush=True)
    # ---- EXACT: q as Fractions (the floats' exact values), then the push
    Q = {k: {v: [Fr(float(q[9 * uidx[k] + 3 * j + c])) for c in range(3)] for j, v in enumerate(k)} for k in unk}
    for k in qload:
        Q[k] = {v: list(qload[k][v]) for v in k}
    for k in free:
        Q[k] = {v: [Fr(0)] * 3 for v in k}

    def g_of(t):
        g = []
        for key, sg, vs in slots[t]:
            for v in vs:
                g += [sg * x for x in Q[key][v]]
        return g
    Pt = [[list(X[v]) for v in tet] for tet in T]
    resid = []
    for t in range(len(T)):
        Fv, Mv = AL.balance(Pt[t], g_of(t))
        resid.append(Fv + Mv)
    # spanning forest: BFS from tets touching a support face
    adj = {t: [] for t in range(len(T))}
    for k, lst in F.items():
        if len(lst) == 2:
            (a, _), (c, _) = lst
            adj[a].append((c, k))
            adj[c].append((a, k))
    parent = {}
    dq = deque()
    for k in support:
        t = F[k][0][0]
        if t not in parent:
            parent[t] = (None, k)
            dq.append(t)
    order = []
    while dq:
        t = dq.popleft()
        order.append(t)
        for c, k in adj[t]:
            if c not in parent:
                parent[c] = (t, k)
                dq.append(c)
    assert len(order) == len(T), "a tet not connected to a support"
    maxden = 0
    for t in reversed(order):
        par, k = parent[t]
        r_ = resid[t]
        if all(x == 0 for x in r_):
            continue
        # the 6 x 9 map of a change d of face k's q on tet t's balance
        f = next(f for f, (key, _, _) in enumerate(slots[t]) if key == k)
        _, sg, vs = slots[t][f]
        Acol = []
        for jv, v in enumerate(vs):
            for c in range(3):
                e = [Fr(0)] * 36
                e[f * 9 + jv * 3 + c] = Fr(sg)
                Fv, Mv = AL.balance(Pt[t], e)
                Acol.append((v, c, Fv + Mv))
        Am = [[col[2][i] for col in Acol] for i in range(6)]          # 6 x 9
        AAt = [[sum(Am[i][m] * Am[j][m] for m in range(9)) for j in range(6)] for i in range(6)]
        y = _solve6(AAt, [-x for x in r_])
        d = [sum(Am[i][m] * y[i] for i in range(6)) for m in range(9)]
        for m, (v, c, _) in enumerate(Acol):
            Q[k][v][c] += d[m]                                          # Am maps a q-change (the sign is in it)
            maxden = max(maxden, Q[k][v][c].denominator.bit_length())
        if par is not None:
            Fv, Mv = AL.balance(Pt[par], g_of(par))
            resid[par] = Fv + Mv
    bad = 0
    for t in range(len(T)):
        Fv, Mv = AL.balance(Pt[t], g_of(t))
        bad += any(x != 0 for x in Fv + Mv)
    print(f"exact push: {len(order)} tets, unbalanced after: {bad}, largest denominator {maxden} bits "
          f"({time.time() - t0:.1f} s)", flush=True)
    up = Fr(0)
    for t in range(len(T)):
        tt, tr2 = AL.energy(Pt[t], g_of(t))
        up += ((1 + nu) * tt - nu * tr2) / E
    exact = Fr(p * p * L ** 3, E)              # the truth only for nu = 0 (with nu > 0 the bottom clamp bites)
    print(f"UPPER bound {float(up)}  exact compliance p^2 L^3 / E = {float(exact)}  ratio {float(up / exact)} "
          f"({time.time() - t0:.1f} s)", flush=True)
    return up, exact, bad


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


def lower_p1(n=2, L=10, p=3, E=1000, nu=0.0):
    """The P1 FE compliance on the same box (float; the rigorous version is ustand.tetfea): <= the truth."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    X, T = box(n, L)
    Xf = np.array([[float(c) for c in x] for x in X])
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    nd = 3 * len(X)
    K = sp.lil_matrix((nd, nd))
    for tet in T:
        P = Xf[list(tet)]
        D = np.stack([P[1] - P[0], P[2] - P[0], P[3] - P[0]], axis=1)
        Di = np.linalg.inv(D)
        gr = np.vstack([-Di.sum(axis=0), Di])                 # rows: grad phi_i
        V = abs(np.linalg.det(D)) / 6
        for i in range(4):
            for j in range(4):
                Kij = V * (mu * (gr[i] @ gr[j]) * np.eye(3) + mu * np.outer(gr[j], gr[i]) + lam * np.outer(gr[i], gr[j]))
                for a in range(3):
                    for b_ in range(3):
                        K[3 * tet[i] + a, 3 * tet[j] + b_] += Kij[a, b_]
    f = np.zeros(nd)
    F = faces_of(T)
    for k, lst in F.items():
        if len(lst) == 1 and all(X[v][2] == L for v in k):
            A, B, C = (Xf[v] for v in k)
            area = np.linalg.norm(np.cross(B - A, C - A)) / 2
            for v in k:
                f[3 * v + 2] += p * area / 3
    free = np.array([X[i // 3][2] != 0 for i in range(nd)])
    Kf = K.tocsr()[free][:, free]
    u = spl.spsolve(Kf.tocsc(), f[free])
    return float(f[free] @ u)


def bracket(ns=(2, 3, 4), nu=0.3):
    print(f"nu = {nu}: the bracket [P1 lower, Alfeld upper] on the box")
    import io, contextlib
    for n in ns:
        lo = lower_p1(n, nu=nu)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            up, ex, bad = run(n, nu=nu)
        print(f"  n = {n}: lower {lo:.6f}  upper {float(up):.6f}  gap {float(up) / lo - 1:.3%}  unbalanced {bad}",
              flush=True)


def upper_from_fe(n=2, L=10, p=3, E=1000, nu=Fr(3, 10)):
    """The cheap route for big meshes: face fluxes from the P1 stress (the AVERAGE of the two tets' sigma n on an
    interior face, sigma n on a supported face, the load on loaded faces, 0 on free faces) — NOT balanced — then the
    same exact push and exact energy. Any q gives a valid bound; the question is how loose. -> (upper, unbalanced)."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    X, T = box(n, L)
    Xf = np.array([[float(c) for c in x] for x in X])
    nuf = float(nu)
    mu, lam = E / (2 * (1 + nuf)), E * nuf / ((1 + nuf) * (1 - 2 * nuf))
    nd = 3 * len(X)
    K = sp.lil_matrix((nd, nd))
    grads = []
    for tet in T:
        P = Xf[list(tet)]
        D = np.stack([P[1] - P[0], P[2] - P[0], P[3] - P[0]], axis=1)
        Di = np.linalg.inv(D)
        gr = np.vstack([-Di.sum(axis=0), Di])
        grads.append(gr)
        V = abs(np.linalg.det(D)) / 6
        for i in range(4):
            for j in range(4):
                Kij = V * (mu * (gr[i] @ gr[j]) * np.eye(3) + mu * np.outer(gr[j], gr[i]) + lam * np.outer(gr[i], gr[j]))
                for a in range(3):
                    for b_ in range(3):
                        K[3 * tet[i] + a, 3 * tet[j] + b_] += Kij[a, b_]
    f = np.zeros(nd)
    F = faces_of(T)
    for k, lst in F.items():
        if len(lst) == 1 and all(X[v][2] == L for v in k):
            A, B, C = (Xf[v] for v in k)
            area = np.linalg.norm(np.cross(B - A, C - A)) / 2
            for v in k:
                f[3 * v + 2] += p * area / 3
    free = np.array([X[i // 3][2] != 0 for i in range(nd)])
    u = np.zeros(nd)
    u[free] = spl.spsolve(K.tocsr()[free][:, free].tocsc(), f[free])
    sig = []
    for tet, gr in zip(T, grads):
        Gu = sum(np.outer(u[3 * tet[i]:3 * tet[i] + 3], gr[i]) for i in range(4))
        eps = (Gu + Gu.T) / 2
        sig.append(2 * mu * eps + lam * np.trace(eps) * np.eye(3))
    # fluxes
    def n2_out(t, f_):
        tet = T[t]
        vs = [tet[v] for v in range(4) if v != f_]
        A, B, C = (Xf[v] for v in vs)
        nn = np.cross(B - A, C - A)
        if nn @ (Xf[tet[f_]] - A) > 0:
            nn = -nn
        return nn
    Q = {}
    for k, lst in F.items():
        t0_, f0 = lst[0]
        n2 = n2_out(t0_, f0)
        if len(lst) == 2:
            qv = 0.5 * (sig[t0_] + sig[lst[1][0]]) @ n2
        elif all(X[v][2] == L for v in k):
            Q[k] = {v: [Fr(0), Fr(0), p * Fr(str(np.linalg.norm(n2)))] for v in k}
            continue
        elif all(X[v][2] == 0 for v in k):
            qv = sig[t0_] @ n2
        else:
            Q[k] = {v: [Fr(0)] * 3 for v in k}
            continue
        Q[k] = {v: [Fr(float(c)) for c in qv] for v in k}
    return _push_and_energy(X, T, F, Q, E, nu, L)


def _push_and_energy(X, T, F, Q, E, nu, L):
    slots = []
    for t, tet in enumerate(T):
        s_ = []
        for f_ in range(4):
            key = tuple(sorted(tet[v] for v in range(4) if v != f_))
            s_.append((key, 1 if F[key][0] == (t, f_) else -1, [tet[v] for v in range(4) if v != f_]))
        slots.append(s_)
    support = {k for k, lst in F.items() if len(lst) == 1 and all(X[v][2] == 0 for v in k)}

    def g_of(t):
        g = []
        for key, sg, vs in slots[t]:
            for v in vs:
                g += [sg * x for x in Q[key][v]]
        return g
    Pt = [[list(X[v]) for v in tet] for tet in T]
    resid = [sum(AL.balance(Pt[t], g_of(t)), []) for t in range(len(T))]
    adj = {t: [] for t in range(len(T))}
    for k, lst in F.items():
        if len(lst) == 2:
            (a, _), (c, _) = lst
            adj[a].append((c, k))
            adj[c].append((a, k))
    parent, dq = {}, deque()
    for k in support:
        t = F[k][0][0]
        if t not in parent:
            parent[t] = (None, k)
            dq.append(t)
    order = []
    while dq:
        t = dq.popleft()
        order.append(t)
        for c, k in adj[t]:
            if c not in parent:
                parent[c] = (t, k)
                dq.append(c)
    for t in reversed(order):
        par, k = parent[t]
        r_ = resid[t]
        if all(x == 0 for x in r_):
            continue
        f_ = next(i for i, (key, _, _) in enumerate(slots[t]) if key == k)
        _, sg, vs = slots[t][f_]
        Acol = []
        for jv, v in enumerate(vs):
            for c in range(3):
                e = [Fr(0)] * 36
                e[f_ * 9 + jv * 3 + c] = Fr(sg)
                Acol.append((v, c, sum(AL.balance(Pt[t], e), [])))
        Am = [[col[2][i] for col in Acol] for i in range(6)]
        AAt = [[sum(Am[i][m] * Am[j][m] for m in range(9)) for j in range(6)] for i in range(6)]
        y = _solve6(AAt, [-x for x in r_])
        for m, (v, c, _) in enumerate(Acol):
            Q[k][v][c] += sum(Am[i][m] * y[i] for i in range(6))
        if par is not None:
            resid[par] = sum(AL.balance(Pt[par], g_of(par)), [])
    bad = sum(any(x != 0 for x in sum(AL.balance(Pt[t], g_of(t)), [])) for t in range(len(T)))
    up = Fr(0)
    for t in range(len(T)):
        tt, tr2 = AL.energy(Pt[t], g_of(t))
        up += ((1 + nu) * tt - nu * tr2) / E
    return up, bad


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fe":
        for n in (2, 3, 4):
            up, bad = upper_from_fe(n)
            print(f"  n = {n}: upper from the FE stress + push {float(up):.6f} (unbalanced {bad})", flush=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "bracket":
        bracket(nu=Fr(3, 10))
    else:
        run(int(sys.argv[1]) if len(sys.argv) > 1 else 2)

