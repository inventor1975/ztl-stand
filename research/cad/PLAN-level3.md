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
