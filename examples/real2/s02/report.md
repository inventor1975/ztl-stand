# s02 report: M12 8.8 torque-tightened bolt, preload and stress under the friction range of the source

## SOURCE
Wuerth Industrie, DINO technical handbook, chapter 6 "Dimensioning metric screw assemblies" (VDI 2230 based),
https://prueflabor.wuerth-industrie.com/web/media/en/pictures/wuerthindustrie/technikportal/dinokapitel/Kapitel_06_DINO_techn_Teil.pdf
A distributor's technical handbook, freely readable. Moderately trustworthy: it carries the disclaimer "without
guarantee", the tables are consistent with the VDI 2230 closed forms (my check, calc2.py: preload within 0.9 %,
90 % yield utilisation reproduced), but the worked example's 29.92 kN is a single division, not a proof.
Details in PROBLEM.md.

## WHERE THE UNCERTAINTY COMES FROM
- mu in [0.14, 0.24]: Tab. 3, friction class C, row "galvanic coatings (Zn ...)", lubricant "None" (the example's
  surface: zinc, passivated, no lubricant). Lower end 0.14 is also the value the example itself picks (section 6.7 A).
  This is the ONLY uncertain quantity in the main brick.
- Not uncertain (exact): M_A = 93 Nm (Tab. 5, M12 8.8, mu 0.14, as in the example). Thread geometry, Dkm and
  Rp0.2 = 640 MPa are exact values ADDED BY ME (not in the source; ISO 724 / ISO 898-1, Dkm from ISO 4017).
- ADDED BY ME, separate run only (v5): torque scatter +-5 %. The source mentions "(e.g. +-5 %)" only as a
  condition for the low alpha_A values, not as a stated wrench tolerance, so I did not put it in the main brick.
- The stand's search quantity `Fneed` (needed clamp load) is a search variable, not data.

## PUBLISHED ANSWER vs STAND
| | Published (section 6.7) | Stand (brick.json, mu in [0.14, 0.24], M_A = 93 Nm) |
|---|---|---|
| max preload | 41.9 kN (Tab. 5, mu 0.14) | proved range up to 42.06 kN (my VDI formula, 0.4 % above the table) |
| min preload | 29.92 kN (= 41.9 / alpha_A 1.4) | largest guaranteed `Fneed` = 25.85 kN (find, precision 0.05; 25.9 refuted at mu = 0.24). Hand value 25.891 kN |
| bolt not overloaded | by construction, 90 % of yield at mu 0.14 | sigma_red <= Rp0.2 (640 MPa) EARNED over the whole mu range (true max 577.05 at mu 0.14 by hand, i.e. 0.902 of Rp0.2; the stand shows only the bound 640); <= 0.9 Rp0.2 REFUTED at mu = 0.14 by 1.05 MPa (577.05 vs 576) |

Verdict: **DISAGREE on the question I could pose, NOT COMPARABLE on the source's intent.**
- The published F_M,min = 29.92 kN rests on alpha_A = 1.4, a choice of tightening method ("electronic wrench"), and
  the source never claims that it covers the whole class C friction range. Put as "F >= 29.92 kN for every mu in
  [0.14, 0.24]" (v1/v2) the stand says REFUTED at mu = 0.24, F = 25.89 kN, short by 4.03 kN. Hand check: 93 / (0.2785
  + 0.5775*10.863*0.24 + 0.5*15.065*0.24) = 25.89 kN. The stand is right.
- Friction alone (no wrench scatter) already spreads preload by 42.06 / 25.89 = 1.62, which matches the source's
  own Tab. 2 for "torque wrench, friction estimated" (1.6-2.0), not the 1.4 used in the example. So the example
  is consistent with Tab. 2 only if the friction is better known than class C. v3 (find): F >= 29.92 holds for
  mu up to 0.204 (hand: 0.20497).
- The 0.9 stress utilisation: the stand's REFUTED by 1.05 MPa (0.2 %) is a rounding artifact of M_A = 93 Nm taken
  from a table rounded to whole Nm (exact torque for exactly 0.9 would be 92.8); the yield check holds.
- Extra (v4): with fixed F >= 29.92 kN and torques from Tab. 5 at mu 0.14, 8.8 REFUTED, 10.9 (137 Nm) and 12.9
  (160 Nm) EARNED against the yield limit.

## EXPRESSED FAITHFULLY
- Friction range from Tab. 3; torque from Tab. 5; the clamp-load and stress checks over the full range (a real
  "for all mu" proof, with a certificate for the stress which peaks at the edge).
- The `find` for the limiting clamp load, as requested by the problem shape.

## APPROXIMATED
- VDI closed forms with the source's table as calibration (not the source's own formulas). Checked by me
  (calc2.py), within 0.9 % on preload, utilisation 0.896-0.907 vs 0.90. Nobody else checks them.
- Dkm, d2, d0, Rp0.2 are my additions as exact numbers; Dkm was chosen from ISO 4017 + 13.5 mm bore. A different
  head or washer changes the 25.89 kN directly.
- mu_K = mu_G (the source's own table assumption). Thread and head friction cannot scatter independently here.
- `Fneed` is a given searched by `find`; the bound `F >= Fneed` is the stand's way to ask "largest guaranteed value".
- Result resolution: find grid 0.05 kN, so 25.85 vs the hand value 25.891.

## COULD NOT EXPRESS
- alpha_A itself (the source treats it as a tabled factor of method uncertainty; there is no physical
  quantity to give a range, so the published 29.92 is only testable as a number, via v1/v2).
- Torque-wrench scatter as source data: the source gives it only as a band attached to alpha_A, not as a tolerance
  of M_A (v5 with my +-5 % gives guaranteed 24.55 kN, hand 24.60).
- Working loads / residual clamp load (section 6.7 E): the example states none.

## TOOL OUTPUT
Every run used `OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1`; no run was killed; each took under 0.5 s.
- brick.json, work mode: EARNED, proved 517/20 (~25.85), beyond 25.9 REFUTED at mu = 6/25 (F = 25.8914).
  F "ZTL, outer range"; sred "ZTL, certificate checked exactly (1 pieces)". 12 tries. (out_work.txt)
- brick.json, --dev: EARNED proved 25.85, same; BUT the tries beyond the limit came back **OPEN** (not
  REFUTED): "F proved within [25.8914, 42.0559] kN ... yet no corner violates it". Work mode found the
  mu = 0.24 corner witness; dev mode did not. That is a work-vs-dev disagreement on the same input (OPEN vs
  REFUTED); the proved side is the same. (dev_brick.txt)
- v1 (F >= 29.92, nu 0.9): REFUTED, witness mu 0.24, by 4.03 kN; work and --dev agree.
- v2 (F >= 29.92, yield): REFUTED, same witness.
- v3 (find largest mu for F >= 29.92): EARNED up to 0.204, refuted at 0.205; work and --dev agree. Hand 0.20497.
- v4 (three classes): 8.8 REFUTED, 10.9 EARNED, 12.9 EARNED.
- v5 (+-5 % torque, mine): guaranteed 24.55 kN.
- v6 (Fneed 0, nu 0.9): REFUTED, witness mu 0.14, sred 577.05 > 576.
The brick label `"grade": "8.8"` in v4 was read as a number (44/5), as BRICKS.md warns; harmless there.

## DOC GAPS
- No guidance on which side a rounding of a source table (93 Nm) should fall, when a stated utilisation (90 %)
  is checked as a bound; the stand reports a 0.2 % failure with no tolerance option.
- `find` with --dev: BRICKS.md says each try is judged by the same machinery, but not that the REFUTED/OPEN split
  can differ between work and dev for the failing end (see TOOL OUTPUT).
- `unit` of a dimensionless given: `""` worked, but section 1 never shows it for a given (only for catalog fields).
- The `ground` text on catalog items vs on quantities: unclear whether a catalog item's `ground` is allowed
  (it was accepted silently).
