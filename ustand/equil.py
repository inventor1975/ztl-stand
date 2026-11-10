# -*- coding: utf-8 -*-
"""
equil — CHOOSING an equilibrated stress on a tet mesh by HYBRIDIZATION (2026-11-10, CAD/FEA level 2b at scale).
Only chooses: the exact admissibility (the forest push) and the exact energy come after, elsewhere.

Unknowns: the face data g of the Alfeld element per tet (36 = 4 faces x 3 vertices x 3: tau(p_v) n2_out).
Prescribed faces (a load traction, a free face = 0, an interface flux fixed from outside) carry known g; support
faces carry free g (reactions); interior faces carry free g with the CONTINUITY condition: the two tets' outward data
sum to 0. Per tet, the local problem
      min 1/2 g^T S g + lam^T g   subject to   BAL g = 0,   g = given on the prescribed slots
(S the compliance form (1/E)((1 + nu) Q1 - nu Q2), lam a displacement-like trace on the faces, 0 on support faces)
is a 42 x 42 KKT, batched: g = -Z lam + z0. Continuity on every interior face gives sum_T E_T^T (Z_T E_T lam - z0_T) = 0
— an SPD system on lam (9 per interior face; singular by the rigid motions when no face is supported), solved by
smoothed-aggregation AMG + CG (rigid near-null space at the face vertices) or a direct solve when small.
"""
from __future__ import annotations

import numpy as np

from . import alfeld as AL

PRESCRIBED_KINDS = (2, 3)          # tetmesh kinds: 2 loaded, 3 free; 0 interior, 1 support


def choose(X, T, F, owner, tface, kind, E, nu, qpres, iface=None, tol=1e-10, direct=None, log=None,
           zdtype=np.float64, matfree=False, maxiter=20000, lin=None):
    """X (nv, 3), T (nt, 4), F/owner/tface/kind from tetmesh; qpres: (nf, 3, 3) the prescribed FLUX q at each face's
    3 vertices (in F's vertex order, oriented as owner[:, 0]'s outward normal) — used on loaded / free / interface
    faces; iface: a bool mask of faces to treat as prescribed in addition (interfaces of a subdomain);
    lin: (nt, 36) or None, a LINEAR term added to each tet's energy (minimise 1/2 g^T S g + lin . g; level 3b: the
    prestress cross term, see prestress_linear_float — only the local right-hand sides change, Z does not).
    -> g (nt, 36) the chosen face data per tet, float energy (g^T S g, without the linear term), info."""
    X = np.asarray(X, float)
    T = np.asarray(T, np.int64)
    nt, nf = len(T), len(F)
    pres = np.isin(kind, PRESCRIBED_KINDS)
    if iface is not None:
        pres = pres | iface
    lam_face = (kind == 0) & ~pres                     # continuity faces carry lam
    lidx = -np.ones(nf, np.int64)
    lidx[lam_face] = np.arange(lam_face.sum())
    nl = 9 * int(lam_face.sum())
    import time as _t
    t0 = _t.time()
    say = (lambda m: log(f"  [equil {(_t.time() - t0):.1f} s] {m}")) if log else (lambda m: None)
    # chunk of tets for the forms and the local KKTs: its temporaries (S, Q1, Q2, Sm, K, Ki: ~6 x 36^2..42^2 doubles a
    # tet) are a FIXED cost — MEASURED on 631 with tracemalloc: 2.0 GB transient at 20000; 8000 keeps it ~0.8 GB
    CH = 8000

    def forms(b):
        # the element forms of a CHUNK of tets, recomputed where needed instead of stored (2026-11-10, toward 640k
        # tets: Q1 + Q2 + S for all tets peaked at ~31 KB a tet — MEASURED ~54 KB/tet overall on SimJEB 40/631)
        Q1, Q2, BALb = AL.float_forms(X[T[b]])
        return ((1 + nu) * Q1 - nu * Q2) / E, BALb

    def energy_of(g):
        return float(sum(np.einsum("ni,nij,nj->", g[c0:c0 + CH], forms(slice(c0, min(nt, c0 + CH)))[0],
                                   g[c0:c0 + CH]) for c0 in range(0, nt, CH)))
    say(f"element forms: computed per chunk of {CH} tets ({nt} tets)")
    # per tet slot (f, jv, c): face, the vertex's position in F's sorted triple, the sign of the tet's outward normal
    # relative to the face's orientation (owner 0's outward)
    loc = np.array([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]])
    gl = np.empty((nt, 36), np.int64)                  # global lam index or -1
    gp = np.zeros((nt, 36))                            # prescribed g values (0 where free)
    open_ = np.zeros((nt, 36), bool)
    for f in range(4):
        fid = tface[:, f]
        verts = T[:, loc[f]]                           # local sorted order of alfeld = increasing local index
        sgn = np.where(owner[fid, 0] == np.arange(nt), 1.0, -1.0)
        for jv in range(3):
            pos = (F[fid] == verts[:, jv:jv + 1]).argmax(axis=1)          # the vertex's position in F[fid]
            for c in range(3):
                col = f * 9 + jv * 3 + c
                isp = pres[fid]
                gp[:, col] = np.where(isp, sgn * qpres[fid, pos, c], 0.0)
                open_[:, col] = ~isp
                gl[:, col] = np.where(lam_face[fid], 9 * lidx[fid] + 3 * pos + c, -1)
    # batched local KKT
    # Z may be stored in float32 (zdtype): it only CHOOSES — the exact push and the rigorous energy make the bound,
    # so float32 never costs validity. But it costs a LOT of tightness, MEASURED 2026-11-10 on SimJEB: the float32
    # choice is as good as float64 (631: 45686 vs 45677), its balance/continuity errors are not, and the exact push
    # over the forest inflates them (proved upper 631: 61518 vs 45677; 40: 44812 vs 31382). Callers default to float64.
    Z = np.zeros((nt, 36, 36), zdtype)
    z0 = np.zeros((nt, 36))
    for c0 in range(0, nt, CH):
        b = slice(c0, min(nt, c0 + CH))
        Sb, BALb = forms(b)
        o = open_[b]
        Sm = np.where(o[:, :, None] & o[:, None, :], Sb, 0.0)
        ii = np.arange(36)
        Sm[:, ii, ii] = np.where(o, Sm[:, ii, ii], 1.0)
        Bm = np.where(o[:, None, :], BALb, 0.0)
        sc = np.abs(Sm).max(axis=(1, 2))
        K = np.zeros((Sm.shape[0], 42, 42))
        K[:, :36, :36] = Sm
        K[:, :36, 36:] = np.transpose(Bm, (0, 2, 1))
        K[:, 36:, :36] = Bm
        K[:, 36:, 36:] = -1e-13 * sc[:, None, None] * np.eye(6)[None]
        Ki = np.linalg.inv(K)
        g_p = gp[b]
        rhs = np.zeros((Sm.shape[0], 42))
        rhs[:, :36] = -np.where(o, np.einsum("nij,nj->ni", Sb, g_p), 0.0)
        if lin is not None:
            rhs[:, :36] -= np.where(o, lin[b], 0.0)
        rhs[:, 36:] = -np.einsum("nij,nj->ni", BALb, g_p)
        sol = np.einsum("nij,nj->ni", Ki, rhs)
        Z[b] = Ki[:, :36, :36] * (o[:, :, None] & o[:, None, :])
        z0[b] = np.where(o, sol[:, :36], 0.0)
    say("local KKTs")
    # global lam system: sum E^T Z E lam = sum E^T z0
    import scipy.sparse as sp
    m = gl >= 0
    if matfree and nl:
        # MATRIX-FREE (2026-11-10, the curator: «тянем до промышленного»): A is never assembled; A x = sum_T E^T Z_T E x
        # from the per-tet blocks (float32 Z: 1296 numbers a tet), CG with the 9 x 9 face-block Jacobi preconditioner.
        rhsl = np.zeros(nl)
        np.add.at(rhsl, gl[m], z0[m])
        glc = np.where(m, gl, 0)
        Zf = Z                                         # the stored dtype (float32 only when the caller asks)

        def Av(x):
            xt = np.where(m, x[glc], 0.0).astype(Zf.dtype)
            y = np.einsum("nij,nj->ni", Zf, xt, optimize=True)
            out = np.zeros(nl)
            np.add.at(out, gl[m], y[m].astype(np.float64))
            return out
        # the face-block diagonal: for each interior face, the 9 x 9 sum of its two tets' blocks
        Dg = np.zeros((nl // 9, 9, 9))
        fidx = gl // 9
        for f in range(4):
            sl = slice(9 * f, 9 * f + 9)
            ok = gl[:, 9 * f] >= 0
            P_ = gl[ok][:, sl] % 9
            Fi = fidx[ok][:, 9 * f]
            B_ = Z[ok][:, sl, sl].astype(np.float64)
            np.add.at(Dg, (Fi[:, None, None], P_[:, :, None], P_[:, None, :]), B_)
        d = np.einsum("fii->f", Dg)
        Dg += (1e-12 * float(np.abs(d).max())) * np.eye(9)[None]
        Dinv = np.linalg.inv(Dg)

        # AUXILIARY-SPACE correction (2026-11-10: block Jacobi alone did not converge on SimJEB 631 — residual ~3
        # after 2200 iterations): lam is a displacement-like trace at the faces' vertices, so the nodal P1 stiffness
        # (AMG with the rigid motions) approximates its system on the smooth modes; Pi maps a node's displacement to
        # every lam slot at that vertex.
        from . import tetmesh as _TM
        import pyamg
        K = _TM.p1_stiffness(X, T, E, nu)
        fixed_nodes = np.unique(F[kind == 1].ravel()) if (kind == 1).any() else np.array([], np.int64)
        freen = np.ones(len(X), bool)
        freen[fixed_nodes] = False
        freed = np.repeat(freen, 3)
        dmap = -np.ones(3 * len(X), np.int64)
        dmap[freed] = np.arange(int(freed.sum()))
        lf_faces = np.where(lam_face)[0]
        node_of = F[lf_faces].repeat(3, axis=1).ravel() * 3 + np.tile(np.arange(3), 3 * len(lf_faces))
        col = dmap[node_of]
        okc = col >= 0
        Pi = sp.csr_matrix((np.ones(int(okc.sum())), (np.arange(nl)[okc], col[okc])), shape=(nl, int(freed.sum())))
        Kf = K[freed][:, freed].tocsr()
        Xn = X[freen].repeat(3, axis=0)
        cmp = np.tile(np.arange(3), int(freen.sum()))
        Bn = np.zeros((Kf.shape[0], 6))
        for c3 in range(3):
            Bn[cmp == c3, c3] = 1.0
        Bn[cmp == 0, 3], Bn[cmp == 1, 3] = -Xn[cmp == 0, 1], Xn[cmp == 1, 0]
        Bn[cmp == 1, 4], Bn[cmp == 2, 4] = -Xn[cmp == 1, 2], Xn[cmp == 2, 1]
        Bn[cmp == 0, 5], Bn[cmp == 2, 5] = Xn[cmp == 0, 2], -Xn[cmp == 2, 0]
        mlK = pyamg.smoothed_aggregation_solver(Kf, B=Bn, symmetry="symmetric", max_coarse=500)
        Kpre = mlK.aspreconditioner(cycle="V")
        # scale: lam = Pi u for a nodal field u has the trace energy (Pi u)^T A (Pi u) ~ c u^T K u; the correction is
        # Pi (c K)^-1 Pi^T — c from random nodal probes (only a scale: the preconditioner stays SPD for any c > 0)
        rng = np.random.default_rng(0)
        cs = []
        for _ in range(3):
            u_ = rng.normal(size=Kf.shape[0])
            cs.append(float((Pi @ u_) @ Av(Pi @ u_)) / float(u_ @ (Kf @ u_)))
        c_aux = float(np.median(cs))
        say(f"auxiliary space: {Kf.shape[0]} nodal dof, AMG {len(mlK.levels)} levels, scale c = {c_aux:.3e}")

        def Mv(r):
            return np.einsum("fij,fj->fi", Dinv, r.reshape(-1, 9)).ravel() + (Pi @ Kpre(Pi.T @ r)) / c_aux
        x = np.zeros(nl)
        r = rhsl - Av(x)
        z = Mv(r)
        p_ = z.copy()
        rz = r @ z
        r0 = np.linalg.norm(r)
        it = 0
        while it < maxiter:
            Ap = Av(p_)
            al = rz / (p_ @ Ap)
            x += al * p_
            r -= al * Ap
            it += 1
            rn = np.linalg.norm(r)
            if it % 200 == 0:
                say(f"matrix-free CG iteration {it}: residual {rn / r0:.2e}")
            if rn <= tol * r0:
                break
            z = Mv(r)
            rz_new = r @ z
            p_ = z + (rz_new / rz) * p_
            rz = rz_new
        lam = x
        info = {"lam_unknowns": nl, "matfree": True, "cg_iterations": it, "cg_residual": rn / r0}
        say(f"matrix-free CG done: {it} iterations, residual {rn / r0:.2e}")
        lt = np.where(m, lam[np.maximum(gl, 0)], 0.0)
        g = np.empty_like(z0)
        for c0 in range(0, nt, 20000):
            b = slice(c0, min(nt, c0 + 20000))
            g[b] = -np.einsum("nij,nj->ni", Z[b].astype(np.float64), lt[b]) + z0[b] + gp[b]
        return g, energy_of(g), info
    A = sp.csr_matrix((nl, nl))
    for c0 in range(0, nt, 20000):                       # assembled in chunks, int32 indices
        b = slice(c0, min(nt, c0 + 20000))
        mb = m[b]
        okm = mb[:, :, None] & mb[:, None, :]
        glb = gl[b].astype(np.int32)
        rows = np.broadcast_to(glb[:, :, None], okm.shape)[okm]
        cols = np.broadcast_to(glb[:, None, :], okm.shape)[okm]
        A = A + sp.csr_matrix((Z[b][okm].astype(np.float64), (rows, cols)), shape=(nl, nl))
        del okm, rows, cols
    rhsl = np.zeros(nl)
    np.add.at(rhsl, gl[m], z0[m])
    info = {"lam_unknowns": nl, "nonzeros": A.nnz}
    say(f"trace system: {nl} unknowns, {A.nnz} nonzeros")
    if nl:
        d = A.diagonal()
        A = A + sp.diags(1e-12 * float(np.abs(d).max()) * np.ones(nl))
        if direct or (direct is None and nl < 60000):
            import scipy.sparse.linalg as spl
            lam = spl.spsolve(A.tocsc(), rhsl)
        else:
            import pyamg
            fv = np.where(lam_face)[0]
            P = X[F[fv]]                                             # (nlf, 3, 3) vertex coordinates
            xyz = P.reshape(-1, 3).repeat(3, axis=0)                 # per lam dof
            comp = np.tile(np.arange(3), len(xyz) // 3)
            Bn = np.zeros((nl, 6))
            for c3 in range(3):
                Bn[comp == c3, c3] = 1.0
            Bn[comp == 0, 3], Bn[comp == 1, 3] = -xyz[comp == 0, 1], xyz[comp == 1, 0]
            Bn[comp == 1, 4], Bn[comp == 2, 4] = -xyz[comp == 1, 2], xyz[comp == 2, 1]
            Bn[comp == 0, 5], Bn[comp == 2, 5] = xyz[comp == 0, 2], -xyz[comp == 2, 0]
            ml = pyamg.smoothed_aggregation_solver(A, B=Bn, symmetry="symmetric", max_coarse=500)
            say(f"AMG set up: {len(ml.levels)} levels")
            res = []
            cb = (lambda xk: say(f"CG iteration {len(res)}: residual {res[-1] / res[0]:.2e}")
                  if len(res) % 50 == 0 and res else None)
            lam = ml.solve(rhsl, tol=tol, accel="cg", maxiter=3000, residuals=res, callback=cb)
            info["cg_iterations"] = len(res)
            info["cg_residual"] = res[-1] / res[0] if res else None
            say(f"CG done: {len(res)} iterations, residual {info['cg_residual']:.2e}")
    else:
        lam = np.zeros(0)
    lt = np.where(m, lam[np.maximum(gl, 0)], 0.0) if nl else np.zeros_like(z0)   # no interior face: no trace
    g = np.empty_like(z0)
    for c0 in range(0, nt, 20000):
        b = slice(c0, min(nt, c0 + 20000))
        g[b] = -np.einsum("nij,nj->ni", Z[b].astype(np.float64), lt[b]) + z0[b] + gp[b]
    energy = energy_of(g)
    # continuity check (float): outward data of the two tets of every interior face sum to ~0
    return g, energy, info


def _solve_int(A, b):
    """FRACTION-FREE (Bareiss) solve of A x = b for an integer matrix A and integer b: -> (N, d) with x = N / d exactly,
    all integers (2026-11-10: the Fraction Gauss on the push's 6 x 6 systems was the finisher's largest cost)."""
    n = len(b)
    M = [list(row) + [b[i]] for i, row in enumerate(A)]
    prev = 1
    for k in range(n):
        if M[k][k] == 0:
            piv = next(i for i in range(k + 1, n) if M[i][k] != 0)
            M[k], M[piv] = M[piv], M[k]
        for i in range(k + 1, n):
            for j in range(k + 1, n + 1):
                M[i][j] = (M[k][k] * M[i][j] - M[i][k] * M[k][j]) // prev
            M[i][k] = 0
        prev = M[k][k]
    d = M[n - 1][n - 1]
    N = [0] * n
    for i in range(n - 1, -1, -1):
        acc = d * M[i][n] - sum(M[i][j] * N[j] for j in range(i + 1, n))
        N[i] = acc // M[i][i]                       # exact (Bareiss)
        assert N[i] * M[i][i] == acc
    return N, d


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


def slot_maps(T, F, owner, tface):
    """pos (nt, 4, 3): the position in F[face] of each local face's vertices (alfeld order); sgn (nt, 4): +1 if the
    tet is the face's owner 0 (its outward normal is the face's orientation), else -1."""
    T = np.asarray(T, np.int64)
    nt = len(T)
    loc = np.array([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]])
    pos = np.empty((nt, 4, 3), np.int64)
    for f in range(4):
        fid = tface[:, f]
        verts = T[:, loc[f]]
        for jv in range(3):
            pos[:, f, jv] = (F[fid] == verts[:, jv:jv + 1]).argmax(axis=1)
    sgn = np.where(owner[tface, 0] == np.arange(nt)[:, None], 1, -1)
    return pos, sgn


def face_flux_float(T, F, owner, tface, g, tets=None):
    """q (nf, 3, 3): every face's flux in owner 0's orientation, the AVERAGE of the data of its tets in `tets`."""
    nt = len(T)
    pos, sgn = slot_maps(T, F, owner, tface)
    use = np.ones(nt, bool) if tets is None else np.isin(np.arange(nt), tets)
    q = np.zeros((len(F), 3, 3))
    cnt = np.zeros(len(F))
    gg = g.reshape(nt, 4, 3, 3)
    for f in range(4):
        fid = tface[:, f]
        for jv in range(3):
            np.add.at(q, (fid[use], pos[use, f, jv]), sgn[use, f, None] * gg[use, f, jv])
        np.add.at(cnt, fid[use], 1.0)
    return q / np.maximum(cnt, 1)[:, None, None], pos, sgn


def finish(Xq, T, F, owner, tface, kind, g, qpres, tets=None, fixed_faces=None, E=None, nu=None, log=None):
    """EXACT admissibility and the exact energy (see the module docstring; 2026-11-10, optimised: the slot maps
    computed once, the float averages vectorised).
    Xq: exact vertex coordinates (Fractions); g: the float choice (nt, 36); qpres: exact prescribed fluxes
    {face: 3x3 Fractions} (loads, free = 0, interfaces); fixed_faces: faces whose q must not change.
    -> (q dict of exact fluxes, unbalanced tets, exact upper bound on the compliance energy if E, nu given,
    the largest denominator in bits)."""
    from collections import deque
    from fractions import Fraction as Fr
    nt = len(T)
    tets = list(range(nt)) if tets is None else [int(t) for t in tets]
    tset = set(tets)
    fixed_faces = set() if fixed_faces is None else set(fixed_faces)
    qf, pos, sgn = face_flux_float(T, F, owner, tface, g, tets)
    need = {int(x) for x in np.unique(tface[tets].ravel())}
    q = {}
    for fid in need:
        q[fid] = [list(r) for r in qpres[fid]] if fid in qpres else [[Fr(float(qf[fid, p_, c])) for c in range(3)]
                                                                  for p_ in range(3)]
    tf_ = tface
    P = {t: [list(Xq[v]) for v in T[t]] for t in tets}

    def g_exact(t):
        out = []
        for f in range(4):
            qq = q[int(tf_[t, f])]
            s_ = int(sgn[t, f])
            for jv in range(3):
                r = qq[int(pos[t, f, jv])]
                out += r if s_ > 0 else [-r[0], -r[1], -r[2]]
        return out
    # THE BALANCE MAP IN INTEGERS (2026-11-10, toward 5M tets: the Fraction sums were the finisher's whole cost —
    # MEASURED by cProfile on a 10k-tet box: 73 s, ~70 % inside fractions.py; on SimJEB 148 the push took 20 min and
    # held ~8 GB of Fractions). With Dx the common denominator of the coordinates, 24 Dx * (the 6 x 36 balance map)
    # is an integer matrix BI (force rows 4 Dx; moment rows sum (1 + d) XI). A residual row is then ONE integer dot
    # product over the tet's common denominator L of its face data, and one Fraction at the end: exact, no gcd per term.
    import math
    from math import lcm
    Dx = 1
    for t in tets:
        for v in T[t]:
            for x in Xq[v]:
                Dx = lcm(Dx, Fr(x).denominator)
    BI = None
    XIall = {}
    for t in tets:
        for v in T[t]:
            if v not in XIall:
                XIall[v] = [int(Fr(x) * Dx) for x in Xq[v]]
    # Python ints never overflow: the integer path always applies (2026-11-10: an int64 guard here sent every SimJEB
    # part, decimals with up to ~10 digits, back to the Fraction path — MEASURED on 631: 660 s under cProfile, _solve6
    # and bal_matrix still called 82414 times; the box with integer coordinates had passed the guard and hidden it)
    if True:
        BI = {}
        for t in tets:
            vsx = [XIall[int(v)] for v in T[t]]
            A = [[0] * 36 for _ in range(6)]
            for f in range(4):
                vs = [v for v in range(4) if v != f]
                for jv in range(3):
                    w = [sum((1 + (iv == jv)) * vsx[vv][k] for iv, vv in enumerate(vs)) for k in range(3)]
                    base = f * 9 + jv * 3
                    A[0][base] = A[1][base + 1] = A[2][base + 2] = 4 * Dx
                    A[4][base], A[5][base] = w[2], -w[1]
                    A[3][base + 1], A[5][base + 1] = -w[2], w[0]
                    A[3][base + 2], A[4][base + 2] = w[1], -w[0]
            BI[t] = A
    DB = 24 * Dx
    BM = None if BI is not None else {t: AL.bal_matrix(P[t]) for t in tets}

    def bm_entry(t, i, col):
        return Fr(BI[t][i][col], DB) if BI is not None else BM[t][i][col]

    def bal(t):
        gv = g_exact(t)
        if BI is None:
            return [sum(a * b for a, b in zip(row, gv) if a and b) for row in BM[t]]
        L = 1
        for x in gv:
            if x:
                L = lcm(L, x.denominator)
        nums = [x.numerator * (L // x.denominator) if x else 0 for x in gv]
        return [Fr(sum(a * b for a, b in zip(row, nums) if a and b), DB * L) for row in BI[t]]
    resid = {t: bal(t) for t in tets}
    adj = {t: [] for t in tets}
    for t in tets:
        for f in range(4):
            fid = int(tf_[t, f])
            if fid in fixed_faces or kind[fid] != 0:
                continue
            o0, o1 = int(owner[fid, 0]), int(owner[fid, 1])
            other = o1 if o0 == t else o0
            if other in tset:
                adj[t].append((other, fid, f))
    parent, dq, order = {}, deque(), []
    for t in tets:
        for f in range(4):
            fid = int(tf_[t, f])
            if kind[fid] == 1 and fid not in fixed_faces and t not in parent:
                parent[t] = (None, fid, f)
                dq.append(t)

    def bfs():
        while dq:
            t = dq.popleft()
            order.append(t)
            for c, fid, _ in adj[t]:
                if c not in parent:
                    fc = int(np.where(tf_[c] == fid)[0][0])
                    parent[c] = (t, fid, fc)
                    dq.append(c)
    bfs()
    for t in tets:
        if t not in parent:
            parent[t] = (None, None, None)
            dq.append(t)
            bfs()
    maxbits = 0
    for t in reversed(order):
        par, fid, f = parent[t]
        r_ = resid[t]
        if fid is None or all(x == 0 for x in r_):
            continue
        s_ = int(sgn[t, f])
        if BI is not None:
            # in integers: Am = Bc / DB with Bc integer, so y = DB^2 M^-1 (-r) with M = Bc Bc^T, and the least-norm
            # change is Am^T y = DB * Bc^T M^-1 (-r) — the same exact numbers, the 6 x 6 system on integers
            slots = [(int(pos[t, f, jv]), c, f * 9 + jv * 3 + c) for jv in range(3) for c in range(3)]
            Bc = [[BI[t][i][col] * s_ for (_, _, col) in slots] for i in range(6)]
            Mi = [[sum(Bc[i][m] * Bc[j][m] for m in range(9)) for j in range(6)] for i in range(6)]
            Dr = 1
            for x in r_:
                Dr = Dr * x.denominator // math.gcd(Dr, x.denominator)
            Rn = [-(x.numerator * (Dr // x.denominator)) for x in r_]      # -r = Rn / Dr
            N, dd = _solve_int(Mi, Rn)                                       # M^-1 Rn = N / dd
            for m, (p_, c, _) in enumerate(slots):
                q[fid][p_][c] += Fr(DB * sum(Bc[i][m] * N[i] for i in range(6) if Bc[i][m]), dd * Dr)
                maxbits = max(maxbits, q[fid][p_][c].denominator.bit_length())
            if par is not None:
                resid[par] = bal(par)
            resid[t] = [Fr(0)] * 6
            continue
        cols = []
        for jv in range(3):
            p_ = int(pos[t, f, jv])
            for c in range(3):
                col = f * 9 + jv * 3 + c
                cols.append((p_, c, [bm_entry(t, i, col) * s_ for i in range(6)]))
        Am = [[col[2][i] for col in cols] for i in range(6)]
        AAt = [[sum(Am[i][m] * Am[j][m] for m in range(9)) for j in range(6)] for i in range(6)]
        y = _solve6(AAt, [-x for x in r_])
        for m, (p_, c, _) in enumerate(cols):
            q[fid][p_][c] += sum(Am[i][m] * y[i] for i in range(6))
            maxbits = max(maxbits, q[fid][p_][c].denominator.bit_length())
        if par is not None:
            resid[par] = bal(par)
        resid[t] = [Fr(0)] * 6
    bad = sum(any(x != 0 for x in bal(t)) for t in tets)
    up = None
    if E is not None:
        up = Fr(0)
        for t in tets:
            tt, tr2 = AL.energy(P[t], g_exact(t))
            up += ((1 + nu) * tt - nu * tr2) / E
    return q, bad, up, maxbits


# ------------------------------------------------------------------------------------------------ level 3b: prestress
# A PRESTRESS load l_p(v) = int_omega eps(v) : sig_e (sig_e a constant symmetric "extractor", omega a set of tets).
# THE UPPER SIDE NEEDS NO NEW ADMISSIBILITY (2026-11-11). tau is admissible for the load f + l_p iff
#     int tau : eps(v) = f(v) + int_omega sig_e : eps(v)  for every v,   i.e.  tau = tau' + sig_e chi_omega
# with tau' admissible for f alone — exactly what choose + finish already deliver. So C(f + l_p) <= ||tau' + p||^2_A
# with p = sig_e chi_omega, and per tet of omega (A the compliance tensor, div tau' = 0 inside the Alfeld element):
#     ||tau' + sig_e||^2_T = ||tau'||^2_T + 2 (A sig_e) : int_T tau' + |T| sig_e : A sig_e,
#     int_T tau'_ij = int_dT t_i x_j = sum over the 36 slots g[f, v, i] w[f, v, j],   w[f, v] = sum_u (1 + d_uv)/24 x_u
# (the same weights as the balance map's moment rows; exact for the linear face traction of the element). So the
# cross term is b_T . g_T with b_T[f, v, i] = sum_j (A sig_e)_ij w[f, v, j] — EXACT rational from the exact fluxes.
# For TIGHTNESS the choice must minimise ||tau' + p||^2, not ||tau'||^2: choose(lin = b) (the same b in floats).
def compliance_apply(sig, E, nu):
    """A sig = ((1 + nu) sig - nu tr(sig) I) / E (exact when the inputs are Fractions)."""
    tr = sig[0][0] + sig[1][1] + sig[2][2]
    return [[((1 + nu) * sig[i][j] - (nu * tr if i == j else 0)) / E for j in range(3)] for i in range(3)]


def _slot_weights(P):
    """w[f * 3 + v] (3-vector): sum over face f's vertices u of (1 + d_uv)/24 x_u (alfeld's face / vertex order)."""
    out = []
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        for jv in range(3):
            out.append([sum(((2 if iv == jv else 1) * P[vv][k] for iv, vv in enumerate(vs)), 0 * P[0][0]) / 24
                        for k in range(3)])
    return out


def mean_stress_integral(P, g):
    """int_T tau (3 x 3) of the element stress with BALANCED face data g on the tet P — from the boundary data alone
    (div tau = 0: int_T tau_ij = int_dT t_i x_j). Exact for Fractions."""
    w = _slot_weights(P)
    return [[sum(g[s * 3 + i] * w[s][j] for s in range(12)) for j in range(3)] for i in range(3)]


def prestress_linear(P, sig, E, nu):
    """b (36): the cross term (A sig) : int_T tau = b . g, exactly (Fractions in, Fractions out)."""
    As = compliance_apply(sig, E, nu)
    w = _slot_weights(P)
    return [sum(As[i][j] * w[s][j] for j in range(3)) for s in range(12) for i in range(3)]


def tet_volume(P):
    """|T| = |det(P1 - P0, P2 - P0, P3 - P0)| / 6 (exact for Fractions)."""
    a = [[P[k + 1][r] - P[0][r] for k in range(3)] for r in range(3)]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    return abs(det) / 6


def prestress_self(P, sig, E, nu):
    """|T| sig : A sig (exact for Fractions)."""
    As = compliance_apply(sig, E, nu)
    return tet_volume(P) * sum(sig[i][j] * As[i][j] for i in range(3) for j in range(3))


def prestress_linear_float(PX, sig, E, nu):
    """The float b for many tets at once: PX (n, 4, 3), sig (3, 3) floats -> (n, 36). Only to CHOOSE."""
    PX = np.asarray(PX, float)
    sig = np.asarray(sig, float)
    As = ((1 + nu) * sig - nu * np.trace(sig) * np.eye(3)) / E
    out = np.zeros((len(PX), 36))
    for f in range(4):
        vs = [v for v in range(4) if v != f]
        for jv in range(3):
            w = sum((2 if iv == jv else 1) * PX[:, vv] for iv, vv in enumerate(vs)) / 24      # (n, 3)
            out[:, f * 9 + jv * 3:f * 9 + jv * 3 + 3] = w @ As.T
    return out
