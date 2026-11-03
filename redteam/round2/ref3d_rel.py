"""Round 2: redteam/ref3d.py's independent space-frame reference WITH END RELEASES (numpy; no ustand code).

`RELEASE, elem, I|J, MY|MZ[, MY|MZ]`: at that member end, the member's rotation about its local y' (MY) or z' (MZ) is
its OWN unknown; the other rotation components and all translations follow the node. Each sub-element's 12 global
DOFs are a linear map of the unknowns (a sparse 12 x ndof Q): K += Q^T (T^T k T) Q. Everything else as ref3d:
Euler-Bernoulli, ns sub-elements per member, second order with the FIRST-ORDER axial forces, geometric stiffness in
both bending planes, no torsional geometric term.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
import scipy.sparse.linalg as sla

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import ref3d as R3  # noqa: E402  (round 1's element matrices and axes)


def parse(text):
    rel = {}
    keep = []
    for raw in text.splitlines():
        line = raw.split("!")[0].strip()
        f = [x.strip() for x in line.split(",")] if line else []
        if f and f[0].upper() == "RELEASE":
            k, end = int(f[1]), f[2].upper()
            for c in f[3:]:
                rel.setdefault(k, set()).add((end, c.upper()))
            continue
        keep.append(raw)
    return R3.parse("\n".join(keep)), rel


def build(text, moduli=None, ns=16):
    (nodes, elems, sups, loads, qloads, E, nu, R), rel = parse(text)
    G = E / (2 * (1 + nu))
    m = len(elems)
    moduli = [1.0] * m if moduli is None else moduli
    pos = dict(nodes)
    nxt = max(nodes) + 1
    q_of = {}
    for k, ax, q in qloads:
        q_of.setdefault(k, np.zeros(3))[ax] += q
    subs = []
    for k, (i, j) in enumerate(elems):
        L, Tm = R3.axes(nodes[i], nodes[j], R["theta"])
        ids = [i]
        for s in range(1, ns):
            pos[nxt] = nodes[i] + (nodes[j] - nodes[i]) * s / ns
            ids.append(nxt); nxt += 1
        ids.append(j)
        subs.append((k, ids, L, Tm))
    idx = {n: q for q, n in enumerate(sorted(pos))}
    ndof = 6 * len(idx)
    extra = {}                                    # (member k, end, axis 1|2) -> dof
    for k in rel:
        for end, comp in sorted(rel[k]):
            extra[(k - 1, end, 1 if comp == "MY" else 2)] = ndof
            ndof += 1
    fixed = {6 * idx[n] + d for n, d in sups}
    els = []
    for (k, ids, L, Tm) in subs:
        l = L / ns
        T = np.zeros((12, 12))
        for b in range(4):
            T[3 * b:3 * b + 3, 3 * b:3 * b + 3] = Tm
        ql = Tm @ q_of.get(k + 1, np.zeros(3))
        fl = np.zeros(12)
        fl[0] = fl[6] = ql[0] * l / 2
        fl[1] = fl[7] = ql[1] * l / 2
        fl[5], fl[11] = ql[1] * l * l / 12, -ql[1] * l * l / 12
        fl[2] = fl[8] = ql[2] * l / 2
        fl[4], fl[10] = -ql[2] * l * l / 12, ql[2] * l * l / 12
        ke = R3.kmat(E * moduli[k], G * moduli[k], R, l)
        for s_, (a, b) in enumerate(zip(ids[:-1], ids[1:])):
            Q = np.zeros((12, ndof))
            for slot, n in ((0, a), (1, b)):
                for c in range(3):
                    Q[6 * slot + c, 6 * idx[n] + c] = 1.0
                end = "I" if (slot == 0 and s_ == 0) else "J" if (slot == 1 and s_ == ns - 1) else None
                # rotations: theta_global = Tm^T theta_local; theta_local = Tm theta_node except released comps
                Mrot = np.zeros((3, ndof))                       # theta_local as a map of the unknowns
                for ax in range(3):
                    key = (k, end, ax)
                    if end is not None and key in extra:
                        Mrot[ax, extra[key]] = 1.0
                    else:
                        for c in range(3):
                            Mrot[ax, 6 * idx[n] + 3 + c] = Tm[ax, c]
                Q[6 * slot + 3:6 * slot + 6] = Tm.T @ Mrot
            els.append((k, sp.csr_matrix(Q), l, T, ke, fl))
    f = np.zeros(ndof)
    for n, d, v in loads:
        f[6 * idx[n] + d] += v
    for (k, Q, l, T, ke, fl) in els:
        f += Q.T @ (T.T @ fl)
    free = np.array([d for d in range(ndof) if d not in fixed])
    return els, idx, ndof, free, f, R, m


def _asm(els, ndof, Ns=None, geo_only=False):
    K = sp.csr_matrix((ndof, ndof))
    for e, (k, Q, l, T, ke, fl) in enumerate(els):
        mat = (Ns[e] * R3.gmat(l) if Ns is not None else 0) + (0 if geo_only else ke)
        K = K + Q.T @ sp.csr_matrix(T.T @ mat @ T) @ Q
    return K


def _endf(els, u, Ns):
    out = []
    for e, (k, Q, l, T, ke, fl) in enumerate(els):
        ul = T @ (Q @ u)
        mat = ke + (Ns[e] * R3.gmat(l) if Ns is not None else 0)
        out.append(mat @ ul - fl)
    return out


def solve(text, moduli=None, ns=16):
    els, idx, ndof, free, f, R, m = build(text, moduli, ns)
    K = _asm(els, ndof)[free][:, free].tocsc()
    u1 = np.zeros(ndof); u1[free] = sla.spsolve(K, f[free])
    N1 = [(-fe[0] + fe[6]) / 2 for fe in _endf(els, u1, None)]
    K2 = _asm(els, ndof, N1)[free][:, free].tocsc()
    u = np.zeros(ndof); u[free] = sla.spsolve(K2, f[free])
    fe2 = _endf(els, u, N1)
    cy, cz = R["tky"] / 2 / R["Iz"], R["tkz"] / 2 / R["Iy"]
    sig = np.zeros(m)
    for e, (k, *_r) in enumerate(els):
        fe = fe2[e]
        for (N, Mz, My) in ((-fe[0], fe[5], fe[4]), (fe[6], fe[11], fe[10])):
            sig[k] = max(sig[k], abs(N) / R["A"] + abs(Mz) * cy + abs(My) * cz)
    disp = {n: u[6 * q:6 * q + 6].copy() for n, q in idx.items()}
    return sig, disp


def buckling(text, moduli=None, ns=12):
    els, idx, ndof, free, f, R, m = build(text, moduli, ns)
    K = _asm(els, ndof)[free][:, free].tocsc()
    u1 = np.zeros(ndof); u1[free] = sla.spsolve(K, f[free])
    N1 = [(-fe[0] + fe[6]) / 2 for fe in _endf(els, u1, None)]
    Kg = _asm(els, ndof, N1, geo_only=True)[free][:, free]
    th = la.eigh(-Kg.toarray(), K.toarray(), eigvals_only=True)
    th = th[th > 1e-14]
    return float(1 / th.max()) if len(th) else None


def first_order_members(text, moduli=None, ns=16):
    """Per member (0-based): max |M_z'|, max |M_y'| along it and its largest compression (first order)."""
    els, idx, ndof, free, f, R, m = build(text, moduli, ns)
    K = _asm(els, ndof)[free][:, free].tocsc()
    u = np.zeros(ndof); u[free] = sla.spsolve(K, f[free])
    out = {k: [0.0, 0.0, 0.0] for k in range(m)}
    for e, fe in enumerate(_endf(els, u, None)):
        k = els[e][0]
        for (N, Mz, My) in ((-fe[0], fe[5], fe[4]), (fe[6], fe[11], fe[10])):
            o = out[k]
            o[0] = max(o[0], abs(Mz)); o[1] = max(o[1], abs(My)); o[2] = max(o[2], -N)
    return out
