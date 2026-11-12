# -*- coding: utf-8 -*-
"""
tetfea2 — the P2 LOWER side: a PROVED lower bound on the compliance with v piecewise QUADRATIC on the deck's own
straight-sided tets (2026-11-12; research/cad/PLAN-level2.md, "A P2 lower side"). ustand.tetfea (P1) is untouched.

THE BOUND is tetfea's: C(load) >= W(v)^2 / a(v, v) for ANY v in H^1 vanishing on the supports. Here v is the
standard 10-node quadratic on each affine tet — values at the 4 vertices and at the 6 edge MIDPOINT dofs; the
midpoint coordinate is never a node of the geometry (shape functions in barycentrics: N_i = l_i (2 l_i - 1),
N_ij = 4 l_i l_j). Admissible: v = 0 at every supported vertex and at the midpoint dof of every edge whose two ends
are supported (then v = 0 on every support face; a superset, still a subspace) — CHECKED again on the support faces
(tetmesh kind 1) before any bound is returned.

THE LOAD (the same continuum traction as the UPPER side, not the P1 lower side's — see traction_flux):
  q (nf, 3, 3) the prescribed flux at each loaded face's 3 vertices, q = t * |n2| (|n2| = twice the face area),
  exactly the array ustand.cadbracket hands to the equilibrated side (its exact Fractions are Fr(float(q))). The
  traction is t = sum_p l_p q_p / (2 A) on the face, LINEAR; its work on a quadratic v is (the 2 A cancels):
      int_F t . v = sum_p q_p . [ sum_i w_v(p, i) v_i + sum_e w_e(p, e) v_e ] / 120,
      w_v = 2 (i = p), -1 (i != p);   w_e = 8 (p an end of e), 4 (p opposite e)
  (int_F l^a l^b l^c = 2A a! b! c! / (a + b + c + 2)!) — exact rational weights, no area, no square root.
  The prestress (level 3b/3c): l_p(v) = int_omega grad v : sig_e, grad v = sum_k l_k G_k LINEAR in a tet (G_k: the
  gradient at vertex k), sig_e constant or linear (its vertex values sig_k):
      constant: |T| / 4 (sum_k G_k) : sig;   linear: |T| / 20 [ sum_k G_k : sig_k + (sum_k G_k) : (sum_k sig_k) ].
THE ENERGY: int_T Q(grad v) with Q quadratic and grad v linear: |T| / 20 [ sum_k Q(G_k) + Q(sum_k G_k) ] (exact for
  degree 2: int l_k l_l = |T| (1 + d_kl) / 20). In integers, with h_i = det * grad l_i (the adjugate rows, the
  coordinates over 10^k) and M_k = sum_i (4 d_ik - 1) V_i (x) h_i + 4 sum_(j != k) V_kj (x) h_j  (V = v 2^S):
      a(v, v) = sum_T [ sum_k (mu Q1 + lam Q2)(M_k) + (mu Q1 + lam Q2)(sum_k M_k) ] / (120 10^k 2^(2S) |det|),
  Q1, Q2 as in tetfea. a_upper_float2 bounds it with errfloat.Ev (every rounding carried); a_upper_exact2 mirrors
  tetfea.a_upper_exact (each tet's exact rational rounded up, then summed and raised); a_exact2 the exact Fraction
  (small meshes / tests). For a P1 field embedded in P2 (midpoints = means of the ends) every M_k = tetfea's M and
  each tet's rational is tetfea's: a_upper_exact2 = tetfea.a_upper_exact BIT FOR BIT (tests/test_p2.py).

PLANTED (tests only; module switch _PLANTED): "a_weight" — 1/24 for 1/20 in a(v, v) (too small, both routes);
"free_midpoint" — one midpoint dof on a support face left free (and not zeroed); "traction_p1" — the traction's work
taken with the P1 formula on the vertex values only (A/12 (2, 1, 1) per face, midpoints ignored).
"""
from __future__ import annotations

import math
import time
from fractions import Fraction as Fr

import numpy as np

from . import tetfea as TF, tetmesh as TM

S = TF.S
U = 2.0 ** -53
LE = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))       # the tet's local edges; local P2 node 4 + e
FE = ((0, 1), (0, 2), (1, 2))                                # a face's local edges (of its sorted vertex triple)
_PLANTED = None


def _pl(name):
    return _PLANTED == name


# ------------------------------------------------------------------------------------------------ the load's flux
def traction_flux(deck, X, F, own, idx, fixed, Fv, Mv):
    """THE traction of the load, as the equilibrated side takes it (moved here from ustand.cadbracket, unchanged, so
    that both sides read ONE definition): -> (kind (nf,), q (nf, 3, 3)).
    coarse deck: f_i = the RBE3 distribution of (Fv, Mv); t = M_s^-1 f solved in floats (tetmesh.rbe3_traction);
    refined deck: t = deck["traction"]["nodal"] (the coarse traction's values at the fine nodes). Then on every loaded
    face q[f, p] = t(F[f, p]) * |n2_f| in binary64 — and THIS q (its exact Fractions Fr(float(q))) defines the
    continuum traction t_q = sum_p l_p q_p / (2 A) on each face that the upper side equilibrates and the P2 lower side
    works against. (The P1 lower side works against the traction whose consistent loads are f_i themselves — the
    same up to the float solve of M_s t = f; MEASURED in tests/test_p2.py.)"""
    trc = deck.get("traction")
    if trc is not None:
        kind = TM.classify(F, own, fixed, {idx[n] for n in trc["nodal"]})
        tr = {idx[n]: np.asarray(v, float) for n, v in trc["nodal"].items()}
    else:
        ref, _, rn = deck["rbe3"][0]
        kind = TM.classify(F, own, fixed, {idx[n] for n in rn})
        xyz = {n: list(X[idx[n]]) for n in rn + [ref]}
        fl = TF.rbe3_loads(xyz, ref, rn, Fv, Mv)
        tr, res, lost = TM.rbe3_traction(X, F, kind, {idx[n]: fl[i] for i, n in enumerate(rn)})
        if lost:
            raise ValueError(f"{len(lost)} RBE3 nodal forces on nodes of no loaded face: the load is not a traction "
                             f"here")
    A, B, C = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    n2 = np.linalg.norm(np.cross(B - A, C - A), axis=1)
    q = np.zeros((len(F), 3, 3))
    for fid in np.where(kind == 2)[0]:
        for p_ in range(3):
            q[fid, p_] = tr[int(F[fid, p_])] * n2[fid]
    return kind, q


def _face_weights(plantable=True):
    """W[p, j]: the weight (over 120) of the face's local P2 node j (0..2 vertices, 3..5 the edges FE) against q_p."""
    W = np.zeros((3, 6), np.int64)
    for p in range(3):
        for i in range(3):
            W[p, i] = 2 if i == p else -1
        for e, (i, j) in enumerate(FE):
            W[p, 3 + e] = 8 if p in (i, j) else 4
    if plantable and _pl("traction_p1"):
        W[:] = 0
        for p in range(3):
            for i in range(3):
                W[p, i] = 10 if i == p else 5          # A/12 (2, 1, 1) = 2A (10, 5, 5) / 120, the vertices only
    return W


# ------------------------------------------------------------------------------------------------ the P2 space
def setup2(deck, E=None, nu=None, log=print, solver=True):
    """The part posed once with P2: exact coordinates, the material, the supports, the edges (midpoint dofs), and —
    if solver — the float P2 stiffness with its smoothed-aggregation AMG (the six rigid motions). -> ctx2."""
    import scipy.sparse as sp
    t0 = time.time()
    g = deck["grids"]
    ids = sorted(g)
    idx = {n: i for i, n in enumerate(ids)}
    dec = {n: tuple(TF._nas(x) for x in g[n]) for n in ids}
    k = max(max(len(str(x.denominator)) - 1 for x in p) for p in dec.values())
    while any((x * 10 ** k).denominator != 1 for p in dec.values() for x in p):
        k += 1
    XI = [tuple(int(x * 10 ** k) for x in dec[n]) for n in ids]
    X = np.array([[float(x) for x in dec[n]] for n in ids])
    E = Fr(str(E)) if E is not None else deck["mat"][0]
    nu = Fr(str(nu)) if nu is not None else deck["mat"][1]
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    tets = [tuple(idx[n] for n in t) for t in deck["tets"] if all(n in idx for n in t)]
    T = np.array(tets, dtype=np.int64)
    fixed = set()
    for ind, deps in deck["rbe2"]:
        if deck["spc"].get(ind, "").startswith("123"):
            fixed |= {idx[n] for n in deps if n in idx}
    nv, nt = len(ids), len(T)
    # ---- the edges: the midpoint dofs, node numbers nv + edge id
    pairs = np.sort(T[:, list(LE)], axis=2).reshape(-1, 2)
    key = pairs[:, 0] * nv + pairs[:, 1]
    ukey, inv = np.unique(key, return_inverse=True)
    te = inv.reshape(nt, 6)
    edges = np.stack([ukey // nv, ukey % nv], axis=1)
    ne = len(edges)
    nn = nv + ne
    fx = np.zeros(nv, bool)
    fx[sorted(fixed)] = True
    fixed_edge = fx[edges[:, 0]] & fx[edges[:, 1]]
    Fm, own, _, _ = TM.faces(T)
    kind_s = TM.classify(Fm, own, fixed, set())                 # kind 1: support faces (all 3 vertices supported)
    fk = np.searchsorted(ukey, np.stack([Fm[:, a] * nv + Fm[:, b] for a, b in FE], axis=1))   # (nf, 3) face edges
    if _pl("free_midpoint"):
        sf = np.where(kind_s == 1)[0]
        if len(sf):
            fixed_edge = fixed_edge.copy()
            fixed_edge[fk[sf[0], 0]] = False                    # PLANTED: one support-face midpoint left free
    fixed_node = np.concatenate([fx, fixed_edge])
    ndof = 3 * nn
    free = np.repeat(~fixed_node, 3)
    ctx = dict(t0=t0, deck=deck, ids=ids, idx=idx, dec=dec, k=k, XI=XI, X=X, E=E, nu=nu, mu=mu, lam=lam, tets=tets,
               T=T, fixed=fixed, nv=nv, ne=ne, nn=nn, ndof=ndof, edges=edges, te=te, fixed_node=fixed_node,
               free=free, F=Fm, own=own, kind_s=kind_s, fedge=fk, ukey=ukey)
    P = X[T]
    D = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=2)
    Dinv = np.linalg.inv(D)
    ctx["grads"] = np.concatenate([-Dinv.sum(axis=1, keepdims=True), Dinv], axis=1)      # (nt, 4, 3)
    ctx["vol"] = np.abs(np.linalg.det(D)) / 6
    ctx["P"] = P
    log(f"  P2: {nv} vertices + {ne} midpoints = {nn} nodes, {ndof} dof ({int(free.sum())} free), {nt} tets; "
        f"{time.time() - t0:.1f} s")
    if not solver:
        return ctx
    # ---- the float P2 stiffness (only to CHOOSE v), chunked
    mu_f, lam_f = float(mu), float(lam)
    I3 = np.eye(3)
    nodes = np.concatenate([T, nv + te], axis=1)                # (nt, 10) the tet's P2 nodes
    K = sp.csr_matrix((ndof, ndof))
    CH = 20000
    for c0 in range(0, nt, CH):
        gr = ctx["grads"][c0:c0 + CH]
        Gm = gamma(gr)                                          # (n, 10, 4, 3)
        Sg = Gm.sum(axis=2)
        H = (np.einsum("nakx,nbky->nabxy", Gm, Gm) + np.einsum("nax,nby->nabxy", Sg, Sg)) \
            * (ctx["vol"][c0:c0 + CH] / 20)[:, None, None, None, None]
        trH = np.einsum("nabxx->nab", H)
        Ke = (mu_f * np.einsum("nab,cd->nacbd", trH, I3) + mu_f * np.einsum("nabdc->nacbd", H)
              + lam_f * np.einsum("nabcd->nacbd", H))
        dofs = (3 * nodes[c0:c0 + CH, :, None] + np.arange(3)[None, None, :]).reshape(len(gr), 30)
        rows = np.repeat(dofs, 30, axis=1).ravel()
        cols = np.tile(dofs, (1, 30)).ravel()
        K = K + sp.csr_matrix((Ke.reshape(len(gr), 900).ravel(), (rows, cols)), shape=(ndof, ndof))
        del Ke, H, Gm
    Kf = K[free][:, free]
    nnz = K.nnz
    del K
    log(f"  P2 assembled: {nnz} nonzeros; {time.time() - t0:.1f} s")
    import pyamg
    Xn = np.concatenate([X, 0.5 * (X[edges[:, 0]] + X[edges[:, 1]])])     # node positions (floats: the solver only)
    Xr = Xn.repeat(3, axis=0)
    comp = np.tile(np.arange(3), nn)
    B = np.zeros((ndof, 6))
    for c3 in range(3):
        B[comp == c3, c3] = 1.0
    B[comp == 0, 3], B[comp == 1, 3] = -Xr[comp == 0, 1], Xr[comp == 1, 0]
    B[comp == 1, 4], B[comp == 2, 4] = -Xr[comp == 1, 2], Xr[comp == 2, 1]
    B[comp == 0, 5], B[comp == 2, 5] = Xr[comp == 0, 2], -Xr[comp == 2, 0]
    ctx["ml"] = pyamg.smoothed_aggregation_solver(Kf, B=B[free], symmetry="symmetric", max_coarse=500)
    ctx["Kf"] = Kf
    ctx["nnz"] = nnz
    log(f"  P2 AMG built; {time.time() - t0:.1f} s")
    return ctx


def gamma(g):
    """g (n, 4, 3) the barycentric gradients -> (n, 10, 4, 3): the gradient of each P2 shape function at each vertex
    (vertex a: (4 d_ak - 1) g_a; edge (i, j): 4 (d_jk g_i + d_ik g_j))."""
    n = len(g)
    Gm = np.zeros((n, 10, 4, 3))
    for a in range(4):
        Gm[:, a, :, :] = -g[:, a, None, :]
        Gm[:, a, a, :] = 3 * g[:, a]
    for e, (i, j) in enumerate(LE):
        Gm[:, 4 + e, j] = 4 * g[:, i]
        Gm[:, 4 + e, i] = 4 * g[:, j]
    return Gm


def embed_p1(ctx, vi):
    """A P1 integer field (3 nv, every entry EVEN) as the P2 field it is: midpoints = the means of the ends."""
    V = np.asarray(vi, dtype=np.int64).reshape(-1, 3)
    if (V % 2).any():
        raise ValueError("embed_p1 needs even integers (the midpoint means must be integers)")
    e = ctx["edges"]
    return np.concatenate([V, (V[e[:, 0]] + V[e[:, 1]]) // 2]).ravel()


# ------------------------------------------------------------------------------------------------ the load (P2)
def _load_FM(ctx, subcase):
    deck = ctx["deck"]
    custom = isinstance(subcase, dict)
    lid = None if custom else int(deck["subcases"][subcase]["LOAD"])
    F, Mm = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    if custom:
        F = tuple(float(x) for x in subcase.get("F", F))
        Mm = tuple(float(x) for x in subcase.get("M", Mm))
    elif lid in deck["force"]:
        ref, sc, v = deck["force"][lid]
        F = tuple(float(sc * x) for x in v)
    if not custom and lid in deck["moment"]:
        ref, sc, v = deck["moment"][lid]
        Mm = tuple(float(sc * x) for x in v)
    no_traction = custom and subcase.get("traction", True) is False
    if no_traction and (any(F) or any(Mm)):
        raise ValueError("a load posed without traction must have F = M = 0")
    trc = deck.get("traction")
    if trc is not None and not no_traction:
        if custom:
            same = all(abs(a - b) <= 1e-9 * (1 + abs(b)) for a, b in zip(F + Mm, tuple(trc["F"]) + tuple(trc["M"])))
        else:
            same = subcase == trc["subcase"]
        if not same:
            raise ValueError("a refined deck carries the traction of ONE load; this subcase / load is not it")
    return custom, F, Mm, no_traction


def case_load2(ctx, subcase, q=None):
    """One load on the P2-posed part -> dict: q (the traction's flux, None without traction), fvec (its float P2
    consistent loads), ftot (+ the prestress's float P2 vector: only CHOOSES v), F, M, pre, om, custom.
    q: the flux array as the upper side has it (traction_flux) — passed in by cadbracket so that BOTH sides use the
    very same array; computed here (by the same function) if not given."""
    custom, F, Mm, no_traction = _load_FM(ctx, subcase)
    ndof = ctx["ndof"]
    fvec = np.zeros(ndof)
    if no_traction:
        q = None
    else:
        if q is None:
            _, q = traction_flux(ctx["deck"], ctx["X"], ctx["F"], ctx["own"], ctx["idx"], ctx["fixed"], F, Mm)
        lf = np.where(np.abs(q).reshape(len(q), -1).max(axis=1) > 0)[0]
        W = _face_weights(plantable=False)             # the float load stays the TRUE one under the plant
        Fm, fk, nv = ctx["F"], ctx["fedge"], ctx["nv"]
        nodes6 = np.concatenate([Fm[lf], nv + fk[lf]], axis=1)            # (nl, 6)
        contrib = np.einsum("pj,fpc->fjc", W.astype(float), q[lf]) / 120.0
        np.add.at(fvec, (3 * nodes6[:, :, None] + np.arange(3)[None, None, :]).ravel(), contrib.ravel())
    pre = subcase.get("prestress") if custom else None
    ftot = fvec
    om = None
    if pre is not None:
        if len(ctx["tets"]) != len(ctx["deck"]["tets"]):
            raise ValueError("a prestress region needs every deck tet on the mesh")
        om = np.asarray(pre["omega"], bool)
        Gm = gamma(ctx["grads"][om])
        vol = ctx["vol"][om]
        if "S1" in pre:
            S0f = np.array([[float(x) for x in r] for r in pre["S0"]])
            S1f = np.array([[[float(x) for x in c] for c in r] for r in pre["S1"]])
            sgk = S0f[None, None] + np.einsum("ijk,nlk->nlij", S1f, ctx["P"][om])         # (n, 4, 3, 3) at vertices
            contrib = (np.einsum("nakb,nkcb->nac", Gm, sgk)
                       + np.einsum("nab,ncb->nac", Gm.sum(axis=2), sgk.sum(axis=1))) * (vol / 20)[:, None, None]
        else:
            sgf = np.array([[float(x) for x in row] for row in pre["sigma"]])
            contrib = np.einsum("nab,cb->nac", Gm.sum(axis=2), sgf) * (vol / 4)[:, None, None]
        nodes = np.concatenate([ctx["T"][om], ctx["nv"] + ctx["te"][om]], axis=1)
        ftot = fvec.copy()
        np.add.at(ftot, (3 * nodes[:, :, None] + np.arange(3)[None, None, :]).ravel(), contrib.ravel())
    return dict(q=q, fvec=fvec, ftot=ftot, F=F, M=Mm, pre=pre, om=om, custom=custom)


def case_field2(ctx, ftot, tol=1e-9, log=print, maxiter=2000):
    """The float P2 solve (only CHOOSES v) and its exact integer field V = round(u 2^S) (np.int64, 3 nn), exactly 0
    on the fixed dofs. -> (u, V, residual history)."""
    free = ctx["free"]
    res = []
    uf = ctx["ml"].solve(ftot[free], tol=tol, accel="cg", maxiter=maxiter, residuals=res)
    log(f"  P2 solved: {len(res)} iterations, residual {res[-1] / res[0]:.2e}; {time.time() - ctx['t0']:.1f} s")
    u = np.zeros(ctx["ndof"])
    u[free] = uf
    V = np.rint(u * 2.0 ** S).astype(np.int64)
    V[~free] = 0
    return u, V, res


def check_admissible(ctx, V):
    """v = 0 on every support face: its 3 vertices and its 3 edge midpoints (from the FACES, independently of the
    fixed-dof mask the solve used). Raises if not."""
    V = np.asarray(V).reshape(-1, 3)
    sf = np.where(ctx["kind_s"] == 1)[0]
    nodes = np.concatenate([ctx["F"][sf], ctx["nv"] + ctx["fedge"][sf]], axis=1)
    bad = int((V[nodes.ravel()] != 0).any(axis=1).sum())
    if bad:
        raise ValueError(f"the P2 field is not admissible: {bad} support-face dofs nonzero")
    return True


# ------------------------------------------------------------------------------------------------ the exact works
def traction_work2(ctx, q, V):
    """f(v) EXACTLY for v = V / 2^S against the traction t_q (q taken as the binary64 values it is — the same exact
    Fractions the upper side's finish takes)."""
    V = np.asarray(V, dtype=np.int64).reshape(-1, 3)
    assert np.abs(V).max(initial=0) < 2 ** 51
    lf = np.where(np.abs(q).reshape(len(q), -1).max(axis=1) > 0)[0]
    W = _face_weights()
    nodes6 = np.concatenate([ctx["F"][lf], ctx["nv"] + ctx["fedge"][lf]], axis=1)
    Vf = V[nodes6]                                              # (nl, 6, 3) integers
    comb = np.einsum("pj,fjc->fpc", W, Vf)                      # int64: |.| < 2^51 * 24 < 2^56
    acc = Fr(0)
    qv = q[lf]
    for f in range(len(lf)):
        for p in range(3):
            for c in range(3):
                x = float(qv[f, p, c])
                if x != 0.0 and comb[f, p, c] != 0:
                    acc += Fr(x) * int(comb[f, p, c])
    return acc / (120 * 2 ** S)


def _tet_ints(XI, tet):
    p0, p1, p2, p3 = tet
    x0 = XI[p0]
    (a11, a12, a13), (a21, a22, a23), (a31, a32, a33) = [[XI[q][r] - x0[r] for q in (p1, p2, p3)] for r in range(3)]
    dt = a11 * (a22 * a33 - a23 * a32) - a12 * (a21 * a33 - a23 * a31) + a13 * (a21 * a32 - a22 * a31)
    if dt == 0:
        raise ValueError("a degenerate tetrahedron")
    adj = [[a22 * a33 - a23 * a32, a13 * a32 - a12 * a33, a12 * a23 - a13 * a22],
           [a23 * a31 - a21 * a33, a11 * a33 - a13 * a31, a13 * a21 - a11 * a23],
           [a21 * a32 - a22 * a31, a12 * a31 - a11 * a32, a11 * a22 - a12 * a21]]
    h = [[-(adj[0][b] + adj[1][b] + adj[2][b]) for b in range(3)], adj[0], adj[1], adj[2]]
    return dt, h


def _Mk_int(h, Vt):
    """Vt: the 10 nodal integer 3-vectors of the tet (4 vertices, 6 edges in LE order) -> [M_0..M_3], M_sum."""
    eid = {}
    for e, (i, j) in enumerate(LE):
        eid[(i, j)] = eid[(j, i)] = 4 + e
    Ms = []
    for kk in range(4):
        M = [[0] * 3 for _ in range(3)]
        for i in range(4):
            cf = 3 if i == kk else -1
            for c in range(3):
                vc = cf * Vt[i][c]
                if vc:
                    for b in range(3):
                        M[c][b] += vc * h[i][b]
        for j in range(4):
            if j == kk:
                continue
            ve = Vt[eid[(kk, j)]]
            for c in range(3):
                vc = 4 * ve[c]
                if vc:
                    for b in range(3):
                        M[c][b] += vc * h[j][b]
        Ms.append(M)
    Msum = [[sum(Ms[kk][c][b] for kk in range(4)) for b in range(3)] for c in range(3)]
    return Ms, Msum


def _q12(M):
    q1 = 2 * (M[0][0] ** 2 + M[1][1] ** 2 + M[2][2] ** 2) + (M[0][1] + M[1][0]) ** 2 \
        + (M[0][2] + M[2][0]) ** 2 + (M[1][2] + M[2][1]) ** 2
    q2 = (M[0][0] + M[1][1] + M[2][2]) ** 2
    return q1, q2


def _tet_V(ctx, t, V):
    T, te, nv = ctx["tets"], ctx["te"], ctx["nv"]
    nodes = list(T[t]) + [nv + int(x) for x in te[t]]
    return [[int(V[3 * n + c]) for c in range(3)] for n in nodes]


def _a_terms(ctx, V):
    """per tet: (num, dd) with the exact term = num / dd (tetfea.a_upper_exact's form, 120 for its 6)"""
    mu, lam, k, XI = ctx["mu"], ctx["lam"], ctx["k"], ctx["XI"]
    mu_n, mu_d, la_n, la_d = mu.numerator, mu.denominator, lam.numerator, lam.denominator
    den0 = (144 if _pl("a_weight") else 120) * 10 ** k * 2 ** (2 * S)
    V = np.asarray(V, dtype=np.int64).ravel()
    for t in range(len(ctx["tets"])):
        dt, h = _tet_ints(XI, ctx["tets"][t])
        Ms, Msum = _Mk_int(h, _tet_V(ctx, t, V))
        q1 = q2 = 0
        for M in Ms + [Msum]:
            a1, a2 = _q12(M)
            q1 += a1
            q2 += a2
        yield mu_n * la_d * q1 + la_n * mu_d * q2, den0 * abs(dt) * mu_d * la_d


def a_upper_exact2(ctx, V):
    """the exact-integer upper bound on a(v, v), tetfea.a_upper_exact's accumulation exactly"""
    a_up, nT = 0.0, 0
    for num, dd in _a_terms(ctx, V):
        a_up += math.nextafter(num / dd, math.inf)
        nT += 1
    a_up = a_up * (1 + (nT + 1) * U) * (1 + U)
    return math.nextafter(a_up, math.inf)


def a_exact2(ctx, V):
    """a(v, v) as an exact Fraction (small meshes: the denominators grow with the number of tets)"""
    return sum((Fr(num, dd) for num, dd in _a_terms(ctx, V)), Fr(0))


def a_upper_float2(ctx, V, chunk=50000):
    """a PROVED upper bound on a(v, v), vectorised with errfloat.Ev: the integer coordinates XI (exact in binary64
    when < 2^53, else rounded once and carried), their differences, the adjugate, det, M_k = sum coef V (x) h, the
    quadratic forms, the division by |det| and the sums — every operation's rounding carried; the readout steps up."""
    from .errfloat import Ev
    XIa = np.asarray(ctx["XI"], dtype=object)
    big = max(abs(int(x)) for x in XIa.ravel()) >= 2 ** 53
    XF = np.asarray(ctx["XI"], dtype=np.float64)
    V = np.asarray(V, dtype=np.int64).reshape(-1, 3)
    assert np.abs(V).max(initial=0) < 2 ** 51
    Vf = V.astype(np.float64)
    T, te, nv, k = ctx["T"], ctx["te"], ctx["nv"], ctx["k"]
    mu = Ev.rounded(np.float64(float(ctx["mu"])))
    lam = Ev.rounded(np.float64(float(ctx["lam"])))
    tk = Ev.exact(np.float64(10.0 ** k)) if k <= 22 else Ev.rounded(np.float64(10.0 ** k))
    c120 = Ev.exact(np.float64((144 if _pl("a_weight") else 120) * 2.0 ** (2 * S))) * tk
    total = None
    nt = len(T)
    for c0 in range(0, nt, chunk):
        Tc = T[c0:c0 + chunk]
        P = XF[Tc]                                                  # (n, 4, 3)
        mk = Ev.rounded if big else Ev.exact
        Pe = [[mk(P[:, q, r]) for r in range(3)] for q in range(4)]
        a = [[Pe[q + 1][r] - Pe[0][r] for q in range(3)] for r in range(3)]          # a[r][q]
        adj = [[a[1][1] * a[2][2] - a[1][2] * a[2][1], a[0][2] * a[2][1] - a[0][1] * a[2][2],
                a[0][1] * a[1][2] - a[0][2] * a[1][1]],
               [a[1][2] * a[2][0] - a[1][0] * a[2][2], a[0][0] * a[2][2] - a[0][2] * a[2][0],
                a[0][2] * a[1][0] - a[0][0] * a[1][2]],
               [a[1][0] * a[2][1] - a[1][1] * a[2][0], a[0][1] * a[2][0] - a[0][0] * a[2][1],
                a[0][0] * a[1][1] - a[0][1] * a[1][0]]]
        det = a[0][0] * adj[0][0] + a[0][1] * adj[1][0] + a[0][2] * adj[2][0]
        if not (np.abs(det.v) > det.e).all():
            raise ZeroDivisionError("a tet whose determinant's sign is not certain")
        adet = Ev(np.abs(det.v), det.e)
        h = [[-(adj[0][b] + adj[1][b] + adj[2][b]) for b in range(3)], adj[0], adj[1], adj[2]]
        nodes = np.concatenate([Tc, nv + te[c0:c0 + chunk]], axis=1)
        Vt = [[Ev.exact(Vf[nodes[:, j], c]) for c in range(3)] for j in range(10)]
        eid = {}
        for e, (i, j) in enumerate(LE):
            eid[(i, j)] = eid[(j, i)] = 4 + e
        Ms = []
        for kk in range(4):
            M = [[None] * 3 for _ in range(3)]
            for c in range(3):
                for b in range(3):
                    acc = None
                    for i in range(4):
                        term = Vt[i][c] * h[i][b] * Ev.exact(np.float64(3.0 if i == kk else -1.0))
                        acc = term if acc is None else acc + term
                    for j in range(4):
                        if j != kk:
                            acc = acc + Vt[eid[(kk, j)]][c] * h[j][b] * Ev.exact(np.float64(4.0))
                    M[c][b] = acc
            Ms.append(M)
        Msum = [[Ms[0][c][b] + Ms[1][c][b] + Ms[2][c][b] + Ms[3][c][b] for b in range(3)] for c in range(3)]
        q1 = q2 = None
        for M in Ms + [Msum]:
            a1 = Ev.exact(np.float64(2.0)) * (M[0][0].sq() + M[1][1].sq() + M[2][2].sq()) \
                + (M[0][1] + M[1][0]).sq() + (M[0][2] + M[2][0]).sq() + (M[1][2] + M[2][1]).sq()
            a2 = (M[0][0] + M[1][1] + M[2][2]).sq()
            q1 = a1 if q1 is None else q1 + a1
            q2 = a2 if q2 is None else q2 + a2
        term = (mu * q1 + lam * q2) / (c120 * adet)
        s_ = term.sum()
        total = s_ if total is None else total + s_
    return float(np.nextafter(total.upper(), np.inf))


def prestress_work2(ctx, pre, om, V):
    """l_p(v) EXACTLY for the P2 field v = V / 2^S (the constant 3b prestress or the linear 3c extractor; exact
    rational weights, see the module docstring)."""
    XI, k, tets = ctx["XI"], ctx["k"], ctx["tets"]
    V = np.asarray(V, dtype=np.int64).ravel()
    linear = "S1" in pre
    acc = Fr(0)
    for t in np.where(om)[0]:
        t = int(t)
        dt, h = _tet_ints(XI, tets[t])
        Ms, Msum = _Mk_int(h, _tet_V(ctx, t, V))
        if linear:
            sgk = []
            for q in tets[t]:
                x = [Fr(XI[q][r], 10 ** k) for r in range(3)]
                sgk.append([[pre["S0"][i][j] + sum(pre["S1"][i][j][kk] * x[kk] for kk in range(3)) for j in range(3)]
                            for i in range(3)])
            ssum = [[sum(sgk[l_][i][j] for l_ in range(4)) for j in range(3)] for i in range(3)]
            term = sum(Ms[kk][c][b] * sgk[kk][c][b] for kk in range(4) for c in range(3) for b in range(3)) \
                + sum(Msum[c][b] * ssum[c][b] for c in range(3) for b in range(3))
            term = term / 5                                     # /120 overall = /24 /5
        else:
            sg = pre["sigma"]
            term = sum(Msum[c][b] * sg[c][b] for c in range(3) for b in range(3))
        acc += term if dt > 0 else -term
    return acc / (24 * 2 ** S * 10 ** (2 * k))


def lower_bound2(ctx, V, q=None, pre=None, om=None, t_scale=1, p_scale=1, exact=False, works=None):
    """tetfea.lower_bound for a GIVEN integer P2 field V: C(t_scale f + p_scale p) >= W^2 / a_up(v, v), W exact.
    The field is checked admissible on the support faces first. -> (lower Fraction, W, f(v), l_p(v) or None, a_up)."""
    check_admissible(ctx, V)
    if works is None:
        fv = traction_work2(ctx, q, V) if (q is not None and t_scale != 0) else Fr(0)
        fp = prestress_work2(ctx, pre, om, V) if (pre is not None and p_scale != 0) else None
    else:
        fv, fp = works
    W = Fr(t_scale) * fv + (Fr(p_scale) * fp if fp is not None else 0)
    a_up = a_upper_exact2(ctx, V) if exact else a_upper_float2(ctx, V)
    return W * W / Fr(a_up), W, fv, fp, a_up


def solve_case2(deck, subcase, q=None, tol=1e-4, log=print, exact=False, ctx=None):
    """setup2 + case_load2 + case_field2 + lower_bound2 -> dict (mirrors tetfea.solve_cases' output keys)."""
    t0 = time.time()
    if ctx is None:
        ctx = setup2(deck, log=log)
    L = case_load2(ctx, subcase, q=q)
    u, V, res = case_field2(ctx, L["ftot"], tol=tol, log=log)
    c_float = float(L["ftot"] @ u)
    lower, W, fv, fp, a_up = lower_bound2(ctx, V, L["q"], L["pre"], L["om"], exact=exact)
    out = {"compliance_float": c_float, "compliance_lower_proved": float(lower) * (1 - 2 * U),
           "lower_exact": lower, "f_v_exact": float(fv), "a_vv_up": a_up, "dof": ctx["ndof"],
           "dof_free": int(ctx["free"].sum()), "midpoints": ctx["ne"], "nnz": ctx.get("nnz"),
           "cg_iterations": len(res), "residual": res[-1] / res[0] if res else None,
           "seconds": round(time.time() - t0, 1), "V": V, "u": u}
    if fp is not None:
        out["prestress_work_exact"] = float(fp)
    return out
