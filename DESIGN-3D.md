# The stand's 3D phase — design (2026-11-02)

The curator: "делать глобально" — 3D is a phase of the stand, not a script for one use. Three tracks, in order.
Every track keeps the stand's contract: proved bounds (not estimates), named premises, ZTL verdicts with provenance,
regression tests against exact answers and independent formulas, measured cost.

## Track 1 — 3D conduction (`ustand/conduction3d.py`, IN)

Ionic / electrical / thermal conductance of a voxel volume, two-sided and proved (P1 potential above, an exactly
conservative Raviart–Thomas face flux below). Use: composite cathodes from tomography, porous electrodes, thermal
paths. MEASURED: 64^3 voxels (1.6 M tetrahedra) in 141 s, 2 GB; 85 % is the hybridized flux solve (Jacobi CG) —
the cure is algebraic multigrid (pyamg, pending the curator's OK to install). Open: adaptive refinement at voxel
edge/corner contacts (they make the bracket close slowly), anisotropic phases (tensor conductivity), sub-volume
sweeps over a large tomogram.

## Track 2 — space frames (`ustand/frame3d.py`, IN — status at the end of the section)

The road to industrial buildings (3D models, 10^4–10^5 unknowns, tens to hundreds of load combinations).
1. **Element.** 3D Euler–Bernoulli beam, 12 DOF (UX UY UZ ROTX ROTY ROTZ per node), ANSYS BEAM4-style deck
   (`R: AREA, IZZ, IYY, TKZ, TKY, THETA, ..., IXX`; `MP: EX, PRXY`, G = E/(2(1+nu))), local axes from THETA or an
   orientation node. Stiffness as a PSD sum of rank-one terms, ZTL zenergy's form: axial EA/L a a^T, torsion GJ/L
   t t^T, and per bending plane the 2D frame's pair (EI/L b b^T, 3 EI/L c c^T) — 6 terms per element, E and G each
   with its tolerance.
2. **First order:** displacements, member forces, fibre stresses (biaxial bending + axial; torsion shear stated
   separately), each a proved range — the 2D frame's code generalised, the same ZTL kernel.
3. **Many load combinations in one run.** Today every load case is its own proof. The factorization and the proved
   lambda_min of K0 do not depend on the load: prepare ONCE, then per combination only u~, its residual and the
   outputs (a refactor of zenergy._fp_prepare into a K-part and an f-part; it speeds up 2D frames too).
4. **Second order and stability:** the 2D machinery per bending plane — geometric stiffness G_y, G_z, the
   continuum correction per plane (k_y, k_z), the bisection with float-built matrices (ZTL pd_ieee_float). PREMISE
   stated: doubly symmetric sections, no torsional-flexural / lateral-torsional buckling (Wagner terms not in) —
   a verdict that depends on them says OPEN.
5. **EN 1993-1-1:** 6.3.1 about both axes; 6.3.3 biaxial interaction (k_yy, k_yz, k_zy, k_zz, Annex B) — after 4.
Tests: cantilever under biaxial tip load and torque (exact), a portal space frame against an independent float
solve, a 2D frame embedded in 3D giving the 2D frame's ranges, Euler columns about the weak and strong axes.

**Status 2026-11-02.** IN: items 1-5, plus materials/sections by id, end releases, transverse member loads (QLOAD;
first and second order), load cases and combinations, EN 5.3.2 sway imperfections. The night battery's sweep G
checks random space frames against an INDEPENDENT numpy FE (`bench/night/frame3d_ref.py`, Przemieniecki 12x12 +
consistent geometric matrix, 8 elements per member): first order at the nodes, second-order displacements, member
stresses and end moments from BOTH sides, the stability bracket. It found a crash (fractions past 4300 digits —
fixed by outward dyadic rounding) and showed the second-order brackets of loaded frames too wide to see a dropped
N (G u) (2/10 frames); the member-load correction made PER MEMBER (zenergy `c_groups`) and the exact signed
fixed-end moment cut the stress bracket from 1.6 to 0.4 sigma (median, MEASURED) and the sabotage is caught on
8/10. Axial member loads: stability IN (lower and upper, both sides against the independent FE; with the 2D
fix of the same day — the split's witness and the clip); second-order DISPLACEMENTS in (2D and 3D, D <= Nmax^2
k/(1-Pk) G); second-order STRESSES with them and combined axial + transverse member loads refused (named); torsional / flexural-torsional /
lateral-torsional buckling (a stated premise — Wagner terms not in); size: measured only up to tens of members.

## Track 3 — 3D elasticity

**Version 1 IN (2026-11-03, the curator's choice (A)): ONE-SIDED.** `ustand/elastic3d.py` — a proved UPPER bound on
the apparent Young's modulus of a voxel sample (smooth grips on x = 0 / x = nx, other faces free): P1 displacements on
Kuhn tetrahedra, minimum potential energy; the energy summed in binary64 with Higham's bound; the moduli's box at
(E_hi, nu_lo) for mu and (E_hi, nu_hi) for lambda. MEASURED: homogeneous, Voigt (laminate along x, equal nu), Reuss
(laminate across x, nu = 0) each from above within ~1e-12 (the rounding raise); a 70 % solid random 6^3 sample 119.3
-> 104.7 -> 98.3 under refinement x1, x2, x3 (the bound converges from above; voxel edge contacts are stiff on the
coarse mesh); 32^3 in 30 s. "E_app <= need" EARNED / OPEN; "E_app >= need" REFUTED / OPEN.

The LOWER bound (the original plan below) is the open half:

The hypercircle in 3D: a P1/P2 displacement field (lower bound of compliance), an EXACTLY equilibrated stress field
(upper) — in 2D it came from the Airy function (HCT); in 3D there is no scalar Airy function, so the equilibrated
field must be built as for track 1's flux: element-wise equilibrium made exact (a stress analogue of the face
fluxes: face tractions balanced per element, integers for exactness). The hardest track; it waits for 1 and 2.
