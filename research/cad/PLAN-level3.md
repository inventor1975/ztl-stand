# CAD/FEA level 3 — certified LOCAL quantities (2026-11-10, plan in words before code)

Logic1 (Claude Opus 5.5, Anthropic; AI system), curator Vitaly Reznik.

## What can be certified at all

The peak stress at a sharp re-entrant edge is infinite in linear elasticity (Williams 1952; NAFEMS: it grows without
limit under refinement). So "max von Mises" is not a number a bound can be put on. That is not a limitation of our
tool; the quantity does not exist. What exists and can be bounded are BOUNDED LINEAR FUNCTIONALS of the solution:
- the displacement averaged over a surface patch (a hole, a face);
- the stress averaged over a region of positive volume;
- the linearised membrane and bending stress on a section (ASME VIII-2 classification line; a line integral of the
  stress, which is why it converges where the peak does not).
See SOURCES-stress.md sections 1–4.

## 3a — displacement averages by POLARIZATION (no new mathematics, the existing bracket does all the work)

A traction g on a surface patch defines l(v) = ∫ g·v, for example the mean displacement of hole B along a direction.
With u the solution for the load f and w the solution for the load g, by symmetry l(u) = a(u, w) = f(w). Polarization:

    l(u) = [ C(f + s g) − C(f − s g) ] / (4 s)        for any s > 0, C(load) = the compliance of that load

Each compliance is already bracketed by `cadbracket` (lower: tetfea; upper: equil + the exact push + errfloat). So

    l(u) ∈ [ (C_lo(f+sg) − C_hi(f−sg)) / 4s ,  (C_hi(f+sg) − C_lo(f−sg)) / 4s ]

Two bracket runs per quantity, on loads that are both tractions, so the existing pipeline applies unchanged. s
balances the two brackets' widths: a free parameter. It does not touch validity, only tightness, and can be chosen
after a float pilot. This is the Paraschivoiu–Peraire–Patera (1997) construction in its simplest form.

What `cadbracket` needs: a load given as a traction on a named face set (the RBE3 load is already one), and the sum
of two loads. So: a `--load` that is not the deck's RBE3, and a combination f ± s g.

The first quantity to certify: on SimJEB 631 (where everything runs in ~20 min), the vertical displacement of the
RBE3 hole averaged over its surface, under the horizontal load, i.e. a CROSS term. It is not a compliance and has
no sign constraint. Check: it must agree with the float FE value, and its bracket must contain it.

## 3b — stress averages over a region (needs a new load type)

The mean of a stress component over a region ω is l(u) = ∫_ω ε(u):σ_e, with a constant "extractor" σ_e on ω. This is
a load of PRESTRESS type (an initial stress on ω), not a traction. Polarization works the same way, but `tetfea`
(lower) and `equil` (upper: the admissible stress must balance the prestress's divergence, which is concentrated on
∂ω as a jump) both need the prestress load. That is new code in both, about a day's work. Only after 3a is green.

## 3c — linearised membrane + bending on a section

Membrane = the section average of σ_nn; bending = its first moment. Both are 3b functionals with ω a thin slab around
the section (or exactly the section, as a surface prestress). This follows from 3b, no new principle.

## Honest limits, stated up front

- The bracket of a local quantity is wider than the compliance bracket: it scales with the adjoint's error, and
  shrinking ω (more local) widens it (Ladevèze–Pled–Chamoin: "poor local bounds" when the error lies away from the
  zone). That is the price of locality, and it will be measured, not hidden.
- A stress at a POINT is not a bounded functional: it gets no bound, and the stand will say so (E: no subject),
  rather than print a number.

## 3a — FIRST RESULT (2026-11-10 21:15, SimJEB 631, MEASURED)

f = the vertical load (0, 0, 35585.77); g = the horizontal load (−37809.9, 0, 0); s = 1 (the balanced choice is
√(C1/C2) = 0.98). Both loads act on the same RBE3 hole. Two brackets, float64 Z, matrix-free:
- C(f + g) ∈ [19709.651, 20940.259] (6.2 %);
- C(f − g) ∈ [152212.842, 163691.504] (7.5 %).

Polarization: a(u_f, u_g) ∈ [−35995.46, −32818.15], width 9.2 % of the midpoint. **The SIGN is PROVED:** under the
vertical load, the load point moves in +x by 0.868 to 0.952 mm (the work-conjugate displacement of the horizontal
load; files results631_cross_{plus,minus}.json). The float pilot's −33125.8 lies inside the bracket.
So a CROSS quantity, one that is not a compliance and has no sign of its own, is certified by the existing pipeline
with no new mathematics. The width (9 %) matches the a-priori estimate 0.08·√(C1·C2)/|X| ≈ 10 %.

## 3b — BUILT (2026-11-11, a fork of Logic1; tests/test_prestress.py, MEASURED)

**Simpler than planned: the upper side needs no new admissibility.** τ is admissible for the load f + l_p iff
τ = τ' + σ_e χ_ω with τ' admissible for f ALONE, which is what `equil.choose` + `equil.finish` already deliver,
unchanged. So C(f + l_p) ≤ ‖τ' + σ_e χ_ω‖², and per tet of ω the extra terms are EXACT from the exact fluxes:
2 (Aσ_e) : ∫_T τ' + |T| σ_e : Aσ_e, with ∫_T τ'_ij = ∫_∂T t_i x_j (div τ' = 0 in the Alfeld element) = b_T · g_T. The
plan's "the admissible stress must balance the prestress's jump on ∂ω" is absorbed by the shift: τ' has no jump.
What changed in code:
- `tetfea`: the load may carry `prestress = {omega, sigma}`; l_p(v) is taken EXACTLY (`prestress_work_exact`:
  |T| grad v = sign(det) dV adj(D) / (6 2^S 10^(2k)) in integers); its float nodal vector only chooses v.
- `equil.choose(lin=b)`: a linear term in each tet's energy, so the choice minimises ‖τ' + p‖², not ‖τ'‖² (only
  the local right-hand sides change; Z, the trace system and the matrix-free CG are untouched).
- `cadbracket`: `--omega-box x0,y0,z0,x1,y1,z1 --mean-stress C --prestress-scale ±s` (σ_e = ℂ:Π_C / |ω|, so
  l_p(u) = the mean of σ_C over ω); `research/cad/polarize.py --mean-stress C`.

Checks (tests/test_prestress.py, 28 checks):
- the upper side's algebra EXACTLY (Fractions, `alfeld.energy`) on 3 random tets with random balanced data:
  ‖τ' + σ‖² = ‖τ'‖² + 2 b·g + |T| σ:Aσ;
- the lower functional EXACTLY: l_p(Gx) = |ω| σ : sym(G) for a linear field;
- KNOWN VALUE: the box (n = 4, ν = 0.3) clamped at z = 0, pulled by F_z = 1000; ω = the full layer 2.5 < z < 7.5.
  By section equilibrium the mean σ_zz over the layer is F/A = 10 exactly. Proved: [9.51169, 10.48831] at s = 0.031.
  CAVEAT, measured: this case is EASY — the prestress part adds NO gap (the gaps of C(f ± sp) are 0.06055 at every
  s from 0.031 to 0.248; the zz-extractor's prestress solution on a full layer is P1-exact, τ' = 0), so the width
  shrinks as 1/s (s = 0.248: [9.93896, 10.06104]). It checks the plumbing against an exact value, not tightness;
- HARD CASE: mean σ_xx over the block (2.5, 7.5)² × (0, 2.5) at the clamp (no closed form). n = 4: [−5.046, 10.203];
  n = 8: [0.02216, 4.87263] — the SIGN IS PROVED (the clamp holds back the Poisson contraction: tension); float FE
  2.73 / 2.51 inside both; the brackets overlap; the prestress gap dominates (0.183 vs the traction's 0.019 at n = 8);
- planted errors: dropping the self term |T|σ:Aσ on the upper side → upper < lower on both signs (caught); the wrong
  extractor on the lower side → caught; 9 and 11 lie outside the layer bracket. NOT caught, and said: dropping BOTH
  upper terms in the hard case (the cross term is negative there, so the "bound" without it is larger — unsound in
  principle, invisible in fact). A bracket only catches errors that push a side across the other.

Honest limits: local brackets are wide (n = 8: width 4.85 on a mean of ~2.5), as Ladevèze–Pled–Chamoin predict. The s
used (balancing C_f and s²C_p) is not the best for WIDTH: width ≈ (gap_f + s² gap_p)/(2 s l) is least at
s = √(gap_f/gap_p) — ~1.7× narrower on the n = 8 block by that estimate (not run).

## 3b — FIRST RESULT ON A REAL PART (2026-11-11 01:00, SimJEB 631, MEASURED)

The quantity: the mean of σ_yy over ω under the vertical load (subcase 1). ω is the tets whose centroid lies in the box
[−23.98, −80.014, 18.324] – [−11.476, −67.509, 30.828]: 1458 tets, |ω| = 589.12 mm³.
- The box is centred on the median centroid of the top 1 % von Mises tets of the float P1 solution. That is the
  high-stress zone, not the singular point: the float vM max is 2285, the 99th percentile 884.
- σ_yy is the dominant mean component there; float P1 gives 530.5 MPa.
- s = √(C_f / C_p) = √(42132.98 / 248.38) = 13 (C_p: the float compliance of the prestress load alone).

Two brackets, matrix-free, float64 Z, the new c rule, 4 cores each:
- C(f + 13 l_p) ∈ [97903.245, 104395.680] (6.6 %), CG 1980 iterations, ~5 min;
- C(f − 13 l_p) ∈ [70316.404, 75462.576] (7.3 %), CG 1936 iterations.

Polarization: **mean σ_yy over ω ∈ [431.55, 655.37] MPa, TENSION PROVED.** The float value, 530.5, lies inside.
Files: results631_3b_yy_{plus,minus}.json; `polarize.py … --s 13 --mean-stress yy`.

The width is 41 % of the midpoint, against the ~7 % of each compliance bracket. That is the price of locality stated
up front: the polarization divides the bracket widths, each ~6.5e3 N·mm, by 4s|l| ≈ 2.8e4. Ways to narrow it, none
tried yet:
- a larger ω (less local);
- the width-optimal s* = √(gap_f / gap_p) in place of the balance;
- a finer mesh near ω (the gap is the discretisation error).
What it is: a two-sided proved bound on a stress average in the most loaded zone of a real bracket. What it is not:
a bound on the peak stress. The peak does not exist as a number; see above.

## 3b — what sets the width (2026-11-11 01:50, MEASURED; corrects the "×1.7 from s*" estimate)

The prestress-alone bracket on the same ω (scale 1): C_p ∈ [248.384, 261.849], width w_p = 13.465 (gap 5.4 %). The
traction bracket: w_f = 3543.745.

Write the combination widths as W(f ± s p) = w_f + s² w_p. Then the mean's width is 2 (w_f + s² w_p) / (4 s):
- predicted at s = 13: 223.81937;
- measured at s = 13 (the two real brackets): 223.81937, equal to 8 digits.
So the model holds here. Its optimum is s* = √(w_f / w_p) = 16.22, with width √(w_f w_p) = 218.44. That is only
2.4 % narrower than s = 13. The "×1.7 narrower" estimate written with the first 3b test was wrong for this part, and
s* is not worth a run.

The width is fixed by the two discretisation gaps: relative width = √(w_f w_p) / |l|. A larger ω does not help by
itself. C_p scales like 1/|ω| at a fixed extractor shape, while the mean |l| also falls. The float pilot gives
530 → 319 MPa from the 3 % box to the 5 % box, against a √(1/2.2) gain, so the relative width would grow ~1.1×
(an estimate, not run). The real lever is a smaller gap: mesh refinement in ω and along the load path, or a
better upper equilibrium field.

## 3c — membrane and bending on a section, IN WORDS (2026-11-11 02:30; not built)

**Membrane** = the mean of σ_nn over a thin slab ω around the classification line (SCL). That is exactly 3b with a
constant extractor. Nothing new.

**Bending** = the first moment of σ_nn across the wall: l(u) = ∫_ω σ_nn(u) (x_n − c) / I. The extractor is now
LINEAR in x: σ_e(x) = C : Π_nn (x_n − c) / I. Does the upper side stay exact? Yes, for two reasons.
1. Because σ_e = C : (…), Aσ_e = Π_nn (x_n − c) / I has only the nn component. So the cross term
   2 ∫_T Aσ_e : τ' is 2/I ∫_T τ'_nn (x_n − c).
2. For a symmetric, divergence-free τ (the Alfeld element, piecewise, with continuous traction inside T):
       ∫_T (τ_ij x_k + τ_ik x_j) = ∫_∂T t_i x_j x_k,
   so 2 ∫_T τ_nn x_n = ∫_∂T t_n x_n². A boundary integral of the linear face traction (the 36 slots g) against a
   quadratic, exact from the exact fluxes. The c-term is the 3b mean, already exact.
- CHECKED EXACTLY (sympy, research/cad/moment_identity_check.py): on a random tet with a random polynomial
  symmetric div-free τ (a Beltrami field of a cubic Φ), the identity holds on all 27 (i, j, k).
- Caution: only the part symmetric in (j, k) is boundary-determined. ∫ τ_mm x_n with m ≠ n alone is NOT. The
  construction must keep Aσ_e = Π_nn·(linear); a general linear extractor would break exactness.
- Lower side: ε(v) is constant on a P1 tet, so ∫_T σ_e(x) = |T| σ_e(centroid), exact. The self term ∫ σ_e : Aσ_e is a
  quadratic over a tet, exact.

**What it needs in code** (~half a day): slot weights for the second moment, per face ∫ φ_v x_n² (exact, rational);
the extractor linear in x; an SCL helper (a point, a unit normal n, the wall thickness → a slab ω).

**The open question for the curator / plan:** WHERE the SCL goes on 631. Through the wall at the 3b hot zone, normal
along the local wall direction. That needs the wall's two faces found along a line, which is a geometry step, not
mathematics.

## 3c — CORRECTION before building (2026-11-11, fork of Logic1; CHECKED EXACTLY, research/cad/moment_full_check.py)

Two statements in "3c IN WORDS" above are wrong.
1. "Only the part symmetric in (j, k) is boundary-determined" — FALSE. For a symmetric div-free τ, EVERY first
   moment is boundary-determined. With M_ijk = ∫_∂T t_i x_j x_k:
       ∫_T τ_ij x_k = ( M_ijk + M_jik − M_kij ) / 2      (the Christoffel trick: A_ijk symmetric in ij)
   sympy, the same random tet and Beltrami field: exact on 27/27. (The earlier "e.g." only showed that
   ∫τ_00 x_1 ≠ M_001/2, which was never the claim.) So ANY linear extractor σ_e(x) = S + L·x keeps the upper side
   exact, and the restriction "Aσ_e must be Π_nn·(linear)" is unnecessary.
2. "Bending = ∫ σ_nn (x_n − c)" is not the ASME bending stress. On a classification line through a wall of normal
   direction n, bending is the first moment of a stress component TANGENT to the wall (σ_tt, t ⊥ n) about the
   through-thickness coordinate x_n: σ_b = (6/t²)∫ σ_tt (x_n − c) dx_n. Membrane likewise averages σ_tt (or each
   component), not σ_nn. In a beam this is σ_xx about y. This is the (i=j=t, k=n) case, exact by 1.

What to build is therefore a design decision for the curator / Logic1, not made here:
- (a) the ASME-style σ_tt membrane + bending on an SCL (exact by the formula above; needs the wall normal n AND a
  chosen tangent t);
- (b) general linear extractors.
Not built: the directive fixed the extractor to Π_nn (x_n − c), which the correction shows is the wrong quantity.

## 3c — BUILT: membrane and bending on an SCL slab (2026-11-11, fork of Logic1; decision (a) of the coordinator)

**What it computes.** A stress classification line through a wall, certified over a thin SLAB ω, not a line. ω is
the tets whose centroid lies inside the wall (|x·n − c| < t_w/2) and within R of the line p + s n.
- σ_m = (1/|ω|) ∫_ω σ_tt;
- σ_b = 6/(t_w |ω|) ∫_ω σ_tt (x·n − c).
These are the line formulas (1/t)∫σ dz and (6/t²)∫σ z dz averaged over the patch, with A_⊥ := |ω|/t_w by definition.
- n is an EXACTLY unit rational vector (inverse stereographic map of a rational point).
- Π = t′t′ᵀ/|t′|², with t′ = u − (u·n) n, is exact and t′ ⊥ n exactly.

**How.** Through the GENERAL linear extractor σ_e(x) = S0 + S1·x:
- lower side (tetfea): ∫_T σ_e : ε(v) = |T| σ_e(centroid) : ε(v), exact in integers;
- upper side (equil): the cross term needs ∫_T τ′_ij x_k = (M_ijk + M_jik − M_kij)/2 from the exact fluxes, with the
  second-moment face weights 1/20, 1/60, 1/120; the self term is the exact quadratic integral.
- Code: equil.extractor_linear_b / _self (+ float versions); alfeld.moments, an INDEPENDENT quadrature check;
  cadbracket.rational_unit / tangent_projector / wall_chord / omega_slab / scl_extractor and `--scl spec.json
  --scl-kind membrane|bending`; research/cad/scl_pilot.py (the float pilot: chord, slab, tangent, s);
  polarize --scl-kind.

**Tests** (tests/test_scl.py, 35/35, MEASURED):
- b·g against the element's OWN first moments (Alfeld sub-tet quadrature, exact to degree 2): exact on 3 random tets.
  The quadrature's sign is T/det; with |det| it failed exactly on a det < 0 tet.
- The self term against the same quadrature, exact. The float b and self term agree with the exact ones.
- Lower side l_p(Gx) for the linear extractor, exact.
- Beam (the box clamped at z = 0, top load F = (0, 500, 1000), M_x = 10000 through the RBE3 at (5, 5, 12); ω = the
  layer 2.5 < z < 7.5; t = e_z, n = e_y, c = 5, t_w = 10). Exact by equilibrium: σ_m = 10 and
  σ_b = 0.006 (M_x − 7 F_y) = 39.

  | n | tets | σ_m (exact 10) | σ_b (exact 39) |
  |---|---|---|---|
  | 4 | 384 | [6.059, 13.941] | [26.570, 44.323] |
  | 8 | 3072 | [8.645, 11.355] | [34.848, 40.972] |

  The float FE values lie inside; the finer mesh is narrower.
- Planted errors, all caught:
  - the moment formula WITHOUT the permutation term: n = 4 and n = 8, the C(f − s p) "bracket" inverts. Measured
    first with F_y = 0: NOT caught, and the two brackets were equal to every digit, because over a full layer the
    permutation term sums to −½κ ∫_∂ω t_y z², which is zero when the section shear is zero. F_y was added for that;
  - the self term dropped: caught on n = 4 and n = 8;
  - the wrong sign of c (c = −5): its bracket contains its own exact value 99 and refutes 39.
- Regression green: prestress 28/28, equil, tetfea, alfeld, errfloat, cadstiff, cadmesh, dd, tetmesh, robust, stand.

**SimJEB 631, subcase 1 (matfree, float64 Z, 3 cores each; ~5 min a bracket, CG ~1930 iterations):**
- SCL point = the 3b box centre (−17.728, −73.7615, 24.576).
- The shortest wall chord: direction ≈ (−0.042, −0.039, 0.998), t_w = 3.8073 mm, c = 27.1741.
- The slab, R = t_w: 456 tets, |ω| = 171.8845 mm³.
- Float mean stress in the slab, projected on the wall plane: the principal 626.0 MPa along t1 ≈ (−0.048, 0.998,
  0.037), the second 63.6 MPa (ratio 0.10, not significant, so t2 is not run).
- **σ_m(σ_t1t1) ∈ [390.71, 898.74] MPa, tension PROVED** (s = 7.3; C(f ± s p) brackets 8.5 % / 9.1 %; float 626.0
  inside; width 79 %).
- **σ_b(σ_t1t1) ∈ [161.40, 1819.42] MPa, the sign PROVED** (s = 5.306; brackets 20.8 % / 21.0 %; float 901.5
  inside; width 167 %).
- Files: results631_3c_t1_{membrane,bending}_{plus,minus}.json.
- Honest reading. The signs are proved; the magnitudes are not usable for a code check yet. The wall is 3.8 mm with
  P1 tets, and the bending field across it is poorly resolved (the brackets' gaps of 21 % say so). As in 3b, the
  width is set by the discretisation gaps, and the lever is refinement through the wall.

## Narrowing 3b/3c — mesh refinement, IN WORDS (2026-11-11 03:15; not built)

The measured lever is a smaller discretisation gap: the 3b width is √(w_f w_p)/|l|. Plan:
1. **Uniform red refinement** (Bey 1:8) of the whole tet mesh: 82k → 660k tets on 631, the size of 148, ~40 min a
   bracket with the new c and ~16.5 GB peak, under the 18G cap.
   - New nodes are edge midpoints. Their coordinates stay exact: the midpoint of two decimals is a decimal with one
     more digit, so the integer scaling of tetfea still applies.
   - Local (graded) refinement only near ω needs conforming transitions. It comes after the uniform version works.
2. **The same continuum problem, exactly:**
   - geometry: flat faces stay flat;
   - supports: a midpoint between two RBE2-fixed hole nodes is fixed (u = 0 on the hole surface is kept);
   - load: the traction is linear on each coarse loaded face, so it is reproduced exactly on the fine faces by its
     values at the midpoints, and the consistent fine nodal loads follow.
   Under these conditions the exact C is the same number. **Both sides check each other:**
   - LOWER: red refinement nests the P1 spaces, so the best fine lower bound is ≥ the coarse one, up to the CG
     tolerance and the rounding of v.
   - UPPER: no nesting is guaranteed. The coarse Alfeld subtets do not align with the fine tets.
   - The HARD check: both brackets contain C, so they must overlap. A fine bracket disjoint from the coarse one means
     a bug.
3. Then rerun the 3b and 3c brackets on the refined 631 and measure the width against the predicted
   √(w_f w_p) scaling (P1: the gap should drop ~×2 per halving of h for smooth parts, less near the singular
   corners).
What this does NOT do: the hole and fillet surfaces are faceted in the SimJEB mesh; refining keeps the facets. It
certifies the faceted part, the same object as before, not a smoother CAD surface.

## Narrowing — BUILT and measured on 631 (2026-11-11 06:15, MEASURED; ustand/refine.py, tests/test_refine.py)

Red 1:8 refinement of SimJEB 631 (ustand.refine): 82 414 → 659 312 tets, 18 141 → 127 771 grids; 0 midpoints
between fixed nodes of different RBE2s; the coarse traction's residual |M_s t − f_RBE3| = 5.7e-14. The load on the
refined deck is the coarse deck's traction, not a new RBE3 spread.

**Compliance (subcase 1, matrix-free, z64, 6 cores):** C ∈ [44350.490, 45615.145], gap **2.85 %** (coarse
[42132.981, 45676.726], 8.41 %).
- The refined bracket lies INSIDE the coarse one: the lower bound rose by 5.3 %, the upper fell by 0.13 %.
- The hard check (overlap) holds. CG took 4050 iterations, the whole run 4000 s, push 370 bits
  (results631r1_s1_matfree.json).

**3b, the mean σ_yy over the same box, s = 13:** C(f ± 13 l_p) gaps 2.67 % / 3.12 % (were 6.6 % / 7.3 %).
- Mean **σ_yy ∈ [507.31, 604.06] MPa, width 17.4 %** (coarse [431.55, 655.37], 41 %). Tension is proved again.
- The refined interval lies inside the coarse one (results631r1_3b_yy_{plus,minus}.json).
- CAUTION, not the identical quantity: the box picks tets by CENTROID. On the refined mesh it selects 11 612 tets,
  |ω| = 581.07 mm³, not the 8 × 1458 children of the coarse ω (589.12 mm³, −1.4 %). The two means are over slightly
  different regions. Both are proved, so the nesting is suggestive, not a theorem.
- For an exact like-for-like comparison, ω on the refined deck must be the children of the coarse ω (tets 8i … 8i+7
  of a coarse tet i keep that order in ustand.refine). That option is not built.

The scaling: the compliance gap fell 8.41 → 2.85 % (×2.95) at h/2, the mean's width 41 → 17.4 % (×2.4). This matches
the prediction width = √(w_f w_p)/|l| with both gaps shrinking ~×3.

## 3b on the refined 631 over the SAME ω — nested (2026-11-11 08:09, MEASURED)

`--omega-children` (185c3d0): ω on the refined deck is the 8 children of each coarse ω tet. That is 11664 =
8 × 1458 tets with |ω| exactly 589.1209 mm³, the coarse region itself (the centroid run above had 11612 tets,
581.07 mm³).
- C(f + 13 l_p) ∈ [101612.414, 104105.870]; C(f − 13 l_p) ∈ [73120.895, 75186.262] (fine, matfree, z64, 6 cores).
- **Mean σ_yy over ω ∈ [508.20, 595.86] MPa, width 15.9 %, tension proved.** Hand check: (101612.414 −
  75186.262)/52 = 508.20, (104105.870 − 73120.895)/52 = 595.86.
- The coarse bracket of the same quantity is [431.55, 655.37] (41 %). **The fine bracket lies inside it.** The
  hard check (overlap) holds, and here it is even nested.
Files: results631r1_3b_yy_children_{plus,minus}.json.

## 3c on the refined 631 over the SAME SCL slab — nested (2026-11-11 11:49, MEASURED)

`--omega-children` now covers the SCL slab as well (children_of, b50b362). The slab is 3648 = 8 × 456 tets,
|ω| = 171.8845 mm³ exactly. A centroid test on the fine tets would have chosen 3593 tets, 169.87 mm³: another
region. Same s as on the coarse mesh; matfree, z64, 6 cores, ~50 min a bracket.

| quantity | coarse (82k tets) | refined (659k tets) |
|---|---|---|
| σ_m, membrane of σ_tt | [390.71, 898.74] MPa, 79 % | **[550.21, 762.10] MPa, 32.3 %** |
| σ_b, bending of σ_tt | [161.40, 1819.42] MPa, 167 % | **[710.94, 1380.44] MPa, 64.0 %** |

- Both signs are proved. Each fine bracket lies inside the coarse bracket of the same quantity.
- Hand checks: membrane (97634.883 − 81568.758)/29.2 = 550.21 and (100918.677 − 78665.368)/29.2 = 762.10;
  bending (104582.590 − 89493.561)/21.224 = 710.94 and (112398.219 − 83099.668)/21.224 = 1380.44.
- Files: results631r1_3c_t1_{membrane,bending}_children_{plus,minus}.json.

Honest reading. One refinement step roughly halves the 3c widths; on 3b and the compliance it cut them by ×2.6
to ×3. Bending stays the widest, as expected for P1 through a thin wall. For a code check (ASME membrane +
bending against an allowable) these brackets are still wide; another level, or a graded refinement through the
wall, is the next lever.

**Why not a second uniform level** (an extrapolation from measured peaks, not run): 148 (640k tets) and the refined
631 (659k) peaked at ~16.5 GB, so 8 × 659k ≈ 5.3M tets would need ~130 GB against the machine's 62 GB. The next
lever is GRADED refinement through the wall near the SCL. Conforming transitions (red-green) or hanging nodes with
constraints are a design decision; plan it in words first.

## Graded refinement through the wall — the two roads, IN WORDS (2026-11-11 11:55; decision pending)

The goal: refine only near the SCL (a ball or slab around ω, a few wall thicknesses), keep the rest at the
current level. That gives the width gain of more levels without ~130 GB.

**(A) Red-green, conforming** (Bank / Bey: red 1:8 inside the zone; green closure tets on the transition layer, so
no face has a hanging node).
- Lower side: the mesh stays conforming, so the P1 space is an ordinary conforming space. f(v)²/a(v,v) stays a
  valid lower bound with NO new mathematics.
- Upper side: every tet is still a tet, and every interior face is shared by exactly two tets. The Alfeld hybrid,
  the trace system and the exact push apply unchanged. NO new mathematics.
- Cost: mesh code only (green patterns for 1, 2 or 3 marked edges; quality of the green tets), plus tests on the box
  with a known answer.
- Risk: green tets are flatter. That can slow CG and widen the local gap a little. It is MEASURED, not hidden.

**(B) Hanging nodes with constraints.**
- Lower side: P1 with the hanging values constrained to the edge or face interpolant is still conforming. Valid, but
  the assembly needs constraint handling.
- Upper side: a coarse face now meets 4 fine faces. The face-by-face traction continuity of the hybrid has no
  partner. It needs a mortar-type balance on non-matching faces, and the exact push must be redone for it: NEW
  mathematics in the part that carries the proof.

**Recommendation: (A).** It keeps both proofs exactly as they are and moves all the novelty into mesh code, where a
mistake shows up as a failed test, not as a wrong bound.

## (A) BUILT — red-green on 631, two levels at the SCL (2026-11-11, MEASURED)

Code: `ustand.refine.graded_refine` with a green closure on edges. The allowed tet patterns are none, one edge, two
opposite edges, the 3 edges of one face, and red. Each face is then split uniquely, so neighbours agree.
`conformity()` counts faces in more than 2 tets and hanging edges. `deck["parent"]` maps every child to its ROOT
coarse tet, and `children_of` uses it. tests/test_graded.py, 22 checks, GREEN; a planted no-closure run shows 67
hanging edges.

Zone: tet centroids in a ball of radius 3 t_w = 11.42 mm around the SCL point. Level 1 marks 2852 of 82414 tets →
104118 tets. Level 2, the same ball on level 1, marks 22697 → **269254 tets**. Both levels are conforming: 0 faces
in more than 2 tets, 0 hanging edges.

Tet quality q = 6√2 V / l_rms³ (1 = regular):

| mesh | tets | p1 | p10 | median | q < 0.1 |
|---|---|---|---|---|---|
| coarse | 82414 | 0.244 | 0.579 | 0.793 | 11 |
| uniform r1 | 659312 | 0.210 | 0.462 | 0.743 | 590 |
| graded g2 | 269254 | 0.167 | 0.395 | 0.721 | 588 |

The green tets are flatter, but the minimum is no worse than the uniform mesh's (0.016 vs 0.013).

Brackets (matfree, z64, 6 cores; the 3c slab = 29184 = 456 × 64 children, |ω| = 171.8845 exactly):

| quantity | coarse 82k | uniform r1 659k | graded g2 269k |
|---|---|---|---|
| C, compliance gap | 8.41 % | 2.85 % | 7.16 % ([42614.75, 45665.60]) |
| σ_m, MPa | [390.71, 898.74] 79 % | [550.21, 762.10] 32.3 % | [514.03, 782.81] 41.5 % |
| σ_b, MPa | [161.40, 1819.42] 167 % | [710.94, 1380.44] 64 % | **[761.78, 1298.90] 52.1 %** |
| CG iterations | ~1930–2200 | 4050 | 6968–8767 |

All brackets overlap; the graded bending lies inside the uniform one. Signs are proved.

**What this says (the width model, measured before):** width ≈ √(w_f·w_p)/|l|.
- Local refinement shrinks w_p, the prestress side, whose error lives in the slab.
- It barely touches w_f, the global traction gap: 7.16 % against 2.85 % for uniform. That error lives along the
  load path and at the singular corners, away from the ball.
- So the more local quantity (bending) beats uniform with 2.4× fewer tets, and the less local one (membrane) does
  not.
The next lever: refine where EACH side's error lives, by goal-oriented indicators of both the f and the p brackets,
not a ball.

Cost: CG iterations rose ×2 against uniform at 2.4× fewer tets, from the grading and the flat greens. Each 3c bracket
took ~45 min. The preconditioner, not memory, is the limit now.
Files: results631g2_s1_matfree.json, results631g2_3c_t1_{membrane,bending}_children_{plus,minus}.json.

## Refining where the error lives — indicator-driven, IN WORDS (2026-11-11 16:40; not built)

What the measurements say: the width of a polarized local quantity is 2 (W(f+sp) + W(f−sp)) / (4s), and each W is
the gap of a whole-part bracket. A ball around the SCL cut the p-part of the gap and left the f-part (the load path)
almost untouched: the compliance gap went 8.41 → 7.16 % only. So refine where BOTH combinations f ± s p lose energy.

**The indicator is already in hand, exactly the gap, localised.** For admissible τ and kinematic v, the
hypercircle (Prager–Synge) gives ‖τ − σ(u)‖² + ‖σ(u) − σ(v)‖² = ‖τ − σ(v)‖². Per tet, η_T² = ‖τ_T − C ε(v_T)‖²_{A,T},
and Σ η_T² bounds the bracket's gap. Both τ (choose + push) and v (tetfea) exist for every bracket we run.
- Indicator for one 3b/3c quantity: η_T² = η_T²(f + s p) + η_T²(f − s p), taken from the two brackets we compute
  anyway.
- Marking (Dörfler): the smallest set of tets that carries θ = 50 % of Σ η_T². It is red-marked, and graded_refine
  closes it green.
- Loop: bracket ± → η → mark → refine → bracket ±, while the deck fits the 18G cap; record the width after each
  round.
- Validity is untouched. The indicator is float and only CHOOSES the mesh; each bracket stays exact on the mesh it
  is run on. --omega-children keeps ω the same region throughout, by the parent map.
- What it costs: each round is two brackets (~1 h each at 270–660k tets) plus the η extraction. The CG slowdown on
  graded meshes (×2 iterations, measured) stays; a better preconditioner on graded meshes is a separate item.
- What would refute the idea: if the marked set is the whole part (the error spread evenly), the indicator gains
  nothing over uniform refinement. The first round's mark fraction shows this.
