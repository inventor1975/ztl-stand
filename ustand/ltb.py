"""Lateral-torsional and torsional buckling of ONE member — a proved critical factor (2026-11-02, DESIGN-LTB.md; the
curator's "замысел да").

The member (length L, doubly symmetric section, loads at the shear centre) between FORK supports (v = 0, phi = 0 at
both ends; v' and phi' free — no warping restraint), its strong-axis moment along it M(xi) = (1 - xi) M_A + xi M_B +
kappa xi (1 - xi) (end moments and a uniform transverse load's parabola), its axial force N (constant; tension +):
    U = 1/2 int [E I v''^2 + G J phi'^2 + E I_w phi''^2]                 (v: the WEAK-axis lateral displacement)
    V = 1/2 int N (v'^2 + i0^2 phi'^2) + int M phi v''                     (i0^2 = (I_y + I_z)/A)
alpha_cr: the smallest lambda with U + lambda V not positive definite (for every M_A, M_B, N in their proved ranges).

LOWER bound — the continuum, not the Hermite model: m sub-elements, Hermite cubics for v and phi; inside a
sub-element (length h) the clamped bubbles eta_v, eta_phi; E I int v_H'' eta_v'' = E I_w int phi_H'' eta_phi'' = 0;
the cross terms (G J + lambda N i0^2) int (phi_H' - mean) eta_phi', lambda N int (v_H' - mean) eta_v',
lambda int M phi_H eta_v'', lambda int M eta_phi v_H'' and the inner lambda int M eta_phi eta_v'' bounded by
Cauchy-Schwarz against the inner energy with |eta'| <= h/(2 pi) |eta''|, |eta| <= h/pi |eta'| (clamped / Dirichlet
Poincare): min over eta >= - 1/2 |beta|^2 / lambda_min(H) — a PSD correction C(lambda) on the nodal values. The form
inequality was checked numerically before this code (DESIGN-LTB.md). PD proved at every vertex of the (M_A, M_B, N)
box (the matrix is affine in them; C is built for the whole box): ZTL zenergy.pd_ieee.
UPPER bound (nominal values, the fork premise): the Hermite field itself is admissible — a witness."""
from fractions import Fraction as F
import itertools

from .frame import PI2_LO, _dy


def _pmul(p, q):
    r = [F(0)] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] += a * b
    return r


def _pint(p):                         # int_0^1 p(s) ds
    return sum(c / (i + 1) for i, c in enumerate(p))


def _shapes(h):
    """Hermite cubics in s in [0, 1] (x = h s): N, dN/dx, d2N/dx2 as coefficient lists in s."""
    N = [[F(1), F(0), F(-3), F(2)], [F(0), h, -2 * h, h], [F(0), F(0), F(3), F(-2)], [F(0), F(0), -h, h]]
    d = [[c * (i + 1) / h for i, c in enumerate(p[1:])] for p in N]
    dd = [[c * (i + 1) / h for i, c in enumerate(p[1:])] for p in d]
    return N, d, dd


def _gram(A, B, h, w=None):
    """int_0^h a_i b_j w dx (w a polynomial in s or None)"""
    return [[h * _pint(_pmul(_pmul(a, b), w) if w else _pmul(a, b)) for b in B] for a in A]


def _sub_forms(h):
    N, d, dd = _shapes(h)
    G = _gram(d, d, h)
    mvec = [h * _pint(p) for p in d]
    Q = [[G[i][j] - mvec[i] * mvec[j] / h for j in range(4)] for i in range(4)]
    return {"N": N, "d": d, "dd": dd, "G": G, "Q": Q, "Mass": _gram(N, N, h), "Bend": _gram(dd, dd, h)}


def _moment_poly(xi0, dxi, MA, MB, kap):
    """M on the sub-element xi = xi0 + s dxi, as a polynomial in s"""
    # (1 - xi) MA + xi MB + kap xi (1 - xi)
    xi = [xi0, dxi]
    one_m = [1 - xi0, -dxi]
    return [a + b + c for a, b, c in itertools.zip_longest(
        [MA * t for t in one_m], [MB * t for t in xi], [kap * t for t in _pmul(xi, one_m)], fillvalue=F(0))]


def _assemble(L, m, sec, lam, MA, MB, kap, N, corr=None):
    """the member's matrix (lower triangle dict) on the free DOFs: node k: v (4k), v' (4k+1), phi (4k+2), phi' (4k+3);
    forks: v and phi fixed at both ends. C_sub: the per-sub-element correction (8 x 8 on (v_i v_i' v_j v_j' phi_i
    phi_i' phi_j phi_j')) or None."""
    EI, GJ, EIw, i02 = sec
    h = L / m
    fx = _sub_forms(h)
    fixed = {0, 2, 4 * m, 4 * m + 2}
    free = [q for q in range(4 * (m + 1)) if q not in fixed]
    pos = {q: i for i, q in enumerate(free)}
    K = {}
    for e in range(m):
        Mp = _moment_poly(F(e, m), F(1, m), MA, MB, kap)
        Kvv = [[EI * fx["Bend"][a][b] + lam * N * fx["G"][a][b] for b in range(4)] for a in range(4)]
        Kpp = [[GJ * fx["G"][a][b] + EIw * fx["Bend"][a][b] + lam * N * i02 * fx["G"][a][b] for b in range(4)]
               for a in range(4)]
        Kpv = _gram(fx["N"], fx["dd"], h, Mp)                  # int M N_phi B_v
        loc = [[F(0)] * 8 for _ in range(8)]
        for a in range(4):
            for b in range(4):
                loc[a][b] = Kvv[a][b]
                loc[4 + a][4 + b] = Kpp[a][b]
                loc[4 + a][b] = lam * Kpv[a][b]
                loc[b][4 + a] = lam * Kpv[a][b]
        if corr is not None:
            C_sub = corr(Mp)
            if C_sub is None:
                return None, 0
            for a in range(8):
                for b in range(8):
                    loc[a][b] -= C_sub[a][b]
        g = [4 * e, 4 * e + 1, 4 * e + 4, 4 * e + 5, 4 * e + 2, 4 * e + 3, 4 * e + 6, 4 * e + 7]
        for a in range(8):
            for b in range(8):
                if g[a] in pos and g[b] in pos:
                    i, j = pos[g[a]], pos[g[b]]
                    if i >= j and loc[a][b]:
                        K[(i, j)] = K.get((i, j), F(0)) + loc[a][b]
    return K, len(free)


def _resid_form(h, N, Mp):
    """|| M phi_H - (its L2 projection on linear functions) ||^2 as a form on phi's 4 nodal values (exact): the clamped
    bubble's eta'' is orthogonal to 1 and x (eta' = 0 at both ends), so only this residual meets it"""
    basis = [[F(1)], [F(0), F(1)]]
    MN = [_pmul(Mp, n_) for n_ in N]
    W = _gram(MN, MN, h)
    U = _gram(basis, MN, h)                          # 2 x 4
    G1 = _gram(basis, basis, h)                      # 2 x 2
    det = G1[0][0] * G1[1][1] - G1[0][1] * G1[1][0]
    Gi = [[G1[1][1] / det, -G1[0][1] / det], [-G1[1][0] / det, G1[0][0] / det]]
    return [[W[i][j] - sum(U[k][i] * Gi[k][l] * U[l][j] for k in range(2) for l in range(2)) for j in range(4)]
            for i in range(4)]


def _correction(h, sec, lam, Nlo, Nhi, Mbar, Mp):
    """the per-sub-element PSD correction C (8 x 8) for the whole box, or None when it cannot be built.
    Inner energy >= 1/2 x' H x over x = (a, b) = (|eta_v''|, |eta_phi''|) (EI_w > 0) or (a, c) = (|eta_v''|,
    |eta_phi'|) (EI_w = 0); cross terms <= beta . x; min >= -1/2 beta' H^-1 beta <= -1/2 sum_i beta_i^2 / (D_i (1 - rho)),
    D = diag(H), rho = |H_12| / sqrt(D_1 D_2) (the diagonally scaled H has lambda_min = 1 - rho); beta_i^2 <=
    (#terms) sum of squares — each a coefficient times an exact PSD form on the nodal values.
    With EI_w > 0 the twist's slope is NOT a free variable: |eta_phi'| <= h/(2 pi) |eta_phi''| (2026-11-02, MEASURED:
    as a free variable with stiffness G J the correction ate the whole torsional stiffness but the chord's — the
    lower bound 0.072 for an exact 0.905)."""
    from zenergy import _sqrt_up
    from .frame import _sqrt_down
    EI, GJ, EIw, i02 = sec
    fx = _sub_forms(h)
    k1sq = h * h / (4 * PI2_LO)                      # >= (h / 2pi)^2
    k0 = h * h / (2 * PI2_LO)                        # >= h^2 / (2 pi^2)
    k2sq = h * h / PI2_LO                            # >= (h / pi)^2
    P = lam * max(F(0), -Nlo)
    Nmax = lam * max(abs(Nlo), abs(Nhi))
    gjn = max(abs(GJ + lam * Nlo * i02), abs(GJ + lam * Nhi * i02))
    Da = EI - P * k1sq
    fx = dict(fx, Resid=_resid_form(h, fx["N"], Mp))
    ta = [(lam * lam, "Resid", "phi"), (Nmax * Nmax * k1sq, "Q", "v")]   # M itself inside Resid (this vertex)
    if EIw > 0:
        Db = EIw + min(F(0), GJ - P * i02) * k1sq    # G J - P i0^2 >= 0 dropped; < 0 through |eta'| <= k1 |eta''|
        tb = [(lam * lam * Mbar * Mbar * k0 * k0, "Bend", "v"), (gjn * gjn * k1sq, "Q", "phi")]
        m_ = lam * Mbar * k0
    else:
        Db = GJ - P * i02                            # the variable is |eta_phi'|
        tb = [(lam * lam * Mbar * Mbar * k2sq, "Bend", "v"), (gjn * gjn, "Q", "phi")]
        m_ = lam * Mbar * _sqrt_up(k2sq)
    if Da <= 0 or Db <= 0:
        return None
    rho = m_ / _sqrt_down(Da * Db) if m_ else F(0)
    if rho >= 1:
        return None
    C = [[F(0)] * 8 for _ in range(8)]
    for D_, ts in ((Da, ta), (Db, tb)):
        fac = len(ts) / (D_ * (1 - rho))
        for cf, fm, dd in ts:
            o = 0 if dd == "v" else 4
            for a in range(4):
                for b in range(4):
                    if fx[fm][a][b]:
                        C[o + a][o + b] += fac * cf * fx[fm][a][b]    # EXACT (C is subtracted: no entry rounding)
    return C


def _pd(K, n):
    """proved positive definite (ZTL zenergy.pd_ieee at 0.9 of the float lambda_min)"""
    import zenergy as ZE
    import numpy as np
    A = np.zeros((n, n))
    for (i, j), v in K.items():
        A[i, j] = A[j, i] = float(v)
    mu = float(np.linalg.eigvalsh(A).min())
    if not mu > 0:
        return False
    return ZE.pd_ieee(n, K, F(mu) * F(9, 10)) is not None


def alpha_lower(L, sec, Nr, MAr, MBr, kap, m=8, rel=F(1, 1000)):
    """A PROVED lower bound of the member's critical factor (forks; lateral-torsional and torsional modes) for every
    N in Nr, M_A in MAr, M_B in MBr (closed ranges); sec = (E I_weak, G J, E I_w, i0^2). None if nothing compressed
    or bent (no mode); 0 if nothing is proved."""
    from . import judge_ztl  # noqa: F401
    Nlo, Nhi = Nr
    if Nlo >= 0 and not any(MAr) and not any(MBr) and not kap:
        return None
    Mbar = max(abs(x) for x in list(MAr) + list(MBr)) + abs(kap) / 4
    verts = list(itertools.product(MAr, MBr, Nr))
    h = L / m
    est = alpha_upper(L, sec, (MAr[0] + MAr[1]) / 2, (MBr[0] + MBr[1]) / 2, kap, (Nlo + Nhi) / 2, m, estimate=True)
    top = F(est) * F(11, 10) if est else None

    def proved(lam):                                # lam: a dyadic (the callers round it first)
        # every vertex of the (M_A, M_B, N) box: x'(K_H(M) - C(M))x is CONCAVE in (M_A, M_B) (affine minus a sum of
        # squared norms of affine maps) and affine in N, so its minimum over the box is at a vertex
        corr = lambda Mp: _correction(h, sec, lam, Nlo, Nhi, Mbar, Mp)
        for MA, MB, N in verts:
            K, n = _assemble(L, m, sec, lam, MA, MB, kap, N, corr)
            if K is None or not _pd(K, n):
                return False
        return True
    if top is None:
        return F(0)
    lo, hi = F(0), top
    start = _dy(top / 1000, False)
    for _ in range(20):
        if proved(start):
            break
        hi, start = start, _dy(start / 10, False)
    else:
        return F(0)
    lo = start
    for _ in range(40):
        mid = _dy((lo + hi) / 2, False)
        if proved(mid):
            lo = mid                                    # the value PROVED, not the unrounded midpoint
        else:
            hi = mid
        if hi - lo <= rel * hi:
            break
    return lo


def alpha_upper(L, sec, MA, MB, kap, N, m=8, estimate=False):
    """The Hermite model's critical factor at these values: a float estimate (estimate=True) or a PROVED upper bound
    by its buckling mode as a witness (x' K_E x + lam x' K_G x <= 0 beyond lam: not PD — the fork premise)."""
    import numpy as np
    import scipy.linalg as sla
    KE, n = _assemble(L, m, sec, F(0), MA, MB, kap, F(0))
    K1, _ = _assemble(L, m, sec, F(1), MA, MB, kap, N)
    A = np.zeros((n, n)); B = np.zeros((n, n))
    for (i, j), v in KE.items():
        A[i, j] = A[j, i] = float(v)
    for (i, j), v in K1.items():
        B[i, j] = B[j, i] = float(v)
    B = B - A                                        # the geometric part at lambda = 1
    vals, vecs = sla.eigh(-B, A)
    k = int(np.argmax(vals))
    if not vals[k] > 0:
        return None
    if estimate:
        return 1 / vals[k]
    x = [F(float(t)) for t in vecs[:, k]]
    q = lambda D: sum(v * x[i] * x[j] * (1 if i == j else 2) for (i, j), v in D.items())
    qE = q(KE)
    qG = q(K1) - qE
    if qG >= 0:
        return None
    lam = qE / -qG
    S = 1 << 64
    return F(-((-lam.numerator * S) // lam.denominator), S)
