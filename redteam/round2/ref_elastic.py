"""Round 2: an INDEPENDENT 3D elasticity reference on the stand's voxel problem (numpy/scipy only; no ustand code).

The sample: voxels [0,nx] x [0,ny] x [0,nz], each one phase (E, nu; E = 0 a pore); smooth grips u_x = 0 on x = 0 and
u_x = nx on x = nx (u_y, u_z free there), the four other faces free. E_app = a(u, u) / V.

Trilinear hexahedra (Q1), each voxel cut into r^3 cubes, 2x2x2 Gauss (exact for Q1's stiffness). The solve uses a tiny
diagonal shift (rigid motions left by the smooth grips, pores, loose islands), but the reported energy is v^T K v with
the UNSHIFTED K at the computed v, which satisfies the grips: a conforming displacement, so its energy is >= the true
a(u, u) for ANY r — a one-sided check of a proved LOWER bound (lower > Q1 value at any r is a false lower bound).
"""
from __future__ import annotations

import itertools

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla

G2 = np.array([-1.0, 1.0]) / np.sqrt(3.0)


def _unit_mats():
    """K_mu, K_la (24 x 24) of the unit cube [0,1]^3: a = int 2 mu eps:eps + la (tr eps)^2."""
    corners = np.array(list(itertools.product((0, 1), repeat=3)))     # node order (i, j, k) lexicographic
    Km, Kl = np.zeros((24, 24)), np.zeros((24, 24))
    for gx, gy, gz in itertools.product(G2, G2, G2):
        x = (np.array([gx, gy, gz]) + 1) / 2
        dN = np.zeros((8, 3))
        for n, c in enumerate(corners):
            f = [x[d] if c[d] else 1 - x[d] for d in range(3)]
            s = [1.0 if c[d] else -1.0 for d in range(3)]
            dN[n] = [s[0] * f[1] * f[2], f[0] * s[1] * f[2], f[0] * f[1] * s[2]]
        B = np.zeros((6, 24))                         # eps = (xx, yy, zz, 2xy, 2xz, 2yz)
        for n in range(8):
            B[0, 3 * n] = dN[n, 0]; B[1, 3 * n + 1] = dN[n, 1]; B[2, 3 * n + 2] = dN[n, 2]
            B[3, 3 * n] = dN[n, 1]; B[3, 3 * n + 1] = dN[n, 0]
            B[4, 3 * n] = dN[n, 2]; B[4, 3 * n + 2] = dN[n, 0]
            B[5, 3 * n + 1] = dN[n, 2]; B[5, 3 * n + 2] = dN[n, 1]
        Dm = np.diag([2, 2, 2, 1, 1, 1.0])            # 2 eps:eps in Voigt with engineering shears
        Dl = np.zeros((6, 6)); Dl[:3, :3] = 1.0
        w = 1 / 8                                     # Gauss weights on [0,1]^3
        Km += w * B.T @ Dm @ B
        Kl += w * B.T @ Dl @ B
    return corners, Km, Kl


CORNERS, KM1, KL1 = _unit_mats()


def solve(V, phases, r=1, return_field=False, tol=1e-12):
    """phases: {id: (E, nu)} floats (E = 0: a pore). Returns E_app (an upper bound of the truth for any r)."""
    V = np.asarray(V)
    nx, ny, nz = V.shape
    Vr = np.repeat(np.repeat(np.repeat(V, r, 0), r, 1), r, 2)
    Nx, Ny, Nz = Vr.shape
    h = 1.0 / r
    nid = lambda i, j, k: i + (Nx + 1) * (j + (Ny + 1) * k)
    nn = (Nx + 1) * (Ny + 1) * (Nz + 1)
    I, J, K = np.meshgrid(np.arange(Nx), np.arange(Ny), np.arange(Nz), indexing="ij")
    I, J, K = I.ravel(), J.ravel(), K.ravel()
    ph = Vr[I, J, K]
    mu = np.array([phases[int(p)][0] / (2 * (1 + phases[int(p)][1])) for p in ph])
    la = np.array([phases[int(p)][0] * phases[int(p)][1] / ((1 + phases[int(p)][1]) * (1 - 2 * phases[int(p)][1]))
                   for p in ph])
    solid = (mu > 0) | (la != 0)
    nodes = np.stack([nid(I + c[0], J + c[1], K + c[2]) for c in CORNERS], axis=1)       # (ne, 8)
    dofs = (3 * nodes[:, :, None] + np.arange(3)[None, None, :]).reshape(len(I), 24)
    vals = h * (mu[:, None, None] * KM1[None] + la[:, None, None] * KL1[None])
    sel = solid
    rr = np.repeat(dofs[sel], 24, axis=1).ravel()
    cc = np.tile(dofs[sel], (1, 24)).ravel()
    Kg = sp.csr_matrix((vals[sel].ravel(), (rr, cc)), shape=(3 * nn, 3 * nn))
    xs = (np.arange(nn) % (Nx + 1)) * h
    fixed = np.zeros(3 * nn, bool)
    ub = np.zeros(3 * nn)
    fixed[3 * np.where(np.isclose(xs, 0))[0]] = True
    gx1 = np.where(np.isclose(xs, nx))[0]
    fixed[3 * gx1] = True
    ub[3 * gx1] = float(nx)
    d = Kg.diagonal()
    active = d > 0
    free = np.where(active & ~fixed)[0]
    Kf = Kg[free][:, free]
    rhs = -(Kg[free][:, np.where(fixed)[0]] @ ub[fixed])
    eps = 1e-11 * float(d.max())
    A = (Kf + eps * sp.identity(len(free))).tocsc()
    if len(free) <= 60000:
        x = sla.spsolve(A, rhs)
    else:
        import pyamg
        ml = pyamg.smoothed_aggregation_solver(A.tocsr(), symmetry="symmetric")
        x = ml.solve(rhs, tol=tol, accel="cg", maxiter=2000)
    u = ub.copy()
    u[free] = x
    energy = float(u @ (Kg @ u))
    Eapp = energy / (nx * ny * nz)
    return (Eapp, u) if return_field else Eapp
