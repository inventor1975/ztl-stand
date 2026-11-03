"""platebuckle — PROVED bounds on the elastic critical stress of a rectangular plate panel (Kirchhoff plate), the input
of EN 1993-1-5's plate buckling check (2026-11-03, the curator's "Ок" to the plan of the day).

THE PANEL: a x b (x along the stress), thickness t, E, nu; each edge simply supported (S) or clamped (C); the in-plane
stress sigma_x(y) = sigma (1 - (1 - psi) y / b) (compression positive; psi the stress ratio of the edges y = b / y = 0,
EN 1993-1-5 Table 4.1), the pre-buckling field exact for this loading. Buckling: D a(w, w) = lambda sigma t b(w, w) with
a(w, w) = int (1 - nu) D2w : D2w + nu (tr D2w)^2 (Kirchhoff, D = E t^3 / (12 (1 - nu^2))) and b(w, w) = int s(y) w_x^2,
s = sigma_x / sigma. The critical stress is lambda_1 sigma.

LOWER (Carstensen & Gallistl, Numer. Math. 126 (2014) 33-51, Theorem 1 and Theorem 3): with the Morley element
(P2; dofs: the vertex values and int_E dw/dn ds per edge) and its eigenvalue lambda_M, lambda_M / (1 + eps^2 lambda_M) <=
lambda_1, provided ||v - I_M v||_b <= eps ||v - I_M v||_a for all v. Theorem 3: ||grad(v - I_M v)||_T <= kappa_CR h_T
||D2(v - I_M v)||_T, kappa_CR = sqrt(1/48 + j_11^-2) = 0.298234942888 (j_11 the first root of J_1). Here b only uses
w_x and s(y) <= s_T^+ (the largest compression on T, at a vertex: s is linear), and a >= (1 - nu) int |D2 w|^2 (nu >= 0),
so eps^2 = max_T s_T^+ kappa_CR^2 h_T^2 / (1 - nu) — in the units of D / (sigma t). Tension parts of s only stabilise:
replacing s by s^+ (pointwise) can only lower lambda_1, so the bound stays a lower bound for any psi. The theorem's
Pythagoras needs D2_NC I_M = Pi_0 D2 (the integral-mean property of the Morley interpolant, any constant-coefficient
a in D2). lambda_M itself from below: K - mu B positive definite (ZTL zenergy.pd_ieee, exact rational entries).
"""
from __future__ import annotations

import math
from fractions import Fraction as F

import numpy as np

MUTANT = {}       # TEST-ONLY sabotage switches; empty = the real bounds
KAPPA_CR = F("0.298234942888") * (1 + F(1, 10 ** 11))    # the paper's value rounded UP (12 digits given)


def mesh(nx, ny, a, b):
    """A structured triangulation of [0, a] x [0, b]: nodes (i, j), two triangles per cell (the diagonal from
    (i, j) to (i + 1, j + 1)). Coordinates exact."""
    nodes = [(F(a) * i / nx, F(b) * j / ny) for j in range(ny + 1) for i in range(nx + 1)]
    nid = lambda i, j: j * (nx + 1) + i
    tris = []
    for j in range(ny):
        for i in range(nx):
            p, q, r, s = nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1)
            tris.append((p, q, r))
            tris.append((p, r, s))
    return nodes, tris


def _morley_basis(P):
    """Coefficients (6 x 6, exact) of the Morley basis on the triangle P (3 points): columns = the 6 basis functions
    in the monomials (1, x, y, x^2, xy, y^2); dofs: v(P_i) (i = 0..2), then int_E dv/dn ds = grad v(mid E) . r_E for the
    edges E_k opposite P_k with r_E the edge vector turned by -90 deg (|r_E| = |E|; the global orientation applied by
    the caller)."""
    rows = []
    for (x, y) in P:
        rows.append([F(1), x, y, x * x, x * y, y * y])
    for k in range(3):
        A, B = P[(k + 1) % 3], P[(k + 2) % 3]
        mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        ex, ey = B[0] - A[0], B[1] - A[1]
        rx, ry = ey, -ex
        # grad of the monomials at (mx, my): d/dx = (0, 1, 0, 2x, y, 0), d/dy = (0, 0, 1, 0, x, 2y)
        gx = [F(0), F(1), F(0), 2 * mx, my, F(0)]
        gy = [F(0), F(0), F(1), F(0), mx, 2 * my]
        rows.append([gx[i] * rx + gy[i] * ry for i in range(6)])
    import sympy as sp
    M = sp.Matrix(rows)
    Minv = M.inv()
    return [[F(int(sp.fraction(Minv[i, j])[0]), int(sp.fraction(Minv[i, j])[1])) for j in range(6)] for i in range(6)]


def _edges_on(nodes, i, j, a, b):
    """Which panel edge ('x0', 'xa', 'y0', 'yb') the segment i-j lies on, or None."""
    (x1, y1), (x2, y2) = nodes[i], nodes[j]
    for name, ok in (("x0", x1 == 0 and x2 == 0), ("xa", x1 == a and x2 == a), ("y0", y1 == 0 and y2 == 0),
                     ("yb", y1 == b and y2 == b)):
        if ok:
            return name
    return None


def morley_system(a, b, nu, psi, bc, nx, ny, want_tension=False):
    """Exact Morley matrices K (from a, units D) and B (from b with s^+_T per triangle, units sigma t) on the free
    dofs, as {(i, j): Fraction} lower triangles, and eps^2 for the lower bound. bc: {'x0','xa','y0','yb'} -> 'S'|'C'."""
    a, b, nu, psi = F(a), F(b), F(nu), F(psi)
    nodes, tris = mesh(nx, ny, a, b)
    s_of = lambda y: 1 - (1 - psi) * y / b                       # sigma_x / sigma
    edge_id, nn = {}, len(nodes)
    for t in tris:
        for k in range(3):
            A_, B_ = t[(k + 1) % 3], t[(k + 2) % 3]
            key = (min(A_, B_), max(A_, B_))
            if key not in edge_id:
                edge_id[key] = nn + len(edge_id)
    fixed = set()
    for (i, j), e in edge_id.items():
        side = _edges_on(nodes, i, j, a, b)
        if side is None:
            continue
        fixed.update((i, j))                                     # w = 0 on every supported edge (S or C)
        if bc[side] == "C":
            fixed.add(e)                                         # dw/dn = 0 on a clamped edge
    free = [d for d in range(nn + len(edge_id)) if d not in fixed]
    col = {d: k for k, d in enumerate(free)}
    K, Bm, Bn = {}, {}, {}
    eps2 = F(0)
    eps2n = F(0)
    cache = {}
    for t in tris:
        P0 = [nodes[v] for v in t]
        P = [(x - P0[0][0], y - P0[0][1]) for x, y in P0]            # local coordinates: translates share a basis
        shape = tuple(P)
        if shape not in cache:
            cache[shape] = _morley_basis(P)
        C = cache[shape]
        area = abs((P[1][0] - P[0][0]) * (P[2][1] - P[0][1]) - (P[2][0] - P[0][0]) * (P[1][1] - P[0][1])) / 2
        dofs, sg = list(t), [1, 1, 1]
        for k in range(3):
            A_, B_ = t[(k + 1) % 3], t[(k + 2) % 3]
            dofs.append(edge_id[(min(A_, B_), max(A_, B_))])
            sg.append(1 if A_ < B_ else -1)
        # a: (1 - nu) |D2|^2 + nu (tr D2)^2 with D2 = [[2c3, c4], [c4, 2c5]]
        Qc = [[F(0)] * 6 for _ in range(6)]
        Qc[3][3] += 4 * (1 - nu); Qc[4][4] += 2 * (1 - nu); Qc[5][5] += 4 * (1 - nu)
        for p_, wp in ((3, 2), (5, 2)):
            for q_, wq in ((3, 2), (5, 2)):
                Qc[p_][q_] += nu * wp * wq
        # b: s_T^+ int w_x^2 (3-point edge-midpoint rule: exact for quadratics)
        sT = max(F(0), max(s_of(y) for _, y in P0))
        if MUTANT.get("b_low"):                          # sabotage (tests only): the load under-integrated by 10 %
            sT = sT * F(9, 10)
        G = [[F(0)] * 6 for _ in range(6)]
        for k in range(3):
            mx = (P[k][0] + P[(k + 1) % 3][0]) / 2
            my = (P[k][1] + P[(k + 1) % 3][1]) / 2
            g = [F(0), F(1), F(0), 2 * mx, my, F(0)]
            for p_ in range(6):
                for q_ in range(6):
                    G[p_][q_] += area / 3 * g[p_] * g[q_]
        h2 = max((P[i][0] - P[j][0]) ** 2 + (P[i][1] - P[j][1]) ** 2 for i in range(3) for j in range(i + 1, 3))
        eps2 = max(eps2, sT * KAPPA_CR ** 2 * h2 / (1 - nu))
        # the TENSION part (2026-11-03): s^- = max(0, -s); in the discrete form at its SMALLEST on T (it is ADDED to
        # the stiffness side: a lower bound of the exact b^-), in eps_minus at its LARGEST
        sn_lo = max(F(0), min(-s_of(y) for _, y in P0))
        if MUTANT.get("tension_hi"):                    # sabotage (tests only): the tension at its LARGEST on T
            sn_lo = max(F(0), max(-s_of(y) for _, y in P0))
        if MUTANT.get("tension_x2"):                    # sabotage (tests only): the stabilising tension doubled
            sn_lo = 2 * sn_lo
        sn_hi = max(F(0), max(-s_of(y) for _, y in P0))
        eps2n = max(eps2n, sn_hi * KAPPA_CR ** 2 * h2 / (1 - nu))
        for (Mloc, out, scale, tag) in ((Qc, K, area, "K"), (G, Bm, sT, "B"), (G, Bn, sn_lo, "B")):
            if scale == 0:
                continue
            ck = (shape, tag)
            if ck not in cache:
                CM = [[sum(Mloc[p_][r] * C[r][j] for r in range(6)) for j in range(6)] for p_ in range(6)]
                cache[ck] = [[sum(C[p_][i] * CM[p_][j] for p_ in range(6)) for j in range(6)] for i in range(6)]
            Lm = cache[ck]
            for i in range(6):
                di = dofs[i]
                if di not in col:
                    continue
                for j in range(6):
                    dj = dofs[j]
                    if dj not in col:
                        continue
                    v = scale * sg[i] * sg[j] * Lm[i][j]
                    if v:
                        key = (max(col[di], col[dj]), min(col[di], col[dj]))
                        if col[di] >= col[dj]:
                            out[key] = out.get(key, F(0)) + v
    if want_tension:
        return K, Bm, Bn, len(free), eps2, eps2n
    return K, Bm, len(free), eps2


def _sparse(entries, n):
    import scipy.sparse as sp
    keys = list(entries)
    r = np.array([k[0] for k in keys]); c = np.array([k[1] for k in keys]); v = np.array([float(entries[k]) for k in keys])
    off = r != c
    return sp.csc_matrix((np.r_[v, v[off]], (np.r_[r, c[off]], np.r_[c, r[off]])), shape=(n, n))


def _dense(entries, n):
    M = np.zeros((n, n))
    for (i, j), v in entries.items():
        M[i, j] = float(v)
        M[j, i] = float(v)
    return M


def lower_factor(a, b, nu, psi, bc, nx, ny):
    """A PROVED lower bound on lambda_1 (sigma_cr = lambda_1 D / t for sigma = 1 at y = 0), and the parts."""
    from . import judge_ztl  # noqa: F401   (puts ZTL on the path)
    import zenergy as ZE
    K, Bm, n, eps2 = morley_system(a, b, nu, psi, bc, nx, ny)
    import scipy.sparse.linalg as ssl
    Ks, Bs = _sparse(K, n), _sparse(Bm, n)
    lam_est = float(ssl.eigsh(Ks, k=1, M=Bs, sigma=0, which="LM", return_eigenvectors=False, v0=np.ones(n))[0]) \
        if n > 400 else 1.0 / float(__import__("scipy.linalg").linalg.eigh(_dense(Bm, n), _dense(K, n), eigvals_only=True)[-1])
    # lambda_M >= mu: K - mu B positive definite, proved
    # lambda_M >= mu: lambda_min(K - mu B) >= the bound pd_ieee proves, positive (a shift just under the floats' own
    # smallest eigenvalue, as frame.stability_lower)
    mu = F(lam_est) * (1 - F(1, 10 ** 4))
    for _ in range(40):
        ent = {key: K.get(key, F(0)) - mu * Bm.get(key, F(0)) for key in set(K) | set(Bm)}
        if n <= 400:
            m = float(__import__("scipy.linalg").linalg.eigvalsh(_dense(ent, n))[0])
        else:
            m = float(ssl.eigsh(_sparse(ent, n), k=1, sigma=0, which="LM", return_eigenvectors=False, v0=np.ones(n))[0])
        if m > 0:
            pd = ZE.pd_ieee(n, ent, F(m) * F(9, 10))
            if pd is not None and pd > 0:
                break
        mu *= 1 - F(1, 100)
    else:
        return None, {"why": "lambda_M not proved"}
    if MUTANT.get("no_correction"):                     # sabotage (tests only): the raw Morley eigenvalue
        eps2 = F(0)
    low = mu / (1 + eps2 * mu)
    return low, {"lambda_M_est": lam_est, "lambda_M_proved": float(mu), "eps2": float(eps2), "unknowns": n}



def lower_factor_t(a, b, nu, psi, bc, nx, ny, thetas=(F(1, 2), F(2, 3), F(4, 5), F(9, 10), F(19, 20))):
    """A PROVED lower bound on lambda_1 KEEPING the tension (2026-11-03; for psi < 0 lower_factor drops it, ~24 % low
    at psi = -1). lambda_1 >= mu iff a(v) + mu b^-(v) - mu b^+(v) >= 0 on V. With v = I_M v + e (Carstensen & Gallistl:
    a(v) = a(I_M v) + a(e) by the projection property; ||e||_{b+-} <= eps_+- ||e||_a, eps^2 = max_T s_T^+- kappa_CR^2
    h_T^2 / (1 - nu)) and Young (b^+(v) <= (1 + eta) b^+(I v) + (1 + 1/eta) ||e||_{b+}^2, b^-(v) >= (1 - delta) b^-(I v)
    - (1/delta - 1) ||e||_{b-}^2), it suffices that
      K + mu (1 - delta) B^- - mu (1 + eta) B^+ >= 0  (discrete, B^- with s^- at its smallest on T: a lower bound of
      b^- on V_M) and  mu (1 + 1/eta) eps_+^2 + mu (1/delta - 1) eps_-^2 <= 1  (the e-terms absorbed by a(e)).
    The budget 1 is split theta (b^+) / 1 - theta (b^-), the best theta of a short list kept (each is a proof, so the
    largest is one too); mu by bisection, each step proved by pd_ieee. Without tension theta = 1: exactly Theorem 1."""
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    import scipy.sparse.linalg as ssl
    K, Bp, Bn, n, e2p, e2n = morley_system(a, b, nu, psi, bc, nx, ny, want_tension=True)
    if MUTANT.get("no_tension_eps"):                     # sabotage (tests only): the tension's interpolation error dropped
        e2n = F(0)
    keys = set(K) | set(Bp) | set(Bn)
    def ok(mu, th):
        if mu <= 0:
            return True
        if e2p and mu * e2p >= th:
            return False
        eta = (mu * e2p / (th - mu * e2p)) if e2p else F(0)            # mu (1 + 1/eta) e2p = theta
        delta = (F(1) / (1 + (1 - th) / (mu * e2n))) if e2n else F(0)  # mu (1/delta - 1) e2n = 1 - theta
        ent = {k_: K.get(k_, F(0)) + mu * (1 - delta) * Bn.get(k_, F(0)) - mu * (1 + eta) * Bp.get(k_, F(0))
               for k_ in keys}
        if n <= 400:
            m = float(__import__("scipy.linalg").linalg.eigvalsh(_dense(ent, n))[0])
        else:
            try:
                m = float(ssl.eigsh(_sparse(ent, n), k=1, sigma=0, which="LM", return_eigenvectors=False,
                                    v0=np.ones(n))[0])
            except Exception:
                return False
        if m <= 0:
            return False
        pd = ZE.pd_ieee(n, ent, F(m) * F(9, 10))
        return pd is not None and pd > 0
    # the float estimate of lambda for the start: K - lam (B+ - B-) (B- added), from lower_factor's float path
    Ks, Bs = _sparse(K, n), _sparse({k_: Bp.get(k_, F(0)) - Bn.get(k_, F(0)) for k_ in keys}, n)
    try:
        lam_est = 1.0 / float(ssl.eigsh(Bs, k=1, M=Ks, which="LA", return_eigenvectors=False, v0=np.ones(n))[0])
    except Exception:
        lam_est = None
    best, best_th = F(0), None
    for th in ((F(1),) if not e2n else thetas):
        hi = F(lam_est) if lam_est else F(10 ** 6)
        lo = F(0)
        for _ in range(40):
            mid = (lo + hi) / 2
            if ok(mid, th):
                lo = mid
            else:
                hi = mid
            if hi - lo <= lo * F(1, 10 ** 5):
                break
        lo = F(float(lo))                  # a short rational for the record (smaller than or equal: re-proved below)
        while lo > 0 and not ok(lo, th):
            lo = lo * (1 - F(1, 10 ** 6))
        if lo > best:
            best, best_th = lo, th
    return best, {"lambda_est": lam_est, "eps2_plus": float(e2p), "eps2_minus": float(e2n), "theta": best_th,
                  "unknowns": n}


# --------------------------------------------------------------------------------------------- UPPER (BFS Ritz)
def _hermite_1d(h):
    """The cubic Hermite basis on [0, h] (dofs u(0), u'(0), u(h), u'(h)) as exact polynomial coefficient lists
    (powers of x), and its derivatives."""
    h = F(h)
    H = [[F(1), F(0), -3 / h ** 2, 2 / h ** 3], [F(0), F(1), -2 / h, 1 / h ** 2],
         [F(0), F(0), 3 / h ** 2, -2 / h ** 3], [F(0), F(0), -1 / h, 1 / h ** 2]]
    der = lambda p: [k * p[k] for k in range(1, len(p))] or [F(0)]
    return H, [der(p) for p in H], [der(der(p)) for p in H]


def _int_poly(p, q, h, w=(F(1),)):
    """int_0^h p q w dx for coefficient lists (w a polynomial weight), exact."""
    prod = {}
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            for k, c in enumerate(w):
                prod[i + j + k] = prod.get(i + j + k, F(0)) + a * b * c
    return sum(c * F(h) ** (e + 1) / (e + 1) for e, c in prod.items())


def bfs_system(a, b, nu, psi, bc, nx, ny):
    """Exact BFS matrices K (a, with nu) and B (b with the TRUE s(y), tension included), free dofs only."""
    a, b, nu, psi = F(a), F(b), F(nu), F(psi)
    hx, hy = a / nx, b / ny
    H, H1, H2 = _hermite_1d(hx)
    G, G1, G2 = _hermite_1d(hy)
    I = lambda P, Q, h, w=(F(1),): [[_int_poly(P[i], Q[j], h, w) for j in range(4)] for i in range(4)]
    X00, X11, X22, X02 = I(H, H, hx), I(H1, H1, hx), I(H2, H2, hx), I(H, H2, hx)
    Y00, Y11, Y22, Y02 = I(G, G, hy), I(G1, G1, hy), I(G2, G2, hy), I(G, G2, hy)
    # local dof k = (end, kind) in 1D: 0 u(0), 1 u'(0), 2 u(h), 3 u'(h); 2D node dofs (w, w_x, w_y, w_xy) at corner (ex, ey)
    def gdof(i, j, kx, ky):            # kx, ky in {0, 1}: value / derivative in x / y
        return 4 * (j * (nx + 1) + i) + (kx + 2 * ky)
    fixed = set()
    for j in range(ny + 1):
        for i in range(nx + 1):
            on = {"x0": i == 0, "xa": i == nx, "y0": j == 0, "yb": j == ny}
            for side, yes in on.items():
                if not yes:
                    continue
                tang_is_y = side in ("x0", "xa")
                fixed.add(gdof(i, j, 0, 0))                                   # w = 0
                fixed.add(gdof(i, j, 0, 1) if tang_is_y else gdof(i, j, 1, 0))  # its tangential derivative
                if bc[side] == "C":
                    fixed.add(gdof(i, j, 1, 0) if tang_is_y else gdof(i, j, 0, 1))  # the normal derivative
                    fixed.add(gdof(i, j, 1, 1))                                  # and the twist along the edge
    ndof = 4 * (nx + 1) * (ny + 1)
    free = [d for d in range(ndof) if d not in fixed]
    col = {d: k for k, d in enumerate(free)}
    K, Bm = {}, {}
    for ey in range(ny):
        y0 = ey * hy
        s0 = 1 - (1 - psi) * y0 / b                       # s(y0 + eta) = s0 + s1 eta
        s1 = -(1 - psi) / b
        Ys = I(G, G, hy, (s0, s1))
        for ex in range(nx):
            loc = []
            for ly in range(4):
                for lx in range(4):
                    i = ex + (lx >= 2); j = ey + (ly >= 2)
                    loc.append((lx, ly, gdof(i, j, lx % 2, ly % 2)))
            for (ax, ay, da) in loc:
                if da not in col:
                    continue
                for (bx, by, db) in loc:
                    if db not in col or col[db] > col[da]:
                        continue
                    kv = (X22[ax][bx] * Y00[ay][by] + X00[ax][bx] * Y22[ay][by]
                          + nu * (X02[ax][bx] * Y02[by][ay] + X02[bx][ax] * Y02[ay][by])
                          + 2 * (1 - nu) * X11[ax][bx] * Y11[ay][by])
                    bv = X11[ax][bx] * Ys[ay][by]
                    key = (col[da], col[db])
                    if kv:
                        K[key] = K.get(key, F(0)) + kv
                    if bv:
                        Bm[key] = Bm.get(key, F(0)) + bv
    return K, Bm, len(free)


def upper_factor(a, b, nu, psi, bc, nx, ny):
    """A PROVED upper bound on lambda_1: the Rayleigh quotient a(w)/b(w) of a conforming (C1) BFS field w — the
    discrete eigenvector rounded to dyadics — computed EXACTLY (Rayleigh: lambda_1 = min a/b over b > 0)."""
    import scipy.sparse.linalg as ssl
    K, Bm, n = bfs_system(a, b, nu, psi, bc, nx, ny)
    Ks, Bs = _sparse(K, n), _sparse(Bm, n)
    # B is INDEFINITE when part of the panel is in tension (psi < 0): the largest eigenvalue of B relative to the
    # positive definite K gives 1 / lambda_1 (shift-invert with B as the mass needs B >= 0)
    vals, vecs = ssl.eigsh(Bs, k=1, M=Ks, which="LA", v0=np.ones(n))
    vals = 1.0 / vals
    v = vecs[:, 0]
    v = v / np.abs(v).max()
    w = [F(int(round(x * 2 ** 40)), 2 ** 40) for x in v]
    def quad(E):
        tot = F(0)
        for (i, j), c in E.items():
            tot += c * w[i] * w[j] * (1 if i == j else 2)
        return tot
    aw, bw = quad(K), quad(Bm)
    if bw <= 0:
        return None, {"why": "the Ritz field does not load the plate"}
    return aw / bw, {"lambda_ritz_est": float(vals[0]), "unknowns": n}


def sigma_cr_bracket(a, b, t, E, nu, psi, bc, n_low=48, n_up=16):
    """PROVED [low, high] for the elastic critical stress sigma_cr (at the edge y = 0, the larger compression) of the
    panel: lambda_1 D / t with D = E t^3 / (12 (1 - nu^2)) — Morley lower, BFS upper. nu >= 0 (the lower bound's
    a >= (1 - nu) |D2|^2). Exact Fractions."""
    a, b, t, E, nu, psi = (F(v) for v in (a, b, t, E, nu, psi))
    if not (0 <= nu < F(1, 2)):
        raise ValueError("Poisson's ratio: 0 <= nu < 1/2 here")
    D = E * t ** 3 / (12 * (1 - nu ** 2))
    # psi < 0: the tension keeps part of the plate straight — the tension-aware bound (psi = -1, 48 x 48: 19.53 -> 23.29
    # against Navier's 25.5283, MEASURED 2026-11-03); psi >= 0 has no tension and the two are the same theorem
    lo, il = (lower_factor_t if psi < 0 else lower_factor)(a, b, nu, psi, bc, n_low, n_low)
    hi, iu = upper_factor(a, b, nu, psi, bc, n_up, n_up)
    if lo is None or hi is None:
        return None, None, {"lower": il, "upper": iu}
    return lo * D / t, hi * D / t, {"lower": il, "upper": iu}


def rho_internal(lam_p, psi):
    """EN 1993-1-5 4.4(2), internal compression elements: rho = 1 for lam_p <= 0.5 + sqrt(0.085 - 0.055 psi), else
    (lam_p - 0.055 (3 + psi)) / lam_p^2 <= 1 (psi >= -1). Non-increasing in lam_p (for lam_p > 0.11 (3 + psi))."""
    lim = 0.5 + math.sqrt(0.085 - 0.055 * float(psi))
    return 1.0 if lam_p <= lim else min(1.0, (lam_p - 0.055 * (3 + float(psi))) / lam_p ** 2)


def judge(a, b, t, E, nu, psi, bc, fy, need_sigma_cr=None, n_low=48, n_up=16):
    """sigma_cr >= need (ZTL over the proved bracket), and EN 1993-1-5 4.4's rho bracket from it (rho is
    non-increasing in the slenderness sqrt(fy / sigma_cr): the LOWER sigma_cr gives the LOWER rho — conservative)."""
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    lo, hi, info = sigma_cr_bracket(a, b, t, E, nu, psi, bc, n_low, n_up)
    if lo is None:
        return {"verdict": "OPEN", "why": "a bound was not proved", "info": info}
    fyf = float(fy)
    rho = (rho_internal(math.sqrt(fyf / float(lo)) * (1 + 1e-12), psi), rho_internal(math.sqrt(fyf / float(hi)), psi))
    out = {"sigma_cr": [float(lo), float(hi)], "rho_EN_1993_1_5_4_4": [rho[0], rho[1]],
           "premise": "Kirchhoff plate, linear elastic, the stated edge supports, sigma_x linear in y (psi), nu >= 0; "
                      "the Morley bound per Carstensen & Gallistl (2014) with kappa_CR rounded up",
           "note": "psi < 0: the lower bound keeps the tension (s^- at its smallest per triangle, its interpolation "
                   "error charged) — MEASURED ~9 % low at psi = -1, 48 x 48 (it was ~24 % with the tension dropped)"}
    if need_sigma_cr is not None:
        f = lambda x: f"{x.numerator}/{x.denominator}"
        qs, mk = parse_quantities(f"scr=[{f(lo)},{f(hi)}] earned:platebuckle")
        r = judge_sheet_claim(f"scr >= {f(F(need_sigma_cr))}", qs, mk)
        out["verdict"] = r["disposition"] + (f" ({r['polarity']})" if r.get("polarity") else "")
    return out
