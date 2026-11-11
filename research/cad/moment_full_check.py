# Exact check: for a symmetric, divergence-free tau on a tet T,  int_T (tau_ij x_k + tau_ik x_j) = int_dT t_i x_j x_k,
# t = tau n.  Case i=j=k (the bending moment of sigma_nn about x_n):  2 int_T tau_nn x_n = int_dT t_n x_n^2.
# tau from an Airy-type stress function per component pair -> polynomial, symmetric, div-free.
import sympy as sp, itertools, random
x, y, z = X = sp.symbols("x y z")
random.seed(1)
def r(): return sp.Rational(random.randint(-9, 9), random.randint(1, 5))
# div-free symmetric field: tau = curl curl (Phi) with Phi a symmetric polynomial tensor (Beltrami): use simple
# construction tau_ij = eps_ikm eps_jln d_k d_l Phi_mn
Phi = [[0]*3 for _ in range(3)]
for a in range(3):
    for b in range(a, 3):
        p = sum(r()*x**i*y**j*z**k for i in range(4) for j in range(4) for k in range(4) if i+j+k <= 3)
        Phi[a][b] = Phi[b][a] = p
eps = sp.LeviCivita
tau = [[sp.expand(sum(eps(i,k,m)*eps(j,l,n)*sp.diff(Phi[m][n], X[k], X[l])
        for k in range(3) for l in range(3) for m in range(3) for n in range(3))) for j in range(3)] for i in range(3)]
assert all(sp.simplify(sum(sp.diff(tau[i][j], X[j]) for j in range(3))) == 0 for i in range(3)), "not div-free"
assert all(sp.simplify(tau[i][j]-tau[j][i]) == 0 for i in range(3) for j in range(3))
P = [sp.Matrix([r(), r(), r()]) for _ in range(4)]
u, v, w = sp.symbols("u v w")
def vol_int(f):
    J = sp.Matrix.hstack(P[1]-P[0], P[2]-P[0], P[3]-P[0]); pt = P[0] + J*sp.Matrix([u, v, w])
    g = f.subs({x: pt[0], y: pt[1], z: pt[2]}, simultaneous=True) * abs(J.det())
    return sp.integrate(sp.integrate(sp.integrate(g, (w, 0, 1-u-v)), (v, 0, 1-u)), (u, 0, 1))
def surf_int(fvec_of_n):
    tot = 0
    for f in range(4):
        A, B, C = [P[i] for i in range(4) if i != f]; D = P[f]
        nvec = (B-A).cross(C-A)                       # |nvec| = 2 area
        if nvec.dot(A-D) < 0: nvec = -nvec            # outward
        pt = A + (B-A)*u + (C-A)*v
        g = fvec_of_n(nvec).subs({x: pt[0], y: pt[1], z: pt[2]}, simultaneous=True)
        tot += sp.integrate(sp.integrate(g, (v, 0, 1-u)), (u, 0, 1))
    return tot
ok = True
for i, j, k in itertools.product(range(3), repeat=3):
    lhs = vol_int(tau[i][j]*X[k] + tau[i][k]*X[j])
    rhs = surf_int(lambda N: sum(tau[i][m]*N[m] for m in range(3)) * X[j] * X[k])
    if sp.simplify(lhs - rhs) != 0:
        ok = False; print("FAIL", i, j, k, lhs, rhs)
print("identity exact on all 27 (i,j,k):", ok)
# and the antisymmetric-in-(j,k) part is NOT boundary-determined: show int tau_ij x_k alone differs from half the rhs
i, j, k = 0, 0, 1
print("e.g. int tau_00 x_1 =", sp.nsimplify(vol_int(tau[i][j]*X[k])), " vs half rhs =",
      sp.nsimplify(surf_int(lambda N: sum(tau[i][m]*N[m] for m in range(3))*X[j]*X[k]) / 2))
# FULL first moments: A_ijk = int_T tau_ij x_k (sym in i,j) from M_ijk = int_dT t_i x_j x_k:  A_ijk = (M_ijk + M_jik - M_kij)/2
Mb = {}
for i, j, k in itertools.product(range(3), repeat=3):
    Mb[i, j, k] = surf_int(lambda N, i=i: sum(tau[i][m]*N[m] for m in range(3)) * X[j] * X[k])
allok = True
for i, j, k in itertools.product(range(3), repeat=3):
    A = vol_int(tau[i][j]*X[k])
    rec = (Mb[i, j, k] + Mb[j, i, k] - Mb[k, i, j]) / 2
    if sp.simplify(A - rec) != 0:
        allok = False; print("FAIL", i, j, k)
print("EVERY first moment int tau_ij x_k is boundary-determined (27/27):", allok)
