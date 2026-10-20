# r05 report: pump operating point and brake power (BYU ChEn 374 lecture 30, slide 12)

## SOURCE
https://www.et.byu.edu/~mjm82/che374/Fall2024/LectureNotes/Lecture_30_notes.pdf , slide 12. University lecture
slides, freely readable; instructor not named. Trust of the published answer: the printed v and H are right (my
independent calculation with Haaland reproduces them to 5-6 digits, and reproduces the printed Hreq at v = 10).
The printed flow and bhp are NOT consistent with the printed v (see below). So: slide-quality source, two of four
printed numbers wrong or sloppy. The friction correlation is not stated on the slide; I inferred it.

## PUBLISHED ANSWER vs STAND
| quantity | published | my hand calc (Haaland, exact data) | stand |
|---|---|---|---|
| v_op | 7.131 m/s | 7.130976 | EARNED inside [7.1305, 7.1315]; proved range 7.13098 (both ends) |
| H_op | 149.149 m | 149.149180 | EARNED inside [149.1485, 149.1495]; proved range 149.149180 |
| Q | 0.055 m^3/s | 0.0560066 | REFUTED (witness 0.0560066, 0.00051 over the upper end 0.0555) |
| bhp | 89.35 kW | 91.020 | REFUTED (conflict set contains the bhp window alone) |

- v, H: AGREE. The stand's value equals my hand number.
- Q, bhp: DISAGREE with the slide. Hand check: A = pi D^2/4 = 0.0078540 m^2; Q = A v = 0.056007, not 0.055.
  bhp = 1000*9.80665*149.149*0.056007/0.9 = 91.02 kW. The printed 89.35 kW corresponds to Q = 0.05496, i.e. the
  slide's own 0.055 used instead of A v. The STAND is right, the SLIDE's Q (2 digits, 1.8 % low) and bhp (1.8 % low)
  are inconsistent with its own v and H. Caveat: I read "0.055" as printed to 2 digits, so I allowed +-0.0005;
  even 0.0555 is below 0.0560.
- Stand minimal_conflicts: exactly two single-requirement sets, flow window and bhp window. Matches hand.
- Extension (brick_tol.json, my own added tolerances, not the source's): Pw <= 92 kW REFUTED, witness 93.645 kW
  (1.645 over). My 5x5x5 grid hand scan gives max P = 93.64507 kW at the corner D = 0.101 m, mu = 0.653e-3, eps = 0.03e-3;
  the stand's overshoot 1.64507 equals 93.64507 - 92. AGREE. For v within +-3 % and H within
  +-3 % of published the stand says OPEN (proved ranges v [6.686, 7.643], H [141.58, 155.30], wider than the true
  v [6.959, 7.344], H [146.07, 151.58] from my scan). By my scan those two do hold, so the true answer is EARNED
  and the stand's OPEN is a loss of power (sound, not wrong), not an error.

## EXPRESSED FAITHFULLY
Pump curve H = 200 - v^2 (catalog H0 = 200 m, c = 1 s^2/m, written in velocity as on the slide), efficiency 0.9,
all pipe and pressure data, rho, mu, Darcy-Weisbach with Haaland, operating point as an implicit law with Q
searched in [0.005, 0.1] m^3/s, bhp = rho g H Q / eta, the published numbers as windows of +-half the last printed digit.

## APPROXIMATED
- Friction law = Haaland, inferred from the slide's printed Hreq(10) = 232.223, not stated by the source.
  Unsafe if wrong; checked by my python (it reproduces 232.223 to 6 digits) and by nothing in the stand.
- The published "within" windows are my reading of the printed digits (+-half last digit). Not the source's claim.
- g = 9.80665 (stand's g0), inferred from 61.662.
- pi is a 1e-15 bracket in the stand; it showed up as the "violating point" of the REFUTED verdict (a bracket
  corner, harmless but odd).
- brick_tol.json: all three tolerances are my additions; windows +-3 % and 92 kW are my arbitrary choices.
- Single-item catalog (the pump is fixed); no choice problem. No uncertainty in the faithful brick: the source
  is deterministic, so this tests the implicit-law solver on a published number, not a worst-case check.

## COULD NOT EXPRESS
- Colebrook (implicit in f): not tried; BRICKS.md gives no way I could see to write it. Not needed here.
- Nothing from the source itself was left out. NPSH, series/parallel pumps (other slides) not attempted.

## TOOL OUTPUT
Command as given (heavy, 3G, 1 core). All rc = 0, no kills.
- brick.json (four published windows): work: REFUTED, 3.9 s; --dev: REFUTED, 4.0 s, same witness and conflict sets.
  `"fails": "published flow 0.055 m3/s (2 digits, +-half of last digit)"`,
  `minimal_conflicts.sets = [[flow window], [bhp window]]`.
- brick_vH.json (v and H windows only): work EARNED 1.2 s; --dev EARNED 1.3 s, checker's own bounds equal ZTL's.
  `how`: "ZTL, interval reading of the definition (sound, may be wide)", yet the proved ranges are points.
- brick_tol.json: work REFUTED 36.8 s (on Pw <= 92), --dev REFUTED 37.3 s; minimal_conflicts has one set (power) and
  three `undecided_sets` (v alone, H alone, both).
- brick_tol_vH.json (v, H +-3 % only): work OPEN 11.6 s, --dev OPEN 11.7 s: "Vel proved within [6.68583,
  7.64328] m/s, which reaches past the bound, yet no corner violates it - the extreme may lie inside the box and
  no certificate decided it".
- Work and --dev agreed on every verdict. No STAND FAULT, no errors.
Files: out_*.txt are the raw outputs.

## DOC GAPS
- BRICKS.md says "ztl-stand/1"; the t19 example it points to still has "universal-stand/1" - unclear which is required.
- Not said whether a brick with NO toleranced quantity and a one-item catalog is meaningful; it worked.
- Not said that Pa*s is accepted as a unit (it was) or that a viscosity in a define chain is fine.
- Not said that a REFUTED verdict on an exact-data brick reports a `pi` bracket corner as "violating point"; confusing.
- `how` says "interval reading ... (sound, may be wide)" even when the proved range is a single point.
- The OPEN reason for the +-3 % case says a "certificate" was searched, but nothing says how to help it (narrower
  box? split into modes?).
- No guidance on picking `search` bounds for an implicit law with a velocity-based pump curve (I used 0.005..0.1).
- BRICKS.md does not say which friction correlations are expressible (Swamee-Jain appears only via t19; Haaland worked via pow/log10).
