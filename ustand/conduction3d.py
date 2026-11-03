"""conduction3d — PROVED two-sided bounds on the conductance of a 3D voxel volume (ionic, electrical or thermal
conduction), judged by ZTL. The stand's 3D phase, track 1 (2026-11-02, the curator: "делать глобально").

    python3 -m ustand.conduction3d volume.npy --s 0:0 --s 1:6.11e-3 [--need 1e-3] [--refine 2] [--blocks 2,2,2]

The quantity: the conductance G of the box [0,nx] x [0,ny] x [0,nz] (voxel units), electrodes on x = 0 and x = nx,
the four other faces insulated; s_eff = G nx / (ny nz) (in the units of the phase conductivities). Linear conduction
is the model (the premise); the voxel map IS the sample (each voxel one phase).

UPPER (Dirichlet): G <= E(u) = sum_T s_T |grad u|^2 |T| for ANY continuous piecewise-linear u with u = 0 / 1 on the
  electrodes. Kuhn tetrahedra (6 per voxel): the barycentric gradients are integer, |grad u|^2 is the sum of squared
  differences along the Kuhn path. The float solve only chooses u.
LOWER (Thomson): 1/G <= E*(J) = sum_T |J_T|^2 / s_T |T| for ANY divergence-free J with zero normal flux on the
  insulated faces and total current 1 (J = 0 where s = 0). J is built from FACE FLUXES (lowest Raviart-Thomas):
  one number per triangular face, shared by the two tetrahedra (normal continuity by construction); a tetrahedron
  whose outward face fluxes sum to EXACTLY 0 carries the constant field J_T = -2 sum_f Q_f p_f (p_f the vertex
  opposite face f, |T| = 1/6) — divergence-free inside, and across every face. Exactness by INTEGERS: the fluxes are
  rounded to a dyadic grid and conservation is restored exactly by pushing each tetrahedron's residual along a
  spanning forest to the electrodes; faces of insulators and of the insulated faces are 0. Total current I = the
  exact net inflow at x = 0; then G >= I^2 / E*(J). Insulating clusters of any topology are no obstacle (the flux
  simply does not enter them); conducting islands not connected to the electrodes carry 0.
ROUNDING (premise, as ZTL zenergy.pd_ieee): IEEE 754 binary64, round to nearest. A sum of N nonnegative computed
  terms is raised by (1 + 3 gamma_N) (Higham 3.5, any order) plus N 2^-1000 for underflow; a field component
  computed from exact inputs carries gamma_8 times its absolute sum.
"""
from __future__ import annotations

import itertools
import json
import sys
from fractions import Fraction as F

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla

U = 2.0 ** -53
PERMS = list(itertools.permutations(range(3)))
EYE = np.eye(3, dtype=np.int64)


def _gam(N):
    return N * U / (1 - N * U)


def _up(sum_float, nterms):
    """Rigorous upper bound (Fraction) on the true value of a computed sum of nonnegative terms."""
    g = _gam(nterms + 16)
    return F(float(sum_float)) * (1 + 3 * F(g)) + F(nterms, 2 ** 1000)


class Mesh:
    """Kuhn tetrahedra of an nx x ny x nz voxel box."""

    def __init__(self, V):
        self.V = np.asarray(V)
        nx, ny, nz = self.V.shape
        self.nx, self.ny, self.nz = nx, ny, nz
        self.off = (1, nx + 1, (nx + 1) * (ny + 1))
        I, J, K = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
        self.vox = np.stack([I.ravel(), J.ravel(), K.ravel()], axis=1)
        base = self.vox[:, 0] * self.off[0] + self.vox[:, 1] * self.off[1] + self.vox[:, 2] * self.off[2]
        self.nn = (nx + 1) * (ny + 1) * (nz + 1)
        tv, tvox, tcoord = [], [], []
        for (a, b, c) in PERMS:
            v0 = base
            v1 = v0 + self.off[a]
            v2 = v1 + self.off[b]
            v3 = v2 + self.off[c]
            tv.append(np.stack([v0, v1, v2, v3], axis=1).astype(np.int32))
            tvox.append(np.arange(len(base), dtype=np.int32))
            p = np.zeros((4, 3), dtype=np.int64)
            p[1] = EYE[a]; p[2] = EYE[a] + EYE[b]; p[3] = EYE[a] + EYE[b] + EYE[c]
            tcoord.append((self.vox[:, None, :] + p[None, :, :]).astype(np.int16))
        self.tv = np.concatenate(tv)                     # (nt, 4) node ids, Kuhn order
        self.tvox = np.concatenate(tvox)                 # voxel index of each tet
        self.tp = np.concatenate(tcoord)                 # (nt, 4, 3) integer vertex coordinates
        self.nt = len(self.tv)
        nid = np.arange(self.nn)
        self.X = nid % (nx + 1)
        self.Y = (nid // (nx + 1)) % (ny + 1)
        self.Z = nid // ((nx + 1) * (ny + 1))

    def sigma(self, s):
        ph = self.V[self.vox[:, 0], self.vox[:, 1], self.vox[:, 2]]
        table = np.zeros(int(ph.max()) + 1)
        for k, v in s.items():
            if k < len(table):
                table[k] = float(v)
        return table[ph][self.tvox]                      # per tet


# --------------------------------------------------------------------------------------------- UPPER (potential)
SPLIT = True        # split nodes at edge/corner-only contacts (False: one potential per node — version 1, looser)


def _q3_table():
    """For every 8-bit mask of conducting voxels around a node (bit b = the voxel at offset b - 1, b = (bx, by, bz)
    read as bx + 2 by + 4 bz), the component of each voxel under FACE adjacency (Hamming distance 1 on the cube Q3),
    -1 where not conducting; and the number of components."""
    comp = np.full((256, 8), -1, dtype=np.int8)
    ncomp = np.zeros(256, dtype=np.int8)
    for m in range(256):
        lab = -1
        for b in range(8):
            if not (m >> b) & 1 or comp[m, b] >= 0:
                continue
            lab += 1
            stack = [b]
            comp[m, b] = lab
            while stack:
                c = stack.pop()
                for k in range(3):
                    d = c ^ (1 << k)
                    if (m >> d) & 1 and comp[m, d] < 0:
                        comp[m, d] = lab
                        stack.append(d)
        ncomp[m] = lab + 1
    return comp, ncomp


_Q3 = None


def _split_nodes(M, cond):
    """(2026-11-03) The conducting region is the INTERIOR of the union of conducting voxels: two of them meeting only
    along an edge or at a corner are not connected there (a line or point contact carries no current in the continuum —
    its spreading resistance is infinite). One continuous potential per node bridged such contacts and made the upper
    bound too high (MEASURED: an insulator/conductor checkerboard with no face path — true G = 0 — had the upper bound
    0.47; a 50 % random 8^3 map's ratio upper/lower 4.0, now 2.0). Here every node gets one copy per FACE-connected
    group of the conducting voxels around it; a tet's vertex takes the copy of its voxel's group. The field is
    continuous inside the region and piecewise linear: admissible, so the bound stays a bound. Returns (tv', nn',
    copy -> original node)."""
    global _Q3
    if _Q3 is None:
        _Q3 = _q3_table()
    comp, ncomp = _Q3
    nx, ny, nz = M.nx, M.ny, M.nz
    vcond = np.zeros(len(M.vox), bool)
    np.logical_or.at(vcond, M.tvox, cond)
    mask = np.zeros(M.nn, dtype=np.int32)
    vx, vy, vz = M.vox[:, 0], M.vox[:, 1], M.vox[:, 2]
    for cx in (0, 1):
        for cy in (0, 1):
            for cz in (0, 1):
                node = (vx + cx) + (nx + 1) * ((vy + cy) + (ny + 1) * (vz + cz))
                b = (1 - cx) + 2 * (1 - cy) + 4 * (1 - cz)          # the voxel's place in the node's 2x2x2 block
                np.bitwise_or.at(mask, node[vcond], 1 << b)
    k = ncomp[mask].astype(np.int64)
    extra = np.maximum(k - 1, 0)
    base = M.nn + np.concatenate([[0], np.cumsum(extra)[:-1]])
    nn2 = M.nn + int(extra.sum())
    orig = np.concatenate([np.arange(M.nn), np.repeat(np.arange(M.nn), extra)])
    tv2 = M.tv.astype(np.int64).copy()
    tvox = M.tvox
    for j in range(4):
        n = M.tv[:, j].astype(np.int64)
        X, Y, Z = M.X[n], M.Y[n], M.Z[n]
        b = (M.vox[tvox, 0] - X + 1) + 2 * (M.vox[tvox, 1] - Y + 1) + 4 * (M.vox[tvox, 2] - Z + 1)
        c = comp[mask[n], b].astype(np.int64)
        tv2[:, j] = np.where(c > 0, base[n] + c - 1, n)
    return tv2, nn2, orig


def upper(M, sig, rtol=1e-12):
    nt = M.nt
    if SPLIT:
        tv, nn, orig = _split_nodes(M, sig > 0)
    else:
        tv, nn, orig = M.tv, M.nn, np.arange(M.nn)
    X = M.X[orig]
    w = sig / 6.0
    rows, cols, vals = [], [], []
    for (p, q) in ((0, 1), (1, 2), (2, 3)):
        a, b = tv[:, p], tv[:, q]
        rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [w, w, -w, -w]
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nn, nn))
    fixed = (X == 0) | (X == M.nx)
    ub = np.where(X == M.nx, 1.0, 0.0)
    free = np.where(~fixed)[0]
    Af = A[free][:, free]
    rhs = -(A[free][:, np.where(fixed)[0]] @ ub[fixed])
    d = Af.diagonal().copy()
    zero = d == 0
    Af = Af + sp.diags(zero.astype(float))
    d[zero] = 1.0
    sol = _spd_solve(Af, rhs, d, rtol)
    u = ub.copy()
    u[free] = sol
    g2 = sum((u[tv[:, q]] - u[tv[:, p]]) ** 2 for p, q in ((0, 1), (1, 2), (2, 3)))
    # the potential per ORIGINAL node (the first copy) for the legacy averaged-flux lower bound, which only CHOOSES
    return _up(float(np.sum(sig * g2)) / 6.0, 4 * nt), u[:M.nn]


# --------------------------------------------------------------------------------------------- UPPER, P2 (2026-11-03)
_EDGES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def _p2_tables():
    """Per Kuhn type: D (3 x 4) the barycentric gradients (integers: the path steps), and the P2 stiffness (10 x 10)
    for s = 1 by an exact degree-2 quadrature (floats: it only CHOOSES the field)."""
    out = []
    a, b = 0.5854101966249685, 0.1381966011250105
    Q = [[a if i == j else b for i in range(4)] for j in range(4)]
    for (p, q_, r) in PERMS:
        D = np.zeros((3, 4))
        for k, ax in enumerate((p, q_, r)):
            D[ax, k + 1] += 1.0
            D[ax, k] -= 1.0
        K = np.zeros((10, 10))
        for lam in Q:
            G = [(4 * lam[i] - 1) * D[:, i] for i in range(4)]
            G += [4 * (lam[j] * D[:, i] + lam[i] * D[:, j]) for i, j in _EDGES]
            G = np.array(G)
            K += (1.0 / 6.0) / 4.0 * (G @ G.T)
        out.append((D, K))
    return out


def upper_p2(M, sig, rtol=1e-12):
    """A rigorous upper bound on G from a continuous piecewise-QUADRATIC potential (P2 on the Kuhn tets: the
    vertices, split at edge/corner-only contacts as upper(), and the edge midpoints). The energy per tet is exact as
    nonnegative squares: the gradient is linear, so int |grad u|^2 = |T|/20 (sum_c sum_i L_ci^2 + sum_c (sum_i L_ci)^2),
    L_ci the gradient's component c at vertex i — from the nodal values with INTEGER coefficients
    (grad u(v_k) = 3 u_k g_k - sum_{i != k} u_i g_i + 4 sum_{j != k} u_kj g_j, g = the integer barycentric gradients),
    each bounded by |L| + gamma_32 (its absolute sum) before squaring."""
    tv, nn, orig = _split_nodes(M, sig > 0) if SPLIT else (M.tv.astype(np.int64), M.nn, np.arange(M.nn))
    nvox = len(M.vox)
    ty = np.arange(M.nt) // nvox
    # edge dofs: one per (vertex copy, vertex copy) pair — split copies give separate edges automatically
    ea = np.stack([np.minimum(tv[:, i], tv[:, j]) for i, j in _EDGES], axis=1)
    eb = np.stack([np.maximum(tv[:, i], tv[:, j]) for i, j in _EDGES], axis=1)
    key = ea.astype(np.int64) * nn + eb
    uk, inv = np.unique(key.ravel(), return_inverse=True)
    eid = nn + inv.reshape(M.nt, 6)
    ndof = nn + len(uk)
    dofs = np.concatenate([tv, eid], axis=1)                   # (nt, 10)
    # x of every dof (the Dirichlet faces): vertices from their original node, midpoints the mean of the two ends
    xv = M.X[orig].astype(float)
    xe = 0.5 * (xv[(uk // nn).astype(np.int64)] + xv[(uk % nn).astype(np.int64)])
    x = np.concatenate([xv, xe])
    tab = _p2_tables()
    rows, cols, vals = [], [], []
    for t_ in range(6):
        blk = np.where((ty == t_) & (sig > 0))[0]
        if not len(blk):
            continue
        K = tab[t_][1]
        d = dofs[blk]
        rows.append(np.repeat(d, 10, axis=1).ravel()); cols.append(np.tile(d, (1, 10)).ravel())
        vals.append((sig[blk][:, None, None] * K[None]).ravel())
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(ndof, ndof))
    fixed = (x == 0) | (x == M.nx)
    ub = np.where(x == M.nx, 1.0, 0.0)
    free = np.where(~fixed)[0]
    Af = A[free][:, free]
    rhs = -(A[free][:, np.where(fixed)[0]] @ ub[fixed])
    dg = Af.diagonal().copy()
    zero = dg == 0
    Af = Af + sp.diags(zero.astype(float))
    dg[zero] = 1.0
    u = ub.copy()
    u[free] = _spd_solve(Af, rhs, dg, rtol)
    # the energy, rigorously from above
    tot = 0.0
    for t_ in range(6):
        blk = np.where((ty == t_) & (sig > 0))[0]
        if not len(blk):
            continue
        D = tab[t_][0]
        uv = u[dofs[blk, :4]]                                  # (n, 4)
        ue = u[dofs[blk, 4:]]                                  # (n, 6)
        edge_of = {}
        for e, (i, j) in enumerate(_EDGES):
            edge_of[(i, j)] = edge_of[(j, i)] = e
        S1 = np.zeros(len(blk)); S2 = np.zeros(len(blk))
        for c in range(3):
            Lc = []
            for k in range(4):
                terms = [3 * uv[:, k] * D[c, k]]
                terms += [-uv[:, i] * D[c, i] for i in range(4) if i != k]
                terms += [4 * ue[:, edge_of[(k, j)]] * D[c, j] for j in range(4) if j != k]
                val = np.sum(terms, axis=0)
                ab = np.sum(np.abs(terms), axis=0)
                Lc.append(np.abs(val) + _gam(32) * ab)          # >= |the exact gradient component at vertex k|
            Lc = np.array(Lc)
            S1 += np.sum(Lc * Lc, axis=0)
            S2 += np.sum(Lc, axis=0) ** 2
        tot += float(np.sum(sig[blk] * (S1 + S2))) / (6.0 * 20.0)
    return _up(tot * (1 + 4 * U), 12 * M.nt), u


# --------------------------------------------------------------------------------------------- LOWER (face fluxes)
def _faces(M):
    """Global faces: id per (tet, local face f = the face opposite local vertex f), the outward sign of the global
    orientation, the global area normal (integer x 2), and each face's two tets."""
    nt = M.nt
    tri = np.stack([np.sort(np.delete(M.tv, f, axis=1), axis=1) for f in range(4)], axis=1)   # (nt, 4, 3) int32
    key = (tri[..., 0].astype(np.int64) * M.nn + tri[..., 1]) * M.nn + tri[..., 2]
    uniq, inv = np.unique(key.ravel(), return_inverse=True)
    del key
    fid = inv.reshape(nt, 4).astype(np.int32)
    del inv
    nf = len(uniq)
    del uniq
    # global orientation: n = (B - A) x (C - A) for the sorted vertices (A < B < C)
    def coords(n):
        return np.stack([M.X[n], M.Y[n], M.Z[n]], axis=-1).astype(np.int32)
    A_, B_, C_ = coords(tri[..., 0]), coords(tri[..., 1]), coords(tri[..., 2])
    nrm2 = np.cross(B_ - A_, C_ - A_)                                       # twice the area normal
    opp = M.tp                                                              # vertex f opposite face f
    cen3 = A_ + B_ + C_                                                     # 3 x face centroid
    out = np.sign(np.einsum("tfk,tfk->tf", nrm2, cen3 - 3 * opp.astype(np.int32))).astype(np.int8)   # +1: outward
    del cen3
    first = np.full(nf, -1); second = np.full(nf, -1)
    flat_t = np.repeat(np.arange(nt), 4)
    order = np.argsort(fid.ravel(), kind="stable")
    sf = fid.ravel()[order]
    st = flat_t[order]
    starts = np.r_[0, np.where(np.diff(sf))[0] + 1]
    first[sf[starts]] = st[starts]
    has2 = np.r_[np.diff(sf) == 0, False]
    second[sf[has2]] = st[np.where(has2)[0] + 1]
    # the global normal per face (take it from the first tet's copy)
    gn = np.zeros((nf, 3), dtype=np.int32)
    gn[fid.ravel()] = nrm2.reshape(-1, 3)
    del nrm2
    # boundary face classes
    x0 = (A_[..., 0] == 0) & (B_[..., 0] == 0) & (C_[..., 0] == 0)
    x1 = (A_[..., 0] == M.nx) & (B_[..., 0] == M.nx) & (C_[..., 0] == M.nx)
    lat = np.zeros_like(x0)
    for ax, top in ((1, M.ny), (2, M.nz)):
        for v in (0, top):
            lat |= (A_[..., ax] == v) & (B_[..., ax] == v) & (C_[..., ax] == v)
    fx0 = np.zeros(nf, bool); fx1 = np.zeros(nf, bool); flat_ = np.zeros(nf, bool)
    fx0[fid[x0]] = True; fx1[fid[x1]] = True; flat_[fid[lat]] = True
    return {"fid": fid, "out": out, "first": first, "second": second, "gn": gn, "nf": nf,
            "x0": fx0, "x1": fx1, "lat": flat_}


def lower(M, sig, u):
    """G_lower from a flux built out of u, made EXACTLY conservative in integers."""
    Fc = _faces(M)
    fid, out, first, second, gn, nf = Fc["fid"], Fc["out"], Fc["first"], Fc["second"], Fc["gn"], Fc["nf"]
    cond = sig > 0
    if MIXED:
        q = _mixed_flux(M, sig, Fc)
        open_f = ~_closed(M, Fc, cond)
        nI = np.where(open_f & (second >= 0))[0]
        t1, t2 = first[nI], second[nI]
        elec = open_f & (second < 0) & (Fc["x0"] | Fc["x1"])
        te = first[elec]
        return _exact_and_energy(M, sig, Fc, q, open_f, nI, t1, t2, elec, te)
    # 1. flux from the potential: J_T = s grad u (Kuhn: grad u = sum_k (u_k - u_{k-1}) e_{axis_k}); face flux
    #    q_f = J . (area normal) averaged over the face's conducting tets, 0 on insulator faces and lateral faces
    gu = np.zeros((M.nt, 3))
    for k in range(3):
        d = M.tp[:, k + 1] - M.tp[:, k]                  # unit axis vector of path step k
        gu += d * (u[M.tv[:, k + 1]] - u[M.tv[:, k]])[:, None]
    J = sig[:, None] * gu
    qn = np.zeros(nf)
    cnt = np.zeros(nf)
    for f in range(4):
        cf = cond
        np.add.at(qn, fid[cf, f], 0.5 * np.einsum("tk,tk->t", J[cf], gn[fid[cf, f]]))
        np.add.at(cnt, fid[cf, f], 1.0)
    q = np.where(cnt > 0, qn / np.maximum(cnt, 1), 0.0)
    ins_face = np.zeros(nf, bool)
    for f in range(4):
        ins_face[fid[~cond, f]] = True
    q[ins_face | Fc["lat"]] = 0.0
    open_f = ~(ins_face | Fc["lat"])                       # faces that may carry flux
    # 2. conservation by a dual-graph correction: q_f += c_f (p_T1 - p_T2) on interior open faces (electrode faces
    #    to ground), L p = -residual
    def residual(qq):
        r = np.zeros(M.nt)
        for f in range(4):
            r += out[:, f] * qq[fid[:, f]]
        return r
    r = residual(q)
    inner = open_f & (second >= 0)
    elec = open_f & (second < 0) & (Fc["x0"] | Fc["x1"])
    t1, t2 = first[inner], second[inner]
    # orientation of the global normal relative to tet t1 (outward from t1?)
    def outsign(t, f):
        loc = np.argmax(fid[t] == f[:, None], axis=1)
        return out[t, loc]
    s1 = outsign(t1, np.where(inner)[0])
    ccoef = 1.0
    nI = np.where(inner)[0]
    rows = np.r_[t1, t2, t1, t2]
    cols = np.r_[t1, t2, t2, t1]
    vals = np.r_[np.full(len(t1), ccoef), np.full(len(t1), ccoef), np.full(len(t1), -ccoef), np.full(len(t1), -ccoef)]
    te = first[elec]
    rows = np.r_[rows, te]; cols = np.r_[cols, te]; vals = np.r_[vals, np.full(len(te), ccoef)]
    L = sp.csr_matrix((vals, (rows, cols)), shape=(M.nt, M.nt))
    act = np.where(cond)[0]
    Lc = L[act][:, act] + sp.identity(len(act)) * 1e-12
    pc, _ = sla.cg(Lc, -r[act], rtol=1e-12, maxiter=50000)
    p = np.zeros(M.nt)
    p[act] = pc
    # an inner face's flux along the global normal: adding c (p_t1 - p_t2) to t1's OUTWARD flux
    q[nI] += s1 * ccoef * (p[t1] - p[t2])
    eS = outsign(te, np.where(elec)[0])
    q[np.where(elec)[0]] += eS * ccoef * p[te]
    return _exact_and_energy(M, sig, Fc, q, open_f, nI, t1, t2, elec, te)


def _closed(M, Fc, cond):
    """Faces that carry no flux: the insulated faces and every face of an insulating tetrahedron."""
    closed = Fc["lat"].copy()
    for f in range(4):
        closed[Fc["fid"][~cond, f]] = True
    return closed


def _exact_and_energy(M, sig, Fc, q, open_f, nI, t1, t2, elec, te):
    fid, out, gn = Fc["fid"], Fc["out"], Fc["gn"]
    cond = sig > 0
    # 3. integers: dyadic grid, then EXACT conservation along a spanning forest rooted at the electrodes
    scale = 2.0 ** (36 - max(0, int(np.ceil(np.log2(max(1.0, float(np.abs(q).max())))))))
    Q = np.round(q * scale).astype(np.int64)
    Q[~open_f] = 0
    R = np.zeros(M.nt, dtype=np.int64)
    for f in range(4):
        R += out[:, f] * Q[fid[:, f]]
    # BFS over conducting tets through open inner faces, from tets holding an electrode face
    nbr_t = np.r_[t1, t2]; nbr_u = np.r_[t2, t1]; nbr_f = np.r_[nI, nI]
    G_ = sp.csr_matrix((nbr_f + 1, (nbr_t, nbr_u)), shape=(M.nt, M.nt))
    root_face = np.full(M.nt, -1)
    root_face[te] = np.where(elec)[0]
    parent = np.full(M.nt, -2)
    pface = np.full(M.nt, -1)
    roots = np.where(root_face >= 0)[0]
    parent[roots] = -1
    order = list(roots)
    head = 0
    indptr, indices, data = G_.indptr, G_.indices, G_.data
    while head < len(order):
        t = order[head]; head += 1
        for k in range(indptr[t], indptr[t + 1]):
            v = indices[k]
            if parent[v] == -2 and cond[v]:
                parent[v] = t
                pface[v] = data[k] - 1
                order.append(v)
    # islands (conducting, unreached): zero every flux touching them
    island = cond & (parent == -2)
    if island.any():
        for f in range(4):
            Q[fid[island, f]] = 0
        R = np.zeros(M.nt, dtype=np.int64)
        for f in range(4):
            R += out[:, f] * Q[fid[:, f]]
    for t in reversed(order):                           # push residuals to the root, exactly
        rt = R[t]
        if rt == 0:
            continue
        f = pface[t] if parent[t] >= 0 else root_face[t]
        loc = int(np.argmax(fid[t] == f))
        so = int(out[t, loc])                            # int8 table: never multiply it unconverted (NumPy 2 keeps int8)
        Q[f] -= so * int(rt)                              # t's outward flux through f drops by rt
        R[t] = 0
        if parent[t] >= 0:
            ploc = int(np.argmax(fid[parent[t]] == f))
            R[parent[t]] -= int(out[parent[t], ploc]) * so * int(rt)
    # exact checks: conservation everywhere, zero on closed faces
    Rchk = np.zeros(M.nt, dtype=np.int64)
    for f in range(4):
        Rchk += out[:, f] * Q[fid[:, f]]
    assert np.all(Rchk[cond] == 0), "conservation not exact"
    assert np.all(Q[~open_f] == 0), "flux through a closed face"
    # total current: net inflow at x = 0 (global normal of an x = 0 face: its sign relative to -x)
    fx0 = np.where(Fc["x0"])[0]
    I_int = int(np.sum(-np.sign(gn[fx0, 0]) * Q[fx0]))          # flux along -x through the x = 0 faces ... sign
    I = F(I_int) / F(scale)
    if I == 0:
        return F(0), "no current path between the electrodes"
    # the field per tet: J_T = -2 sum_f Q_out,f p_f ; energy with rounding bounds
    Qf = Q.astype(np.float64) / scale                            # exact (|Q| < 2^53)
    Jt = np.zeros((M.nt, 3)); Ja = np.zeros((M.nt, 3))
    for f in range(4):
        qo = out[:, f] * Qf[fid[:, f]]
        Jt += -2.0 * qo[:, None] * M.tp[:, f]
        Ja += 2.0 * np.abs(qo)[:, None] * np.abs(M.tp[:, f])
    assert np.all(Jt[~cond] == 0.0), "flux in an insulator"
    Jb = np.abs(Jt) + 2 * _gam(8) * Ja
    w = np.where(cond, 1.0 / np.where(cond, sig, 1.0), 0.0) / 6.0
    E = _up(float(np.sum(w * (Jb * Jb).sum(axis=1))) * (1 + 4 * U), 4 * M.nt)
    return I * I / E, "ok"



# --------------------------------------------------------------------------------------------- LOWER, BDM1 (2026-11-03)
MUTANT = {}             # TEST-ONLY sabotage switches; empty = the real bounds
BDM1_KKT_UP_TO = 3000   # conducting tets: BDM1's float choice by a direct KKT below, hybridized + AMG above
BDM1_UP_TO = 400000     # conducting tets: BDM1 in bounds() up to here, RT0 above (MEASURED hybridized, random 50 %:
                        # 16^3 2.9 s, 32^3 16 s / 3.9 GB, 48^3 50 s / 12.9 GB — the memory sets the line under 18 GB)


def _bdm1_tables(M, Fc):
    """Per Kuhn type (all its tets are translates): for each vertex v, the three faces through it (as (face, place
    of v among that face's sorted vertices)), the integer matrix N_v of their OUTWARD area normals (rows), adj(N_v)
    and det(N_v) — J(v) = adj(N_v) q_v / det(N_v); and the 12 x 12 energy form for s = 1 (floats: the CHOICE only)."""
    fid, out, gn = Fc["fid"], Fc["out"], Fc["gn"]
    nvox = len(M.vox)
    tabs = []
    for ty in range(6):
        t0 = ty * nvox
        n2 = [out[t0, f] * gn[fid[t0, f]].astype(np.int64) for f in range(4)]
        verts = []
        Jmap = np.zeros((4, 3, 12))
        for v in range(4):
            fs = [f for f in range(4) if f != v]
            pos = [[w for w in range(4) if w != f].index(v) for f in fs]
            N = np.array([n2[f] for f in fs], dtype=np.int64)
            det = int(round(np.linalg.det(N.astype(float))))
            adj = np.round(np.linalg.inv(N.astype(float)) * det).astype(np.int64)
            assert (N @ adj == det * np.eye(3, dtype=np.int64)).all()
            verts.append((fs, pos, adj, det))
            for a, (f, p) in enumerate(zip(fs, pos)):
                Jmap[v, :, 3 * f + p] += adj[:, a] / det
        A1 = sum(Jmap[v].T @ Jmap[v] for v in range(4))
        Js = Jmap.sum(axis=0)
        tabs.append({"verts": verts, "Q0": (1 / 6) / 20 * (A1 + Js.T @ Js)})
        # every tet of the type has the same outward normals (translates): checked on the type's last tet
        t1 = t0 + nvox - 1
        assert all((out[t1, f] * gn[fid[t1, f]] == n2[f]).all() for f in range(4))
    return tabs


def _bdm1_hybrid(M, Fc, tabs, act, ty, slot, G12, S12, sig, nu_):
    """BDM1's float CHOICE by hybridization (2026-11-03; as the RT0 mixed flux and elastic3d): per conducting tet the
    local problem min 1/2 q^T A q + lam^T q, sum_out q = 0 (13 x 13, batched) gives q_T = -Z_T lam_T; the outward data
    of a face's two tets sum to 0 — an SPD system on lam (a potential trace, 3 per open face, the SAME for both tets:
    no orientation sign), lam = 0 / 1 on the x = 0 / x = nx electrodes, smoothed-aggregation AMG + CG."""
    rows, cols, vals = [], [], []
    Zs = {}
    for t_ in range(6):
        b = act[ty[act] == t_]
        if not len(b):
            continue
        Q0 = tabs[t_]["Q0"]
        for c0 in range(0, len(b), 20000):
            bb = b[c0:c0 + 20000]
            G = G12[bb]
            open_ = G >= 0
            A = Q0[None] / sig[bb][:, None, None]
            A = np.where(open_[:, :, None] & open_[:, None, :], A, 0.0)
            idx = np.arange(12)
            A[:, idx, idx] = np.where(open_, A[:, idx, idx], 1.0)
            Bv = open_.astype(float)          # conservation in the tet's OWN frame: q are outward already, all +1
            sc = np.abs(A).max(axis=(1, 2))
            K = np.zeros((len(bb), 13, 13))
            K[:, :12, :12] = A
            K[:, :12, 12] = Bv
            K[:, 12, :12] = Bv
            K[:, 12, 12] = -1e-12 * sc
            Z = np.linalg.inv(K)[:, :12, :12] * (open_[:, :, None] & open_[:, None, :])
            for i_, t in enumerate(bb):
                Zs[int(t)] = Z[i_]
            okm = open_[:, :, None] & open_[:, None, :]
            rows.append(np.broadcast_to(G[:, :, None], okm.shape)[okm])
            cols.append(np.broadcast_to(G[:, None, :], okm.shape)[okm])
            vals.append(Z[okm])
    Am = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nu_, nu_))
    lamD = np.full(nu_, np.nan)
    for key, val in (("x0", 0.0), ("x1", 1.0)):
        fz = np.where(Fc[key] & (slot[:, 0] >= 0))[0]
        lamD[slot[fz].ravel()] = val
    dir_ = ~np.isnan(lamD)
    free = np.where(~dir_)[0]
    Af = Am[free][:, free]
    rhs = -(Am[free][:, np.where(dir_)[0]] @ lamD[dir_])
    d = Af.diagonal().copy()
    zero = d == 0
    Af = Af + sp.diags(zero.astype(float))
    d[zero] = 1.0
    lam = np.where(dir_, lamD, 0.0)
    lam[free] = _spd_solve(Af, rhs, d, 1e-11)
    q = np.zeros(nu_); cnt = np.zeros(nu_)
    for t, Z in Zs.items():
        G = G12[t]
        m = G >= 0
        lt = np.where(m, lam[np.maximum(G, 0)], 0.0)
        qt = -(Z @ lt) * S12[t]                                         # outward -> the face's global orientation
        np.add.at(q, G[m], qt[m]); np.add.at(cnt, G[m], 1.0)
    return np.where(cnt > 0, q / np.maximum(cnt, 1), 0.0)


def lower_bdm1(M, sig):
    """The conductance's LOWER bound from a BDM1 flux (linear on each tet; its normal component linear on each face,
    3 values per face q_{f,v} = J(v).n2): at each vertex the three faces through it fix J(v), so the 12 face values
    ARE the tet's field; div J is a constant, sum_out q / (6 |T|), so conservation is ONE integer condition per tet and
    the RT0 path's spanning-forest push carries over (a residual moved through one value of one face, coefficient 1).
    MEASURED (float choice, same mesh): checkerboard 1/0.25 RT0 2.630 -> BDM1 3.004 (RT0 at x2: 2.902). The energy
    int |J|^2 / s = |T|/20 (sum_v |J(v)|^2 + |sum_v J(v)|^2) / s, rigorously from above."""
    Fc = _faces(M)
    fid, out, gn, nf, first, second = Fc["fid"], Fc["out"], Fc["gn"], Fc["nf"], Fc["first"], Fc["second"]
    cond = sig > 0
    closed = _closed(M, Fc, cond)
    openf = ~closed
    nvox = len(M.vox)
    ty = np.arange(M.nt) // nvox
    tabs = _bdm1_tables(M, Fc)
    act = np.where(cond)[0]
    slot = -np.ones((nf, 3), dtype=np.int64)
    oi = np.where(openf)[0]
    slot[oi] = np.arange(3 * len(oi)).reshape(-1, 3)
    nu_ = 3 * len(oi)
    # 1. the float choice: min energy, conservation per tet, net inflow 1 at x = 0 (direct KKT)
    rows, cols, vals = [], [], []
    G12 = slot[fid].reshape(M.nt, 12)                          # (nt, 12): face f's three values, in order
    S12 = np.repeat(out, 3, axis=1).astype(float)
    for t_ in range(6):
        b = act[ty[act] == t_]
        if not len(b):
            continue
        Q0 = tabs[t_]["Q0"]
        G = G12[b]; Sg = S12[b]
        okm = (G[:, :, None] >= 0) & (G[:, None, :] >= 0)
        rows.append(np.broadcast_to(G[:, :, None], okm.shape)[okm])
        cols.append(np.broadcast_to(G[:, None, :], okm.shape)[okm])
        vals.append((Q0[None] / sig[b][:, None, None] * Sg[:, :, None] * Sg[:, None, :])[okm])
    Qm = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nu_, nu_))
    ai = np.repeat(np.arange(len(act)), 12)
    gg = G12[act].ravel(); ss = S12[act].ravel()
    m = gg >= 0
    x0f = np.where(Fc["x0"] & openf)[0]
    x0t = first[x0f]
    x0o = np.array([out[t, list(fid[t]).index(f)] for t, f in zip(x0t, x0f)], dtype=float)
    B = sp.csr_matrix((np.r_[ss[m] / 6.0, np.repeat(-x0o / 6.0, 3)],
                       (np.r_[ai[m], np.full(3 * len(x0f), len(act))], np.r_[gg[m], slot[x0f].ravel()])),
                      shape=(len(act) + 1, nu_))
    if len(act) > BDM1_KKT_UP_TO or MUTANT.get("bdm1_hybrid"):
        qf = _bdm1_hybrid(M, Fc, tabs, act, ty, slot, G12, S12, sig, nu_)
    else:
        rhs = np.zeros(len(act) + 1); rhs[-1] = 1.0
        eps = 1e-12 * max(1.0, abs(Qm).max())
        K = sp.bmat([[Qm + eps * sp.identity(nu_), B.T], [B, -eps * sp.identity(len(act) + 1)]]).tocsc()
        import scipy.sparse.linalg as sla_
        qf = sla_.spsolve(K, np.r_[np.zeros(nu_), rhs])[:nu_]
    # 2. integers and the exact push (as the RT0 path, one value per face moved)
    scale = 2.0 ** (40 - max(0, int(np.ceil(np.log2(max(1.0, float(np.abs(qf).max())))))))   # |Q| < 2^41
    Qi = np.zeros((nf, 3), dtype=np.int64)
    Qi[oi] = np.round(qf.reshape(-1, 3) * scale).astype(np.int64)
    def residual():
        R = np.zeros(M.nt, dtype=np.int64)
        for f in range(4):
            R += out[:, f].astype(np.int64) * Qi[fid[:, f]].sum(axis=1)
        return R
    R = residual()
    inner = openf & (second >= 0)
    nI = np.where(inner)[0]
    t1, t2 = first[nI], second[nI]
    elec = openf & (second < 0) & (Fc["x0"] | Fc["x1"])
    te = first[elec]
    G_ = sp.csr_matrix((np.r_[nI, nI] + 1, (np.r_[t1, t2], np.r_[t2, t1])), shape=(M.nt, M.nt))
    root_face = np.full(M.nt, -1)
    root_face[te] = np.where(elec)[0]
    parent = np.full(M.nt, -2); pface = np.full(M.nt, -1)
    roots = np.where(root_face >= 0)[0]
    parent[roots] = -1
    order = list(roots); head = 0
    indptr, indices, data = G_.indptr, G_.indices, G_.data
    while head < len(order):
        t = order[head]; head += 1
        for k in range(indptr[t], indptr[t + 1]):
            v = indices[k]
            if parent[v] == -2 and cond[v]:
                parent[v] = t; pface[v] = data[k] - 1; order.append(v)
    island = cond & (parent == -2)
    if island.any():
        for f in range(4):
            Qi[fid[island, f]] = 0
        R = residual()
    for t in reversed(order):
        rt = int(R[t])
        if rt == 0:
            continue
        f = pface[t] if parent[t] >= 0 else root_face[t]
        loc = int(np.argmax(fid[t] == f))
        so = int(out[t, loc])
        Qi[f, 0] -= so * rt
        R[t] = 0
        if parent[t] >= 0:
            ploc = int(np.argmax(fid[parent[t]] == f))
            R[parent[t]] -= int(out[parent[t], ploc]) * so * rt
    Rc = residual()
    assert not Rc[cond].any(), "conservation not exact"
    assert not Qi[closed].any(), "flux through a closed face"
    assert np.abs(Qi).max() < 2 ** 46, "face values too large for exact int64 products"
    I_int = int(np.sum(-x0o.astype(np.int64)[:, None] * Qi[x0f]))   # 6 x the net inflow at x = 0, times scale
    if I_int == 0:
        return F(0), "no current path between the electrodes"
    I = F(I_int, 6) / F(scale)
    # 3. the energy, from above: J(v) = adj q_v / det (adj q_v exact in int64), nonnegative squares
    tot = 0.0
    g8 = _gam(8)
    for t_ in range(6):
        b = act[ty[act] == t_]
        if not len(b):
            continue
        Jv = []
        for fs, pos, adj, det in tabs[t_]["verts"]:
            qv = np.stack([out[b, f].astype(np.int64) * Qi[fid[b, f], p] for f, p in zip(fs, pos)], axis=1)
            Jv.append((qv @ adj.T).astype(np.float64) / det)              # one rounding per component
        Jv = np.array(Jv)                                                  # (4, n, 3)
        Jb = np.abs(Jv) * (1 + 2 * U)
        S1 = np.sum(Jb * Jb, axis=(0, 2))
        A = np.abs(Jv.sum(axis=0)) + g8 * Jb.sum(axis=0)
        S2 = np.sum(A * A, axis=1)
        if MUTANT.get("bdm1_no_cross"):                  # sabotage (tests only): the |sum J_v|^2 term dropped
            S2 = 0 * S2
        tot += float(np.sum((S1 + S2) / sig[b])) / (6.0 * 20.0)
    # each tet's term: ~20 operations on its inputs (12 squares, 3 sums of 4, the division by s, s itself rounded to
    # nearest) -> (1 + gamma_24); the sum of len(act) nonnegative terms in 6 blocks -> _up's (1 + 3 gamma_(n+16))
    E = _up(tot, len(act) + 6) * (1 + F(_gam(24))) / F(scale) ** 2
    return I * I / E, "ok"



MIXED = True        # the lower bound's flux from the hybridized mixed problem (False: from the potential, averaged)


def _spd_solve(S, rhs, dg, rtol=1e-10):
    """CG preconditioned by smoothed-aggregation algebraic multigrid when pyamg is installed (2026-11-02, MEASURED:
    Jacobi CG took 2108 iterations, 85 % of the lower bound's time at 40^3), Jacobi otherwise. The solve only CHOOSES
    the flux; admissibility and the bound are made exact afterwards, so its accuracy changes the width, never the
    truth."""
    try:
        import pyamg
        ml = pyamg.smoothed_aggregation_solver(S.tocsr(), symmetry="symmetric", max_coarse=500)
        return ml.solve(rhs, tol=rtol, accel="cg", maxiter=500)
    except ImportError:
        x, _ = sla.cg(S, rhs, M=sp.diags(1.0 / dg), rtol=rtol, maxiter=100000)
        return x


def _mixed_flux(M, sig, Fc):
    """The lowest-order Raviart-Thomas flux of the MIXED problem (2026-11-02), hybridized: on each conducting tet
    the outward face fluxes Q = A_T^+ lam_T, A_T = (4/(3 s)) P P^T (P the centred vertex coordinates; A_T's kernel is
    the constant vector, so sum Q = 0 holds), lam the face traces (= -u: 0 / -1 on the electrodes, free elsewhere,
    multipliers on closed faces). The SPD system: sum_T (A_T^+ lam_T)_f = 0 on every free face. Floats only CHOOSE the
    flux; _exact_and_energy makes it exactly admissible and bounds its energy."""
    fid, out, nf = Fc["fid"], Fc["out"], Fc["nf"]
    cond = sig > 0
    act = np.where(cond)[0]
    # per Kuhn type: B = P (P^T P)^-2 P^T with P centred; the 6 types repeat in blocks of nvox
    nvox = len(M.vox)
    Bs = []
    for k in range(6):
        P = M.tp[k * nvox].astype(float)
        P = P - P.mean(axis=0)
        G = np.linalg.inv(P.T @ P)
        Bs.append(P @ G @ G @ P.T)
    lamD = np.full(nf, np.nan)
    lamD[Fc["x0"]] = 0.0
    lamD[Fc["x1"]] = -1.0
    dir_ = ~np.isnan(lamD)
    free = np.where(~dir_)[0]
    col = np.full(nf, -1, dtype=np.int64); col[free] = np.arange(len(free))
    rows, cols, vals = [], [], []
    rhs = np.zeros(len(free))
    # one Kuhn type at a time (2026-11-02: the full (nt, 4, 4) arrays were the memory peak)
    for ty in range(6):
        blk = np.arange(ty * nvox, (ty + 1) * nvox)
        blk = blk[cond[blk]]
        if not len(blk):
            continue
        sg = 0.75 * sig[blk]
        fa = fid[blk]
        for a in range(4):
            ca = col[fa[:, a]]
            okr = ca >= 0
            for b in range(4):
                kab = sg * Bs[ty][a, b]
                cb = col[fa[:, b]]
                both = okr & (cb >= 0)
                rows.append(ca[both].astype(np.int32)); cols.append(cb[both].astype(np.int32)); vals.append(kab[both])
                dirb = okr & (cb < 0)
                np.add.at(rhs, ca[dirb], -kab[dirb] * lamD[fa[dirb, b]])
    S = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(free), len(free)))
    dg = S.diagonal().copy()
    S = S + sp.diags(np.where(dg == 0, 1.0, 0.0))
    dg[dg == 0] = 1.0
    lam_f = _spd_solve(S, rhs, dg)
    lam = np.where(dir_, lamD, 0.0)
    lam[free] = lam_f
    # outward fluxes per tet, one Kuhn type at a time; one number per face in the global orientation: the mean of
    # the two tets' (sign-corrected) values
    qn = np.zeros(nf); cnt = np.zeros(nf)
    for ty in range(6):
        blk = np.arange(ty * nvox, (ty + 1) * nvox)
        blk = blk[cond[blk]]
        if not len(blk):
            continue
        Ql = (0.75 * sig[blk])[:, None] * (lam[fid[blk]] @ Bs[ty].T)
        for f in range(4):
            np.add.at(qn, fid[blk, f], out[blk, f] * Ql[:, f])
            np.add.at(cnt, fid[blk, f], 1.0)
    return np.where(cnt > 0, qn / np.maximum(cnt, 1), 0.0)


def bounds(V, s, refine=1, p2=False):
    V = np.asarray(V)
    if refine > 1:
        V = np.repeat(np.repeat(np.repeat(V, refine, 0), refine, 1), refine, 2)
    M = Mesh(V)
    sig = M.sigma(s)
    up, u = upper(M, sig)
    if p2:
        # a piecewise-quadratic potential (2026-11-03): never above P1 (its space contains P1's), MEASURED small gains
        # (0.2-6 %: the field is singular at the phases' edges and corners) — the bracket's gap is mostly the LOWER side
        up = min(up, upper_p2(M, sig)[0])
    if 0 < int((sig > 0).sum()) <= BDM1_UP_TO:
        lo, note = lower_bdm1(M, sig)                   # (2026-11-03) BDM1: MEASURED median gap 1.244 -> 1.118
    else:
        lo, note = lower(M, sig, u)
    k = refine
    # conductance of the refined box in refined voxel units = k x that in original units (G = s A / L, h -> h/k)
    return lo / k, up / k, note, M


def _cuts(n, p):
    """p contiguous index ranges covering 0..n (as equal as possible)."""
    e = [round(n * i / p) for i in range(p + 1)]
    return [(e[i], e[i + 1]) for i in range(p) if e[i + 1] > e[i]]


def bounds_blocks(V, s, px=1, py=1, pz=1, refine=1):
    """(2026-11-03) Bounds for a sample TOO LARGE for one solve, from smaller solves — each piece by the unchanged
    proved machinery above; only the GLUING is new, and it is monotonicity (Rayleigh's):
      UPPER: short the planes x = const between px slabs (perfect conductors only RAISE G): slab k, its own two faces
        electrodes, has U_k >= its conductance; slab potentials with drops d_k = (1/U_k) / sum (1/U_j) glue into one
        continuous admissible u of the whole box, so G <= E(u) = 1 / sum_k (1/U_k) (exact Fractions).
      LOWER: insert insulating sheets along x between py x pz columns (insulators only LOWER G): column c, full x
        length, has L_c <= its conductance; its divergence-free flux (zero normal flux on its sides) glues with the
        others into one admissible flux of the whole box, so G >= sum_c L_c.
    The price is a wider bracket (the sheets are not in the sample); the gain is memory (the pieces are 1/px resp.
    1/(py pz) of the box). Returns (lower, upper, notes) in the box's (refined: divided by refine) voxel units."""
    V = np.asarray(V)
    if refine > 1:
        V = np.repeat(np.repeat(np.repeat(V, refine, 0), refine, 1), refine, 2)
    nx, ny, nz = V.shape
    inv = F(0)
    for (x0, x1) in _cuts(nx, px):
        M = Mesh(V[x0:x1])
        u_k = upper(M, M.sigma(s))[0]
        if u_k == 0:
            inv = None                                     # a non-conducting slab: the whole box conducts nothing
            break
        inv += 1 / u_k
    up = F(0) if inv is None else 1 / inv
    if MUTANT.get("blocks_upper_len"):                   # sabotage (tests only): the slabs' length counted twice
        up = up / px
    lo, notes = F(0), []
    for (y0, y1) in _cuts(ny, py):
        for (z0, z1) in _cuts(nz, pz):
            l_c, _u, note, _M = bounds(V[:, y0:y1, z0:z1], s)
            lo += l_c
            notes.append(note)
    if MUTANT.get("blocks_lower_series"):                # sabotage (tests only): the columns taken in series
        lo = lo * (py * pz) if py * pz > 1 else lo
    return lo / refine, up / refine, notes


def s_eff(V, s, refine=1, blocks=None):
    nx, ny, nz = np.asarray(V).shape
    if blocks:
        lo, up, note = bounds_blocks(V, s, *blocks, refine=refine)
        note = {"blocks": list(blocks), "pieces": note}
    else:
        lo, up, note, _ = bounds(V, s, refine)
    g = F(nx, ny * nz)
    return lo * g, up * g, note


def _box(vals, what):
    """A conductivity box [lo, hi] (or one value), REFUSED when written high-to-low (2026-11-03, the cloud red team's
    round 2: a descending box gave an inverted bracket)."""
    lo, hi = F(vals[0]), F(vals[-1])
    if lo > hi:
        raise ValueError(f"{what}: the box [{vals[0]}, {vals[-1]}] is written high-to-low — write it [low, high]")
    return lo, hi


def judge(V, phases, need, refine=1, blocks=None):
    """s_eff >= need, by ZTL: the proved bracket at the conductivity box's ends (G is non-decreasing in every
    phase conductivity), provenance the weakest input's. phases: {id: {"s": [lo, hi] | [v], "earned": bool}}."""
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    boxes = {k: _box(p["s"], f"phase {k} conductivity") for k, p in phases.items()}
    lo, _, note = s_eff(V, {k: b[0] for k, b in boxes.items()}, refine, blocks)
    _, up, _ = s_eff(V, {k: b[1] for k, b in boxes.items()}, refine, blocks)
    used = set(np.unique(np.asarray(V)).tolist())
    prov = "earned:conduction3d" if all(phases[k].get("earned") for k in used if k in phases) else "credit"
    f = lambda x: f"{x.numerator}/{x.denominator}"
    qs, mk = parse_quantities(f"seff=[{f(lo)},{f(up)}] {prov}")
    nd = F(need)
    r = judge_sheet_claim(f"seff >= {f(nd)}", qs, mk)
    return {"lower": float(lo), "upper": float(up), "note": note,
            "verdict": r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else ""),
            "premise": "linear conduction; the voxel map is the sample; electrodes x = 0 / x = nx, other faces "
                       "insulated; IEEE 754 rounding (bounded)"}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    V = np.load(argv[0])
    s, need, refine, blocks = {}, None, 1, None
    i = 1
    while i < len(argv):
        if argv[i] == "--s":
            k, v = argv[i + 1].split(":")
            s[int(k)] = {"s": [v] if "," not in v else v.split(","), "earned": False}
            i += 2
        elif argv[i] == "--need":
            need = argv[i + 1]; i += 2
        elif argv[i] == "--refine":
            refine = int(argv[i + 1]); i += 2
        elif argv[i] == "--blocks":                      # px,py,pz: x-slabs (upper) and y-z columns (lower)
            blocks = tuple(int(x) for x in argv[i + 1].split(",")); i += 2
        else:
            raise SystemExit(f"unknown argument {argv[i]}")
    if need is None:
        # the box's ends (2026-11-03: both bounds were computed at the LOW end, so with a box the printed upper bound
        # did not cover its high end — found beside the round-2 finding): lower at lo, upper at hi (G is monotone)
        boxes = {k: _box(p["s"], f"phase {k} conductivity") for k, p in s.items()}
        lo, _, note = s_eff(V, {k: b[0] for k, b in boxes.items()}, refine, blocks)
        _, up, _ = s_eff(V, {k: b[1] for k, b in boxes.items()}, refine, blocks)
        print(json.dumps({"s_eff_lower": float(lo), "s_eff_upper": float(up), "note": note}))
    else:
        print(json.dumps(judge(V, s, need, refine, blocks)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
