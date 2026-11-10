# -*- coding: utf-8 -*-
"""CAD/FEA level 2b — DOMAIN DECOMPOSITION prototype on the box (2026-11-10). Measured against the global KKT.

Steps (PLAN-level2.md, "2b by domain decomposition"):
 1. subdomains: the box's tets split by their centroids into octants (2 x 2 x 2);
 2. interface fluxes from the P1 stress (the average of the two tets' sigma n), fixed;
 3. coarse balance: every subdomain with no support face must be balanced by its boundary data alone — the forest
    push on the SUBDOMAIN graph (roots: subdomains with a support), each correction the least-norm change of the
    interface fluxes to the parent (exact rationals);
 4. per subdomain: the float KKT over its interior (+ support) faces, the boundary data fixed;
 5. the exact per-tet push INSIDE each subdomain (roots: its support faces, or — for a floating subdomain — one root
    tet whose residual is then exactly the subdomain's imbalance, 0 by step 3); the exact energy."""
import os
import sys
import time
from collections import deque
from fractions import Fraction as Fr

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ustand import alfeld as AL                       # noqa: E402
import upper_box as UB                                # noqa: E402


def fe_stress(X, T, L, p, E, nu):
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
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
    F = UB.faces_of(T)
    for k, lst in F.items():
        if len(lst) == 1 and all(X[v][2] == L for v in k):
            A, B, C = (Xf[v] for v in k)
            for v in k:
                f[3 * v + 2] += p * np.linalg.norm(np.cross(B - A, C - A)) / 6
    free = np.array([X[i // 3][2] != 0 for i in range(nd)])
    u = np.zeros(nd)
    u[free] = spl.spsolve(K.tocsr()[free][:, free].tocsc(), f[free])
    sig = []
    for tet, gr in zip(T, grads):
        Gu = sum(np.outer(u[3 * tet[i]:3 * tet[i] + 3], gr[i]) for i in range(4))
        eps = (Gu + Gu.T) / 2
        sig.append(2 * mu * eps + lam * np.trace(eps) * np.eye(3))
    return sig, float(f[free] @ u[free])


def run(n=4, L=10, p=3, E=1000, nu=Fr(3, 10), parts=2):
    t0 = time.time()
    X, T = UB.box(n, L)
    F = UB.faces_of(T)
    Xf = np.array([[float(c) for c in x] for x in X])
    cen = [Xf[list(tet)].mean(axis=0) for tet in T]
    sub = [tuple(min(int(c[a] / (L / parts)), parts - 1) for a in range(3)) for c in cen]
    subs = sorted(set(sub))
    sid = {s: i for i, s in enumerate(subs)}
    sub = [sid[s] for s in sub]
    sig, c_fe = fe_stress(X, T, L, p, E, nu)
    slots = []
    for t, tet in enumerate(T):
        s_ = []
        for f_ in range(4):
            key = tuple(sorted(tet[v] for v in range(4) if v != f_))
            s_.append((key, 1 if F[key][0] == (t, f_) else -1, [tet[v] for v in range(4) if v != f_]))
        slots.append(s_)

    def n2_out(t, f_):
        tet = T[t]
        vs = [tet[v] for v in range(4) if v != f_]
        A, B, C = (Xf[v] for v in vs)
        nn = np.cross(B - A, C - A)
        if nn @ (Xf[tet[f_]] - A) > 0:
            nn = -nn
        return nn
    kind, Q = {}, {}
    for k, lst in F.items():
        if len(lst) == 2:
            a, b = lst[0][0], lst[1][0]
            kind[k] = "interior" if sub[a] == sub[b] else "interface"
            if kind[k] == "interface":
                qv = 0.5 * (sig[a] + sig[b]) @ n2_out(*lst[0])
                Q[k] = {v: [Fr(float(c)) for c in qv] for v in k}
        elif all(X[v][2] == L for v in k):
            kind[k] = "load"
            Q[k] = {v: [Fr(0), Fr(0), p * Fr(str(np.linalg.norm(n2_out(*lst[0]))))] for v in k}
        elif all(X[v][2] == 0 for v in k):
            kind[k] = "support"
        else:
            kind[k] = "free"
            Q[k] = {v: [Fr(0)] * 3 for v in k}
    Pt = [[list(X[v]) for v in tet] for tet in T]

    def bal_of(t, only=None):
        g = []
        for key, sg, vs in slots[t]:
            for v in vs:
                q = Q.get(key, {}).get(v) if (only is None or kind[key] in only) else None
                g += [sg * x for x in q] if q is not None else [Fr(0)] * 3
        Fv, Mv = AL.balance(Pt[t], g)
        return Fv + Mv

    # ---- 3. coarse balance on the subdomain graph
    nS = len(subs)
    touches_support = [False] * nS
    for k, kd in kind.items():
        if kd == "support":
            touches_support[sub[F[k][0][0]]] = True

    def sub_imbalance(s):
        tot = [Fr(0)] * 6
        for t in range(len(T)):
            if sub[t] == s:
                b = bal_of(t, only={"interface", "load", "free"})
                tot = [x + y for x, y in zip(tot, b)]
        return tot
    iface = {}
    for k, kd in kind.items():
        if kd == "interface":
            a, b = sub[F[k][0][0]], sub[F[k][1][0]]
            iface.setdefault(frozenset((a, b)), []).append(k)
    sadj = {s: [] for s in range(nS)}
    for pair in iface:
        a, b = tuple(pair)
        sadj[a].append(b)
        sadj[b].append(a)
    parent, dq = {}, deque()
    for s in range(nS):
        if touches_support[s]:
            parent[s] = None
            dq.append(s)
    order = []
    while dq:
        s = dq.popleft()
        order.append(s)
        for c in sadj[s]:
            if c not in parent:
                parent[c] = s
                dq.append(c)
    for s in reversed(order):
        if parent[s] is None:
            continue
        r_ = sub_imbalance(s)
        if all(x == 0 for x in r_):
            continue
        # the least-norm change on the interface to the parent, as seen from s
        cols = []
        for k in iface[frozenset((s, parent[s]))]:
            t, f_ = next((t, f_) for t, f_ in F[k] if sub[t] == s)
            _, sg, vs = slots[t][f_]
            for jv, v in enumerate(vs):
                for c in range(3):
                    e = [Fr(0)] * 36
                    e[f_ * 9 + jv * 3 + c] = Fr(sg)
                    Fv, Mv = AL.balance(Pt[t], e)
                    cols.append((k, v, c, Fv + Mv))
        Am = [[col[3][i] for col in cols] for i in range(6)]
        AAt = [[sum(Am[i][m] * Am[j][m] for m in range(len(cols))) for j in range(6)] for i in range(6)]
        y = UB._solve6(AAt, [-x for x in r_])
        for m, (k, v, c, _) in enumerate(cols):
            Q[k][v][c] += sum(Am[i][m] * y[i] for i in range(6))
    floating_bad = [s for s in range(nS) if not touches_support[s] and any(x != 0 for x in sub_imbalance(s))]
    print(f"coarse: {nS} subdomains, {len(iface)} interfaces; floating subdomains still unbalanced: {floating_bad} "
          f"({time.time() - t0:.1f} s)", flush=True)
    # ---- 4. per-subdomain float KKT over interior + support faces (boundary data fixed)
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    mats = [UB.float_mats(Pt[t]) for t in range(len(T))]
    for s in range(nS):
        tets = [t for t in range(len(T)) if sub[t] == s]
        unk = sorted({key for t in tets for key, _, _ in slots[t] if kind[key] in ("interior", "support")})
        uidx = {k: i for i, k in enumerate(unk)}
        nq = 9 * len(unk)
        H = np.zeros((nq, nq))
        h = np.zeros(nq)
        A = np.zeros((6 * len(tets), nq))
        bb = np.zeros(6 * len(tets))
        for it, t in enumerate(tets):
            Q1, Q2, BAL = mats[t]
            Qm = ((1 + float(nu)) * Q1 - float(nu) * Q2) / E
            Smap = np.zeros((36, nq))
            gl = np.zeros(36)
            for f_, (key, sg, vs) in enumerate(slots[t]):
                for jv, v in enumerate(vs):
                    for c in range(3):
                        row = f_ * 9 + jv * 3 + c
                        if key in uidx:
                            Smap[row, 9 * uidx[key] + 3 * list(key).index(v) + c] = sg
                        elif key in Q:
                            gl[row] = sg * float(Q[key][v][c])
            H += Smap.T @ Qm @ Smap
            h += Smap.T @ Qm @ gl
            A[6 * it:6 * it + 6] = BAL @ Smap
            bb[6 * it:6 * it + 6] = -(BAL @ gl)
        # A has rank 6 * len(tets) - 6 for a floating subdomain (its sum is the subdomain's balance): lstsq-KKT
        K = np.block([[H + 1e-12 * np.eye(nq), A.T], [A, np.zeros((len(bb), len(bb)))]])
        sol = np.linalg.lstsq(K, np.concatenate([-h, bb]), rcond=None)[0]
        for k in unk:
            Q[k] = {v: [Fr(float(sol[9 * uidx[k] + 3 * j + c])) for c in range(3)] for j, v in enumerate(k)}
    # ---- 5. exact push inside each subdomain over its interior faces
    resid = [bal_of(t) for t in range(len(T))]
    adj = {t: [] for t in range(len(T))}
    for k, lst in F.items():
        if kind[k] == "interior":
            (a, _), (c, _) = lst
            adj[a].append((c, k))
            adj[c].append((a, k))
    parent_t, order_t = {}, []
    for s in range(nS):
        tets = [t for t in range(len(T)) if sub[t] == s]
        roots = [(F[k][0][0], k) for k, kd in kind.items() if kd == "support" and sub[F[k][0][0]] == s]
        if not roots:
            roots = [(tets[0], None)]
        dq = deque()
        for t, k in roots:
            if t not in parent_t:
                parent_t[t] = (None, k)
                dq.append(t)
        while dq:
            t = dq.popleft()
            order_t.append(t)
            for c, k in adj[t]:
                if c not in parent_t:
                    parent_t[c] = (t, k)
                    dq.append(c)
    for t in reversed(order_t):
        par, k = parent_t[t]
        r_ = resid[t]
        if k is None or all(x == 0 for x in r_):
            continue
        f_ = next(i for i, (key, _, _) in enumerate(slots[t]) if key == k)
        _, sg, vs = slots[t][f_]
        cols = []
        for jv, v in enumerate(vs):
            for c in range(3):
                e = [Fr(0)] * 36
                e[f_ * 9 + jv * 3 + c] = Fr(sg)
                Fv, Mv = AL.balance(Pt[t], e)
                cols.append((v, c, Fv + Mv))
        Am = [[col[2][i] for col in cols] for i in range(6)]
        AAt = [[sum(Am[i][m] * Am[j][m] for m in range(9)) for j in range(6)] for i in range(6)]
        y = UB._solve6(AAt, [-x for x in r_])
        for m, (v, c, _) in enumerate(cols):
            Q[k][v][c] += sum(Am[i][m] * y[i] for i in range(6))
        if par is not None:
            resid[par] = bal_of(par)
    bad = sum(any(x != 0 for x in bal_of(t)) for t in range(len(T)))
    up = Fr(0)
    for t in range(len(T)):
        g = []
        for key, sg, vs in slots[t]:
            for v in vs:
                g += [sg * x for x in Q[key][v]]
        tt, tr2 = AL.energy(Pt[t], g)
        up += ((1 + nu) * tt - nu * tr2) / E
    print(f"DD upper {float(up):.6f}, unbalanced tets {bad}; P1 lower {c_fe:.6f} ({time.time() - t0:.1f} s)", flush=True)
    return up, bad, c_fe


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
