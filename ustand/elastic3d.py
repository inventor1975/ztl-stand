"""elastic3d — a PROVED upper bound on the apparent Young's modulus of a 3D voxel sample (linear elasticity), judged
by ZTL. The stand's 3D phase, track 3, version 1 (2026-11-03): ONE-SIDED, by the curator's choice (A) of the night.

    python3 -m ustand.elastic3d volume.npy --e 0:0 --e 1:200e9 --nu 1:0.3 [--need-max 150e9] [--refine 2]

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
NOT HERE (version 1): a LOWER bound — it needs an exactly equilibrated SYMMETRIC stress field vanishing in the pores
  (in 3D there is no scalar Airy function); so "E_app >= need" is REFUTED or OPEN, never EARNED; "E_app <= need" is
  EARNED or OPEN.
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


def judge(V, phases, need_max=None, need_min=None, refine=1):
    """E_app <= need_max (EARNED / OPEN) and E_app >= need_min (REFUTED / OPEN), by ZTL over [0, upper]."""
    from . import judge_ztl  # noqa: F401
    from znumjudge import parse_quantities, judge_sheet_claim
    up, _, _ = upper(V, phases, refine)
    used = set(np.unique(np.asarray(V)).tolist())
    prov = "earned:elastic3d" if all(phases[k].get("earned") for k in used if k in phases) else "credit"
    f = lambda x: f"{x.numerator}/{x.denominator}"
    qs, mk = parse_quantities(f"eapp=[0,{f(up)}] {prov}")
    out = {"upper": float(up), "lower": 0.0,
           "premise": "linear isotropic elasticity per phase; the voxel map is the sample; smooth grips on x = 0 / "
                      "x = nx (mean strain 1), other faces free; IEEE 754 rounding (bounded); ONE-SIDED (no lower "
                      "bound in version 1)"}
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
    refine, i = 1, 0
    while i < len(rest):
        if rest[i] == "--need-max":
            need_max = rest[i + 1]; i += 2
        elif rest[i] == "--need-min":
            need_min = rest[i + 1]; i += 2
        elif rest[i] == "--refine":
            refine = int(rest[i + 1]); i += 2
        else:
            raise SystemExit(f"unknown argument {rest[i]}")
    print(json.dumps(judge(V, ph, need_max, need_min, refine)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
