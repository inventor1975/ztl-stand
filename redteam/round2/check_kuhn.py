"""Round 2: an INDEPENDENT re-derivation of the Alfeld-split element (numpy SVD and a degree-2 exact quadrature —
not ustand.kuhn_split's sympy nullspace path) on all six Kuhn types, against ustand/data/kuhn_split.json:
  (1) the element space (linear symmetric div-free stress per sub-tet, normal traction continuous across the 6 inner
      faces) has dimension 30 and its outer trace map is injective (rank 30);
  (2) every trace of the space is balanced: my own force (int t dA) and moment (int x x t dA, exact for a linear t on a
      triangle) vanish, and the JSON's BAL annihilates it;
  (3) for traces of random element stresses: g^T S1 g = int tau:tau and g^T S2 g = int (tr tau)^2 (my quadrature).
--mutant: S1 multiplied by 0.999 (a too-soft compliance) — check (3) must see it.
    python3 redteam/round2/check_kuhn.py [--mutant]"""
import itertools, json, os, sys
from fractions import Fraction as F
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = json.load(open(os.path.join(ROOT, "ustand", "data", "kuhn_split.json")))
PERMS = list(itertools.permutations(range(3)))            # conduction3d.PERMS order (asserted below)
VO = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]
MUT = "--mutant" in sys.argv
# degree-2 exact rule on the reference tetrahedron (4 points)
A_, B_ = 0.5854101966249685, 0.1381966011250105
QP = np.array([[B_, B_, B_], [A_, B_, B_], [B_, A_, B_], [B_, B_, A_]])


def stress_at(c, si, x):
    """the symmetric 3x3 stress of sub-tet si at point x from the 96 coefficients (6 comps x [1, x, y, z])"""
    T = np.zeros((3, 3))
    for p, (i, j) in enumerate(VO):
        k = (si * 6 + p) * 4
        v = c[k] + c[k + 1] * x[0] + c[k + 2] * x[1] + c[k + 3] * x[2]
        T[i, j] = T[j, i] = v
    return T


def lin_rows(si, x, i, j):
    """row over the 96 coefficients giving T[i,j](x) in sub-tet si"""
    r = np.zeros(96)
    p = VO.index((min(i, j), max(i, j)))
    k = (si * 6 + p) * 4
    r[k:k + 4] = [1, x[0], x[1], x[2]]
    return r


def one(perm, data):
    e = np.eye(3)
    a, b, c_ = perm
    P = [np.zeros(3), e[a], e[a] + e[b], e[a] + e[b] + e[c_]]
    bc = sum(P) / 4
    cons = []
    for si in range(4):                                    # divergence: d T_ij / d x_j summed, a constant
        for i in range(3):
            r = np.zeros(96)
            for j in range(3):
                p = VO.index((min(i, j), max(i, j)))
                r[(si * 6 + p) * 4 + 1 + j] += 1
            cons.append(r)
    for f, g in itertools.combinations(range(4), 2):       # inner face between sub-tets f and g: bc, P[v1], P[v2]
        v1, v2 = [v for v in range(4) if v not in (f, g)]
        n = np.cross(P[v1] - bc, P[v2] - bc)
        for pt in (bc, P[v1], P[v2]):
            for i in range(3):
                r = sum(n[j] * (lin_rows(f, pt, i, j) - lin_rows(g, pt, i, j)) for j in range(3))
                cons.append(r)
    C = np.array(cons)
    U, s, Vt = np.linalg.svd(C)
    rank = int((s > 1e-10 * s[0]).sum())
    N = Vt[rank:].T                                        # 96 x dim
    dim = N.shape[1]
    # outer faces as the JSON lists them (verts, n2): check the normal is outward and twice the area
    trace = []
    for f in range(4):
        fc = data["faces"][f]
        vs = fc["verts"]; n2 = np.array(fc["n2"], float)
        assert vs == [v for v in range(4) if v != f]
        A0, B0, C0 = (P[v] for v in vs)
        nn = np.cross(B0 - A0, C0 - A0)
        assert np.allclose(np.abs(nn), np.abs(n2)) and np.dot(n2, P[f] - A0) < 0, "n2 not the outward area normal"
        for v in vs:
            for i in range(3):
                trace.append(sum(n2[j] * lin_rows(f, P[v], i, j) for j in range(3)))
    Tm = np.array(trace)                                   # 36 x 96
    TN = Tm @ N
    rk = np.linalg.matrix_rank(TN, tol=1e-9)
    BAL = np.array([[float(F(x)) for x in row] for row in data["BAL"]])
    S1 = np.array([[float(F(x)) for x in row] for row in data["S1"]]) * (0.999 if MUT else 1)
    S2 = np.array([[float(F(x)) for x in row] for row in data["S2"]])
    rng = np.random.default_rng(sum(perm) * 7 + perm[0])
    worst = {"bal_own": 0.0, "bal_json": 0.0, "S1": 0.0, "S2": 0.0}
    for _ in range(25):
        cf = N @ rng.standard_normal(dim)
        g = Tm @ cf
        # my own balance: force int t dA = (1/6) sum_v g_v ; moment int x x t dA with t linear on the triangle
        Fo, Mo = np.zeros(3), np.zeros(3)
        for f in range(4):
            vs = data["faces"][f]["verts"]
            gv = [g[9 * f + 3 * k:9 * f + 3 * k + 3] for k in range(3)]
            Fo += sum(gv) / 6
            for i, wv in enumerate(vs):
                for j in range(3):
                    Mo += (1 + (i == j)) / 24 * np.cross(P[wv], gv[j])
        scale = np.abs(g).max()
        worst["bal_own"] = max(worst["bal_own"], np.abs(np.r_[Fo, Mo]).max() / scale)
        worst["bal_json"] = max(worst["bal_json"], np.abs(BAL @ g).max() / scale)
        tt = tr2 = 0.0
        for si in range(4):
            vs = [bc] + [P[v] for v in range(4) if v != si]
            J = np.column_stack([vs[1] - vs[0], vs[2] - vs[0], vs[3] - vs[0]])
            vol = abs(np.linalg.det(J)) / 6
            for q in QP:
                T = stress_at(cf, si, vs[0] + J @ q)
                tt += vol / 4 * np.sum(T * T)
                tr2 += vol / 4 * np.trace(T) ** 2
        worst["S1"] = max(worst["S1"], abs(g @ S1 @ g - tt) / tt)
        worst["S2"] = max(worst["S2"], abs(g @ S2 @ g - tr2) / max(tr2, 1e-300))
    return {"perm": perm, "space_dim": dim, "trace_rank": int(rk), **worst}


out = []
for perm, data in zip(PERMS, DATA):
    assert tuple(data["perm"]) == perm, "JSON type order differs from PERMS"
    out.append(one(perm, data))
ok = all(r["space_dim"] == 30 and r["trace_rank"] == 30 and r["bal_own"] < 1e-10 and r["bal_json"] < 1e-10
         and r["S1"] < 1e-9 and r["S2"] < 1e-9 for r in out)
print(json.dumps({"mutant": MUT, "all_ok": ok, "types": out}, default=float))
