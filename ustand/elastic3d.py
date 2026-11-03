"""elastic3d — PROVED two-sided bounds on the apparent Young's modulus of a 3D voxel sample (linear elasticity),
judged by ZTL. The stand's 3D phase, track 3: version 1 (2026-11-03 night, the curator's choice (A)) the upper bound;
version 2 (the same day, his "берёмся") the lower bound.

    python3 -m ustand.elastic3d volume.npy --e 0:0 --e 1:200e9 --nu 1:0.3 [--need-max 150e9] [--need-min 9e10]
            [--refine 2] [--one-sided]

THE TEST: the box [0,nx] x [0,ny] x [0,nz] (voxel units), smooth grips on x = 0 and x = nx (u_x = 0 and u_x = nx:
mean axial strain 1; u_y, u_z free there), the four other faces free. The apparent modulus E_app = 2 U / (V eps^2)
= a(u, u) / V (u the true displacement, a the energy form, V = nx ny nz) — the sample's own response, not a
homogenised one (a stated premise: the voxel map IS the sample; linear isotropic elasticity per phase).

UPPER (minimum potential energy): for ANY v with the grips' u_x, a(u, u) <= a(v, v). v: continuous piecewise-linear
  on Kuhn tetrahedra (6 per voxel, |T| = 1/6); on a Kuhn tetrahedron the displacement gradient is EXACTLY the three
  differences along its path, G[c][axis_k] = v_c(p_k+1) - v_c(p_k). The energy per tetrahedron,
      |T| (2 mu eps:eps + lambda (tr eps)^2),  eps:eps = sum_a G_aa^2 + (1/2) sum_a<b (G_ab + G_ba)^2,
  is a sum of NONNEGATIVE terms, so E_app <= a(v, v) / V. The float solve only CHOOSES v; any v is admissible.
THE BOX: a(v, v) does not decrease in mu or lambda; mu = E/(2(1 + nu)) is largest at (E_hi, nu_lo), lambda =
  E nu/((1 + nu)(1 - 2 nu)) at (E_hi, nu_hi) (increasing in nu below 1/2): one bound for every modulus in the box.
  The coefficients are rounded UP to binary64 before use.
ROUNDING (premise, as conduction3d / ZTL zenergy.pd_ieee): IEEE 754 binary64, round to nearest. Each nonnegative
  term is computed from exact binary64 inputs in at most 6 operations; the sum of N such terms is raised by
  (1 + 3 gamma_(N+16)) (1 + 8 u) plus N 2^-1000 (underflow).
LOWER (version 2, 2026-11-03; complementary energy): for ANY statically admissible symmetric tau (div tau = 0, zero
  traction on free faces and pore walls, zero tangential traction on the grips) with resultant F on the grip,
  n_x F = (tau, sigma)_{C^-1} <= ||tau|| sqrt(a(u, u)) (Green), so E_app >= n_x F^2 / (n_y n_z ||tau||^2_{C^-1}).
  tau: the ALFELD-split element on every solid Kuhn tet (ustand.kuhn_split: dimension 30, a bijection onto balanced
  linear face tractions — a single polynomial reaches only 21 of 30), built from FACE data; a float KKT chooses it,
  integers make it exactly admissible (spanning-forest push through unimodular face blocks; the roots' residual
  into a grip face's normal traction), every tet's balance asserted exactly. The compliance at the box's softest
  corner per tet (E_lo; nu at the worse end — the form is linear in nu). Cost: a direct KKT solve (10^3 in 34 s,
  MEASURED); larger samples need an iterative solve — not yet. Pores and voxel EDGE contacts: the stress passes faces
  only, so an edge-only contact carries nothing below while the P1 field bridges it above — the gap is widest there.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F

import numpy as np
import scipy.sparse as sp

from .conduction3d import Mesh, PERMS, U, _gam, _spd_solve

_MUTANT = {}       # TEST-ONLY sabotage switches; empty = the real bound


def _up_float(x):
    """The least binary64 >= the exact rational x."""
    f = float(x)
    return f if F(f) >= x else float(np.nextafter(f, np.inf))


def _lame_hi(E, nu):
    """(mu_hi, lambda_hi) as floats rounded up, over E in [E_lo, E_hi], nu in [nu_lo, nu_hi] (Fractions)."""
    (E_lo, E_hi), (nu_lo, nu_hi) = E, nu
    if not (F(-1) < nu_lo <= nu_hi < F(1, 2)):
        raise ValueError(f"Poisson's ratio {nu_lo}..{nu_hi}: needs -1 < nu < 1/2")
    if _MUTANT.get("e_low"):                         # sabotage (tests only): the box's LOW end
        E_hi = E_lo
    mu = E_hi / (2 * (1 + nu_lo))
    lam = max(F(0), E_hi * nu_hi / ((1 + nu_hi) * (1 - 2 * nu_hi)))
    return _up_float(mu), _up_float(lam)


def _grad_tables():
    """Per Kuhn type t (PERMS order): D[t] (3 x 4): d phi_j / d x_axis for the four vertices (axis = path step)."""
    out = []
    for (a, b, c) in PERMS:
        D = np.zeros((3, 4))
        for k, ax in enumerate((a, b, c)):
            D[ax, k + 1] += 1.0
            D[ax, k] -= 1.0
        out.append(D)
    return out


def _elem_mats():
    """Per Kuhn type: K_mu, K_lam (12 x 12, dof order (vertex j, component c) -> 3 j + c), |T| = 1/6 included:
    v^T K_mu v = |T| 2 eps:eps, v^T K_lam v = |T| (tr eps)^2."""
    Km, Kl = [], []
    for D in _grad_tables():
        # eps_ab = (G_ab + G_ba)/2 with G_ab = d v_a / d x_b = sum_j D[b, j] v_(j, a)
        def Gop(a, b):
            r = np.zeros(12)
            for j in range(4):
                r[3 * j + a] += D[b, j]
            return r
        rows = []
        for a in range(3):
            rows.append(Gop(a, a))                                   # eps_aa
        for a, b in ((0, 1), (0, 2), (1, 2)):
            rows.append((Gop(a, b) + Gop(b, a)) / 2)                 # eps_ab
        E_ = np.array(rows)
        w = np.array([1, 1, 1, 2, 2, 2], float)                      # eps:eps = sum eps_aa^2 + 2 sum eps_ab^2
        Km.append((2.0 / 6.0) * E_.T @ (w[:, None] * E_))
        tr = E_[0] + E_[1] + E_[2]
        Kl.append((1.0 / 6.0) * np.outer(tr, tr))
    return Km, Kl


def material(M, phases):
    """Per tet: float (mu, lambda) for the SOLVE (box midpoints) and rounded-up (mu_hi, lambda_hi) for the BOUND.
    phases: {id: {"E": [lo, hi], "nu": [lo, hi]}} (Fractions); a phase with E_hi = 0 is a pore."""
    ph = M.V[M.vox[:, 0], M.vox[:, 1], M.vox[:, 2]]
    n = int(ph.max()) + 1
    mu_s, la_s, mu_h, la_h = (np.zeros(n) for _ in range(4))
    for k in range(n):
        if k not in phases:
            if np.any(ph == k):
                raise ValueError(f"phase {k} has no modulus")
            continue
        p = phases[k]
        E, nu = (p["E"][0], p["E"][-1]), (p["nu"][0], p["nu"][-1])
        if E[1] == 0:
            continue
        Em, nm = (E[0] + E[1]) / 2, (nu[0] + nu[1]) / 2
        mu_s[k] = float(Em / (2 * (1 + nm)))
        la_s[k] = float(Em * nm / ((1 + nm) * (1 - 2 * nm)))
        mu_h[k], la_h[k] = _lame_hi(E, nu)
    t = ph[M.tvox]
    return mu_s[t], la_s[t], mu_h[t], la_h[t]


def _solve(M, mu, la, rtol=1e-10):
    """The P1 displacement with the grips' u_x (floats: it only CHOOSES v)."""
    Km, Kl = _elem_mats()
    nvox = len(M.vox)
    ndof = 3 * M.nn
    K = None
    for ty in range(6):
        blk = np.arange(ty * nvox, (ty + 1) * nvox)
        blk = blk[(mu[blk] > 0) | (la[blk] > 0)]
        if not len(blk):
            continue
        dofs = (3 * M.tv[blk][:, :, None] + np.arange(3)[None, None, :]).reshape(len(blk), 12)
        vals = mu[blk][:, None, None] * Km[ty][None] + la[blk][:, None, None] * Kl[ty][None]
        r = np.repeat(dofs, 12, axis=1).ravel()
        c = np.tile(dofs, (1, 12)).ravel()
        part = sp.csr_matrix((vals.ravel(), (r, c)), shape=(ndof, ndof))
        K = part if K is None else K + part
    X = M.X
    fixed = np.zeros(ndof, bool)
    fixed[3 * np.where((X == 0) | (X == M.nx))[0]] = True
    ub = np.zeros(ndof)
    ub[3 * np.where(X == M.nx)[0]] = float(M.nx)
    free = np.where(~fixed)[0]
    Kf = K[free][:, free]
    rhs = -(K[free][:, np.where(fixed)[0]] @ ub[fixed])
    d = Kf.diagonal().copy()
    # rigid motions left free by the grips (y, z translation, rotation about x), pores and loose islands: a tiny
    # diagonal shift makes the solve definite; it changes WHICH v is chosen, never the bound's truth
    eps = 1e-10 * (float(d.max()) if len(d) and d.max() > 0 else 1.0)
    Kf = Kf + sp.diags(np.where(d == 0, 1.0, eps))
    d = np.where(d == 0, 1.0, d + eps)
    sol = _spd_solve(Kf, rhs, d, rtol)
    v = ub.copy()
    v[free] = sol
    return v.reshape(M.nn, 3)


def energy_upper(M, v, mu_h, la_h):
    """A rigorous upper bound (Fraction) on a(v, v) with (mu_hi, lambda_hi) per tet: nonnegative float terms,
    each from exact binary64 inputs in <= 6 operations, their sum raised by the Higham bound."""
    G = np.zeros((M.nt, 3, 3))                       # G[t, c, axis] = d v_c / d x_axis
    for k in range(3):
        ax = np.argmax(M.tp[:, k + 1] - M.tp[:, k], axis=1)
        dv = v[M.tv[:, k + 1]] - v[M.tv[:, k]]       # (nt, 3): one subtraction each
        G[np.arange(M.nt), :, ax] = dv
    diag = G[:, 0, 0] ** 2 + G[:, 1, 1] ** 2 + G[:, 2, 2] ** 2
    off = sum((G[:, a, b] + G[:, b, a]) ** 2 for a, b in ((0, 1), (0, 2), (1, 2)))
    tr = (G[:, 0, 0] + G[:, 1, 1] + G[:, 2, 2]) ** 2
    terms = (2.0 * mu_h) * diag + mu_h * off + la_h * tr        # = 2 mu eps:eps + lambda tr^2 (each >= 0)
    s = float(np.sum(terms)) / 6.0
    N = 8 * M.nt
    g = _gam(N + 16)
    return F(s) * (1 + 3 * F(g)) * (1 + 8 * F(U)) + F(N, 2 ** 1000)


def upper(V, phases, refine=1):
    """(E_app upper bound as a Fraction, the chosen field, the mesh) for every modulus in the phases' boxes."""
    V = np.asarray(V)
    if refine > 1:
        V = np.repeat(np.repeat(np.repeat(V, refine, 0), refine, 1), refine, 2)
    M = Mesh(V)
    mu_s, la_s, mu_h, la_h = material(M, phases)
    v = _solve(M, mu_s, la_s)
    a = energy_upper(M, v, mu_h, la_h)
    # refined units: lengths x k, the strain field the same, a and V both x k^3: E_app = a / V unchanged
    return a / (M.nx * M.ny * M.nz), v, M



# --------------------------------------------------------------------------------------------- LOWER (2026-11-03)
_KS = None


def _ks():
    """Per Kuhn type: integer balance BALI = diag(6,6,6,24,24,24) BAL (6 x 36), its four face blocks' INTEGER right
    inverses (Smith decomposition: every block is unimodular, MEASURED and asserted), the compliance forms S1, S2
    (floats rounded to nearest, |error| <= u |S|), and the face table."""
    global _KS
    if _KS is None:
        import sympy as sp
        from sympy.matrices.normalforms import smith_normal_decomp
        from . import kuhn_split as KS
        out = []
        for t in KS.load():
            BALI = [[(6 if r < 3 else 24) * v for v in t["BAL"][r]] for r in range(6)]
            assert all(v.denominator == 1 for row in BALI for v in row)
            BALI = np.array([[int(v) for v in row] for row in BALI], dtype=object)
            Xs = []
            for f in range(4):
                A = sp.Matrix(BALI[:, 9 * f:9 * f + 9].tolist())
                S_, U_, V_ = smith_normal_decomp(A, domain=sp.ZZ)
                assert all(S_[i, i] == 1 for i in range(6)), "a face block is not unimodular"
                X = V_[:, :6] * U_
                assert A * X == sp.eye(6)
                Xs.append(np.array([[int(X[i, j]) for j in range(6)] for i in range(9)], dtype=object))
            S1 = np.array([[float(v) for v in row] for row in t["S1"]])
            S2 = np.array([[float(v) for v in row] for row in t["S2"]])
            out.append({"BALI": BALI, "X": Xs, "S1": S1, "S2": S2, "faces": t["faces"],
                        "BALf": BALI.astype(float)})
        _KS = out
    return _KS


def _phase_soft(M, phases):
    """Per tet: solid?, E_lo (the softest), nu_lo, nu_hi (Fractions -> floats for the SOLVE only), and per tet the
    exact (E_lo, nu_lo, nu_hi) for the bound."""
    ph = M.V[M.vox[:, 0], M.vox[:, 1], M.vox[:, 2]][M.tvox]
    solid = np.zeros(M.nt, bool)
    Elo, nl, nh = np.ones(M.nt), np.zeros(M.nt), np.zeros(M.nt)
    exact = {}
    for k, p in phases.items():
        E_lo, E_hi = p["E"][0], p["E"][-1]
        nu_lo, nu_hi = p["nu"][0], p["nu"][-1]
        sel = ph == k
        if E_hi == 0:
            continue
        if E_lo <= 0:
            raise ValueError(f"phase {k}: E from {E_lo} — a solid phase needs E_lo > 0 for a lower bound")
        solid[sel] = True
        Elo[sel], nl[sel], nh[sel] = float(E_lo), float(nu_lo), float(nu_hi)
        exact[k] = (E_lo, nu_lo, nu_hi)
    return solid, Elo, nl, nh, ph, exact


def lower(V, phases, refine=1):
    """A PROVED LOWER bound on E_app (Fraction) for every modulus in the phases' boxes, and a note.
    The stress: the Alfeld-split element on every solid Kuhn tet (ustand.kuhn_split), built from FACE data g = tau n2
    (9 numbers per face): a float KKT chooses g, then it is made EXACTLY admissible in integers (spanning-forest push
    through unimodular face blocks; the roots' residual into a grip face's normal traction)."""
    from .conduction3d import _faces
    V = np.asarray(V)
    if refine > 1:
        V = np.repeat(np.repeat(np.repeat(V, refine, 0), refine, 1), refine, 2)
    M = Mesh(V)
    KS = _ks()
    nvox = len(M.vox)
    Fc = _faces(M)
    fid, out, gn, nf, first, second = Fc["fid"], Fc["out"], Fc["gn"], Fc["nf"], Fc["first"], Fc["second"]
    ty = np.arange(M.nt) // nvox
    solid, Elo, nl, nh, ph, exact = _phase_soft(M, phases)
    Ehi = np.ones(M.nt)
    for k_, p_ in phases.items():
        Ehi[ph == k_] = float(p_["E"][-1]) or 1.0
    # local outward normals agree with the global ones (out * gn): the face tables and _faces must match
    for t_ in range(6):
        t0 = t_ * nvox
        for f in range(4):
            assert list(out[t0, f] * gn[fid[t0, f]]) == KS[t_]["faces"][f]["n2"], "face orientation mismatch"
    # which face slots may carry traction: inner faces between two solid tets (all 9), grip faces of a solid tet
    # (the normal component x only: tangential traction 0 on a smooth grip), nothing else (free surfaces, pores)
    both = (second >= 0)
    sol2 = np.zeros(nf, bool)
    sol2[both] = solid[first[both]] & solid[second[both]]
    grip = (Fc["x0"] | Fc["x1"]) & ~both
    grip &= solid[first]
    openslot = np.zeros((nf, 3, 3), bool)                   # face, vertex, component
    openslot[sol2] = True
    openslot[grip, :, 0] = True
    slot = -np.ones(nf * 9, dtype=np.int64)
    ok_ = openslot.reshape(-1)
    slot[ok_] = np.arange(int(ok_.sum()))
    nu_ = int(ok_.sum())
    act = np.where(solid)[0]
    if not len(act) or not grip.any():
        return F(0), "no solid path to a grip"
    # tet-local slot index (36) -> global slot and sign
    gl = np.zeros((M.nt, 36), dtype=np.int64)
    sg = np.zeros((M.nt, 36))
    for f in range(4):
        for v in range(3):
            for c in range(3):
                gl[:, 9 * f + 3 * v + c] = slot[9 * fid[:, f] + 3 * v + c]
                sg[:, 9 * f + 3 * v + c] = out[:, f]
    # 1. the float KKT: min sum_T g_T^T S_T g_T, BAL g_T = 0 per solid tet, resultant at x = nx equal to 1
    nm = 0.5 * (nl + nh)
    rows, cols, vals = [], [], []
    for t_ in range(6):
        blk = act[ty[act] == t_]
        if not len(blk):
            continue
        S = KS[t_]["S1"][None] * ((1 + nm[blk]) / Elo[blk])[:, None, None] - \
            KS[t_]["S2"][None] * (nm[blk] / Elo[blk])[:, None, None]
        G = gl[blk]; Sg = sg[blk]
        okm = (G[:, :, None] >= 0) & (G[:, None, :] >= 0)
        r_ = np.broadcast_to(G[:, :, None], okm.shape)[okm]
        c_ = np.broadcast_to(G[:, None, :], okm.shape)[okm]
        v_ = (S * Sg[:, :, None] * Sg[:, None, :])[okm]
        rows.append(r_); cols.append(c_); vals.append(v_)
    Q = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nu_, nu_))
    cr, cc, cv = [], [], []
    for i_, t in enumerate(act):
        B = KS[ty[t]]["BALf"]
        for r in range(6):
            for j in range(36):
                if B[r, j] and gl[t, j] >= 0:
                    cr.append(6 * i_ + r); cc.append(gl[t, j]); cv.append(B[r, j] * sg[t, j])
    nb = 6 * len(act)
    x1f = np.where(Fc["x1"] & grip)[0]
    for fz in x1f:
        t = first[fz]
        for v in range(3):
            # the body's outward x-traction data at x = nx: the tet's outward g_x; force (1/6) sum g
            cr.append(nb); cc.append(slot[9 * fz + 3 * v]); cv.append(out[t, list(fid[t]).index(fz)] / 6.0)
    Bm = sp.csr_matrix((cv, (cr, cc)), shape=(nb + 1, nu_))
    rhs_c = np.zeros(nb + 1); rhs_c[-1] = 1.0
    eps = 1e-12 * max(1.0, abs(Q).max())
    K = sp.bmat([[Q + eps * sp.identity(nu_), Bm.T], [Bm, -eps * sp.identity(nb + 1)]]).tocsc()
    import scipy.sparse.linalg as sla
    sol = sla.spsolve(K, np.r_[np.zeros(nu_), rhs_c])
    g = sol[:nu_]
    # 2. integers: a dyadic grid, then EXACT balance by a spanning-forest push
    scale = 2.0 ** (40 - max(0, int(np.ceil(np.log2(max(1.0, float(np.abs(g).max())))))))
    Gi = [int(v) for v in np.round(g * scale)]                 # Python ints: no overflow in the pushes
    def gT(t):
        return [sg_ * Gi[s_] if s_ >= 0 else 0 for s_, sg_ in zip(gl[t], sg[t].astype(int))]
    def resid(t):
        B = KS[ty[t]]["BALI"]
        gt = gT(t)
        return [sum(int(B[r, j]) * gt[j] for j in range(36) if gt[j]) for r in range(6)]
    # tree over solid tets through inner open faces, roots at tets owning a grip face
    nbr = {}
    for fz in np.where(sol2)[0]:
        a_, b_ = int(first[fz]), int(second[fz])
        nbr.setdefault(a_, []).append((b_, int(fz)))
        nbr.setdefault(b_, []).append((a_, int(fz)))
    gripface = {}
    for fz in np.where(grip)[0]:
        gripface.setdefault(int(first[fz]), int(fz))
    parent = {}
    order = []
    for root in list(gripface) + [int(t) for t in act]:
        if root in parent:
            continue
        parent[root] = (-1, -1)
        order.append(root)
        head = len(order) - 1
        while head < len(order):
            t = order[head]; head += 1
            for u_, fz in nbr.get(t, ()):
                if u_ not in parent:
                    parent[u_] = (t, fz)
                    order.append(u_)
    for t in reversed(order):
        p_, fz = parent[t]
        r = resid(t)
        if not any(r):
            continue
        if p_ < 0:
            if t not in gripface:
                raise AssertionError("a component without a grip has a nonzero total balance")
            continue                                           # roots: absorbed below
        f = list(fid[t]).index(fz)
        X = KS[ty[t]]["X"][f]
        d = [-sum(int(X[i, j]) * r[j] for j in range(6)) for i in range(9)]   # the tet's outward face data change
        so = int(out[t, f])
        for i in range(9):
            s_ = slot[9 * fz + i]
            assert s_ >= 0 or d[i] == 0
            if d[i]:
                Gi[s_] += so * d[i]
    # roots: (6 F_x, 24 M_y, 24 M_z) into the grip face's normal values (F_y, F_z, M_x are exactly 0: asserted)
    Gq = [F(v) for v in Gi]
    def residF(t):
        B = KS[ty[t]]["BALI"]
        gt = [sg_ * Gq[s_] if s_ >= 0 else F(0) for s_, sg_ in zip(gl[t], sg[t].astype(int))]
        return [sum(int(B[r, j]) * gt[j] for j in range(36) if gt[j]) for r in range(6)]
    for t in order:
        if parent[t][0] >= 0:
            continue
        r = residF(t)
        if not any(r):
            continue
        assert r[1] == 0 and r[2] == 0 and r[3] == 0, f"root residual {r} has F_y/F_z/M_x"
        fz = gripface[t]
        f = list(fid[t]).index(fz)
        B = KS[ty[t]]["BALI"]
        cols3 = [9 * f + 3 * v for v in range(3)]
        A3 = [[F(int(B[rr, c])) for c in cols3] for rr in (0, 4, 5)]
        import sympy as sp_
        sol3 = sp_.Matrix(A3).inv() * sp_.Matrix([-r[0], -r[4], -r[5]])
        so = int(out[t, f])
        for v in range(3):
            Gq[slot[9 * fz + 3 * v]] += so * F(int(sp_.fraction(sol3[v])[0]), int(sp_.fraction(sol3[v])[1]))
    # EXACT checks: every solid tet balanced; nothing outside the open slots (by construction of slot)
    for t in act:
        assert not any(residF(int(t))), "balance not exact"
    # 3.-4. the resultant and the energy bound
    Fres = sum((Gq[slot[9 * fz + 3 * v]] * int(out[first[fz], list(fid[first[fz]]).index(fz)])
                for fz in x1f for v in range(3)), F(0)) / 6
    if Fres <= 0:
        return F(0), "no load carried"
    gf = np.array([float(v) for v in Gq])                      # |gf - Gq| <= u |gf| (round to nearest)
    tot = 0.0
    nterms = 0
    gam = _gam(1300)
    for t_ in range(6):
        blk = act[ty[act] == t_]
        if not len(blk):
            continue
        G = np.where(gl[blk] >= 0, gf[np.maximum(gl[blk], 0)], 0.0) * sg[blk]
        Ab = np.abs(G)
        S1, S2 = KS[t_]["S1"], KS[t_]["S2"]
        e1 = np.einsum("ti,ij,tj->t", G, S1, G); w1 = np.einsum("ti,ij,tj->t", Ab, np.abs(S1), Ab)
        e2 = np.einsum("ti,ij,tj->t", G, S2, G); w2 = np.einsum("ti,ij,tj->t", Ab, np.abs(S2), Ab)
        # S1, S2 forms bounded from above (each ~ a dot of 1296 products, the inputs' rounding included)
        e1u = e1 + 2 * gam * w1
        e2l = e2 - 2 * gam * w2
        e2u = e2 + 2 * gam * w2
        # compliance (1/E_lo)((1 + nu) S1 - nu S2): linear in nu, the larger end; E at its lowest
        best = np.maximum((1 + nl[blk]) * e1u - np.where(nl[blk] >= 0, nl[blk] * e2l, nl[blk] * e2u),
                          (1 + nh[blk]) * e1u - np.where(nh[blk] >= 0, nh[blk] * e2l, nh[blk] * e2u))
        # nu as a binary64 differs from the exact endpoint by u |nu|: d/dnu of the form is S1 - S2, |.| <= e1 + e2
        best = best + 4 * U * (np.abs(e1u) + np.abs(e2) + 2 * gam * w2)
        Elo_up = Elo[blk] * (1 - 2 * U)                         # 1/E rounded: dividing by a slightly smaller E
        if _MUTANT.get("lower_e_high"):                       # sabotage (tests only): the STIFFEST end of the box
            Elo_up = Ehi[blk]
        term = np.maximum(best, 0.0) / Elo_up * (1 + 4 * U)
        tot += float(np.sum(term))
        nterms += len(blk)
    En = F(tot) * (1 + 3 * F(_gam(nterms + 16))) + F(nterms, 2 ** 1000)
    if En == 0:
        return F(0), "zero energy"
    k = refine
    # refined units: the box and every length x k; F scales as k^2 at fixed stress, the energy as k^3, so
    # nx F^2 / (ny nz En) is unchanged with nx, ny, nz the refined counts
    return F(M.nx) * Fres * Fres / (F(M.ny * M.nz) * En), "ok"


def judge(V, phases, need_max=None, need_min=None, refine=1, two_sided=True):
    """E_app <= need_max and E_app >= need_min, by ZTL over the proved [lower, upper] (two_sided=False: [0, upper],
    version 1's one-sided bracket)."""
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    up, _, _ = upper(V, phases, refine)
    lo, note = lower(V, phases, refine) if two_sided else (F(0), "one-sided")
    used = set(np.unique(np.asarray(V)).tolist())
    prov = "earned:elastic3d" if all(phases[k].get("earned") for k in used if k in phases) else "credit"
    f = lambda x: f"{x.numerator}/{x.denominator}"
    qs, mk = parse_quantities(f"eapp=[{f(lo)},{f(up)}] {prov}")
    out = {"upper": float(up), "lower": float(lo), "lower_note": note,
           "premise": "linear isotropic elasticity per phase; the voxel map is the sample; smooth grips on x = 0 / "
                      "x = nx (mean strain 1), other faces free; Green's formula; IEEE 754 rounding (bounded)"}
    for key, op, need in (("max", "<=", need_max), ("min", ">=", need_min)):
        if need is not None:
            r = judge_sheet_claim(f"eapp {op} {f(F(need))}", qs, mk)
            out[f"verdict_{key}"] = r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else "")
    return out


def _parse_phases(argv):
    ph, i, rest = {}, 0, []
    while i < len(argv):
        if argv[i] in ("--e", "--nu"):
            k, v = argv[i + 1].split(":")
            vals = [F(x) for x in v.split(",")]
            ph.setdefault(int(k), {})["E" if argv[i] == "--e" else "nu"] = vals
            i += 2
        else:
            rest.append(argv[i]); i += 1
    for k, p in ph.items():
        p.setdefault("nu", [F(0)])
        if "E" not in p:
            raise SystemExit(f"phase {k}: --e missing")
        p["earned"] = False
    return ph, rest


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    V = np.load(argv[0])
    ph, rest = _parse_phases(argv[1:])
    need_max = need_min = None
    refine, i, two_sided = 1, 0, True
    while i < len(rest):
        if rest[i] == "--need-max":
            need_max = rest[i + 1]; i += 2
        elif rest[i] == "--need-min":
            need_min = rest[i + 1]; i += 2
        elif rest[i] == "--one-sided":
            two_sided = False; i += 1
        elif rest[i] == "--refine":
            refine = int(rest[i + 1]); i += 2
        else:
            raise SystemExit(f"unknown argument {rest[i]}")
    print(json.dumps(judge(V, ph, need_max, need_min, refine, two_sided)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
