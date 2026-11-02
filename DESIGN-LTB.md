# Lateral-torsional and torsional buckling — design (2026-11-02, the curator's "замысел да")

Goal: remove the premise "no lateral-torsional / torsional buckling" from the space frame's EN checks — a PROVED
lower bound of each member's critical factor alpha_LT for its own lateral-torsional (LTB) and torsional modes, then
EN 1993-1-1 6.3.2 (chi_LT) and 6.3.3 with chi_LT.

## Scope of version 1 (said in every output)
- MEMBER level, as EN 6.3.2 itself: each member under its own first-order moment diagram (end moments, plus the
  parabola of a transverse member load) and its axial force, both scaled by lambda; ends are FORKS (v = 0, phi = 0,
  v' and phi' free: no warping restraint) — EN's usual premise, the designer's to provide (lateral restraint at the
  member ends). Free warping is the conservative side for the lower bound.
- Why not the global frame mode: in 3D the geometric stiffness of a frame depends on the nature of the joint moments
  (quasi- vs semi-tangential, Argyris) — a sign error there is invisible on single members and unsound on frames.
  On one member the coupling's overall sign does not matter (phi -> -phi), so version 1 cannot fall into that.
- Doubly symmetric sections (shear centre = centroid, no Wagner beta terms); loads at the shear centre (no load-height
  term) — both said; a section with one axis of symmetry refuses.

## The member's energy (Vlasov, doubly symmetric)
  U  = 1/2 int [ E I_z v''^2 + G J phi'^2 + E I_w phi''^2 ]                 (lateral bending v about z', twist phi)
  V  = 1/2 int [ N (v'^2 + i0^2 phi'^2) ] + int M phi v''                     (i0^2 = (I_y + I_z)/A)
for bending about y' (the strong axis, moment M, lateral displacement v); the other plane alike with I_y and w. The
critical factor: the smallest lambda with U + lambda V not positive definite. Fibre stresses alone give
-int M v' phi' ; with the shear stresses (varying M) the correct term is int M phi v'' (Trahair; Yang & McGuire).

## The proof (as the frames' stability)
Sub-elements (Hermite cubics for v and for phi), K_E + lambda K_G(N, M) built exactly (N constant, M linear +
parabola per sub-element: polynomial integrals, rationals). A continuum lower bound per sub-element: the inner fields
eta_v, eta_phi (eta, eta' = 0 at its ends) give
  - E I_z int v_H'' eta_v'' = 0 and E I_w int phi_H'' eta_phi'' = 0 (cubics against clamped bubbles);
  - G J int phi_H' eta_phi' = G J int (phi_H' - mean) eta_phi' (int eta' = 0) — NOT zero: a cross term in U itself;
  - lambda cross terms N (v_H' eta_v'), N i0^2 (phi_H' eta_phi'), M (phi_H eta_v'' + eta_phi v_H'' + eta_phi eta_v'');
  each bounded by Cauchy-Schwarz against the inner energies with the clamped Poincare constants
  (|eta'|^2 <= (L/2pi)^2 |eta''|^2, |eta|^2 <= (L/2pi)^2 |eta'|^2 ... to be fixed in the derivation), the minimum over
  eta of (inner energy + 2 cross) >= - sum of squares of forms on the nodal values — a PSD correction C(lambda).
  MUST be checked as an inequality of forms before any code: the exact condensed continuum (fine mesh) minus the
  claimed matrix PSD, on many N, M, sections — as done 2026-11-02 for the axial member load (that check caught the
  P^2-vs-Nmax^2 error).
Upper bound: the Hermite field itself (admissible), the frames' witness.

## Tests (both sides, exact)
- uniform moment, forks: M_cr = (pi/L) sqrt(E I_z G J (1 + pi^2 E I_w / (G J L^2)));
- end moments psi = 0 and -1 (C1 ~ 1.88 and 2.75 — tabulated: test against a fine mesh, not the table);
- a column, torsional: N_cr,T = (G J + pi^2 E I_w / L^2) / i0^2; flexural-torsional = min with Euler (doubly sym.);
- mutations: the M coupling dropped, the GJ cross term dropped, the correction dropped — each must be caught.

## Then EN
6.3.2.2: lambda_LT = sqrt(W fy / M_cr), M_cr = alpha_LT M_Ed; chi_LT by curves (6.3.2.2 general case first; the
rolled-section case 6.3.2.3 later). 6.3.3: chi_LT into (6.61)/(6.62) with k_ij of Annex B for members susceptible to
torsional deformation.

## Status 2026-11-02 (MEASURED)
IN: `ustand/ltb.py` (both I_w > 0 — Hermite twist — and I_w = 0 — linear twist), `frame3d.judge_ltb` (EN 6.3.2),
`judge_interaction(curve_lt=...)` (chi_LT, Table B.2 k_zy <= 1), the night battery's sweep I and I-MUTL.
Both sides against exact formulas: uniform moment (I_w > 0 and = 0), torsional / flexural columns; against a
96-element fine mesh: moment gradients, member-load parabolas, N + M, boxes.
Cost (24 cores, 0.5 % moduli, I_w = 0 as the generator gives): 160 members 9.7 s, 1330 members 76 s — after the
caches, the outward 64-bit inputs and the pool (before: 108 s and 975 s).
OPEN: axial member loads (refused, named); single-symmetric sections (Wagner) and load height; global frame
lateral-torsional modes (the joint-moment question) — version 1 is member level with forks.
