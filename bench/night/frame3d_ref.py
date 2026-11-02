"""An INDEPENDENT float reference for space frames (2026-11-02, the night battery's sweep G): the textbook 12 x 12
Euler-Bernoulli beam (Przemieniecki) with the consistent geometric matrix, a member split into m elements, axial
forces from the first-order solve (the stand's named premise), solved in numpy. Nothing is shared with
ustand/frame3d.py's rank-one energy terms but the deck reader and the local-axes CONVENTION (y' horizontal, vertical
members y' = global Y)."""
import math

import numpy as np


def _axes(p, q, theta):
    d = np.array(q, float) - np.array(p, float)
    L = float(np.linalg.norm(d))
    x = d / L
    if abs(d[0]) < 1e-15 and abs(d[1]) < 1e-15:
        y = np.array([0.0, 1.0, 0.0])
    else:
        y = np.cross([0.0, 0.0, 1.0], d)
        y /= np.linalg.norm(y)
    z = np.cross(x, y)
    if theta == 90:
        y, z = z, -y
    return L, np.array([x, y, z])


def _k_local(E, G, A, Iz, Iy, J, L):
    k = np.zeros((12, 12))
    a = E * A / L
    k[0, 0] = k[6, 6] = a; k[0, 6] = k[6, 0] = -a
    t = G * J / L
    k[3, 3] = k[9, 9] = t; k[3, 9] = k[9, 3] = -t
    # v - theta_z (bending about z')
    c = E * Iz / L ** 3
    for (i, j, v) in ((1, 1, 12), (1, 5, 6 * L), (1, 7, -12), (1, 11, 6 * L), (5, 5, 4 * L * L), (5, 7, -6 * L),
                      (5, 11, 2 * L * L), (7, 7, 12), (7, 11, -6 * L), (11, 11, 4 * L * L)):
        k[i, j] = k[j, i] = c * v
    # w - theta_y (bending about y'): dw/dx = -theta_y
    c = E * Iy / L ** 3
    for (i, j, v) in ((2, 2, 12), (2, 4, -6 * L), (2, 8, -12), (2, 10, -6 * L), (4, 4, 4 * L * L), (4, 8, 6 * L),
                      (4, 10, 2 * L * L), (8, 8, 12), (8, 10, 6 * L), (10, 10, 4 * L * L)):
        k[i, j] = k[j, i] = c * v
    return k


def _g_local(N, L):
    """consistent geometric matrix for axial force N (tension +), both bending planes"""
    g = np.zeros((12, 12))
    c = N / (30 * L)
    for (i, j, v) in ((1, 1, 36), (1, 5, 3 * L), (1, 7, -36), (1, 11, 3 * L), (5, 5, 4 * L * L), (5, 7, -3 * L),
                      (5, 11, -L * L), (7, 7, 36), (7, 11, -3 * L), (11, 11, 4 * L * L)):
        g[i, j] = g[j, i] = c * v
    for (i, j, v) in ((2, 2, 36), (2, 4, -3 * L), (2, 8, -36), (2, 10, -3 * L), (4, 4, 4 * L * L), (4, 8, 3 * L),
                      (4, 10, -L * L), (8, 8, 36), (8, 10, 3 * L), (10, 10, 4 * L * L)):
        g[i, j] = g[j, i] = c * v
    return g


def solve(nodes, elems, props, loads, supports, qloads, m=1, second=False, forces=False, buckling=False):
    """nodes {id: (x,y,z)}, elems [(i,j)], props {k: Props}, loads {(node, dir): v} dir in X Y Z RX RY RZ,
    supports {(node, dir)}, qloads {k: (qx, qy, qz)}; each member split into m elements. Returns {(node, dir): u};
    forces=True also {member k: [(N, Mz_I, Mz_J, My_I, My_J) per sub-element]} (local end forces of the (K_E + N G)
    rows minus the consistent load); buckling=True returns the lowest positive lambda of (K_E + lambda G(N_1)) x = 0."""
    D = ("X", "Y", "Z", "RX", "RY", "RZ")
    nid = dict(nodes)
    next_id = max(nid) + 1
    el = []
    for k, (i, j) in enumerate(elems, 1):
        p, q = np.array(nodes[i], float), np.array(nodes[j], float)
        chain = [i]
        for s in range(1, m):
            nid[next_id] = tuple(p + (q - p) * s / m)
            chain.append(next_id); next_id += 1
        chain.append(j)
        for a, b in zip(chain, chain[1:]):
            el.append((a, b, k))
    idx = {}
    for n in sorted(nid):
        for d in D:
            if (n, d) not in supports:
                idx[(n, d)] = len(idx)
    nd = len(idx)
    f = np.zeros(nd)
    for (n, d), v in loads.items():
        if (n, d) in idx:
            f[idx[(n, d)]] += float(v)
    mats, fls = [], []
    for (a, b, k) in el:
        pk = props[k]
        E, nu = float(pk.ex), float(pk.nu)
        L, R = _axes(nid[a], nid[b], pk.theta)
        T = np.zeros((12, 12))
        for blk in range(4):
            T[3 * blk:3 * blk + 3, 3 * blk:3 * blk + 3] = R
        kl = _k_local(E, E / (2 * (1 + nu)), float(pk.area), float(pk.izz), float(pk.iyy), float(pk.ixx), L)
        dofs = [idx.get((n, d), -1) for n in (a, b) for d in D]
        # consistent member load: global q -> local, then the Hermite end forces and moments
        fl = np.zeros(12)
        if k in qloads:
            ql = R @ np.array([float(x) for x in qloads[k]])
            fl[0] = fl[6] = ql[0] * L / 2
            fl[1] = fl[7] = ql[1] * L / 2; fl[5] = ql[1] * L * L / 12; fl[11] = -ql[1] * L * L / 12
            fl[2] = fl[8] = ql[2] * L / 2; fl[4] = -ql[2] * L * L / 12; fl[10] = ql[2] * L * L / 12
        fg = T.T @ fl
        fls.append(fl)
        for r_, d_ in enumerate(dofs):
            if d_ >= 0:
                f[d_] += fg[r_]
        mats.append((T, kl, dofs, L))
    def assemble(extra):
        K = np.zeros((nd, nd))
        for e_, (T, kl, dofs, L) in enumerate(mats):
            ke = T.T @ (kl + (extra[e_] if extra is not None else 0)) @ T
            ii = [d for d in dofs if d >= 0]
            pos = [r for r, d in enumerate(dofs) if d >= 0]
            K[np.ix_(ii, ii)] += ke[np.ix_(pos, pos)]
        return K
    K0 = assemble(None)
    u = np.linalg.solve(K0, f)
    loc = lambda T, dofs: T @ np.array([u[d] if d >= 0 else 0.0 for d in dofs])
    extra = None
    if second or buckling:
        extra = []
        for (T, kl, dofs, L) in mats:
            ul = loc(T, dofs)
            N = kl[6, 6] * (ul[6] - ul[0])          # EA/L (u_j - u_i): the first-order axial force
            extra.append(_g_local(N, L))
    if buckling:
        Gm = assemble(extra) - K0
        mu = np.linalg.eigvals(np.linalg.solve(K0, -Gm)).real
        mu = mu[mu > 1e-12]
        return float(1 / mu.max()) if len(mu) else None
    if second:
        u = np.linalg.solve(assemble(extra), f)
    out = {key: u[i] for key, i in idx.items()}
    if not forces:
        return out
    fr = {}
    for e_, ((a, b, k), (T, kl, dofs, L)) in enumerate(zip(el, mats)):
        ul = loc(T, dofs)
        fe = (kl + (extra[e_] if extra is not None else 0)) @ ul - fls[e_]
        fr.setdefault(k, []).append((fe[6], fe[5], fe[11], fe[4], fe[10]))
    return out, fr
