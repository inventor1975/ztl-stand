"""An INDEPENDENT 3D space-frame reference (redteam, 2026-11-02): numpy only, its own parser and element matrices.

Model = the stand's named premises: Euler-Bernoulli members, linear elasticity, second order with the FIRST-ORDER axial
forces, geometric stiffness in both bending planes, no torsional geometric term (no torsional / flexural-torsional
buckling). Each member is cut into `ns` sub-elements (N piecewise constant per sub-element). Local axes follow the deck
semantics of BEAM4 as frame3d documents them: x' along the member; y' = e_Z x d / H (vertical members: y' = global Y);
z' = x' x y'; THETA = 90 turns (y', z') into (z', -y'). IZZ bends about z' (displacement along y'), IYY about y'.
QLOAD (global direction, per length) as consistent sub-element loads. Releases are NOT modelled (decks without them).
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla

DOF = {"UX": 0, "UY": 1, "UZ": 2, "ROTX": 3, "ROTY": 4, "ROTZ": 5}
FD = {"FX": 0, "FY": 1, "FZ": 2, "MX": 3, "MY": 4, "MZ": 5}


def parse(text):
    nodes, elems, sups, loads, qloads = {}, [], set(), [], []
    E = nu = None
    R = None
    for raw in text.splitlines():
        line = raw.split("!")[0].strip()
        if not line:
            continue
        f = [x.strip() for x in line.split(",")]
        c = f[0].upper()
        if c == "N":
            nodes[int(f[1])] = np.array([float(Fraction(x)) for x in f[2:5]])
        elif c == "E":
            elems.append((int(f[1]), int(f[2])))
        elif c == "MP" and f[1].upper() == "EX":
            E = float(f[3])
        elif c == "MP" and f[1].upper() == "PRXY":
            nu = float(f[3])
        elif c == "R":
            v = [float(x) if x else 0.0 for x in f[2:]]
            R = dict(A=v[0], Iz=v[1], Iy=v[2], tkz=v[3], tky=v[4], theta=v[5], Ix=v[7])
        elif c == "D":
            d = f[2].upper()
            for dd in (DOF.values() if d == "ALL" else [DOF[d]]):
                sups.add((int(f[1]), dd))
        elif c == "F":
            loads.append((int(f[1]), FD[f[2].upper()], float(f[3])))
        elif c == "QLOAD":
            qloads.append((int(f[1]), "XYZ".index(f[2].upper()[1]), float(f[3])))
        elif c == "RELEASE":
            raise ValueError("ref3d: releases are not modelled")
    return nodes, elems, sups, loads, qloads, E, nu, R


def axes(pi, pj, theta):
    d = pj - pi
    L = np.linalg.norm(d)
    x = d / L
    if abs(d[0]) + abs(d[1]) < 1e-12:
        y = np.array([0.0, 1.0, 0.0])
    else:
        y = np.array([-d[1], d[0], 0.0]); y /= np.linalg.norm(y)
    z = np.cross(x, y)
    if round(theta) == 90:
        y, z = z, -y
    return L, np.vstack([x, y, z])


def kmat(E, G, R, l):
    A, Iz, Iy, Ix = R["A"], R["Iz"], R["Iy"], R["Ix"]
    k = np.zeros((12, 12))
    # axial
    for a, b, s in ((0, 0, 1), (6, 6, 1), (0, 6, -1), (6, 0, -1)):
        k[a, b] = s * E * A / l
    for a, b, s in ((3, 3, 1), (9, 9, 1), (3, 9, -1), (9, 3, -1)):
        k[a, b] = s * G * Ix / l
    # bending about z' (v = u_y', th_z): dofs 1, 5, 7, 11
    bz = E * Iz / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                     [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
    iz = [1, 5, 7, 11]
    # bending about y' (w = u_z', th_y = -w'): dofs 2, 4, 8, 10 with the rotations' sign flipped
    by = E * Iy / l ** 3 * np.array([[12, -6 * l, -12, -6 * l], [-6 * l, 4 * l * l, 6 * l, 2 * l * l],
                                     [-12, 6 * l, 12, 6 * l], [-6 * l, 2 * l * l, 6 * l, 4 * l * l]])
    iy = [2, 4, 8, 10]
    k[np.ix_(iz, iz)] += bz
    k[np.ix_(iy, iy)] += by
    return k


def gmat(l):
    g = np.zeros((12, 12))
    gz = 1 / (30 * l) * np.array([[36, 3 * l, -36, 3 * l], [3 * l, 4 * l * l, -3 * l, -l * l],
                                  [-36, -3 * l, 36, -3 * l], [3 * l, -l * l, -3 * l, 4 * l * l]])
    gy = 1 / (30 * l) * np.array([[36, -3 * l, -36, -3 * l], [-3 * l, 4 * l * l, 3 * l, -l * l],
                                  [-36, 3 * l, 36, 3 * l], [-3 * l, -l * l, 3 * l, 4 * l * l]])
    g[np.ix_([1, 5, 7, 11], [1, 5, 7, 11])] += gz
    g[np.ix_([2, 4, 8, 10], [2, 4, 8, 10])] += gy
    return g


def build(text, moduli=None, ns=16):
    nodes, elems, sups, loads, qloads, E, nu, R = parse(text)
    G = E / (2 * (1 + nu))
    m = len(elems)
    moduli = [1.0] * m if moduli is None else moduli
    pos = dict(nodes)
    nxt = max(nodes) + 1
    els = []
    q_of = {}
    for k, ax, q in qloads:
        q_of.setdefault(k, np.zeros(3))[ax] += q
    for k, (i, j) in enumerate(elems):
        L, Tm = axes(nodes[i], nodes[j], R["theta"])
        ids = [i]
        for s in range(1, ns):
            pos[nxt] = nodes[i] + (nodes[j] - nodes[i]) * s / ns
            ids.append(nxt); nxt += 1
        ids.append(j)
        l = L / ns
        T = np.zeros((12, 12))
        for b in range(4):
            T[3 * b:3 * b + 3, 3 * b:3 * b + 3] = Tm
        qg = q_of.get(k + 1, np.zeros(3))
        ql = Tm @ qg                                         # (axial, along y', along z') per length
        fl = np.zeros(12)
        fl[0] = fl[6] = ql[0] * l / 2
        fl[1] = fl[7] = ql[1] * l / 2
        fl[5], fl[11] = ql[1] * l * l / 12, -ql[1] * l * l / 12
        fl[2] = fl[8] = ql[2] * l / 2
        fl[4], fl[10] = -ql[2] * l * l / 12, ql[2] * l * l / 12
        ke = kmat(E * moduli[k], G * moduli[k], R, l)
        for a, b in zip(ids[:-1], ids[1:]):
            els.append((k, a, b, l, T, ke, fl))
    idx = {n: q for q, n in enumerate(sorted(pos))}
    ndof = 6 * len(idx)
    fixed = {6 * idx[n] + d for n, d in sups}
    free = np.array([d for d in range(ndof) if d not in fixed])
    f = np.zeros(ndof)
    for n, d, v in loads:
        f[6 * idx[n] + d] += v
    for (k, a, b, l, T, ke, fl) in els:
        dofs = list(range(6 * idx[a], 6 * idx[a] + 6)) + list(range(6 * idx[b], 6 * idx[b] + 6))
        f[dofs] += T.T @ fl
    return els, idx, ndof, free, f, R, m


def _assemble(els, idx, ndof, Ns=None, geo_only=False):
    rows, cols, vals = [], [], []
    for e, (k, a, b, l, T, ke, fl) in enumerate(els):
        mat = (Ns[e] * gmat(l) if Ns is not None else 0) + (0 if geo_only else ke)
        kg = T.T @ mat @ T
        dofs = list(range(6 * idx[a], 6 * idx[a] + 6)) + list(range(6 * idx[b], 6 * idx[b] + 6))
        for r_ in range(12):
            for c_ in range(12):
                if kg[r_, c_]:
                    rows.append(dofs[r_]); cols.append(dofs[c_]); vals.append(kg[r_, c_])
    return sp.csr_matrix((vals, (rows, cols)), shape=(ndof, ndof))


def _endf(els, idx, u, Ns):
    out = []
    for e, (k, a, b, l, T, ke, fl) in enumerate(els):
        dofs = list(range(6 * idx[a], 6 * idx[a] + 6)) + list(range(6 * idx[b], 6 * idx[b] + 6))
        mat = ke + (Ns[e] * gmat(l) if Ns is not None else 0)
        out.append(mat @ (T @ u[dofs]) - fl)
    return out


def solve(text, moduli=None, ns=16):
    els, idx, ndof, free, f, R, m = build(text, moduli, ns)
    K = _assemble(els, idx, ndof)[free][:, free].tocsc()
    u1 = np.zeros(ndof); u1[free] = sla.spsolve(K, f[free])
    N1 = [(-fe[0] + fe[6]) / 2 for fe in _endf(els, idx, u1, None)]
    K2 = _assemble(els, idx, ndof, N1)[free][:, free].tocsc()
    u = np.zeros(ndof); u[free] = sla.spsolve(K2, f[free])
    fe2 = _endf(els, idx, u, N1)
    cy, cz = R["tky"] / 2 / R["Iz"], R["tkz"] / 2 / R["Iy"]
    sig = np.zeros(m)
    for e, (k, *_r) in enumerate(els):
        fe = fe2[e]
        for (N, Mz, My) in ((-fe[0], fe[5], fe[4]), (fe[6], fe[11], fe[10])):
            sig[k] = max(sig[k], abs(N) / R["A"] + abs(Mz) * cy + abs(My) * cz)
    disp = {n: u[6 * q:6 * q + 6].copy() for n, q in idx.items()}
    return sig, disp


def buckling(text, moduli=None, ns=16):
    import scipy.linalg as la
    els, idx, ndof, free, f, R, m = build(text, moduli, ns)
    K = _assemble(els, idx, ndof)[free][:, free].tocsc()
    u1 = np.zeros(ndof); u1[free] = sla.spsolve(K, f[free])
    N1 = [(-fe[0] + fe[6]) / 2 for fe in _endf(els, idx, u1, None)]
    Kg = _assemble(els, idx, ndof, N1, geo_only=True)[free][:, free]
    th = la.eigh(-Kg.toarray(), K.toarray(), eigvals_only=True)
    th = th[th > 1e-14]
    return float(1 / th.max()) if len(th) else None
