# The stand's 3D phase — design (2026-11-02)

The curator: "делать глобально" — 3D is a phase of the stand, not a script for one use. Three tracks, in order.
Every track keeps the stand's contract: proved bounds (not estimates), named premises, ZTL verdicts with provenance,
regression tests against exact answers and independent formulas, measured cost.

## Track 1 — 3D conduction (`ustand/conduction3d.py`, IN)

Ionic / electrical / thermal conductance of a voxel volume, two-sided and proved (P1 potential above, an exactly
conservative Raviart–Thomas face flux below). Use: composite cathodes from tomography, porous electrodes, thermal
paths. MEASURED: 64^3 voxels (1.6 M tetrahedra) in 141 s, 2 GB; 85 % is the hybridized flux solve (Jacobi CG) —
the cure is algebraic multigrid (pyamg, pending the curator's OK to install). Open: adaptive refinement at voxel
edge/corner contacts (they make the bracket close slowly — MEASURED 2026-11-03: the gap is mostly the LOWER side, a BDM1 flux (linear per tet,
conservation still one integer per tet) took the median gap 1.244 -> 1.118; P2 above gained 0.2-6 %; where the other voxels INSULATE, the potential is split since
2026-11-03 — a line or point contact carries no current — MEASURED ratio 4.0 -> 2.0 on a 50 % random 8^3 map), anisotropic phases (tensor conductivity), sub-volume
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

The LOWER bound (the original plan below) is the open half. **Spike (B), 2026-11-03, FLOAT ONLY (not a proof):**
symmetric stresses linear on each Kuhn tetrahedron (24 numbers per tet), divergence-free per tet, normal traction
continuous at the three vertices of every inner face, zero in pores, traction-free on free faces, smooth grips;
||tau||^2_{C^-1} minimised with resultant 1 (a quasi-definite KKT, scipy spsolve). MEASURED lower / upper (E 200,
nu 0.3): homogeneous 3^3 200 / 200; one central pore 3^3 181.72 / 191.32 (gap 5.3 %), refined x2 184.15 / 189.20
(2.7 %); random 80 % solid 4^3 126.27 / 161.07 (27.6 %), x2 133.85 / 152.83 (14.2 %) — the space is rich, the gap
halves per refinement: GO on the approximation. NOT solved: EXACTNESS (the constraints hold to 1e-15 in floats; a
proof needs them exact — conduction3d pushed one residual per tet along a spanning forest; here a tet's 24 numbers
meet 39 conditions given its face tractions, so a push needs elements whose inside realises ANY equilibrated face
traction: Krizek's composite tetrahedron / a Johnson-Mercier-type split — the next design step) and COST (62208
unknowns took 93 s with a direct solve).

**The exact construction (2026-11-03, the curator's "берёмся").** MEASURED by exact rank (sympy): on one Kuhn
tetrahedron, symmetric divergence-free polynomial stresses whose face tractions are linear realise only 21 of the 30
dimensions of balanced linear face tractions — at degree 1, 2 AND 3: no single-polynomial element works. The ALFELD
split (the barycentre, 4 sub-tetrahedra, linear symmetric divergence-free stress on each, normal traction continuous
across the 6 inner faces) has a space of dimension exactly 30 and its outer trace map has rank 30: a BIJECTION onto
the balanced linear face tractions. So the lower bound is built from FACE data, as conduction3d's flux:
  1. unknowns g_f = tau n2 at the 3 vertices of every face (n2 the integer area normal, 9 numbers per face, shared by
     the face's two tets with opposite sign); free faces 0, grips: tangential 0; per tet the 6 balance equations
     (force (1/6) sum g, moment (1/24) sum (1 + delta_ij) x_i x g_j); a float KKT minimises sum_T g_T^T S g_T with
     resultant 1 (S: the element's compliance form through the bijection — exact rationals per Kuhn type);
  2. g rounded to a dyadic grid; balance restored EXACTLY by pushing each tet's 6-residual through a face of its
     spanning tree (the face's 9 values carry any force and moment: an exact 9 x 6 right inverse), the roots' residual
     absorbed by a grip face's normal traction (3 values: F_x, M_y, M_z; F_y, F_z, M_x of a component's total are
     exactly 0 because shared faces cancel and grip tractions are normal); islands without a grip total 0;
  3. inside each tet the stress is R g_T (the bijection, exact): divergence-free, symmetric, traction-continuous;
  4. E_app >= n_x F^2 / (n_y n_z ||tau||^2), the energy at the box's softest corner per tet, summed in floats with a
     rigorous bound (Higham, plus the conversion of g to binary64). Premise: Green's formula, as the hypercircle.

**Edge/corner-only contacts (2026-11-03, after conduction3d):** the upper bound's displacement is split where solid
voxels meet only along an edge or at a corner (MEASURED: a 60 % random 6^3 map 83.68 -> 51.12, the lower 25.15; 100
random maps never below a proved lower bound, median ratio 1.69 -> 1.54). **Box order (the cloud's round 2):** a box
written high-to-low is refused (it gave a false EARNED).

**Version 2 IN (2026-11-03): TWO-SIDED.** `ustand/kuhn_split.py` (the element, sympy, cached exact JSON; rank 30 and
the balance asserted per type) and `elastic3d.lower` (the four steps above; the 24 face blocks are UNIMODULAR —
Smith normal form all ones, MEASURED — so the push stays in integers, no denominator growth). MEASURED: homogeneous,
Voigt, Reuss: lower = upper within 4e-12; one central pore [183.59, 191.32] (the P1-per-tet spike gave 181.72);
random 80 % solid 4^3 [132.08, 161.07]; 100 random two-phase porous samples with moduli boxes: lower <= the soft
corner's refined upper in every case, the sabotage (stiff end in the compliance) caught in 68; cost with a direct
KKT 6^3 1.4 s, 8^3 9.3 s, 10^3 34 s. **The hybridized choice (same day):** per tet the 42 x 42 local KKT (batched),
an SPD system on displacement-like face traces (the same for both tets — a sign there once made it a SUM, caught by
the balance residual), smoothed-aggregation AMG with the six rigid motions as near-null space (without them CG hit
500 iterations); MEASURED random 80 % solid: 10^3 4.6 s, 16^3 17 s, 24^3 45 s (7 GB), 32^3 106 s (15.6 GB, the
lower 106.21, the upper 151.26); the same bound as the KKT
(1e-10); the solver tolerance 1e-9 (1e-6 moves the bound by 7e-5, 1e-4 collapses it 3x: the exact push pays for a
mismatch at every face). The gap is widest where voxels touch by an EDGE only: the
P1 displacement bridges the edge (too stiff on a coarse mesh), the face-based stress cannot pass it (it is the
truth's side: an edge contact carries no force in the continuum).

The hypercircle in 3D: a P1/P2 displacement field (lower bound of compliance), an EXACTLY equilibrated stress field
(upper) — in 2D it came from the Airy function (HCT); in 3D there is no scalar Airy function, so the equilibrated
field must be built as for track 1's flux: element-wise equilibrium made exact (a stress analogue of the face
fluxes: face tractions balanced per element, integers for exactness). The hardest track; it waits for 1 and 2.
