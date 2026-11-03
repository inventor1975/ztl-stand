"""An INDEPENDENT 2D reference for second-order member forces (redteam, 2026-11-02). Nothing from ustand or ZTL:
its own deck parser, its own element matrices, numpy dense/sparse solves.

Model (the stand's named premises, taken as given): Euler-Bernoulli members, linear elasticity, second order with the
AXIAL FORCES OF THE FIRST-ORDER ANALYSIS. Each member is cut into `ns` Hermite sub-elements; on each the first-order
axial force is its mean (exact for a linear N over the sub-element's length: (EA/l) du); the geometric stiffness of a
sub-element uses that mean (piecewise-constant N; O(h^2) against the linear N). Member loads (QLOAD, global FX|FY per
unit length) are resolved into axial a and transverse w and lumped consistently per sub-element.

Outputs per original member, at every sub-element end: the axial force N and the bending moment M (from the sub-
element's end forces (K + N G) u_e - f_e), and |N|/A + |M|/W. The member's end moments in the stand's convention:
M_I = +(end force)_theta at the member's I end, M_J = -(end force)_theta at its J end.
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla


def parse(text):
    nodes, elems, loads, sups, qloads = {}, [], [], [], []
    E = A = I = h = None
    for raw in text.splitlines():
        line = raw.split("!")[0].strip()
        if not line:
            continue
        f = [x.strip() for x in line.split(",")]
        c = f[0].upper()
        if c == "N":
            nodes[int(f[1])] = (float(Fraction(f[2])), float(Fraction(f[3])))
        elif c == "E":
            elems.append((int(f[1]), int(f[2])))
        elif c == "MP":
            E = float(f[3])
        elif c == "R":
            A, I = float(f[2]), float(f[3])
            h = float(f[4]) if len(f) > 4 and f[4] else None
        elif c == "F":
            loads.append((int(f[1]), f[2].upper(), float(f[3])))
        elif c == "D":
            sups.append((int(f[1]), f[2].upper()))
        elif c == "QLOAD":
            qloads.append((int(f[1]), f[2].upper(), float(f[3])))
    return nodes, elems, loads, sups, qloads, (E, A, I, h)


def solve(text, moduli=None, ns=64, order=2):
    """moduli: one factor per ORIGINAL member (E * factor); None = all 1. Returns per member a dict with the arrays
    x (position along the member), N, M (internal, sign as the end forces), sig = |N|/A + |M|/W, and M_I, M_J."""
    nodes, elems, loads, sups, qloads, (E, A, I, h) = parse(text)
    m = len(elems)
    moduli = [1.0] * m if moduli is None else list(moduli)
    # fine nodes: the original nodes keep their ids; inner nodes appended
    pos = {nid: np.array(xy) for nid, xy in nodes.items()}
    nxt = max(nodes) + 1
    subs = []                               # per member: list of (a, b) fine node ids
    for (i, j) in elems:
        ids = [i]
        for s in range(1, ns):
            pos[nxt] = pos[i] + (pos[j] - pos[i]) * s / ns
            ids.append(nxt)
            nxt += 1
        ids.append(j)
        subs.append(list(zip(ids[:-1], ids[1:])))
    order_ids = sorted(pos)
    idx = {nid: k for k, nid in enumerate(order_ids)}
    ndof = 3 * len(order_ids)
    fixed = set()
    for nid, d in sups:
        fixed.add(3 * idx[nid] + {"UX": 0, "UY": 1, "ROTZ": 2}[d])
    fvec = np.zeros(ndof)
    for nid, d, v in loads:
        fvec[3 * idx[nid] + {"FX": 0, "FY": 1, "MZ": 2}[d]] += v
    q_of = {}
    for k, d, q in qloads:
        gx, gy = q_of.get(k, (0.0, 0.0))
        q_of[k] = (gx + q, gy) if d == "FX" else (gx, gy + q)

    def geom(k, a, b):
        p, r = pos[a], pos[b]
        d = r - p
        l = float(np.hypot(*d))
        return l, d[0] / l, d[1] / l

    def T6(c, s):
        T = np.zeros((6, 6))
        R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
        T[:3, :3] = R
        T[3:, 3:] = R
        return T

    def KE(EA, EI, l):
        k = np.zeros((6, 6))
        k[0, 0] = k[3, 3] = EA / l
        k[0, 3] = k[3, 0] = -EA / l
        b = EI / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                    [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
        ix = [1, 2, 4, 5]
        for r_ in range(4):
            for c_ in range(4):
                k[ix[r_], ix[c_]] = b[r_, c_]
        return k

    def KG(N, l):
        g = np.zeros((6, 6))
        b = N / (30 * l) * np.array([[36, 3 * l, -36, 3 * l], [3 * l, 4 * l * l, -3 * l, -l * l],
                                     [-36, -3 * l, 36, -3 * l], [3 * l, -l * l, -3 * l, 4 * l * l]])
        ix = [1, 2, 4, 5]
        for r_ in range(4):
            for c_ in range(4):
                g[ix[r_], ix[c_]] = b[r_, c_]
        return g

    els = []                                # (member k, a, b, l, c, s, EA, EI, local load vector)
    for k, sl in enumerate(subs):
        EA, EI = E * moduli[k] * A, E * moduli[k] * I
        gx, gy = q_of.get(k + 1, (0.0, 0.0))
        for (a, b) in sl:
            l, c, s = geom(k, a, b)
            ax, w = gx * c + gy * s, -gx * s + gy * c
            fl = np.array([ax * l / 2, w * l / 2, w * l * l / 12, ax * l / 2, w * l / 2, -w * l * l / 12])
            els.append((k, a, b, l, c, s, EA, EI, fl))
    for (k, a, b, l, c, s, EA, EI, fl) in els:
        dofs = [3 * idx[a], 3 * idx[a] + 1, 3 * idx[a] + 2, 3 * idx[b], 3 * idx[b] + 1, 3 * idx[b] + 2]
        fvec[dofs] += T6(c, s).T @ fl
    free = np.array([d for d in range(ndof) if d not in fixed])

    def assemble(Ns):
        rows, cols, vals = [], [], []
        for e, (k, a, b, l, c, s, EA, EI, fl) in enumerate(els):
            T = T6(c, s)
            ke = KE(EA, EI, l) + (KG(Ns[e], l) if Ns is not None else 0)
            kg = T.T @ ke @ T
            dofs = [3 * idx[a], 3 * idx[a] + 1, 3 * idx[a] + 2, 3 * idx[b], 3 * idx[b] + 1, 3 * idx[b] + 2]
            for r_ in range(6):
                for c_ in range(6):
                    rows.append(dofs[r_]); cols.append(dofs[c_]); vals.append(kg[r_, c_])
        return sp.csr_matrix((vals, (rows, cols)), shape=(ndof, ndof))

    def solve_with(Ns):
        K = assemble(Ns)[free][:, free]
        u = np.zeros(ndof)
        u[free] = sla.spsolve(K.tocsc(), fvec[free])
        return u

    def endforces(u, Ns):
        out = []
        for e, (k, a, b, l, c, s, EA, EI, fl) in enumerate(els):
            T = T6(c, s)
            dofs = [3 * idx[a], 3 * idx[a] + 1, 3 * idx[a] + 2, 3 * idx[b], 3 * idx[b] + 1, 3 * idx[b] + 2]
            ul = T @ u[dofs]
            ke = KE(EA, EI, l) + (KG(Ns[e], l) if Ns is not None else 0)
            out.append(ke @ ul - fl)
        return out

    u1 = solve_with(None)
    f1 = endforces(u1, None)
    N1 = [(-fe[0] + fe[3]) / 2 for fe in f1]           # mean axial force (tension +) of each sub-element
    if order == 1:
        u, fe2, Ns = u1, f1, None
    else:
        u = solve_with(N1)
        fe2 = endforces(u, N1)
    res = []
    for k, sl in enumerate(subs):
        es = [e for e, x in enumerate(els) if x[0] == k]
        xs, Ns_, Ms_ = [], [], []
        L = sum(els[e][3] for e in es)
        acc = 0.0
        for e in es:
            fe = fe2[e]
            l = els[e][3]
            # internal forces at the sub-element's two ends: N = -f_axial,i = +f_axial,j; M (end-force convention)
            xs += [acc, acc + l]
            Ns_ += [-fe[0], fe[3]]
            Ms_ += [fe[2], -fe[5]]
            acc += l
        xs, Ns_, Ms_ = np.array(xs), np.array(Ns_), np.array(Ms_)
        W = I / (h / 2) if h else None
        sig = np.abs(Ns_) / A + (np.abs(Ms_) / W if W else 0)
        res.append({"x": xs, "N": Ns_, "M": Ms_, "sig": sig, "M_I": fe2[es[0]][2], "M_J": -fe2[es[-1]][5],
                    "N1_mean": float(np.mean([N1[e] for e in es])), "L": L})
    disp = {nid: u[3 * idx[nid]:3 * idx[nid] + 3].copy() for nid in nodes}
    return res, disp


def buckling(text, moduli=None, ns=32):
    """The linear critical load factor of the continuum frame (N from the first-order analysis): the smallest lam > 0
    with K + lam K_G(N1) singular; ns Hermite sub-elements per member, piecewise-constant N per sub-element."""
    import scipy.linalg as la
    nodes, elems, loads, sups, qloads, (E, A, I, h) = parse(text)
    # reuse solve()'s machinery by a first-order call that also returns the matrices
    res = _matrices(text, moduli, ns)
    K, KG = res
    th = la.eigh(-KG, K, eigvals_only=True)
    th = th[th > 1e-14]
    return float(1 / th.max()) if len(th) else None


def _matrices(text, moduli, ns):
    """(K, K_G(N1)) dense on the free DOFs (the same model as solve())."""
    nodes, elems, loads, sups, qloads, (E, A, I, h) = parse(text)
    m = len(elems)
    moduli = [1.0] * m if moduli is None else list(moduli)
    pos = {nid: np.array(xy) for nid, xy in nodes.items()}
    nxt = max(nodes) + 1
    subs = []
    for (i, j) in elems:
        ids = [i]
        for s in range(1, ns):
            pos[nxt] = pos[i] + (pos[j] - pos[i]) * s / ns
            ids.append(nxt); nxt += 1
        ids.append(j)
        subs.append(list(zip(ids[:-1], ids[1:])))
    idx = {nid: k for k, nid in enumerate(sorted(pos))}
    ndof = 3 * len(idx)
    fixed = {3 * idx[nid] + {"UX": 0, "UY": 1, "ROTZ": 2}[d] for nid, d in sups}
    free = np.array([d for d in range(ndof) if d not in fixed])
    f = np.zeros(ndof)
    for nid, d, v in loads:
        f[3 * idx[nid] + {"FX": 0, "FY": 1, "MZ": 2}[d]] += v
    q_of = {}
    for k, d, q in qloads:
        gx, gy = q_of.get(k, (0.0, 0.0))
        q_of[k] = (gx + q, gy) if d == "FX" else (gx, gy + q)
    els = []
    for k, sl in enumerate(subs):
        gx, gy = q_of.get(k + 1, (0.0, 0.0))
        for (a, b) in sl:
            d = pos[b] - pos[a]; l = float(np.hypot(*d)); c, s = d[0] / l, d[1] / l
            ax, w = gx * c + gy * s, -gx * s + gy * c
            fl = np.array([ax * l / 2, w * l / 2, w * l * l / 12, ax * l / 2, w * l / 2, -w * l * l / 12])
            T = np.zeros((6, 6)); R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]); T[:3, :3] = R; T[3:, 3:] = R
            dofs = [3 * idx[a], 3 * idx[a] + 1, 3 * idx[a] + 2, 3 * idx[b], 3 * idx[b] + 1, 3 * idx[b] + 2]
            f[dofs] += T.T @ fl
            EA, EI = E * moduli[k] * A, E * moduli[k] * I
            ke = np.zeros((6, 6)); ke[0, 0] = ke[3, 3] = EA / l; ke[0, 3] = ke[3, 0] = -EA / l
            bb = EI / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                         [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
            gg = 1 / (30 * l) * np.array([[36, 3 * l, -36, 3 * l], [3 * l, 4 * l * l, -3 * l, -l * l],
                                          [-36, -3 * l, 36, -3 * l], [3 * l, -l * l, -3 * l, 4 * l * l]])
            ix = [1, 2, 4, 5]
            kb = np.zeros((6, 6)); kg = np.zeros((6, 6))
            for r_ in range(4):
                for c_ in range(4):
                    kb[ix[r_], ix[c_]] = bb[r_, c_]; kg[ix[r_], ix[c_]] = gg[r_, c_]
            els.append((dofs, T, ke + kb, kg, fl))
    K = np.zeros((ndof, ndof))
    for dofs, T, ke, kg, fl in els:
        K[np.ix_(dofs, dofs)] += T.T @ ke @ T
    Kf = K[np.ix_(free, free)]
    u = np.zeros(ndof); u[free] = np.linalg.solve(Kf, f[free])
    KG = np.zeros((ndof, ndof))
    for dofs, T, ke, kg, fl in els:
        fe = ke @ (T @ u[dofs]) - fl
        N = (-fe[0] + fe[3]) / 2
        KG[np.ix_(dofs, dofs)] += N * (T.T @ kg @ T)
    return Kf, KG[np.ix_(free, free)]


def _matrices_sparse(text, ns):
    """(K, K_G(N1)) sparse on the free DOFs (as _matrices, for large frames)."""
    nodes, elems, loads, sups, qloads, (E, A, I, h) = parse(text)
    pos = {nid: np.array(xy) for nid, xy in nodes.items()}
    nxt = max(nodes) + 1
    els = []
    for (i, j) in elems:
        ids = [i]
        for s in range(1, ns):
            pos[nxt] = pos[i] + (pos[j] - pos[i]) * s / ns
            ids.append(nxt); nxt += 1
        ids.append(j)
        els += list(zip(ids[:-1], ids[1:]))
    idx = {nid: k for k, nid in enumerate(sorted(pos))}
    ndof = 3 * len(idx)
    fixed = {3 * idx[nid] + {"UX": 0, "UY": 1, "ROTZ": 2}[d] for nid, d in sups}
    free = np.array([d for d in range(ndof) if d not in fixed])
    f = np.zeros(ndof)
    for nid, d, v in loads:
        f[3 * idx[nid] + {"FX": 0, "FY": 1, "MZ": 2}[d]] += v
    data = []
    for (a, b) in els:
        d = pos[b] - pos[a]; l = float(np.hypot(*d)); c, s = d[0] / l, d[1] / l
        T = np.zeros((6, 6)); R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]); T[:3, :3] = R; T[3:, 3:] = R
        ke = np.zeros((6, 6)); ke[0, 0] = ke[3, 3] = E * A / l; ke[0, 3] = ke[3, 0] = -E * A / l
        bb = E * I / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                        [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
        gg = 1 / (30 * l) * np.array([[36, 3 * l, -36, 3 * l], [3 * l, 4 * l * l, -3 * l, -l * l],
                                      [-36, -3 * l, 36, -3 * l], [3 * l, -l * l, -3 * l, 4 * l * l]])
        ix = [1, 2, 4, 5]
        kg = np.zeros((6, 6))
        for r_ in range(4):
            for c_ in range(4):
                ke[ix[r_], ix[c_]] += bb[r_, c_]; kg[ix[r_], ix[c_]] = gg[r_, c_]
        dofs = [3 * idx[a], 3 * idx[a] + 1, 3 * idx[a] + 2, 3 * idx[b], 3 * idx[b] + 1, 3 * idx[b] + 2]
        data.append((dofs, T, ke, kg))

    def asm(mats):
        rr, cc, vv = [], [], []
        for (dofs, T, ke, kg), M in zip(data, mats):
            Mg = T.T @ M @ T
            for r_ in range(6):
                for c_ in range(6):
                    rr.append(dofs[r_]); cc.append(dofs[c_]); vv.append(Mg[r_, c_])
        return sp.csr_matrix((vv, (rr, cc)), shape=(ndof, ndof))[free][:, free].tocsc()
    K = asm([d[2] for d in data])
    u = np.zeros(ndof); u[free] = sla.spsolve(K, f[free])
    Ns = []
    for (dofs, T, ke, kg) in data:
        fe = ke @ (T @ u[dofs])
        Ns.append((-fe[0] + fe[3]) / 2)
    KG = asm([N * d[3] for N, d in zip(Ns, data)])
    return K, KG
