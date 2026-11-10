# CAD/FEA level 2 — the bracket's stiffness, PROVED two-sided (plan, 2026-11-10 01:10; word before code)

## What SimJEB's FEA is (bracket 148, read from 148.fem — OptiStruct, HyperMesh 2020)
- 129260 nodes, 640197 CTETRA (4-node, linear); MAT1 Ti-6Al-4V: E = 113800 MPa, nu = 0.342, rho 4.43e-9 t/mm^3.
- Supports: 4 RBE2 (rigid spiders, all 6 dof) from the 4 bolt-hole surfaces to 4 nodes, each SPC 123456 = 0 —
  i.e. EXACTLY: displacement 0 on the four bolt-hole surfaces.
- Load: one RBE3 (weights 1.0, components 123) from the clevis-hole surface nodes to node 129265
  (-21.04, -75.06, 44.80); four subcases: vertical F = (0, 0, 35585.77) N; horizontal (-37809.9, 0, 0);
  diagonal (-28276.2, 0, 31403.9); torsion M = (0, 0, 564924.2) N mm.

## The choice (mine, the curator asleep): THEIR tetrahedral mesh, not voxels
The voxel sandwich of the evening plan needs a domain-monotonicity theorem AND the bolt-hole / clevis surfaces to lie
inside the inner voxel body — they do not (a hole's surface is cut by voxels). Their tet mesh fills the solid
(its exact volume = the surface mesh's to 3e-9, measured) and its boundary faces ARE the hole surfaces. So:

**2a. LOWER bound on the compliance (= on the work of the load, = on the load-point displacement along F).**
Minimum potential energy: for ANY v with v = 0 on the bolt holes, C >= 2 f(v) - a(v, v), C the true compliance of
the solid the mesh fills (linear isotropic elasticity). v = P1 on their tets, chosen by a float solve; a(v, v) and
f(v) evaluated with outward rounding (elastic3d's binary64 bound). Any v is admissible: the float only chooses.
The known fact behind it: a conforming P1 FE solution is too stiff — its compliance is BELOW the truth.
**2b. UPPER bound on the compliance** — complementary energy: for any statically admissible stress tau
(div tau = 0, traction = the load on the clevis, 0 on free faces), C <= ||tau||^2_{C^-1}. tau: an equilibrated
piecewise-linear field on the tets (elastic3d builds one on Kuhn tets via the Alfeld split — to be generalised to
arbitrary tets). This is the hard half: days, not a tick.

## Premises (said, each a ZTL ground)
- The surface/tet mesh IS the part (the CAD's faceting is not stated by the file) — EARNED IF STABLE on its sha256.
- The RBE3 load is modelled as the distributed nodal forces RBE3 defines (weighted average; its moment terms for
  the offset of node 129265 from the clevis centroid) — the FEA's own idealisation, taken as the load.
- E and nu: the deck's values (a datasheet's word: ON CREDIT); the bound is monotone in E — a range gives a range.
- The three self-intersecting surfaces (432, 473, 551) and the 15 multi-body meshes are excluded until resolved.

## Against what
SimJEB reports max displacement magnitudes over vertices, not the compliance; the comparison will be: our proved
compliance bracket -> the load-point displacement along F, against THEIR FE value at node 129265 (the h3d/csv
results hold it — to be downloaded for 148 only if needed).

## 2a DONE on bracket 148, vertical (2026-11-10 01:55; ustand/tetfea.py, tests/test_tetfea.py 7 checks)
387 795 dof, 640 197 tets; AMG with the six rigid motions + CG, 55 iterations (residual 6e-10), 30 s in all.
**Proved: compliance >= 59 892.152 N mm, i.e. the RBE3 reference node moves along F by at least 1.68304 mm.**
The float FE compliance is 59 892.15232; the exact re-evaluation (v rounded to integers over 2^40, every tet's energy
an exact rational rounded up) loses 4e-6 N mm. MEASURED first: without the rigid motions in the AMG, CG stopped at
501 iterations (residual 0.12) and the bound was still valid — 59 869.3 — only looser (any v is admissible).
SimJEB's own number for this case is the MAXIMUM vertex displacement, 2.226 mm in z (2.49 magnitude) — a
different quantity (a maximum over the part, not the work-conjugate displacement of the load), so no contradiction.

## 2a, all four load cases of bracket 148 (02:10; research/cad/results148/*.json; each ~24 s, 51-55 CG iterations)

| case | load | proved compliance >= | proved, work-conjugate | SimJEB max vertex disp (a different quantity) |
|---|---|---|---|---|
| vertical | Fz 35 585.77 N | 59 892.152 N mm | load point >= 1.68304 mm along F | 2.491 mm (z 2.226) |
| horizontal | Fx -37 809.9 N | 39 329.694 N mm | >= 1.04020 mm along F | 1.894 mm |
| diagonal | (-28 276.2, 0, 31 403.9) N | 19 486.824 N mm | >= 0.46114 mm along F | 0.869 mm |
| torsion | Mz 564 924.2 N mm | 3 225.452 N mm | reference rotation about z >= 0.0057095 rad (0.327 deg) | 0.284 mm |

E enters as 1/E for a fixed choice of v (the bound scales exactly): a datasheet range E in [E_lo, E_hi] gives
compliance >= (bound at the deck's E) x E_deck / E_hi — the judge's input when E is ON CREDIT.

## 2b — the UPPER bound: design (02:25, word before code)
elastic3d's lower bound on E_app builds an equilibrated stress on KUHN tets only: the Alfeld-split element
(kuhn_split.py: on a tet split at its barycentre, piecewise-linear symmetric divergence-free stresses; dimension 30;
the outer trace a bijection onto BALANCED linear face tractions) is generated with sympy for the 6 Kuhn shapes.
A CAD tet mesh has 640 197 different shapes. The way to any tet:

1. **The double Piola map.** For x = B x^ + b and a symmetric field s^ on the reference tet,
   tau(x) = (1 / det B) B s^(x^) B^T  is symmetric and  div tau = (1 / det B) B div^ s^  — divergence-free maps to
   divergence-free (a one-line check: d^_j s^_ij = det B (B^-1)_ia d_c tau_ab B_cj (B^-T)_bj = det B (B^-1 div tau)_i),
   and the normal traction maps face to face. So the 30-dimensional Alfeld element on ANY tet is the image of the
   reference one: built once, exactly (sympy), mapped per tet. To be CHECKED, not trusted: on random tets, exactly,
   (a) symmetric and divergence-free on each sub-tet, (b) traction continuous across the 6 inner faces, (c) the outer
   trace a bijection onto balanced linear tractions (rank 30).
2. **The compliance energy per tet** int tau : C^-1 tau = (1/E)((1 + nu) int tau:tau - nu int (tr tau)^2): tau is
   linear on each sub-tet, the integrand of degree 2 — integrated EXACTLY by the rational rule (vertices weight -1/20,
   edge midpoints 1/5, times the volume) on each of the 4 sub-tets. Exact rationals per tet, rounded up.
3. **Admissibility.** Face data: a linear traction per face (9 numbers); each tet balanced (6 equations); interior
   faces equal and opposite; free faces 0; the RBE3 faces carry the load traction t (the P1 field with consistent
   nodal loads = the RBE3 forces: a surface mass-matrix solve, exactly); the bolt-hole faces free (reactions).
   A float KKT (minimise the energy subject to these) CHOOSES the face data; an EXACT spanning-forest push from
   the free leaves to the bolt holes cancels every tet's residual imbalance (a face's 9 numbers reach all 6 balance
   components — the map to be asserted per face), as elastic3d does on Kuhn tets.
4. **Bound.** C <= ||tau||^2_{C^-1} (complementary energy) with the E range at its SOFT end — with 2a: a proved
   two-sided bracket on the compliance, i.e. on the load point's displacement.
Cost guess (said as a guess): the exact push over 640k tets in Python — tens of minutes; first on a box mesh.

## 2b step 1 — the double Piola map CHECKED (03:10; research/cad/alfeld_piola_check.py, log beside it)
On 20 random rational tetrahedra (both orientations), exactly over QQ: the Alfeld element built DIRECTLY on the tet
has dimension 30 and outer-trace rank 30; the 30 reference basis fields mapped by tau = (1/det B) B s^ B^T are
independent (rank 30) and lie in the direct space (union rank 30). So the map is ONTO the element on every tet
tested — measured, not argued; the literature scout found no source stating it for this element ([M] there), and one
(Aznaran et al.) uses a 1/det^2 normalisation for a different (normal-normal) setting. A proof for all tets is the
one-line divergence identity of the design section plus this rank check (an argument, not Lean).

## 2b step 3 — admissibility, PROTOTYPE on a box (03:45; research/cad/upper_box.py)
Box [0,10]^3, Kuhn tets, u = 0 at z = 0, uniform traction p = 3 on z = 10, E = 1000, nu = 0: the exact compliance
p^2 L^3 / E = 9 (P1 and the Alfeld space both contain the exact fields). Float KKT chooses the face fluxes; the EXACT
spanning-forest push (leaves first, least-norm on the parent face, roots at the support faces) leaves every tet
balanced exactly; the energy exactly (alfeld.energy):
| mesh | tets | KKT residual | unbalanced after push | largest denominator | UPPER bound | exact |
|---|---|---|---|---|---|---|
| 2^3 | 48 | 1.6e-13 | 0 | 102 bits | 9.000000000000002 | 9 |
| 3^3 | 162 | 5.0e-13 | 0 | 140 bits | 9.0 | 9 |
(A first run left 40 tets unbalanced: the face sign applied twice in the push — found by the exact recount, fixed.)
Denominators grow slowly along the tree (no blow-up seen at this depth — to be MEASURED at depth ~100).
Next: a case with lower < upper strictly (nu > 0), then the scale-up (vectorised element forms; the KKT at 10^7
unknowns needs elastic3d's hybridisation + AMG), then bracket 148.

## 2b step 3b — a STRICT bracket, nu = 0.3 (03:58; `python3 research/cad/upper_box.py bracket`)
The same box with nu = 0.3 (the clamped bottom now bites; no closed form). Lower: P1 FE compliance (float here; the
rigorous version is tetfea's). Upper: the exactly admissible Alfeld stress, exact energy.
| n | tets | lower | upper | gap |
|---|---|---|---|---|
| 2 | 48 | 8.345521 | 8.817970 | 5.66 % |
| 3 | 162 | 8.493235 | 8.782992 | 3.41 % |
| 4 | 384 | 8.565067 | 8.767626 | 2.37 % |
The lower rises and the upper falls with refinement, the bracket closes about linearly in h — what the two
principles predict; the truth lies in [8.5651, 8.7676]. Every push left 0 unbalanced tets.

## 2b step 4 — the CHEAP route measured, and rejected (04:12; `python3 research/cad/upper_box.py fe`)
Face fluxes from the P1 stress (the average of the two tets' sigma n), then the same exact push: valid bounds, but
| n | KKT upper | FE-average + push upper | truth in |
|---|---|---|---|
| 2 | 8.818 | 28.89 | [8.35, 8.82] |
| 3 | 8.783 | 21.26 | [8.49, 8.78] |
| 4 | 8.768 | 21.90 | [8.57, 8.77] |
2.5-3.3x the truth and NOT improving with refinement: the push carries every tet's imbalance down the tree, and the
FE average is far from balanced (O(1) residuals). So the fluxes must be CHOSEN balanced (the KKT) — the push only
for rounding-sized residuals. For 640k tets the KKT has ~1.2e7 unknowns: next, a scalable choice — the global KKT
with the per-tet blocks eliminated (hybridisation, as elastic3d) or a vertex-patch equilibration (local problems,
Braess-Schoberl type) whose sum is balanced up to rounding.

## 2b at full scale — the size, MEASURED by count, and the decision (04:25)
The hybridized global choice (elastic3d's): lambda = 9 per face, ~1.3e6 faces -> ~1.2e7 unknowns; the assembled SPD
matrix ~ tets x 12 off-diagonal 9x9 blocks + faces x 81 = 6.2e8 + 1.1e8 = ~7.3e8 nonzeros (~9 GB in CSR) before
AMG setup; elastic3d measured 32^3 Kuhn voxels (196 608 tets) at 15.6 GB. Bracket 148 has 640 197 tets: over the
18 GB cap. Two ways, both days of work, not a night tick: (i) DOMAIN DECOMPOSITION — subdomains, interface tractions
balanced per subdomain (a 6-dof rigid correction), an exact KKT per subdomain (elastic3d's lower_blocks is the seed);
(ii) VERTEX-PATCH EQUILIBRATION (Braess-Schoberl type; for symmetric elasticity stresses the patch problems need the
rigid-motion compatibility — research-grade). Recommendation for the morning: (i). Tonight: 2a on ALL brackets.

## 2b by DOMAIN DECOMPOSITION — design (12:16, word before code)
1. Partition the tets into subdomains of ~2-4e4 tets (a KKT of that size fits: elastic3d's 196k tets took 15.6 GB,
   so ~30k tets ~2.5 GB) — by recursive coordinate bisection of the tet centroids (no foreign partitioner).
2. Interface fluxes q_Gamma on every face between two subdomains: from the P1 stress (the average of the two tets'
   sigma n) — fixed, the same for both sides with opposite signs (so the global traction continuity holds exactly).
3. A COARSE balance: a subdomain that touches no support face must be balanced by its boundary data alone (6
   conditions); the averaged fluxes are not exactly. Correct q_Gamma by a rigid-motion-dual correction per interface
   (6 numbers: a linear traction field with a chosen resultant force and moment) found by the same forest push, now on
   the SUBDOMAIN graph (leaves first, roots at subdomains with a support) — exact rationals, ~10^2 nodes, cheap.
4. Per subdomain: the hybridized KKT (elastic3d's _hybrid_g on arbitrary tets via alfeld) with Neumann data on its
   interface faces, the load on loaded faces, reactions free on support faces -> fluxes balanced up to rounding.
5. The exact per-tet push for the rounding residuals (step 3 of the prototype), the exact energy, the bound.
What it costs in quality: the interface fluxes are not optimised — the bound is looser than the global KKT's. To be
MEASURED on the box against the global KKT (8 subdomains) before bracket 148.

## 2b by domain decomposition — PROTOTYPE MEASURED (12:47; research/cad/upper_dd.py)
Box 4^3 (384 tets), nu = 0.3, 8 octant subdomains, 12 interfaces. Interface fluxes from the P1 stress, the coarse
push on the subdomain graph left 0 floating subdomains unbalanced (exact), the per-subdomain KKTs and the exact
per-tet push left 0 tets unbalanced:
| | upper | bracket with P1 lower 8.5651 |
|---|---|---|
| global KKT | 8.7676 | 2.37 % |
| domain decomposition, 8 subdomains | 8.8557 | 3.39 % |
The decomposition costs 1.0 % of looseness here (the interface fluxes are not optimised) and keeps every piece small.
Next (days, not ticks): the same on a CAD tet mesh — vectorised element forms, sparse per-subdomain KKTs
(hybridised), supports and the RBE3 load as a traction (a surface mass-matrix solve), subdomains of ~3e4 tets.

## The STAND BRICK for a part's stiffness — design (15:03, word before code; direction 2 of the curator's plan)
A brick `cad_stiffness`: inputs — a solid tet deck (Nastran/OptiStruct: supports RBE2+SPC, load RBE3), its sha256,
a load case, E and nu with their grounds (a datasheet range: ON CREDIT; a tested value: EARNED), and a requirement on
the work-conjugate displacement d = C / |F| (or the rotation for a moment): d <= D_max and/or d >= D_min.
What the stand computes: the PROVED bracket d in [d_lo, d_hi] (2a lower, 2b upper) at the deck's E; E enters as 1/E
for a fixed choice of both fields, so a range E in [E_lo, E_hi] gives d in [d_lo E_deck / E_hi, d_hi E_deck / E_lo]
(nu enters non-monotonically: a nu range is a second axis — first version: nu as given, said).
The verdict, by ZTL's numeric judge on `d <= D_max` with d's range as an EARNED quantity of the mesh and E's ground:
  d_lo > D_max -> REFUTED (proved: the part is too soft — at every admissible E);
  d_hi <= D_max -> EARNED (proved stiff enough), or ON CREDIT when E is credit (polarity toward T, next_check: E);
  otherwise OPEN — the bracket straddles the requirement: what to do is named (a finer mesh narrows the bracket;
  the gap is the bracket's width, 8.4 % on bracket 631).
Every verdict carries "rests_on": the deck's sha256 (EARNED IF STABLE on that revision), the RBE3 load as a traction
(a stated premise), linear isotropic elasticity.

## THE FIRST PROVED TWO-SIDED BRACKET ON A REAL CAD PART (15:28) — SimJEB bracket 631, vertical load 35 585.77 N
82 414 tets (their 2 mm OptiStruct mesh), Ti-6Al-4V E 113 800 MPa, nu 0.342, supports and the RBE3 load as in
their deck (the load as the traction with RBE3's consistent nodal loads).
- LOWER (2a, tetfea): compliance >= 42 132.981 N mm.
- UPPER (2b, equil.choose: global hybrid, 1.4M trace unknowns, CG 217 iterations, 366 s; equil.finish: the exact
  push — 0 unbalanced tets, denominators <= 366 bits, 239 s; alfeld.energy_upper_ev: the rigorous binary64 energy,
  20 s): compliance <= 45 784.619 N mm. (The float choice's own energy was 45 665.09; the push for the CG's 9e-9
  residuals raised it by 0.26 %.)
- So the load point moves along F by d in [1.18398, 1.28660] mm — PROVED both ways; gap 8.7 %.
  SimJEB's max vertex displacement for this case, 2.080 mm, is a different quantity (a maximum over the part).
- The brick (cadstiff) on it, E a datasheet range 110-119 GPa ON CREDIT, d <= 1.4 mm: ON CREDIT toward T, next check
  "document E" — over the whole E range d <= 1.331 mm.
The exact-Fraction energy (a cross-check of the errfloat number) re-runs; its first run finished the sum but crashed
PRINTING it (an int over Python's 4300-digit str limit) — the print fixed.

## Bracket 631, all four load cases PROVED both ways (16:07; ustand.cadbracket; research/cad/results631_s*.json)
| case | compliance (N mm) | work-conjugate | gap |
|---|---|---|---|
| vertical | [42 132.98, 45 784.62] | d along F [1.18398, 1.28660] mm | 8.7 % |
| horizontal | [43 828.27, 46 723.56] | d along F [1.15917, 1.23575] mm | 6.6 % |
| diagonal | [13 600.75, 14 569.91] | d along F [0.32185, 0.34478] mm | 7.1 % |
| torsion | [17 746.65, 20 648.05] | rotation [0.031414, 0.036550] rad | 16.4 % |
**The errfloat energy CHECKED against the exact Fractions on the real part** (vertical): exact upper 45 784.61912531
(a 21.6-million-bit numerator, 37 min), errfloat 45 784.61912600 — above it, 1.5e-11 apart.
DD: a coordinate bisection of 631 into 8 subdomains has 114 face-connected pieces (single tets touching their
subdomain by an edge or a vertex only); the coarse balance is per piece now (tetmesh.connected_subdomains) — the first
DD run left 1 tet unbalanced, which is how this was found.

## DD on a REAL part, MEASURED: the P1 interface fluxes are the weak link (16:30)
Bracket 631 vertical, upper bounds (all PROVED — exact pushes, 0 unbalanced, errfloat energy):
| method | upper | vs the global 45 784.62 |
|---|---|---|
| global hybrid (one system, 1.4M unknowns, 7 GB) | 45 784.62 | — |
| DD, 8 bisection subdomains = 114 face-connected pieces | 116 153.60 | x 2.54 |
| DD, the same glued to 11 pieces (merge_small) | 116 473.45 | x 2.54 |
The two DD numbers agree: the small pieces do not matter; the FIXED interface fluxes (the P1 stress, averaged) do. On
the box (smooth uniform stress) they cost 1 %; on the bracket the cuts cross the loaded lug and the stress
concentrations, where a piecewise-constant P1 traction is far from an equilibrated one (one subdomain alone: 60 134).
Next (my decision, inside my construction): OVERLAP — solve each subdomain with a layer of its neighbours, the rough
fluxes on the layer's outer boundary, and take the interface fluxes from that solution (elastic3d's lower_overlap is
the same idea); then the exact coarse balance and the non-overlapping solves as now.

## DD with OVERLAP (4 face-layers), MEASURED — worse, not better (16:47; research/cad/dd631_overlap4.log)
Each subdomain grown by 4 face-steps (393-2220 tets in the layer), solved with the rough fluxes on its cut; interface
fluxes = the two grown solves' average. Per subdomain the NON-overlapping proved energies barely move — except
subdomain 0: 60 134 -> 112 360, while its own grown solve had only 15 487. So the interface data imposed on 0 is
incompatible with it, though each estimate came from a good solve. The likely cause: subdomain 0 is a ROOT of the
coarse forest; every floating child pushes its imbalance onto its interface with its parent, the least-norm change
concentrates on few faces, and the root's subdomain carries it. NOT verified (a diagnosis to measure next).
What it says: a fixed-interface DD — P1 fluxes or one overlap pass — does not reach the global bound on a real part.
The interface fluxes must be OPTIMISED (the global trace system solved iteratively by subdomains: a Schur complement /
FETI-type iteration — the subdomain solves stay small, the bound reaches the global one). Days, and the curator's
call whether to spend them now: the global hybrid already covers parts up to ~2e5 tets within the 18 GB cap.

## The DD diagnosis, MEASURED (16:56) — the root-accumulation hypothesis WEAKENED
Bracket 631, 11 pieces, P1 interface fluxes: the FLOATING subdomains' imbalance before the coarse correction is
0.4-1.2 kN (1-3 % of the 35.6 kN load); the corrections are 1 % of the flux at the median (the 68x maximum sits on
faces whose flux is ~0). So the coarse push is not what spoils the bound. The subdomains that carry the load path
(0 and 7: 48 and 45 kN resolved on their supports) are where the energy explodes: the Alfeld element must reproduce
the ROUGH (piecewise-constant, or averaged-from-two-solves) interface traction face by face, in the highest-stress
zone. Remedy unchanged: optimise the interface fluxes (the trace system iterated by subdomains).
