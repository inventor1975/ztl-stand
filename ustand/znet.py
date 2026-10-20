"""NETWORKS: a bound on a branch current over a box of conductances, CHECKED EXACTLY (a kernel module).

Written to the kernel's rules (exact fractions, no search, no budget, the cost follows the certificate) so that it
can move into ZTL once the curator and Logik3 say so (E3); until then it lives here, in the private stand.
(The curator, 2026-10-11: "build it in the ZTL stand". Its mathematics is the circuit stand's energy certificate,
2026-10-09, there in floating point with a 1e-9 margin.)

THE CLASS. A network L(g) = S^T G S: nodes, branches j = (u, v) with conductances g_j > 0, each anywhere in its own
box [lo_j, hi_j]; one source branch holds node a at V and node b at 0. Electrical resistor networks, thermal
conductance networks, diffusion grids — any scalar Laplacian. (Trusses have the same form with vector unknowns;
there L is not an M-matrix and step 2 below needs another certificate — not in this module.)

WHAT IS CERTIFIED: max over the box of  dir * I_k  <=  U,  I_k = g_k (x_u - x_v) the current in branch k.

THE CERTIFICATE (brought by a search outside, ustand/netsearch.py; trusted for nothing): per ROUND, at the centre
g0 of that round's box,
    y  — an approximate solution of L0 x = c0 (the node potentials),
    z  — an approximate solution of L0 x = s_k (a unit current through k, the source shorted: the reverse field),
    w  — a positive vector (for a lower bound of L0's smallest eigenvalue),
each a list of integers over one common denominator.

WHAT THE KERNEL DOES, per round, exactly:
  1. the residuals  c0 - L0 y  and  s_k - L0 z  (a sparse product in fractions);
  2. lam <= lambda_min(L0):  lam = min_i (L0 w)_i / w_i, with w > 0 and L0 w > 0 — true for a symmetric
     irreducible M-matrix (L0's off-diagonals are -g <= 0; Collatz-Wielandt for its inverse, which is >= 0);
  3. the error of y in L0's energy norm <= |res| / sqrt(lam), so every branch voltage of the centre field is
     known within  sqrt(1 / g0_j) * |res| / sqrt(lam)  (the projection bound S^T L0^-1 S <= G0^-1); the same for z;
  4. the ENERGY enclosure over the round's box (g_j = g0_j (1 + d_j), |d_j| <= t_j <= t < 1):
        a branch voltage within  centre +- sqrt(1/g0_j) * rn / (1 - t),  rn = sqrt(sum_i t_i^2 g0_i u0_i^2);
        the target's u_k within  centre +- (sum_i t_i g0_i |T0_ki u0_i| + tk * rn / (1 - t)),
        tk = sqrt(sum_i t_i^2 g0_i T0_ki^2)  (first order read exactly, second order by Cauchy-Schwarz);
     the same bound for the reverse field T_kj over the box;
  5. the SIGN of each branch's influence on dir * I_k over the whole box:
        dI_k/dg_j = -g_k T_kj u_j  (j != k),   dI_k/dg_k = u_k (1 - g_k T_kk) with 0 < g_k T_kk < 1;
     a branch whose sign is certain is pinned at its favourable end — the max over the box equals the max over
     the pinned box — and the next round works on that smaller box;
  6. after the last round: U = the upper end of dir * g_k u_k over the final box.
Every square root is bounded from above by a rational, every |.| and sum is exact. The result: (True, U, info) when
the claimed bound >= U, else (False, why).
LEAN (lean/ZNet.lean, zero axioms, 2026-10-12): steps 2-6 are PROVED — cw_bound; energy_bound, laplacian_energy,
branch_error; step 4 in squared form (energy_perturbation, target_identity, target_second, target_first); pin_sound,
rounds_sound, split_sound. Named premises: Kirchhoff's law (the network's equations), the derivative-sign formulas
behind a pin (calculus); every rational root _sqrt_up gives is CHECKED (r >= 0, r*r >= q), and the pair target's
B against ZNet.quad_bound's conditions, here at run time — checked facts, not premises.
"""
from __future__ import annotations

from fractions import Fraction as F
from math import isqrt

SQRT_DEN = 1 << 64


class _RootFailed(Exception):
    pass


def _sqrt_up(q):
    """A rational >= sqrt(q), q >= 0 — CHECKED here exactly (r >= 0 and r*r >= q): lean/ZNet.lean's squared theorems
    need exactly that, so it is a checked fact, not a premise (2026-10-12)."""
    q = F(q)
    if q <= 0:
        return F(0)
    n = q.numerator * SQRT_DEN * SQRT_DEN
    r = F(isqrt(n // q.denominator) + 1, SQRT_DEN)
    if r < 0 or r * r < q:
        raise _RootFailed(f"the rational root of {q} is not above it")
    return r


class Net:
    """nodes 0..n-1; edges [(u, v)]; the source branch src = (a, b): a held at V, b at 0."""

    def __init__(self, n, edges, src, current=False):
        """current=False: the source branch holds node a at V and node b at 0 (a voltage source).
        current=True (since 2026-10-12, network v2): the source injects a current I into node a and draws it
        from node b, the reference at 0; node a is then FREE (a heat source and the ambient, for a thermal
        network). Either way the free nodes' matrix is a grounded Laplacian: a symmetric M-matrix."""
        self.n, self.edges, self.src = n, [tuple(e) for e in edges], src
        self.a, self.b = self.edges[src]
        self.current = current
        self.free = [x for x in range(n) if x not in ((self.b,) if current else (self.a, self.b))]
        self.idx = {x: i for i, x in enumerate(self.free)}
        self.res = [j for j in range(len(self.edges)) if j != src]
        self.inc = {}
        for j in self.res:
            u, v = self.edges[j]
            self.inc.setdefault(u, []).append(j)
            self.inc.setdefault(v, []).append(j)

    def pots(self, x, Va):
        """free-node vector -> all node potentials (a at Va, b at 0)."""
        p = [F(0)] * self.n
        p[self.a] = F(Va)
        for node, i in self.idx.items():
            p[node] = x[i]
        return p

    def apply(self, g, x):
        """L(g) x over the free nodes (exact)."""
        p = self.pots(x, 0)
        out = []
        for node in self.free:
            s = F(0)
            for j in self.inc.get(node, ()):
                u, v = self.edges[j]
                other = v if u == node else u
                s += g[j] * (p[node] - p[other])
            out.append(s)
        return out

    def rhs_source(self, g, V):
        """c(g): the source's injections into the free nodes (for a current source: V is the current I, put into
        node a, independent of g)."""
        if self.current:
            out = [F(0)] * len(self.free)
            out[self.idx[self.a]] = F(V)
            return out
        out = []
        for node in self.free:
            s = F(0)
            for j in self.inc.get(node, ()):
                u, v = self.edges[j]
                other = v if u == node else u
                if other == self.a:
                    s += g[j] * F(V)
            out.append(s)
        return out

    def unit(self, k):
        """s_k: +1 at k's first node, -1 at its second (free nodes only). k may be a branch index or, for a
        potential target, a PAIR of nodes ("p", "q") given as a tuple ('pair', p, q)."""
        out = [F(0)] * len(self.free)
        u, v = (k[1], k[2]) if isinstance(k, tuple) else self.edges[k]
        if u in self.idx:
            out[self.idx[u]] += 1
        if v in self.idx:
            out[self.idx[v]] -= 1
        return out

    def branch(self, p):
        return [p[u] - p[v] for (u, v) in self.edges]


def _vec(d):
    den = F(d["den"])
    return [F(int(x)) / den for x in d["v"]]


def _norm2(r):
    return sum((x * x for x in r), F(0))


def round_enclose(net, gl, gh, V, k, y, z, w):
    """One round (below); a root that fails its own check is a refusal of the round, never an exception."""
    try:
        return _round_enclose(net, gl, gh, V, k, y, z, w)
    except _RootFailed as e:
        return str(e)


def _round_enclose(net, gl, gh, V, k, y, z, w):
    """One round, exactly: enclosures over the box [gl, gh] of every branch voltage u_j, of T_kj, and of u_k
    (first order exact). -> dict, or a string saying why the round cannot be read."""
    g0 = [(a + b) / 2 for a, b in zip(gl, gh)]
    t = [((b - a) / 2) / g if g > 0 else F(0) for a, b, g in zip(gl, gh, g0)]
    tmax = max((t[j] for j in net.res), default=F(0))
    if tmax >= 1:
        return "a conductance box reaches 0 (t >= 1)"
    if any(g0[j] <= 0 for j in net.res):
        return "a conductance at or below 0"
    # 2. lambda_min of L0 from below
    if not w or any(x <= 0 for x in w):
        return "w is not positive"
    Lw = net.apply(g0, w)
    if any(x <= 0 for x in Lw):
        return "L0 w is not positive: no eigenvalue bound"
    lam = min(a / b for a, b in zip(Lw, w))
    # 1. residuals, 3. the centre fields within their errors
    c0 = net.rhs_source(g0, V)
    ry = [a - b for a, b in zip(c0, net.apply(g0, y))]
    sk = net.unit(k)
    rz = [a - b for a, b in zip(sk, net.apply(g0, z))]
    ey = _sqrt_up(_norm2(ry) / lam)                 # ||x0 - y||_L0
    ez = _sqrt_up(_norm2(rz) / lam)
    py, pz = net.pots(y, V), net.pots(z, 0)
    uy = net.branch(py)
    uz = net.branch(pz)
    inv_sqrt_g = {j: _sqrt_up(1 / g0[j]) for j in net.res}
    du0 = {j: inv_sqrt_g[j] * ey for j in net.res}   # |u0_j - uy_j|
    dT0 = {j: inv_sqrt_g[j] * ez for j in net.res}   # |T0_kj - uz_j|
    # 4. energy enclosures over the box
    absu = {j: abs(uy[j]) + du0[j] for j in net.res}
    absT = {j: abs(uz[j]) + dT0[j] for j in net.res}
    rn = _sqrt_up(sum((t[j] * t[j] * g0[j] * absu[j] * absu[j] for j in net.res), F(0)))
    rnT = _sqrt_up(sum((t[j] * t[j] * g0[j] * absT[j] * absT[j] for j in net.res), F(0)))
    den = 1 - tmax
    U = {j: (uy[j] - du0[j] - inv_sqrt_g[j] * rn / den, uy[j] + du0[j] + inv_sqrt_g[j] * rn / den) for j in net.res}
    T = {j: (uz[j] - dT0[j] - inv_sqrt_g[j] * rnT / den, uz[j] + dT0[j] + inv_sqrt_g[j] * rnT / den) for j in net.res}
    first = sum((t[j] * g0[j] * absT[j] * absu[j] for j in net.res), F(0))
    tk = _sqrt_up(sum((t[j] * t[j] * g0[j] * absT[j] * absT[j] for j in net.res), F(0)))
    hk = first + tk * rn / den
    if isinstance(k, tuple):
        # A POTENTIAL TARGET (network v2): u = x_p - x_q, no branch of its own. The centre's error on it is bounded
        # by the effective resistance R between p and q: |s.(x0 - y)| <= sqrt(R) * ey, and R = s.z0 itself is
        # bounded from z: R <= s.z + sqrt(R) * ez, so sqrt(R) <= (ez + sqrt(ez^2 + 4 max(s.z, 0))) / 2.
        _, p_, q_ = k
        sz = pz[p_] - pz[q_]
        sqrtR = (ez + _sqrt_up(ez * ez + 4 * max(sz, F(0)))) / 2
        # checked, not assumed: the two conditions ZNet.quad_bound asks of this root (sigma + B eps <= B^2, eps <= 2B)
        if not (sqrtR >= 0 and sz + sqrtR * ez <= sqrtR * sqrtR and ez <= 2 * sqrtR):
            return "the pair target's root bound fails its own check"
        c = py[p_] - py[q_]
        uk = (c - sqrtR * ey - hk, c + sqrtR * ey + hk)
        return {"U": U, "T": T, "uk": uk, "lam": lam}
    uk = (uy[k] - du0[k] - hk, uy[k] + du0[k] + hk)
    if U[k][1] - U[k][0] < uk[1] - uk[0]:
        uk = U[k]                                    # the cheap form, when it is the tighter
    return {"U": U, "T": T, "uk": uk, "lam": lam}


def pin(net, gl, gh, glo, ghi, k, direction, enc):
    """The branches whose influence on direction * I_k has a certain sign over the box: pinned at the end that
    raises it. -> (new gl, new gh, number pinned)."""
    gl, gh = list(gl), list(gh)
    pinned = 0
    U, T = enc["U"], enc["T"]
    sgn = lambda iv: 1 if iv[0] > 0 else (-1 if iv[1] < 0 else 0)
    for j in net.res:
        if gl[j] == gh[j]:
            continue
        su = sgn(U[j])
        if isinstance(k, tuple):
            s = -direction * su * sgn(T[j])          # d(x_p - x_q)/dg_j = -T_j u_j (a potential target)
        elif j == k:
            s = direction * su                       # dI_k/dg_k = u_k (1 - g_k T_kk), the bracket in (0, 1)
        else:
            s = -direction * su * sgn(T[j])          # dI_k/dg_j = -g_k T_kj u_j
        if s > 0:
            gl[j] = gh[j] = ghi[j]; pinned += 1
        elif s < 0:
            gl[j] = gh[j] = glo[j]; pinned += 1
    return gl, gh, pinned


def target_bound(net, gl, gh, k, direction, enc):
    """The upper end of direction * g_k u_k over the box (a potential target: of direction * u)."""
    a, b = enc["uk"]
    if isinstance(k, tuple):
        return max(a, b) if direction > 0 else -min(a, b)
    p = [gl[k] * a, gl[k] * b, gh[k] * a, gh[k] * b]
    return max(p) if direction > 0 else -min(p)


EXACT_POINT_NODES = 60      # a point box this small is solved exactly in fractions (Gaussian elimination)


def exact_value(net, g, V, k):
    """The target's EXACT value at one conductance vector: the linear system solved in fractions (no search, no
    rounding — the kernel's arithmetic). Used when the rounds pinned every branch: the box is then a point, and a
    requirement met with EQUALITY (a bridge's worst offset is exactly TOL x VEX) is decided, not left OPEN by the
    certificate's rounding (2026-10-12, network v2)."""
    m = len(net.free)
    A = [[F(0)] * m for _ in range(m)]
    for j in net.res:
        u, v = net.edges[j]
        for x, y in ((u, v), (v, u)):
            if x in net.idx:
                A[net.idx[x]][net.idx[x]] += g[j]
                if y in net.idx:
                    A[net.idx[x]][net.idx[y]] -= g[j]
    b = net.rhs_source(g, V)
    for i in range(m):
        piv = next((r for r in range(i, m) if A[r][i] != 0), None)
        if piv is None:
            return None
        A[i], A[piv], b[i], b[piv] = A[piv], A[i], b[piv], b[i]
        for r in range(i + 1, m):
            if A[r][i]:
                q = A[r][i] / A[i][i]
                for c in range(i, m):
                    A[r][c] -= q * A[i][c]
                b[r] -= q * b[i]
    x = [F(0)] * m
    for i in reversed(range(m)):
        x[i] = (b[i] - sum(A[i][c] * x[c] for c in range(i + 1, m))) / A[i][i]
    p = net.pots(x, V)
    if isinstance(k, tuple):
        return p[k[1]] - p[k[2]]
    u, v = net.edges[k]
    return g[k] * (p[u] - p[v])


def check(net, glo, ghi, V, k, direction, bound, cert):
    """Is max over the box of direction * I_k <= bound, by this certificate? (True, U, info) | (False, why).

    A certificate is a list of ROUNDS, or a SPLIT {"split": j, "at": "p/q", "lo": cert, "hi": cert}: branch j's box
    cut at `at` (strictly inside); the max over the box is the larger of the two halves' maxima, each certified on
    its own — the bound returned is the larger of the two."""
    glo, ghi, bound = [F(x) for x in glo], [F(x) for x in ghi], F(bound)
    if isinstance(k, tuple):
        if not (len(k) == 3 and k[0] == "pair" and k[1] in range(net.n) and k[2] in range(net.n) and k[1] != k[2]
                and (k[1] in net.idx or k[2] in net.idx) and direction in (1, -1)):
            return False, "the potential target is not a pair of distinct nodes with a free one, or the direction is not +-1"
    elif direction not in (1, -1) or k == net.src or not (0 <= k < len(net.edges)):
        return False, "the target is not a resistive branch, or the direction is not +-1"
    if any(glo[j] <= 0 or glo[j] > ghi[j] for j in net.res):
        return False, "a conductance box is not positive"
    if isinstance(cert, dict) and "split" in cert:
        try:
            j, at = int(cert["split"]), F(str(cert["at"]))
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            return False, "an unreadable split"
        if j not in net.res or not (glo[j] < at < ghi[j]):
            return False, f"a split of branch {j} at {at} not strictly inside its box"
        lo_hi, hi_lo = list(ghi), list(glo)
        lo_hi[j], hi_lo[j] = at, at
        a = check(net, glo, lo_hi, V, k, direction, bound, cert.get("lo") or {})
        if not a[0]:
            return a
        b = check(net, hi_lo, ghi, V, k, direction, bound, cert.get("hi") or {})
        if not b[0]:
            return b
        return True, max(a[1], b[1]), {"pieces": a[2].get("pieces", 1) + b[2].get("pieces", 1)}
    rounds = cert.get("rounds") or []
    if not rounds:
        return False, "no rounds"
    gl, gh = list(glo), list(ghi)
    for r, rd in enumerate(rounds):
        try:
            y, z, w = _vec(rd["y"]), _vec(rd["z"]), _vec(rd["w"])
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            return False, f"round {r}: unreadable vectors"
        m = len(net.free)
        if not (len(y) == len(z) == len(w) == m):
            return False, f"round {r}: vectors of the wrong length"
        enc = round_enclose(net, gl, gh, V, k, y, z, w)
        if isinstance(enc, str):
            return False, f"round {r}: {enc}"
        if r < len(rounds) - 1:
            gl, gh, _ = pin(net, gl, gh, glo, ghi, k, direction, enc)
        else:
            U = target_bound(net, gl, gh, k, direction, enc)
            free = sum(1 for j in net.res if gl[j] != gh[j])
            if free == 0 and len(net.free) <= EXACT_POINT_NODES:
                ex = exact_value(net, gl, V, k)     # the pinned box is a point: its exact value
                if ex is not None:
                    U = min(U, direction * ex)
            if U <= bound:
                return True, U, {"rounds": len(rounds), "free": free, "lam": enc["lam"]}
            return False, f"the bound {float(bound):.6g} is below the certified {float(U):.6g} ({free} branches free)"
    return False, "unreachable"
