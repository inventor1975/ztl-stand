"""Track 3 (B) spike, FLOAT ONLY (not a proof): is the space of P1-per-tet symmetric stresses that are exactly
divergence-free, traction-continuous, zero in pores, traction-free on free faces and smooth-gripped rich enough to give
a lower bound on E_app close to the P1 upper bound? Lower: E_app >= F^2 nx / (ny nz ||tau||^2_{C^-1}), tau admissible
with resultant F on the grip. Minimise ||tau||^2 subject to the constraints and F = 1 (quasi-definite KKT)."""
import sys, time
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as sla
from fractions import Fraction as F
sys.path.insert(0, "/media/vitaly/SSD_1000GB/Projects/ztl-stand")
from ustand.conduction3d import Mesh, PERMS
from ustand import elastic3d as EL

VO = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]          # Voigt order of the 6 components


def grads():
    out = []
    for (a, b, c) in PERMS:
        D = np.zeros((3, 4))
        for k, ax in enumerate((a, b, c)):
            D[ax, k + 1] += 1.0; D[ax, k] -= 1.0
        out.append(D)                       # column j = grad lambda_j
    return out


def lower(V, E, nu, refine=1):
    V = np.asarray(V)
    if refine > 1:
        V = np.repeat(np.repeat(np.repeat(V, refine, 0), refine, 1), refine, 2)
    M = Mesh(V)
    nvox = len(M.vox)
    solid = (V[M.vox[:, 0], M.vox[:, 1], M.vox[:, 2]] > 0)[M.tvox]
    act = np.where(solid)[0]
    col = -np.ones(M.nt, int); col[act] = np.arange(len(act))
    nu_ = len(act) * 24                     # unknowns: tet, vertex i (4), component (6)
    idx = lambda t, i, c: col[t] * 24 + i * 6 + c
    Gs = grads()
    # objective: sum_T int tau : C^-1 tau, P1 mass (|T|/20)(1 + delta_ij), compliance in Voigt with tau:tau weights
    Cinv = np.zeros((6, 6))
    for p in range(6):
        w = 1.0 if p < 3 else 2.0
        Cinv[p, p] += (1 + nu) * w / E
    for p in range(3):
        for q in range(3):
            Cinv[p, q] -= nu / E
    Mm = (1 / 6) / 20 * (np.ones((4, 4)) + np.eye(4))
    Qe = np.kron(Mm, Cinv)                  # (24 x 24), order (vertex, component)
    rows, cols, vals = [], [], []
    for t in act:
        b = col[t] * 24
        r, c = np.meshgrid(np.arange(24) + b, np.arange(24) + b, indexing="ij")
        rows.append(r.ravel()); cols.append(c.ravel()); vals.append(Qe.ravel())
    Q = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nu_, nu_))
    cr, cc, cv, nc = [], [], [], [0]
    def add(entries):                        # one constraint row: list of (unknown, coefficient)
        for u_, v_ in entries:
            cr.append(nc[0]); cc.append(u_); cv.append(v_)
        nc[0] += 1
    def comp(a, b):
        return VO.index((min(a, b), max(a, b)))
    # divergence per tet: sum_i tau_i[a, :] . grad lambda_i = 0
    for t in act:
        D = Gs[t // nvox]
        for a in range(3):
            add([(idx(t, i, comp(a, b)), D[b, i]) for i in range(4) for b in range(3) if D[b, i]])
    # faces: tet face f = opposite vertex f; global key by sorted node ids
    faces = {}
    for t in range(M.nt):
        for f in range(4):
            key = tuple(sorted(np.delete(M.tv[t], f)))
            faces.setdefault(key, []).append((t, f))
    pts = lambda n: np.array([M.X[n], M.Y[n], M.Z[n]], float)
    Fres = []                                # resultant on x = nx: sum over faces (area/3) sum_vertices tau_xx
    for key, lst in faces.items():
        A_, B_, C_ = (pts(n) for n in key)
        nrm = np.cross(B_ - A_, C_ - A_); area = np.linalg.norm(nrm) / 2; n = nrm / (2 * area)
        sl = [(t, f) for t, f in lst if solid[t]]
        if not sl:
            continue
        def vloc(t, node):
            return int(np.where(M.tv[t] == node)[0][0])
        onx0 = all(M.X[k] == 0 for k in key); onx1 = all(M.X[k] == M.nx for k in key)
        if len(sl) == 2:
            (t1, _), (t2, _) = sl
            for node in key:
                i1, i2 = vloc(t1, node), vloc(t2, node)
                for a in range(3):
                    add([(idx(t1, i1, comp(a, b)), n[b]) for b in range(3) if n[b]]
                        + [(idx(t2, i2, comp(a, b)), -n[b]) for b in range(3) if n[b]])
        else:
            t1, _ = sl[0]
            for node in key:
                i1 = vloc(t1, node)
                comps = [1, 2] if (onx0 or onx1) else [0, 1, 2]       # grips: tangential traction 0 only
                for a in comps:
                    add([(idx(t1, i1, comp(a, b)), n[b]) for b in range(3) if n[b]])
            if onx1:
                for node in key:
                    Fres.append((idx(t1, vloc(t1, node), 0), area / 3))
    B = sp.csr_matrix((cv, (cr, cc)), shape=(nc[0], nu_))
    frow = sp.csr_matrix(([v for _, v in Fres], ([0] * len(Fres), [u for u, _ in Fres])), shape=(1, nu_))
    Bf = sp.vstack([B, frow]).tocsr()
    rhs_c = np.zeros(Bf.shape[0]); rhs_c[-1] = 1.0
    eps = 1e-12
    K = sp.bmat([[Q + eps * sp.identity(nu_), Bf.T], [Bf, -eps * sp.identity(Bf.shape[0])]]).tocsc()
    rhs = np.r_[np.zeros(nu_), rhs_c]
    t0 = time.time()
    sol = sla.spsolve(K, rhs)
    tau = sol[:nu_]
    en = float(tau @ (Q @ tau))
    res = np.abs(Bf @ tau - rhs_c).max()
    Fv = float((frow @ tau)[0])
    lowE = Fv ** 2 * M.nx / (M.ny * M.nz * en)
    return lowE, res, nu_, Bf.shape[0], time.time() - t0


if __name__ == "__main__":
    P = lambda E, nu: {"E": [F(E)], "nu": [F(nu)]}
    cases = [("homog 3^3", np.ones((3, 3, 3), int)),
             ("one pore 3^3", (lambda V: (V.__setitem__((1, 1, 1), 0), V)[1])(np.ones((3, 3, 3), int))),
             ("random 4^3 80%", (np.random.default_rng(3).random((4, 4, 4)) < 0.8).astype(int))]
    for name, V in cases:
        for r in (1, 2):
            lo, res, nu_, ncon, ts = lower(V, 200.0, 0.3, r)
            up = float(EL.upper(V, {0: P(0, 0), 1: P(200, "0.3")}, refine=r)[0])
            print(f"{name} refine {r}: lower {lo:.4f} upper {up:.4f} gap {up / lo - 1:.2%}  (resid {res:.1e}, "
                  f"{nu_} unknowns, {ncon} constraints, {ts:.1f} s)", flush=True)
