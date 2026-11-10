# -*- coding: utf-8 -*-
"""
tetmesh — the face structure of a large tetrahedral mesh, its subdomains, and the RBE3 load as a TRACTION
(2026-11-10, CAD/FEA level 2b at scale). numpy throughout (a 640k-tet mesh has ~1.3M faces).

  faces(T)            -> F (nf, 3) sorted vertex triples, owner (nf, 2) tets (-1 = none), lface (nf, 2) the local
                         face index (opposite local vertex), and tface (nt, 4) the global face of each tet's local face.
  classify(F, owner, fixed, loaded) -> kind per face: 0 interior, 1 support (all 3 vertices fixed), 2 loaded (all 3
                         in the RBE3 set), 3 free boundary.
  partition(cen, size) -> a subdomain id per tet by recursive coordinate bisection of the centroids (median splits
                         along the longest extent) down to <= size tets — no foreign partitioner.
  rbe3_traction(X, F, kind, nodal) -> the P1 traction t on the loaded faces whose CONSISTENT nodal loads (the surface
                         mass matrix times t) are the RBE3 nodal forces: M_s t = f per component. Then the load is a
                         traction, f(v) = sum f_i . v_i for every P1 v, and the problem is well posed.
"""
from __future__ import annotations

import numpy as np


def faces(T):
    T = np.asarray(T, dtype=np.int64)
    nt = len(T)
    loc = np.array([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]])        # the face opposite local vertex f
    tri = np.sort(T[:, loc], axis=2).reshape(-1, 3)                     # (4 nt, 3)
    tet = np.repeat(np.arange(nt), 4)
    lf = np.tile(np.arange(4), nt)
    order = np.lexsort((tri[:, 2], tri[:, 1], tri[:, 0]))
    tri, tet, lf = tri[order], tet[order], lf[order]
    new = np.ones(len(tri), bool)
    new[1:] = (tri[1:] != tri[:-1]).any(axis=1)
    fid = np.cumsum(new) - 1
    nf = fid[-1] + 1
    F = tri[new]
    owner = -np.ones((nf, 2), np.int64)
    lface = -np.ones((nf, 2), np.int64)
    first = new
    owner[fid[first], 0], lface[fid[first], 0] = tet[first], lf[first]
    second = ~first
    if (np.bincount(fid, minlength=nf) > 2).any():
        raise ValueError("a face shared by more than two tetrahedra: not a manifold mesh")
    owner[fid[second], 1], lface[fid[second], 1] = tet[second], lf[second]
    tface = np.empty((nt, 4), np.int64)
    tface[tet, lf] = fid
    return F, owner, lface, tface


def classify(F, owner, fixed, loaded):
    fixed = np.asarray(sorted(fixed), np.int64)
    loaded = np.asarray(sorted(loaded), np.int64)
    inF = lambda S: np.isin(F, S).all(axis=1)
    kind = np.full(len(F), 3, np.int8)
    bnd = owner[:, 1] < 0
    kind[~bnd] = 0
    kind[bnd & inF(fixed)] = 1
    kind[bnd & inF(loaded) & (kind != 1)] = 2
    return kind


def partition(cen, size):
    cen = np.asarray(cen)
    sid = np.zeros(len(cen), np.int64)
    stack, nxt = [np.arange(len(cen))], 0
    out = []
    while stack:
        idx = stack.pop()
        if len(idx) <= size:
            out.append(idx)
            continue
        ext = cen[idx].max(axis=0) - cen[idx].min(axis=0)
        ax = int(np.argmax(ext))
        med = np.median(cen[idx, ax])
        left = idx[cen[idx, ax] <= med]
        right = idx[cen[idx, ax] > med]
        if not len(left) or not len(right):
            half = len(idx) // 2
            o = idx[np.argsort(cen[idx, ax], kind="stable")]
            left, right = o[:half], o[half:]
        stack += [left, right]
    for k, idx in enumerate(out):
        sid[idx] = k
    return sid


def rbe3_traction(X, F, kind, nodal):
    """nodal: {node: (fx, fy, fz)} -> (t: {node: 3-vector} on the loaded faces' nodes, the residual of M_s t = f,
    the load NOT representable: nodal forces on nodes that belong to no loaded face)."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    LF = F[kind == 2]
    nodes = np.unique(LF)
    idx = {int(n): i for i, n in enumerate(nodes)}
    A, B, C = X[LF[:, 0]], X[LF[:, 1]], X[LF[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    # P1 surface mass: area/12 * [[2,1,1],[1,2,1],[1,1,2]]
    loc = np.array([[2, 1, 1], [1, 2, 1], [1, 1, 2]]) / 12.0
    li = np.vectorize(idx.get)(LF)
    rows = np.repeat(li, 3, axis=1).ravel()
    cols = np.tile(li, (1, 3)).ravel()
    vals = (area[:, None, None] * loc[None]).ravel()
    M = sp.csr_matrix((vals, (rows, cols)), shape=(len(nodes), len(nodes)))
    f = np.zeros((len(nodes), 3))
    lost = {}
    for n, v in nodal.items():
        if int(n) in idx:
            f[idx[int(n)]] += v
        else:
            lost[int(n)] = v
    t = np.column_stack([spl.spsolve(M.tocsc(), f[:, c]) for c in range(3)])
    res = float(np.abs(M @ t - f).max())
    return {int(n): t[i] for i, n in enumerate(nodes)}, res, lost


def p1_stress(X, T, u, E, nu):
    """The P1 stress per tet (constant), sigma = 2 mu eps + lam tr(eps) I, from the nodal displacement u (nv, 3)."""
    X = np.asarray(X, float)
    T = np.asarray(T, np.int64)
    P = X[T]
    D = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=2)
    Di = np.linalg.inv(D)                                          # rows: grad of barycentric 1..3
    gr = np.concatenate([-Di.sum(axis=1, keepdims=True), Di], axis=1)      # (n, 4, 3)
    Gu = np.einsum("nic,nik->nck", u[T], gr)                       # du_c/dx_k
    eps = 0.5 * (Gu + np.transpose(Gu, (0, 2, 1)))
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    tr = np.trace(eps, axis1=1, axis2=2)
    return 2 * mu * eps + lam * tr[:, None, None] * np.eye(3)[None]


def interface_flux(X, T, F, owner, lface, sig, faces_mask):
    """q (nf, 3, 3): on the masked faces, the AVERAGE of the two tets' sigma times n2 (n2: owner 0's OUTWARD area
    normal, |n2| = twice the area) — one constant traction, so the same at the face's 3 vertices; a face with one tet
    takes that tet's. Elsewhere 0. (The float source of interface fluxes for a domain decomposition.)"""
    X = np.asarray(X, float)
    T = np.asarray(T, np.int64)
    A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    n2 = np.cross(B - A, C - A)
    x4 = X[T[owner[:, 0], lface[:, 0]]]
    flip = np.einsum("fk,fk->f", n2, x4 - A) > 0
    n2[flip] = -n2[flip]
    q = np.zeros((len(F), 3, 3))
    idx = np.where(faces_mask)[0]
    s0 = sig[owner[idx, 0]]
    has1 = owner[idx, 1] >= 0
    s1 = np.where(has1[:, None, None], sig[np.maximum(owner[idx, 1], 0)], s0)
    tq = np.einsum("fij,fj->fi", 0.5 * (s0 + s1), n2[idx])
    q[idx] = tq[:, None, :]
    return q


def connected_subdomains(sid, owner):
    """Split every subdomain into its CONNECTED pieces (through shared faces inside it) and number them anew.
    (2026-11-10: a coordinate bisection can cut a curved part into a subdomain of two separate pieces; the coarse
    balance makes each SUBDOMAIN balanced, not each piece, so a piece without a support kept a residual — found on
    SimJEB 631 as one unbalanced tet after the push.)"""
    import scipy.sparse as sp
    from scipy.sparse.csgraph import connected_components
    nt = len(sid)
    o0, o1 = owner[:, 0], owner[:, 1]
    m = (o1 >= 0) & (sid[o0] == sid[np.maximum(o1, 0)])
    G = sp.coo_matrix((np.ones(int(m.sum())), (o0[m], o1[m])), shape=(nt, nt))
    n, lab = connected_components(G, directed=False)
    return lab


def merge_small(sid, owner, min_size=200):
    """Glue every face-connected piece smaller than min_size to the neighbouring piece with which it shares the most
    faces, repeat until none is left (or none can be glued); renumber. The result's pieces are face-connected:
    gluing two pieces that share a face keeps connectivity. (2026-11-10: bisection left single tets as pieces.)"""
    sid = np.asarray(sid).copy()
    o0, o1 = owner[:, 0], owner[:, 1]
    inner = o1 >= 0
    for _ in range(50):
        sizes = np.bincount(sid)
        a, b = sid[o0[inner]], sid[o1[inner]]
        cross = a != b
        a, b = a[cross], b[cross]
        small = sizes < min_size
        if not small[np.unique(np.concatenate([a, b]))].any():
            break
        # for each small piece: the neighbour with the most shared faces
        pa = np.concatenate([a, b])
        pb = np.concatenate([b, a])
        sel = small[pa]
        pa, pb = pa[sel], pb[sel]
        if not len(pa):
            break
        key = pa.astype(np.int64) * (sid.max() + 1) + pb
        uk, cnt = np.unique(key, return_counts=True)
        src, dst = uk // (sid.max() + 1), uk % (sid.max() + 1)
        best = {}
        for s_, d_, c_ in zip(src, dst, cnt):
            if s_ not in best or c_ > best[s_][1]:
                best[s_] = (d_, c_)
        remap = np.arange(sid.max() + 1)
        done = set()
        for s_, (d_, _) in sorted(best.items(), key=lambda kv: sizes[kv[0]]):
            if s_ in done or d_ in done:
                continue
            remap[s_] = d_
            done.add(s_)
        sid = remap[sid]
    _, sid = np.unique(sid, return_inverse=True)
    return sid
