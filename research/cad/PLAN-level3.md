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
