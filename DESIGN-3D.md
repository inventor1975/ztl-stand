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

## Track 2 — space frames (`ustand/frame3d.py`, NEXT)

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

## Track 3 — 3D elasticity (LATER)

The hypercircle in 3D: a P1/P2 displacement field (lower bound of compliance), an EXACTLY equilibrated stress field
(upper) — in 2D it came from the Airy function (HCT); in 3D there is no scalar Airy function, so the equilibrated
field must be built as for track 1's flux: element-wise equilibrium made exact (a stress analogue of the face
fluxes: face tractions balanced per element, integers for exactness). The hardest track; it waits for 1 and 2.
