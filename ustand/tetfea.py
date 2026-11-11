# -*- coding: utf-8 -*-
"""
tetfea — a PROVED lower bound on the compliance of a part, on its own tetrahedral mesh (2026-11-10, CAD/FEA level 2a).

    python3 -m ustand.tetfea deck.fem [--subcase 1] [--E 113800] [--nu 0.342]

THE PROBLEM (read from a Nastran/OptiStruct bulk deck: GRID, CTETRA, RBE2 + SPC, RBE3, FORCE / MOMENT, MAT1):
  linear isotropic elasticity on the solid the CTETRA mesh fills; u = 0 on the surfaces an RBE2 ties to an SPC'd
  node (a rigid spider to a fixed node: EXACTLY zero displacement there); the load: the RBE3 distribution of the
  subcase's FORCE / MOMENT at the RBE3's reference node to its dependent nodes (equal weights, translations):
      f_i = w_i [ F / W + (J^-1 M_c) x d_i ],  d_i = x_i - c,  c the weighted centroid,
      J = sum w_i (|d_i|^2 I - d_i d_i^T),  M_c = M + (x_ref - c) x F      (sum f_i = F, sum d_i x f_i = M_c).
  PREMISE (said): the continuum load is the surface traction on the RBE3's faces whose consistent P1 nodal loads ARE
  these f_i — then f(v) = sum f_i . v_i holds EXACTLY for every P1 field v below, and the problem is well posed
  (a point force has infinite compliance in 3D; a traction does not).

THE BOUND (minimum potential energy): for ANY v with v = 0 on the supports, C >= 2 a f(v) - a^2 a(v, v) for every
  scalar a; at the best a, C >= f(v)^2 / a(v, v). C = the work of the load = the true compliance. v: continuous P1 on
  the mesh's tets, CHOSEN by a float solve (smoothed-aggregation AMG + CG) — any v is admissible, the float only
  chooses. Then v is ROUNDED to integers over 2^S (still admissible) and both numbers are computed exactly:
      f(v): an exact rational (the f_i taken as the binary64 values they are — the load's definition);
      a(v, v) = sum over tets of (mu Q1 + lambda Q2) / (6 * 10^k * 2^(2S) * det),  M = dV . adj(D) in integers,
          Q1 = 2 sum M_aa^2 + sum_(a<b) (M_ab + M_ba)^2,  Q2 = (tr M)^2  — each tet's term an exact rational,
          rounded UP to binary64, the sum of N such terms raised by (1 + (N + 1) u)(1 + u)  (u = 2^-53).
  With the subcase's load the compliance is a WORK: for a pure FORCE at the RBE3 reference node it is F . u_ref, so
  C / |F| is a proved LOWER bound on the reference node's displacement along F.
WHAT IT IS NOT: an upper bound (that needs an equilibrated stress field — level 2b), nor a bound on a maximum
displacement or stress at a point. The mesh is taken as the part (its sha256 is reported: EARNED IF STABLE on it).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
from fractions import Fraction as Fr

S = 40                      # v rounded to integers over 2^S (|v| ~ mm: integers up to ~2^43)
U = 2.0 ** -53


# ------------------------------------------------------------------------------------------------ reading the deck
_NUM = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))([eEdD]?[+-]\d+)?$")


def _nas(s):
    """A Nastran real in small-field form: '4.43-9' = 4.43e-9, '-.2018' , '1.0' -> exact decimal Fraction."""
    s = s.strip()
    if not s:
        return Fr(0)
    m = _NUM.match(s)
    if not m:
        raise ValueError(f"not a Nastran number: {s!r}")
    base, ex = m.group(1), m.group(2)
    v = Fr(base)
    if ex:
        v *= Fr(10) ** int(ex.lstrip("eEdD"))
    return v


def _fields(line):
    line = line.rstrip("\r\n")
    return [line[i:i + 8] for i in range(0, max(len(line), 8), 8)]


def read_deck(path):
    if str(path).endswith(".deck.pkl"):
        # a deck WE wrote (ustand.refine: a red refinement carrying its traction) — never a downloaded file
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)
    grids, tets, rbe2, rbe3, spc, force, moment, mat = {}, [], [], [], {}, {}, {}, None
    subcases = {}
    cards, cur = [], None
    cur_sub, bulk = None, False
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("$"):
                continue
            s = line.strip()
            if not bulk:                              # the case control section: SUBCASE n / KEY = value / LABEL x
                if s.startswith("BEGIN BULK"):
                    bulk = True
                elif s.startswith("SUBCASE"):
                    cur_sub = int(s.split()[1])
                    subcases[cur_sub] = {}
                elif cur_sub is not None and "=" in s:
                    key, val = [x.strip() for x in s.split("=", 1)]
                    subcases[cur_sub][key] = val
                elif cur_sub is not None and s.startswith("LABEL"):
                    subcases[cur_sub]["LABEL"] = s[5:].strip()
                continue
            if line.startswith("+"):
                if cur is not None:
                    cur.extend(_fields(line)[1:])
                continue
            if line[:1].isalpha():
                cur = _fields(line)
                cards.append(cur)
    for c in cards:
        k = c[0].strip()
        if k == "GRID":
            grids[int(c[1])] = tuple(c[3:6])
        elif k == "CTETRA":
            tets.append(tuple(int(x) for x in c[3:7]))
        elif k == "RBE2":
            rbe2.append((int(c[2]), [int(x) for x in c[4:] if x.strip()]))
        elif k == "RBE3":
            ref, wt = int(c[3]), _nas(c[5])
            rbe3.append((ref, wt, [int(x) for x in c[7:] if x.strip()]))     # EID, -, REFGRID, REFC, WT1, C1, G...
        elif k == "SPC":
            spc[int(c[2])] = c[3].strip()
        elif k == "FORCE":
            force[int(c[1])] = (int(c[2]), _nas(c[4]), tuple(_nas(x) for x in c[5:8]))
        elif k == "MOMENT":
            moment[int(c[1])] = (int(c[2]), _nas(c[4]), tuple(_nas(x) for x in c[5:8]))
        elif k == "MAT1":
            mat = (_nas(c[2]), _nas(c[4]), _nas(c[5]))        # E, nu, rho  (G left blank)
    if not grids or not tets:
        # SimJEB's own archive holds one such deck (bracket 293: 0 bytes, while its metadata reports results) — said,
        # not crashed on (2026-11-10)
        raise ValueError(f"the deck has no GRID / CTETRA cards ({len(grids)} grids, {len(tets)} tets): empty or not a "
                         f"solid tet deck")
    return dict(grids=grids, tets=tets, rbe2=rbe2, rbe3=rbe3, spc=spc, force=force, moment=moment, mat=mat,
                subcases=subcases)


# ------------------------------------------------------------------------------------------------ the load
def rbe3_loads(xyz, ref, nodes, F, M):
    """RBE3 (equal weights, translations): nodal forces with sum = F and moment about c = M + (x_ref - c) x F."""
    import numpy as np
    X = np.array([xyz[n] for n in nodes], dtype=float)
    c = X.mean(axis=0)
    d = X - c
    J = (d * d).sum() * np.eye(3) - d.T @ d
    Mc = np.array(M, float) + np.cross(np.array(xyz[ref], float) - c, np.array(F, float))
    w = np.linalg.solve(J, Mc)
    f = np.array(F, float) / len(nodes) + np.cross(w, d)
    return f


# ------------------------------------------------------------------------------------------------ the bound
def a_upper_float(XI, T, vi, mu, lam, k, Xf=None):
    """A PROVED upper bound on a(v, v), VECTORISED in binary64 with every rounding bounded (2026-11-10, the curator:
    «6 часов на расчёт — это долго»). Notation: U = 2^-53, g_n = nU / (1 - nU); every bound is entrywise.
      coordinates Xf = the exact decimals rounded (|X~ - X| <= U |X~| (1 + U));
      D~ = fl(X~_q - X~_0):  e_D = U (|X~_q| + |X~_0|)(1 + 2U) + U |D~|;
      adj~ (2x2 minors of D~ in float):  e_adj = sum over its two products (|a| e_b + |b| e_a + e_a e_b)
                                                 + g3 (|a b| + |c d|),   all (1 + 4U);
      det~ = sum_q D~_0q adj~_q0:  e_det = sum_q (|D~| e_adj + e_D |adj~| + e_D e_adj) + g4 sum |D~| |adj~|, (1 + 4U);
      dV integers < 2^52 (exact in float);  M~ = dV . adj~:  e_M = (sum |dV| e_adj + g4 sum |dV| |adj~|)(1 + 4U);
      every |M_ab|, |M_ab + M_ba|, |tr M| at its upper end, squared, summed; |det| >= |det~| - e_det (asserted > 0);
      each tet's term (mu Q1 + lam Q2) / (6 10^k 2^(2S) |det|) — the 10^k cancels: the coordinates are in mm here, so
      the term is (mu Q1 + lam Q2) / (6 2^(2S) |det|) with M and det in mm units — raised by (1 + g16), the sum by
      (1 + (N + 1) U). The exact integer version (a_upper_exact) is compared in tests/test_tetfea.py."""
    import numpy as np
    T = np.asarray(T, dtype=np.int64)
    X = np.asarray(Xf, dtype=np.float64)
    g3, g4, g16 = (n * U / (1 - n * U) for n in (3, 4, 16))
    X0 = X[T[:, 0]]
    Xq = np.stack([X[T[:, 1]], X[T[:, 2]], X[T[:, 3]]], axis=2)          # (n, r, q)
    D = Xq - X0[:, :, None]
    eD = U * (np.abs(Xq) + np.abs(X0)[:, :, None]) * (1 + 2 * U) + U * np.abs(D)

    def minor(i1, j1, i2, j2, i3, j3, i4, j4):
        a, b, c, d = D[:, i1, j1], D[:, i2, j2], D[:, i3, j3], D[:, i4, j4]
        ea, eb, ec, ed = eD[:, i1, j1], eD[:, i2, j2], eD[:, i3, j3], eD[:, i4, j4]
        val = a * b - c * d
        err = (np.abs(a) * eb + np.abs(b) * ea + ea * eb + np.abs(c) * ed + np.abs(d) * ec + ec * ed
               + g3 * (np.abs(a * b) + np.abs(c * d))) * (1 + 4 * U)
        return val, err
    spec = {(0, 0): (1, 1, 2, 2, 1, 2, 2, 1), (0, 1): (0, 2, 2, 1, 0, 1, 2, 2), (0, 2): (0, 1, 1, 2, 0, 2, 1, 1),
            (1, 0): (1, 2, 2, 0, 1, 0, 2, 2), (1, 1): (0, 0, 2, 2, 0, 2, 2, 0), (1, 2): (0, 2, 1, 0, 0, 0, 1, 2),
            (2, 0): (1, 0, 2, 1, 1, 1, 2, 0), (2, 1): (0, 1, 2, 0, 0, 0, 2, 1), (2, 2): (0, 0, 1, 1, 0, 1, 1, 0)}
    adj = np.empty_like(D)
    eadj = np.empty_like(D)
    for (i, j), args in spec.items():
        adj[:, i, j], eadj[:, i, j] = minor(*args)
    det = (D[:, 0, :] * adj[:, :, 0]).sum(axis=1)
    edet = ((np.abs(D[:, 0, :]) * eadj[:, :, 0] + eD[:, 0, :] * np.abs(adj[:, :, 0]) + eD[:, 0, :] * eadj[:, :, 0]).sum(axis=1)
            + g4 * (np.abs(D[:, 0, :]) * np.abs(adj[:, :, 0])).sum(axis=1)) * (1 + 4 * U)
    adet_lo = np.abs(det) - edet
    assert (adet_lo > 0).all(), "a tetrahedron too flat for the float determinant bound"
    V = np.asarray(vi, dtype=np.int64).reshape(-1, 3)
    assert np.abs(V).max() < 2 ** 51
    v0 = V[T[:, 0]]
    dV = np.stack([V[T[:, 1]] - v0, V[T[:, 2]] - v0, V[T[:, 3]] - v0], axis=2).astype(np.float64)   # (n, c, q) exact
    Mt = np.einsum("ncq,nqb->ncb", dV, adj)
    aV = np.abs(dV)
    Me = (np.einsum("ncq,nqb->ncb", aV, eadj) + g4 * np.einsum("ncq,nqb->ncb", aV, np.abs(adj))) * (1 + 4 * U)
    up = lambda x, e: np.abs(x) + e
    q1 = 2 * (up(Mt[:, 0, 0], Me[:, 0, 0]) ** 2 + up(Mt[:, 1, 1], Me[:, 1, 1]) ** 2 + up(Mt[:, 2, 2], Me[:, 2, 2]) ** 2) \
        + up(Mt[:, 0, 1] + Mt[:, 1, 0], Me[:, 0, 1] + Me[:, 1, 0]) ** 2 \
        + up(Mt[:, 0, 2] + Mt[:, 2, 0], Me[:, 0, 2] + Me[:, 2, 0]) ** 2 \
        + up(Mt[:, 1, 2] + Mt[:, 2, 1], Me[:, 1, 2] + Me[:, 2, 1]) ** 2
    q2 = up(Mt[:, 0, 0] + Mt[:, 1, 1] + Mt[:, 2, 2], Me[:, 0, 0] + Me[:, 1, 1] + Me[:, 2, 2]) ** 2
    mu_up = math.nextafter(float(mu), math.inf)
    la_up = math.nextafter(float(lam), math.inf)
    term = (mu_up * q1 + la_up * q2) / (6.0 * 2.0 ** (2 * S) * adet_lo)
    total = float(term.sum()) * (1 + g16) * (1 + (len(term) + 1) * U)
    return math.nextafter(total, math.inf)


def solve(deck, subcase=1, E=None, nu=None, tol=1e-9, log=print, exact=False):
    return solve_cases(deck, [subcase], E, nu, tol, log, exact)[0]


def solve_cases(deck, subcases, E=None, nu=None, tol=1e-9, log=print, exact=False, return_u=False):
    """The stiffness, its AMG and the supports once; then each subcase: its load, its solve, its exact bound."""
    import numpy as np
    import scipy.sparse as sp
    t0 = time.time()
    g = deck["grids"]
    ids = sorted(g)
    idx = {n: i for i, n in enumerate(ids)}
    # exact integer coordinates over one power of ten
    dec = {n: tuple(_nas(x) for x in g[n]) for n in ids}
    k = max(max(len(str(x.denominator)) - 1 for x in p) for p in dec.values())
    while any((x * 10 ** k).denominator != 1 for p in dec.values() for x in p):
        k += 1
    XI = [tuple(int(x * 10 ** k) for x in dec[n]) for n in ids]
    X = np.array([[float(x) for x in dec[n]] for n in ids])
    E = Fr(str(E)) if E is not None else deck["mat"][0]
    nu = Fr(str(nu)) if nu is not None else deck["mat"][1]
    mu, lam = E / (2 * (1 + nu)), E * nu / ((1 + nu) * (1 - 2 * nu))
    tets = [tuple(idx[n] for n in t) for t in deck["tets"] if all(n in idx for n in t)]
    T = np.array(tets)
    # supports: RBE2 dependents of SPC'd (123456) independents, plus the SPC'd grids themselves if they are mesh nodes
    fixed = set()
    for ind, deps in deck["rbe2"]:
        if deck["spc"].get(ind, "").startswith("123"):
            fixed |= {idx[n] for n in deps if n in idx}
    ndof = 3 * len(ids)
    log(f"  read: {len(ids)} nodes, {len(T)} tets, {len(fixed)} supported nodes; {time.time() - t0:.1f} s")
    # ---- float stiffness (only to CHOOSE v)
    P = X[T]                                     # (n, 4, 3)
    D = np.stack([P[:, 1] - P[:, 0], P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]], axis=2)   # columns
    det = np.linalg.det(D)
    Dinv = np.linalg.inv(D)                      # rows: grad of barycentric 1..3
    grads = np.concatenate([-Dinv.sum(axis=1, keepdims=True), Dinv], axis=1)          # (n, 4, 3)
    vol = np.abs(det) / 6
    mu_f, lam_f = float(mu), float(lam)
    # element stiffness K_e[(i,a),(j,b)] = vol (mu (g_i.g_j) delta_ab + mu g_ib g_ja + lam g_ia g_jb)
    # assembled in CHUNKS (2026-11-10: the whole-mesh einsum temporaries peaked at ~3.2 GB a process; 8 processes
    # under the 18 GB cap were killed by the cgroup OOM — MEASURED)
    K = sp.csr_matrix((ndof, ndof))
    for c0 in range(0, len(T), 100000):
        gr = grads[c0:c0 + 100000]
        gg = np.einsum("nik,njk->nij", gr, gr)
        Ke = (mu_f * np.einsum("nij,ab->niajb", gg, np.eye(3)) + mu_f * np.einsum("nib,nja->niajb", gr, gr)
              + lam_f * np.einsum("nia,njb->niajb", gr, gr)) * vol[c0:c0 + 100000, None, None, None, None]
        dofs = (3 * T[c0:c0 + 100000, :, None] + np.arange(3)[None, None, :]).reshape(len(gr), 12)
        rows = np.repeat(dofs, 12, axis=1).ravel()
        cols = np.tile(dofs, (1, 12)).ravel()
        K = K + sp.csr_matrix((Ke.reshape(len(gr), 144).ravel(), (rows, cols)), shape=(ndof, ndof))
        del Ke, gg
    free = np.ones(ndof, bool)
    for i in fixed:
        free[3 * i:3 * i + 3] = False
    Kf = K[free][:, free]
    log(f"  assembled {ndof} dof ({free.sum()} free), {K.nnz} nonzeros; {time.time() - t0:.1f} s")
    import pyamg
    # THE SIX RIGID MOTIONS as the near-null space (as elastic3d, 2026-11-03): without them CG stalled — MEASURED
    # 2026-11-10 on SimJEB 148: 501 iterations, residual 1.2e-1 (the bound still holds — any v does — but is loose)
    Xn = X.repeat(3, axis=0)
    comp = np.tile(np.arange(3), len(X))
    B = np.zeros((ndof, 6))
    for c3 in range(3):
        B[comp == c3, c3] = 1.0
    B[comp == 0, 3], B[comp == 1, 3] = -Xn[comp == 0, 1], Xn[comp == 1, 0]
    B[comp == 1, 4], B[comp == 2, 4] = -Xn[comp == 1, 2], Xn[comp == 2, 1]
    B[comp == 0, 5], B[comp == 2, 5] = Xn[comp == 0, 2], -Xn[comp == 2, 0]
    ml = pyamg.smoothed_aggregation_solver(Kf, B=B[free], symmetry="symmetric", max_coarse=500)
    outs = []
    for subcase in subcases:
        # load: a deck subcase, or (2026-11-10, level 3a) an explicit RBE3 resultant {"F": (3,), "M": (3,), "label": ..}
        # on the deck's RBE3 — a combination f +- s g of subcases for polarization
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
        trc = deck.get("traction")
        if trc is not None:
            # a REFINED deck (ustand.refine): the load IS the coarse deck's traction, linear per coarse face, given by
            # its nodal values; the fine nodal loads are its consistent loads. Only that load is defined here.
            if custom:
                same = all(abs(a - b) <= 1e-9 * (1 + abs(b)) for a, b in zip(F + Mm, tuple(trc["F"]) + tuple(trc["M"])))
            else:
                same = subcase == trc["subcase"]
            if not same:
                raise ValueError("a refined deck carries the traction of ONE load; this subcase / load is not it")
            from . import tetmesh as _TM
            from . import refine as _RF
            Fm, own_, _, _ = _TM.faces(T)
            kind_ = _TM.classify(Fm, own_, fixed, {idx[n] for n in trc["nodal"]})
            fn = _RF.traction_loads(X, Fm, kind_, {idx[n]: v for n, v in trc["nodal"].items()})
            fvec = fn.ravel().copy()
            rnodes = list(trc["nodal"])
        else:
            rref, _, rnodes = deck["rbe3"][0]
            xyz = {n: [float(x) for x in dec[n]] for n in rnodes + [rref]}
            fl = rbe3_loads(xyz, rref, rnodes, F, Mm)
            fvec = np.zeros(ndof)
            for n, fi in zip(rnodes, fl):
                fvec[3 * idx[n]:3 * idx[n] + 3] += fi
        # level 3b (2026-11-11): a PRESTRESS added to the load, l_p(v) = int_omega eps(v) : sig_e — {"omega": a bool
        # mask over the deck's tets, "sigma": 3 x 3 exact (Fractions)}; its float nodal vector only CHOOSES v, the bound
        # takes l_p(v) exactly (prestress_work_exact)
        pre = subcase.get("prestress") if custom else None
        ftot = fvec
        if pre is not None:
            if len(tets) != len(deck["tets"]):
                raise ValueError("a prestress region needs every deck tet on the mesh")
            om = np.asarray(pre["omega"], bool)
            if "S1" in pre:
                # level 3c: a LINEAR extractor sig_e(x) = S0 + S1 . x; eps(v) is constant on a P1 tet, so
                # int_T sig_e(x) : eps(v) = |T| sig_e(centroid) : eps(v) EXACTLY
                S0f = np.array([[float(x) for x in r] for r in pre["S0"]])
                S1f = np.array([[[float(x) for x in c] for c in r] for r in pre["S1"]])
                cen = P[om].mean(axis=1)
                sgT = S0f[None] + np.einsum("ijk,nk->nij", S1f, cen)
                contrib = vol[om, None, None] * np.einsum("nia,nba->nib", grads[om], sgT)
            else:
                sgf = np.array([[float(x) for x in row] for row in pre["sigma"]])
                contrib = vol[om, None, None] * (grads[om] @ sgf.T)                   # (n, 4, 3): node i, comp a
            dofs_p = 3 * T[om, :, None] + np.arange(3)[None, None, :]
            ftot = fvec.copy()
            np.add.at(ftot, dofs_p.ravel(), contrib.ravel())
        res = []
        uf = ml.solve(ftot[free], tol=tol, accel="cg", maxiter=2000, residuals=res)
        log(f"  solved: {len(res)} iterations, residual {res[-1] / res[0]:.2e}; {time.time() - t0:.1f} s")
        u = np.zeros(ndof)
        u[free] = uf
        c_float = float(ftot @ u)
        # ---- EXACT: v = round(u * 2^S) / 2^S, zero on the supports (exactly)
        vi = [int(round(x * 2 ** S)) for x in u]
        for i in fixed:
            vi[3 * i] = vi[3 * i + 1] = vi[3 * i + 2] = 0
        fv = sum(Fr(float(fvec[j])) * vi[j] for j in range(ndof) if fvec[j] != 0) / 2 ** S
        fp_exact = None
        if pre is not None:
            if "S1" in pre:
                sig_per = {}
                for tt_ in np.where(om)[0]:
                    cq = [Fr(sum(XI[q][r] for q in tets[int(tt_)]), 4 * 10 ** k) for r in range(3)]
                    sig_per[int(tt_)] = [[pre["S0"][i][j] + sum(pre["S1"][i][j][kk] * cq[kk] for kk in range(3))
                                          for j in range(3)] for i in range(3)]
                fp_exact = prestress_work_exact(XI, tets, vi, np.where(om)[0], None, k, sig_per=sig_per)
            else:
                fp_exact = prestress_work_exact(XI, tets, vi, np.where(om)[0], pre["sigma"], k)
            fv += fp_exact
        if not exact:
            a_up = a_upper_float(XI, tets, vi, mu, lam, k, Xf=X)
        else:
            a_up = a_upper_exact(XI, tets, vi, mu, lam, k)
        lower = fv * fv / Fr(a_up)
        Fn = math.sqrt(sum(x * x for x in F))
        out = {"subcase": ({kk: vv for kk, vv in subcase.items() if kk != "prestress"} if custom else subcase), "label": (subcase.get("label", "custom") if custom
                                             else deck["subcases"][subcase].get("LABEL")), "F": F, "M": Mm,
               "E": float(E), "nu": float(nu), "dof": ndof, "fixed_nodes": len(fixed), "loaded_nodes": len(rnodes),
               "compliance_float": c_float, "compliance_lower_proved": float(lower) * (1 - 2 * U),
               "f_v_exact": float(fv), "a_vv_up": a_up, "seconds": round(time.time() - t0, 1),
               "cg_iterations": len(res), "a_bound": "exact integers" if exact else "binary64, rounding bounded"}
        if pre is not None:
            out["prestress"] = {"tets": int(om.sum()), "work_exact": float(fp_exact)}
        if Fn and not any(Mm) and pre is None:
            out["ref_disp_along_F_lower_proved"] = out["compliance_lower_proved"] / Fn * (1 - 2 * U)
        if return_u:
            out["u"] = u.reshape(-1, 3)                  # the float FE displacement (node order = sorted GRID ids)
        outs.append(out)
    return outs


def prestress_work_exact(XI, tets, vi, omega, sig, k, sig_per=None):
    """l_p(v) = sum over the tets of omega of |T| eps(v) : sig, EXACTLY, for v = vi / 2^S (P1) and the exact coordinates
    XI / 10^k: |T| grad v = sign(det) dV adj(D) / (6 2^S 10^(2k)) with D, adj(D), dV in integers (sig symmetric, so
    eps : sig = grad : sig). sig: 3 x 3 Fractions."""
    acc = Fr(0)
    for t in omega:
        p0, p1, p2, p3 = tets[int(t)]
        x0 = XI[p0]
        (a11, a12, a13), (a21, a22, a23), (a31, a32, a33) = [[XI[q][r] - x0[r] for q in (p1, p2, p3)] for r in range(3)]
        dt = a11 * (a22 * a33 - a23 * a32) - a12 * (a21 * a33 - a23 * a31) + a13 * (a21 * a32 - a22 * a31)
        if dt == 0:
            raise ValueError("a degenerate tetrahedron")
        adj = [[a22 * a33 - a23 * a32, a13 * a32 - a12 * a33, a12 * a23 - a13 * a22],
               [a23 * a31 - a21 * a33, a11 * a33 - a13 * a31, a13 * a21 - a11 * a23],
               [a21 * a32 - a22 * a31, a12 * a31 - a11 * a32, a11 * a22 - a12 * a21]]
        v0 = vi[3 * p0:3 * p0 + 3]
        dV = [[vi[3 * q + c] - v0[c] for q in (p1, p2, p3)] for c in range(3)]
        sg_ = sig_per[int(t)] if sig_per is not None else sig      # level 3c: sig_e at the tet's centroid
        term = sum(sum(dV[c][q] * adj[q][b] for q in range(3)) * sg_[c][b] for c in range(3) for b in range(3))
        acc += term if dt > 0 else -term
    return acc / (6 * 2 ** S * 10 ** (2 * k))


def a_upper_exact(XI, tets, vi, mu, lam, k):
    """The exact-integer version of a_upper_float (every tet's term an exact rational, rounded up)."""
    if True:
        mu_n, mu_d = mu.numerator, mu.denominator
        la_n, la_d = lam.numerator, lam.denominator
        den0 = 6 * 10 ** k * 2 ** (2 * S)
        a_up = 0.0
        nT = 0
        for (p0, p1, p2, p3) in tets:
            x0 = XI[p0]
            cols3 = [[XI[q][r] - x0[r] for q in (p1, p2, p3)] for r in range(3)]   # D (rows r, cols q)
            (a11, a12, a13), (a21, a22, a23), (a31, a32, a33) = cols3
            dt = a11 * (a22 * a33 - a23 * a32) - a12 * (a21 * a33 - a23 * a31) + a13 * (a21 * a32 - a22 * a31)
            if dt == 0:
                raise ValueError("a degenerate tetrahedron")
            adj = [[a22 * a33 - a23 * a32, a13 * a32 - a12 * a33, a12 * a23 - a13 * a22],
                   [a23 * a31 - a21 * a33, a11 * a33 - a13 * a31, a13 * a21 - a11 * a23],
                   [a21 * a32 - a22 * a31, a12 * a31 - a11 * a32, a11 * a22 - a12 * a21]]
            v0 = vi[3 * p0:3 * p0 + 3]
            dV = [[vi[3 * q + c] - v0[c] for q in (p1, p2, p3)] for c in range(3)]   # dV[c][q]
            Mx = [[sum(dV[c][q] * adj[q][b] for q in range(3)) for b in range(3)] for c in range(3)]
            q1 = 2 * (Mx[0][0] ** 2 + Mx[1][1] ** 2 + Mx[2][2] ** 2) + (Mx[0][1] + Mx[1][0]) ** 2 \
                + (Mx[0][2] + Mx[2][0]) ** 2 + (Mx[1][2] + Mx[2][1]) ** 2
            q2 = (Mx[0][0] + Mx[1][1] + Mx[2][2]) ** 2
            num = mu_n * la_d * q1 + la_n * mu_d * q2
            dd = den0 * abs(dt) * mu_d * la_d
            # int / int is correctly rounded, so x may lie BELOW the true quotient: always step up (2026-11-10: the first
            # version tested `x * dd != num` in FLOATS, which can call an inexact quotient exact — fixed, not observed)
            a_up += math.nextafter(num / dd, math.inf)
            nT += 1
        a_up = a_up * (1 + (nT + 1) * U) * (1 + U)
        return math.nextafter(a_up, math.inf)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="ustand.tetfea")
    ap.add_argument("deck")
    ap.add_argument("--subcase", type=int, default=1)
    ap.add_argument("--E", type=float)
    ap.add_argument("--nu", type=float)
    a = ap.parse_args(argv)
    sha = hashlib.sha256(open(a.deck, "rb").read()).hexdigest()
    deck = read_deck(a.deck)
    r = solve(deck, a.subcase, a.E, a.nu, log=lambda s: print(s, file=sys.stderr))
    r["sha256"] = sha
    print(json.dumps(r, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
