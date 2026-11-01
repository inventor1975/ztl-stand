"""THE CONTINUUM, NOT THE MESH (2026-11-01, the curator's "максимальное устранение ошибок"; "не подтягиваться к
решению, а решить"). Two-sided PROVED bounds on the compliance of a plane-stress plate — the work of the loads,
C = int_GammaN t.u ds — of the ELASTIC CONTINUUM, not of the finite-element model, with every modulus anywhere in
E (1 +- t) (any field: pointwise, not per element).

Why the compliance and not a point displacement: in a 2D continuum a point value is not bounded by the energy (a
point force gives an infinite displacement), so no finite proved bound on it exists — a property of the problem.
The compliance is: under a uniform traction on one edge it is the resultant times the traction-weighted mean
displacement of that edge.

THE TWO BOUNDS — each one Cauchy-Schwarz, nothing else (u the true displacement, sigma = C eps(u), a(.,.) the
energy, f(v) = int t.v the load's work; f(u) = a(u, u) = ||sigma||^2_{C^-1}):
  LOWER  any v that is zero on the clamped edges:  f(v) = a(u, v) <= sqrt(a(u,u) a(v,v))  =>  f(u) >= f(v)^2 / a(v,v).
         v = the CST solution, rounded to dyadics; a(v, v) is EXACT (CST strains are constant), so is f(v).
  UPPER  any tau STATICALLY ADMISSIBLE (div tau = 0, tau n = t on the loaded/free edges; anything on the clamped
         ones): int tau : eps(u) = f(u) (Green), so f(u) = (tau, sigma)_{C^-1} <= ||tau|| ||sigma||  =>
         f(u) <= ||tau||^2_{C^-1}.
  Moduli in the box: a_E <= (1 + t) a_E0 and ||.||_{C_E^-1} <= ||.||_{C_E0^-1} / (1 - t), pointwise.
PREMISES (named, not proved here): linear plane-stress elasticity is the model; Green's formula (the weak form).

tau, exactly: an Airy function phi (sigma_xx = phi_yy, sigma_yy = phi_xx, sigma_xy = -phi_xy: divergence-free for
ANY phi) in the Hsieh-Clough-Tocher C1 macro-element on the plate's own triangles (each split at its centroid into
three cubics). Along the loaded/free boundary the gradient of phi is the integrated traction (d/ds phi_y = t_x,
d/ds phi_x = -t_y), so the boundary degrees of freedom are PRESCRIBED exactly; the interior ones are free, found in
floating point (minimising ||tau||) — and rounded: any values give an admissible tau. HCT, not Bogner-Fox-Schmit:
a uniform shear on an edge meeting a free edge needs sigma_xy = -p and 0 at the same corner; HCT has no twist
degree of freedom at the vertices, BFS does.

NOT TRUSTED: the construction. An independent EXACT checker (check_admissible) verifies the tau it produced —
div tau = 0 in every sub-triangle, the normal traction continuous across every interior edge, tau n = t on every
loaded/free edge — before ||tau||^2 is used.

THE DECK: plate.py's, plus the continuum's loads, which nodal forces cannot fix (a corner node's force splits
between two edges in any way):
    python3 -m ustand.hypercircle deck.txt --tol 0.5%                       the proved compliance bracket
    python3 -m ustand.hypercircle deck.txt --tol 0.5% --req "MEAN <= 0.00135"   a requirement on C or MEAN
    TRAC, n1, n2, Fx, Fy        a uniform traction on the boundary segment n1-n2 with resultant (Fx, Fy);
                                the deck's F at every free degree of freedom must be its consistent load (checked)
Version 1: the loaded/free boundary is one connected arc, the rest CLAMPED (UX and UY on whole edges); a point
support or a roller edge is refused (not a continuum condition here); one material; no body force.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction as F

from .plate import PlateError, energy_system_full, read_deck
from .spice import tolerance
from .truss import _num, _show

MON = [(0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2), (3, 0), (2, 1), (1, 2), (0, 3)]   # x^a y^b, cubic


class HCError(PlateError):
    pass


def split_deck(text):
    """(the plate deck without TRAC lines, [(n1, n2, Fx, Fy)])."""
    keep, tr = [], []
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split("!")[0].strip()
        f = [x.strip() for x in (line.split(",") if "," in line else line.split())] if line else []
        if f and f[0].upper() == "TRAC":
            if len(f) != 5:
                raise HCError(f"line {ln}: TRAC, n1, n2, Fx, Fy")
            tr.append((int(f[1]), int(f[2]), _num(f[3], f"line {ln}"), _num(f[4], f"line {ln}")))
        else:
            keep.append(raw)
    return "\n".join(keep), tr


# ---------------------------------------------------------------------------------------------------------------
# polynomials (cubic, coefficients over MON, coordinates relative to a point)

def _val(c, x, y):
    return sum(ci * x ** a * y ** b for ci, (a, b) in zip(c, MON) if ci)


def _grad(c, x, y):
    gx = sum(ci * a * x ** (a - 1) * y ** b for ci, (a, b) in zip(c, MON) if ci and a)
    gy = sum(ci * b * x ** a * y ** (b - 1) for ci, (a, b) in zip(c, MON) if ci and b)
    return gx, gy


def _rows_val(x, y):
    return [x ** a * y ** b for a, b in MON]


def _rows_grad(x, y):
    return ([a * x ** (a - 1) * y ** b if a else F(0) for a, b in MON],
            [b * x ** a * y ** (b - 1) if b else F(0) for a, b in MON])


def _stress(c, x, y):
    """(sigma_xx, sigma_yy, sigma_xy) of the Airy cubic c at (x, y): (phi_yy, phi_xx, -phi_xy)."""
    pxx = 2 * c[3] + 6 * c[6] * x + 2 * c[7] * y
    pxy = c[4] + 2 * c[7] * x + 2 * c[8] * y
    pyy = 2 * c[5] + 2 * c[8] * x + 6 * c[9] * y
    return pyy, pxx, -pxy


def _solve_exact(A, B):
    """A X = B exactly (A m x n, consistent, rank n): X n x k. Gauss-Jordan over Fractions."""
    m, n, k = len(A), len(A[0]), len(B[0])
    M = [list(A[i]) + list(B[i]) for i in range(m)]
    r = 0
    piv = []
    for col in range(n):
        p = next((i for i in range(r, m) if M[i][col] != 0), None)
        if p is None:
            raise HCError("internal: HCT system singular")
        M[r], M[p] = M[p], M[r]
        inv = 1 / M[r][col]
        M[r] = [v * inv for v in M[r]]
        for i in range(m):
            if i != r and M[i][col] != 0:
                fct = M[i][col]
                M[i] = [a - fct * b for a, b in zip(M[i], M[r])]
        piv.append(col)
        r += 1
    for i in range(r, m):                                # consistency: the redundant rows reduce to zero
        if any(M[i][n + j] != 0 for j in range(k)):
            raise HCError("internal: HCT system inconsistent")
    return [[M[i][n + j] for j in range(k)] for i in range(n)]


_BASIS = {}


def hct_basis(P, nus):
    """The HCT macro-element on the triangle P = (P1, P2, P3) (counterclockwise), coordinates RELATIVE TO THE
    CENTROID: a 30 x 12 exact matrix, sub-triangle cubics (T1 = P2 P3 G, T2 = P3 P1 G, T3 = P1 P2 G, 10 each) from
    the 12 degrees of freedom [phi, phi_x, phi_y at P1, P2, P3; grad phi(mid) . nu at the edges P2P3, P3P1, P1P2],
    nu the (unnormalised) edge normals given. Cached by shape."""
    G = ((P[0][0] + P[1][0] + P[2][0]) / 3, (P[0][1] + P[1][1] + P[2][1]) / 3)
    Q = [(p[0] - G[0], p[1] - G[1]) for p in P]
    key = (tuple(Q), tuple(nus))
    if key in _BASIS:
        return _BASIS[key]
    z = [F(0)] * 10
    rows, rhs = [], []
    def put(sub, vec, r):
        row = [F(0)] * 30
        for i, v in enumerate(vec):
            row[10 * sub + i] = v
        rows.append(row)
        rhs.append(r)
    def put2(s1, v1, s2, v2):
        row = [F(0)] * 30
        for i, v in enumerate(v1):
            row[10 * s1 + i] += v
        for i, v in enumerate(v2):
            row[10 * s2 + i] -= v
        rows.append(row)
        rhs.append([F(0)] * 12)
    # internal edges G-Pj: shared by the two sub-triangles holding Pj (T1: P2 P3; T2: P3 P1; T3: P1 P2)
    share = {0: (1, 2), 1: (2, 0), 2: (0, 1)}            # vertex j -> the two subs
    for j, (s1, s2) in share.items():
        for u in (F(0), F(1, 3), F(2, 3), F(1)):
            x, y = Q[j][0] * u, Q[j][1] * u
            put2(s1, _rows_val(x, y), s2, _rows_val(x, y))
        for u in (F(0), F(1, 2), F(1)):
            x, y = Q[j][0] * u, Q[j][1] * u
            gx, gy = _rows_grad(x, y)
            put2(s1, gx, s2, gx)
            put2(s1, gy, s2, gy)
    unit = lambda d: [F(int(i == d)) for i in range(12)]
    # vertex degrees of freedom, on one sub-triangle holding the vertex
    for j in range(3):
        s = share[j][0]
        x, y = Q[j]
        gx, gy = _rows_grad(x, y)
        put(s, _rows_val(x, y), unit(3 * j))
        put(s, gx, unit(3 * j + 1))
        put(s, gy, unit(3 * j + 2))
    # edge midpoints: edge e opposite vertex e lies in sub-triangle e
    for e in range(3):
        a, b = Q[(e + 1) % 3], Q[(e + 2) % 3]
        x, y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        gx, gy = _rows_grad(x, y)
        nu = nus[e]
        put(e, [nu[0] * p + nu[1] * q for p, q in zip(gx, gy)], unit(9 + e))
    X = _solve_exact(rows, rhs)
    _BASIS[key] = (X, Q)
    return X, Q


# ---------------------------------------------------------------------------------------------------------------
# the problem

def setup(text, tol="0"):
    plate, trac = split_deck(text)
    nodes, elems, loads, supports, ex, nu, th = read_deck(plate)
    t = F(0) if tol in (None, "0", 0) else tolerance(tol) if isinstance(tol, str) else F(tol)
    tris = []
    for (a, b, c) in elems:
        (x1, y1), (x2, y2), (x3, y3) = nodes[a], nodes[b], nodes[c]
        a2 = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if a2 == 0:
            raise HCError(f"element {a}-{b}-{c}: zero area")
        tris.append((a, b, c) if a2 > 0 else (a, c, b))
    edges = {}
    for k, tr in enumerate(tris):
        for e in range(3):
            a, b = tr[(e + 1) % 3], tr[(e + 2) % 3]
            edges.setdefault((min(a, b), max(a, b)), []).append((k, e, a, b))
    bnd = {key: v[0] for key, v in edges.items() if len(v) == 1}
    if any(len(v) > 2 for v in edges.values()):
        raise HCError("an edge shared by more than two triangles: not a plane domain")
    clamped = {key for key in bnd if all((n, d) in supports for n in key for d in "XY")}
    covered = {n for key in clamped for n in key}
    for (n, d) in supports:
        if n not in covered:
            raise HCError(f"node {n}: a support not on a clamped edge (a point support or a roller) — not a "
                          f"continuum condition in version 1")
    if not clamped:
        raise HCError("no clamped edge: version 1 needs one (rigid motions)")
    # the boundary loop, counterclockwise (each boundary edge as its triangle traverses it)
    nxt = {}
    for key, (k, e, a, b) in bnd.items():
        if a in nxt:
            raise HCError(f"node {a}: the boundary touches itself (not one simple loop)")
        nxt[a] = (b, key)
    start = next(iter(nxt))
    loop, n = [], start
    while True:
        b, key = nxt[n]
        loop.append((n, b, key))
        n = b
        if n == start:
            break
    if len(loop) != len(bnd):
        raise HCError("more than one boundary loop (a hole): version 1 needs a simply connected plate")
    # the loaded/free arc: one contiguous run of non-clamped edges
    i0 = next(i for i, (_, _, key) in enumerate(loop) if key in clamped and loop[(i + 1) % len(loop)][2] not in clamped) \
        if len(clamped) < len(loop) else None
    arc = []
    if i0 is not None:
        i = (i0 + 1) % len(loop)
        while loop[i][2] not in clamped:
            arc.append(loop[i])
            i = (i + 1) % len(loop)
        if len(arc) + len(clamped) != len(loop):
            raise HCError("the clamped edges are not one contiguous run: version 1 needs one loaded/free arc")
    tmap = {}
    for (a, b, fx, fy) in trac:
        key = (min(a, b), max(a, b))
        if key not in bnd or key in clamped:
            raise HCError(f"TRAC {a}-{b}: not a loaded/free boundary segment")
        tmap[key] = tmap.get(key, (F(0), F(0)))
        tmap[key] = (tmap[key][0] + fx, tmap[key][1] + fy)
    # the deck's nodal forces must be the consistent loads (half of each resultant to each end)
    cons = {}
    for (a, b), (fx, fy) in tmap.items():
        for n in (a, b):
            cons[(n, "X")] = cons.get((n, "X"), F(0)) + fx / 2
            cons[(n, "Y")] = cons.get((n, "Y"), F(0)) + fy / 2
    for nd in set(cons) | set(loads):
        if nd in supports:
            continue
        if cons.get(nd, F(0)) != loads.get(nd, F(0)):
            raise HCError(f"node {nd[0]} {nd[1]}: the deck's force {loads.get(nd, F(0))} is not the TRAC lines' "
                          f"consistent load {cons.get(nd, F(0))}")
    return {"nodes": nodes, "tris": tris, "edges": edges, "bnd": bnd, "clamped": clamped, "arc": arc,
            "trac": tmap, "ex": ex, "nu": nu, "th": th, "t": t, "plate": plate, "supports": supports}


def _nu(nodes, a, b):
    """The global normal of edge {a, b}: from the smaller node id to the larger, rotated clockwise."""
    p, q = (a, b) if a < b else (b, a)
    dx, dy = nodes[q][0] - nodes[p][0], nodes[q][1] - nodes[p][1]
    return (dy, -dx)


def prescribed(S):
    """Along the loaded/free arc: phi, phi_x, phi_y at its nodes and grad phi(mid) . nu on its edges, exact."""
    nodes, th = S["nodes"], S["th"]
    vals, edge = {}, {}
    if not S["arc"]:
        return vals, edge
    a0 = S["arc"][0][0]
    ph, gx, gy = F(0), F(0), F(0)
    vals[a0] = (ph, gx, gy)
    for (a, b, key) in S["arc"]:
        fx, fy = S["trac"].get(key, (F(0), F(0)))
        dx, dy = nodes[b][0] - nodes[a][0], nodes[b][1] - nodes[a][1]
        tx, ty = fx / th, fy / th                    # int t ds over the segment (stress x length)
        ph2 = ph + dx * (gx - ty / 2) + dy * (gy + tx / 2)
        gx2, gy2 = gx - ty, gy + tx
        nu = _nu(nodes, a, b)
        edge[key] = ((gx + gx2) / 2) * nu[0] + ((gy + gy2) / 2) * nu[1]
        ph, gx, gy = ph2, gx2, gy2
        vals[b] = (ph, gx, gy)
    return vals, edge


def _dofs(S):
    """Global degree-of-freedom numbering: (node, 0|1|2) and ('e', key)."""
    idx = {}
    for n in sorted(S["nodes"]):
        for c in range(3):
            idx[(n, c)] = len(idx)
    for key in sorted(S["edges"]):
        idx[("e", key)] = len(idx)
    return idx


def _local(S, k):
    nodes = S["nodes"]
    tr = S["tris"][k]
    P = [nodes[n] for n in tr]
    keys = [(min(tr[(e + 1) % 3], tr[(e + 2) % 3]), max(tr[(e + 1) % 3], tr[(e + 2) % 3])) for e in range(3)]
    nus = [_nu(nodes, *key) for key in keys]
    X, Q = hct_basis(P, nus)
    return tr, keys, X, Q


def _sub_energy_gram(Qa, Qb, nu):
    """The 10 x 10 exact Gram matrix of int (1/E0-free) [sxx^2 + syy^2 - 2 nu sxx syy + 2(1+nu) sxy^2] dA over the
    sub-triangle (Qa, Qb, origin), in the cubic's coefficients (midpoint rule: exact for the quadratic density)."""
    pts = [((Qa[0] + Qb[0]) / 2, (Qa[1] + Qb[1]) / 2), (Qa[0] / 2, Qa[1] / 2), (Qb[0] / 2, Qb[1] / 2)]
    area = abs(Qa[0] * Qb[1] - Qa[1] * Qb[0]) / 2
    Gm = [[F(0)] * 10 for _ in range(10)]
    for (x, y) in pts:
        # linear maps coefficient -> stress components
        sxx = [F(0)] * 10; syy = [F(0)] * 10; sxy = [F(0)] * 10
        syy[3], syy[6], syy[7] = F(2), 6 * x, 2 * y
        sxy[4], sxy[7], sxy[8] = F(-1), -2 * x, -2 * y
        sxx[5], sxx[8], sxx[9] = F(2), 2 * x, 6 * y
        for i in range(10):
            for j in range(10):
                v = sxx[i] * sxx[j] + syy[i] * syy[j] - nu * (sxx[i] * syy[j] + syy[i] * sxx[j]) \
                    + 2 * (1 + nu) * sxy[i] * sxy[j]
                if v:
                    Gm[i][j] += v * area / 3
    return Gm


_GRAM = {}


def _elem_gram(S, k):
    tr, keys, X, Q = _local(S, k)
    gkey = (tuple(Q), tuple(_nu(S["nodes"], *key) for key in keys), S["nu"])
    if gkey not in _GRAM:
        subs = [(Q[1], Q[2]), (Q[2], Q[0]), (Q[0], Q[1])]
        Gs = [_sub_energy_gram(a, b, S["nu"]) for a, b in subs]
        Kl = [[F(0)] * 12 for _ in range(12)]
        for s in range(3):
            Gm = Gs[s]
            Xs = X[10 * s:10 * s + 10]
            GX = [[sum(Gm[i][l] * Xs[l][j] for l in range(10)) for j in range(12)] for i in range(10)]
            for p in range(12):
                for q in range(12):
                    Kl[p][q] += sum(Xs[i][p] * GX[i][q] for i in range(10))
        _GRAM[gkey] = Kl
    return tr, keys, _GRAM[gkey]


def _elem_dofs(idx, tr, keys):
    return [idx[(tr[j], c)] for j in range(3) for c in range(3)] + [idx[("e", key)] for key in keys]


def airy_field(S):
    """The Airy degrees of freedom: prescribed exactly on the loaded/free arc, the rest from minimising ||tau||^2
    in floating point, rounded to dyadics. Returns {dof index: exact value}."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    idx = _dofs(S)
    vals, edge = prescribed(S)
    fixed = {}
    for n, v in vals.items():
        for c in range(3):
            fixed[idx[(n, c)]] = v[c]
    for key, v in edge.items():
        fixed[idx[("e", key)]] = v
    N = len(idx)
    rows, cols, data = [], [], []
    for k in range(len(S["tris"])):
        tr, keys, Kl = _elem_gram(S, k)
        ds = _elem_dofs(idx, tr, keys)
        for p in range(12):
            for q in range(12):
                if Kl[p][q]:
                    rows.append(ds[p]); cols.append(ds[q]); data.append(float(Kl[p][q]))
    K = sp.csr_matrix((data, (rows, cols)), shape=(N, N))
    free = np.array([i for i in range(N) if i not in fixed])
    fx = np.array([i for i in range(N) if i in fixed])
    xp = np.array([float(fixed[i]) for i in fx])
    # dofs of the clamped edge's interior that touch nothing loaded are free; a dof no element touches: zero
    Kff = K[free][:, free]
    rhs = -(K[free][:, fx] @ xp) if len(fx) else np.zeros(len(free))
    diag = Kff.diagonal()
    keep = diag > 0
    sol = np.zeros(len(free))
    if keep.any():
        Kk = Kff[keep][:, keep].tocsc()
        sol[keep] = sla.spsolve(Kk, rhs[keep])
    out = dict(fixed)
    for i, v in zip(free, sol):
        out[int(i)] = F(float(v))
    return out, idx


def tau_pieces(S, dof, idx):
    """Every sub-triangle's exact Airy cubic, in GLOBAL coordinates' offsets: [(k, s, origin G, coefficients,
    vertices relative to G)]."""
    out = []
    for k in range(len(S["tris"])):
        tr, keys, X, Q = _local(S, k)
        P = [S["nodes"][n] for n in tr]
        G = ((P[0][0] + P[1][0] + P[2][0]) / 3, (P[0][1] + P[1][1] + P[2][1]) / 3)
        d = [dof[i] for i in _elem_dofs(idx, tr, keys)]
        subs = [(1, 2), (2, 0), (0, 1)]
        for s in range(3):
            c = [sum(X[10 * s + i][j] * d[j] for j in range(12) if d[j]) for i in range(10)]
            out.append((k, s, G, c, (Q[subs[s][0]], Q[subs[s][1]])))
    return out


def check_admissible(S, pieces):
    """INDEPENDENT EXACT CHECK of tau (piecewise linear on the sub-triangles): div tau = 0 in each; tau n
    continuous across every interior edge (both ends of it); tau n = the traction on every loaded/free edge (both
    ends). Works on tau alone — not on how it was built. Raises on the first failure; returns the counts."""
    nodes, th = S["nodes"], S["th"]
    def st(c, G, p):
        return _stress(c, p[0] - G[0], p[1] - G[1])
    def tn(s, nu):
        return (s[0] * nu[0] + s[2] * nu[1], s[2] * nu[0] + s[1] * nu[1])
    seg = {}
    divs = 0
    for (k, s, G, c, (qa, qb)) in pieces:
        # div: d/dx sxx + d/dy sxy = phi_yyx - phi_xyy = 2c8 - 2c8 ; d/dx sxy + d/dy syy = -(2c7) + 2c7
        if (2 * c[8] - 2 * c[8]) != 0 or (-2 * c[7] + 2 * c[7]) != 0:
            raise HCError(f"element {k} sub {s}: div tau != 0")
        divs += 1
        A = (G[0] + qa[0], G[1] + qa[1])
        B = (G[0] + qb[0], G[1] + qb[1])
        for (p, q, r) in ((A, B, G), (B, G, A), (G, A, B)):
            key = (min(p, q), max(p, q))
            seg.setdefault(key, []).append((c, G, r))      # r: the sub-triangle's third vertex
    inner = outer = 0
    tr_on = {}
    for (a, b), (fx, fy) in S["trac"].items():
        tr_on[(min(nodes[a], nodes[b]), max(nodes[a], nodes[b]))] = (fx, fy, a, b)
    clamped_pts = {(min(nodes[a], nodes[b]), max(nodes[a], nodes[b])) for (a, b) in S["clamped"]}
    for key, lst in seg.items():
        p, q = key
        nu = (q[1] - p[1], -(q[0] - p[0]))
        if len(lst) == 2:
            (c1, G1, _), (c2, G2, _) = lst
            for pt in (p, q):
                if tn(st(c1, G1, pt), nu) != tn(st(c2, G2, pt), nu):
                    raise HCError(f"traction jumps across the interior edge {p}-{q}")
            inner += 1
        elif len(lst) == 1:
            if key in clamped_pts:
                continue
            (c1, G1, r), = lst
            fx, fy, a, b = tr_on.get(key, (F(0), F(0), None, None))
            # nu has the edge's length; turned OUTWARD (away from the third vertex): tau nu = t * length = F / th
            if (r[0] - p[0]) * nu[0] + (r[1] - p[1]) * nu[1] > 0:
                nu = (-nu[0], -nu[1])
            want = (fx / th, fy / th)
            for pt in (p, q):
                got = tn(st(c1, G1, pt), nu)
                if got != want:
                    raise HCError(f"boundary edge {p}-{q}: tau n = {got}, the traction is {want}")
            outer += 1
        else:
            raise HCError("internal: a segment in more than two sub-triangles")
    return {"sub_triangles": divs, "interior_edges": inner, "boundary_edges": outer}


def lower_lst(S):
    """The LOWER bound's admissible field, one order up (2026-11-01): quadratic (6-node) triangles on the same mesh,
    zero on the clamped edges (corner and mid-side values), solved in floating point, rounded to dyadics; then
    f(v) EXACT (Simpson along each loaded segment: exact for the quadratic trace under a uniform traction) and a(v,v)
    EXACT (the strain is linear in a triangle: the three edge midpoints integrate its square exactly).
    Returns (f(v), a(v,v)) at the nominal modulus."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    nodes, tris, ex, nu, th = S["nodes"], S["tris"], S["ex"], S["nu"], S["th"]
    clamped = S["clamped"]
    pts = {n: ("n", n) for n in nodes}
    for key in S["edges"]:
        pts[("m", key)] = ("m", key)
    fixed = {n for key in clamped for n in key} | {("m", key) for key in clamped}
    ids = {}
    for p_ in sorted(pts, key=str):
        if p_ in fixed:
            continue
        ids[(p_, 0)] = len(ids)
        ids[(p_, 1)] = len(ids)
    def loc(tr):
        a, b, c = tr
        mids = [("m", (min(b, c), max(b, c))), ("m", (min(c, a), max(c, a))), ("m", (min(a, b), max(a, b)))]
        return [a, b, c] + mids                         # N1 N2 N3, then N23 N31 N12
    s_ = 1 / (1 - nu * nu)
    D = [[s_, s_ * nu, F(0)], [s_ * nu, s_, F(0)], [F(0), F(0), s_ * (1 - nu) / 2]]
    def grads(P, L):
        (x1, y1), (x2, y2), (x3, y3) = P
        a2 = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        dL = [((y2 - y3) / a2, (x3 - x2) / a2), ((y3 - y1) / a2, (x1 - x3) / a2), ((y1 - y2) / a2, (x2 - x1) / a2)]
        g = [((4 * L[i] - 1) * dL[i][0], (4 * L[i] - 1) * dL[i][1]) for i in range(3)]
        for (i, j) in ((1, 2), (2, 0), (0, 1)):
            g.append((4 * (L[j] * dL[i][0] + L[i] * dL[j][0]), 4 * (L[j] * dL[i][1] + L[i] * dL[j][1])))
        return g, a2 / 2
    QP = [(F(0), F(1, 2), F(1, 2)), (F(1, 2), F(0), F(1, 2)), (F(1, 2), F(1, 2), F(0))]
    def bmat(g):
        # rows eps_xx, eps_yy, gamma_xy over [u1 v1 u2 v2 ... u6 v6]
        r0, r1, r2 = [], [], []
        for gx, gy in g:
            r0 += [gx, F(0)]; r1 += [F(0), gy]; r2 += [gy, gx]
        return [r0, r1, r2]
    Df = np.array([[float(x) for x in r] for r in D])
    rows, cols, data = [], [], []
    elem_info = []
    for tr in tris:
        P = [nodes[n] for n in tr]
        L6 = loc(tr)
        gl = [ids.get((L6[i], c)) for i in range(6) for c in range(2)]
        Bs = []
        Ke = np.zeros((12, 12))
        for L in QP:
            g, area = grads(P, L)
            Bm = bmat(g)
            Bs.append(Bm)
            Bf = np.array([[float(x) for x in r] for r in Bm])
            Ke += float(area / 3) * (Bf.T @ Df @ Bf)
        Ke *= float(ex * th)
        elem_info.append((gl, Bs, area))
        for p_ in range(12):
            if gl[p_] is None:
                continue
            for q in range(12):
                if gl[q] is None:
                    continue
                rows.append(gl[p_]); cols.append(gl[q]); data.append(Ke[p_, q])
    N = len(ids)
    K = sp.csr_matrix((data, (rows, cols)), shape=(N, N))
    fvec = np.zeros(N)
    loads = []                                          # (dof list [a, m, b] per component, resultant)
    for (a, b), (fx, fy) in S["trac"].items():
        key = (a, b)
        for c, fc in ((0, fx), (1, fy)):
            if not fc:
                continue
            trip = [ids.get((a, c)), ids.get((("m", key), c)), ids.get((b, c))]
            loads.append((trip, fc))
            for w, d in zip((F(1, 6), F(4, 6), F(1, 6)), trip):
                if d is not None:
                    fvec[d] += float(fc * w)
    v = sla.spsolve(K.tocsc(), fvec)
    vq = [F(float(x)) for x in v]
    fv = F(0)
    for trip, fc in loads:
        fv += fc * sum(w * vq[d] for w, d in zip((F(1, 6), F(4, 6), F(1, 6)), trip) if d is not None)
    av = F(0)
    for gl, Bs, area in elem_info:
        ve = [vq[d] if d is not None else F(0) for d in gl]
        for Bm in Bs:
            eps = [sum(b * x for b, x in zip(r, ve) if b and x) for r in Bm]
            av += area / 3 * sum(eps[i] * D[i][j] * eps[j] for i in range(3) for j in range(3) if D[i][j])
    return fv, av * ex * th


def compliance_bounds(text, tol="0", lower_field="lst"):
    """The PROVED bracket [lower, upper] on the continuum's compliance f(u) for every modulus field in the box."""
    import numpy as np
    import scipy.sparse.linalg as sla
    from . import judge_ztl  # noqa: F401
    import zenergy as ZE
    S = setup(text, tol)
    t = S["t"]
    # LOWER: an admissible field v, rounded; f(v)^2 / a(v, v), exact — quadratic triangles (lower_lst), or the
    # CST solution itself (lower="cst")
    if lower_field == "cst":
        parts, f, dof, emap, _ = energy_system_full(S["plate"], "0")
        n = len(dof)
        K0 = ZE.matrix(parts, n)
        A = ZE._float_matrix(K0, n)
        vf = sla.spsolve(A.tocsc(), np.array([float(x) for x in f]))
        v = [F(float(x)) for x in vf]
        fv = sum(a * b for a, b in zip(f, v))
        av = sum(a * b for a, b in zip(v, ZE._kmul(K0, v, n)))
    else:
        n = None
        fv, av = lower_lst(S)
    if fv <= 0 or av <= 0:
        raise HCError("the loads do no work on the mesh solution: nothing to bound")
    lower = fv * fv / av / (1 + t)
    # UPPER: tau from the Airy field, checked, then ||tau||^2 / (1 - t)
    adof, idx = airy_field(S)
    pieces = tau_pieces(S, adof, idx)
    chk = check_admissible(S, pieces)
    th, ex, nu = S["th"], S["ex"], S["nu"]
    energy = F(0)
    for (k, s, G, c, (qa, qb)) in pieces:
        Gm = _sub_energy_gram(qa, qb, nu)
        energy += sum(c[i] * Gm[i][j] * c[j] for i in range(10) for j in range(10) if c[i] and c[j] and Gm[i][j])
    upper = th * energy / ex / (1 - t)
    return {"lower": lower, "upper": upper, "check": chk, "unknowns_fe": n, "airy_dofs": len(idx)}


def judge(text, tol, requirements):
    """Requirements on the CONTINUUM: ("C" | "MEAN", "<=" | ">=", v). C the compliance (N m); MEAN = C / |R|, the
    traction-weighted mean displacement ALONG the load (R the resultant), defined when every TRAC resultant points
    the same way. EARNED when the proved bracket is inside, REFUTED when it is wholly outside (then for EVERY modulus
    field in the box), OPEN otherwise."""
    r = compliance_bounds(text, tol)
    S = setup(text, tol)
    lo, hi = r["lower"], r["upper"]
    rows = []
    for tgt, op, v in requirements:
        a, b = lo, hi
        if tgt == "MEAN":
            fs = [fv for fv in S["trac"].values() if fv != (0, 0)]
            if not fs or any(f1[0] * f2[1] != f1[1] * f2[0] or f1[0] * f2[0] + f1[1] * f2[1] <= 0
                             for f1 in fs for f2 in fs):
                raise HCError("MEAN needs every TRAC resultant in one direction (else use C)")
            R2 = sum(f[0] for f in fs) ** 2 + sum(f[1] for f in fs) ** 2
            from .truss import _sqrt
            R = _sqrt(R2)
            if R is None:
                raise HCError("MEAN: the resultant's length is irrational — use C")
            a, b = lo / R, hi / R
        ok = (b <= v) if op == "<=" else (a >= v)
        bad = (a > v) if op == "<=" else (b < v)
        rows.append({"requirement": f"{tgt} {op} {v}", "proved_range": [_show(a, -1), _show(b, 1)],
                     "verdict": "EARNED" if ok else "REFUTED" if bad else "OPEN"})
    vs = [x["verdict"] for x in rows]
    return {"verdict": "REFUTED" if "REFUTED" in vs else "EARNED" if all(x == "EARNED" for x in vs) else "OPEN",
            "path": "the continuum (hypercircle): kinematic field from below, exactly checked equilibrated stress "
                    "from above", "requirements": rows, "admissibility_checked": r["check"],
            "premises": "linear plane-stress elasticity; Green's formula"}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    import re
    text = open(argv[0], encoding="utf-8").read()
    tol = argv[argv.index("--tol") + 1] if "--tol" in argv else "0"
    reqs = []
    for i, a in enumerate(argv):
        if a == "--req":
            m = re.match(r"^\s*(C|MEAN)\s*(<=|>=)\s*(\S+)\s*$", argv[i + 1])
            if not m:
                raise HCError(f"{argv[i + 1]!r}: a requirement is C or MEAN, <= or >=, a value")
            reqs.append((m.group(1), m.group(2), _num(m.group(3), argv[i + 1])))
    if reqs:
        print(json.dumps(judge(text, tol, reqs), indent=1, ensure_ascii=False))
        return 0
    r = compliance_bounds(text, tol)
    print(json.dumps({"compliance_proved": [_show(r["lower"], -1), _show(r["upper"], 1)],
                      "admissibility_checked": r["check"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
