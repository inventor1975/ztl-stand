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
