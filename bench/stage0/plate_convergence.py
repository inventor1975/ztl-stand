"""Discretization error, MEASURED (2026-11-01, night plan item 4): a clamped 4 m x 1 m plate (10 mm, E 200 GPa,
nu 0.3) under a uniform tip shear traction, meshed with CST triangles nx = 4k by ny = k. The proved bounds of the
stand are bounds for THE MESH; this measures how far the mesh is from the continuum, so the two numbers are not
confused. Reference: Timoshenko beam (bending + shear, kappa = 5/6) and Richardson extrapolation of the sequence
(CST: error ~ h^2 in energy, the tip deflection converging from below - the mesh is too stiff)."""
import json, pathlib, subprocess, sys, time
from fractions import Fraction as F
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from ustand import plate as PL
E, nu, th, p, Lx, H = 200e9, 0.3, 0.01, 1e6, 4.0, 1.0
P = p * th * H
I = th * H ** 3 / 12
G = E / (2 * (1 + nu))
beam = P * Lx ** 3 / (3 * E * I) + P * Lx / (5 / 6 * G * th * H)
print(f"Timoshenko beam tip deflection: {beam:.6e} m (bending {P*Lx**3/(3*E*I):.6e} + shear {P*Lx/(5/6*G*th*H):.6e})")
rows = []
for k in [int(a) for a in sys.argv[1:]]:
    nx, ny = 4 * k, k
    text = subprocess.run([sys.executable, str(ROOT / "examples/plate/gen_plate.py"), str(nx), str(ny), "--load", "shear",
                           "--h", str(F(1, k)), "--th", "1/100", "--p", "1e6"], capture_output=True, text=True,
                          check=True).stdout
    tip = (nx + 1) * (ny + 1)
    t0 = time.time()
    r = PL.range_of(text, "0", f"U({tip},Y)")
    v = -float(F(r["nominal"].split()[0]))
    rows.append((k, r["unknowns"], v, time.time() - t0))
    print(f"k={k:3d} mesh {nx}x{ny} ({r['unknowns']} unknowns): tip {v:.6e} m = {v/beam*100:.2f} % of the beam value, "
          f"{time.time()-t0:.1f} s", flush=True)
for (k1, _, v1, _), (k2, _, v2, _) in zip(rows, rows[1:]):
    rich = v2 + (v2 - v1) / 3                         # h^2: halving h removes 3/4 of the error
    print(f"Richardson {k1}->{k2}: {rich:.6e} m; the finer mesh's own error vs it: {(rich - v2)/rich*100:.2f} %")
json.dump(rows, open(ROOT / "bench/stage0/plate_convergence.json", "w"))
