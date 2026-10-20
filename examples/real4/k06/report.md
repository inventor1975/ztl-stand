# k06 report: lift-station pump head over a range of level and force-main pressure

## SOURCE
- Mark Ludwigson, "Centrifugal Pump Selection", PDH Academy course 431, Example 3 (PDF pp. 29-31).
  https://pdhacademy.com/wp-content/uploads/2023/06/431-Centrifugal-Pump-Selection.pdf
- A continuing-education course text with worked examples by a licensed engineer; freely readable PDF.
- Trust in the published answer: I recomputed it independently (python, same formulas): 26.79 / 38.03 ft static,
  2.358 ft minor, 4.820 ft friction, TDH 33.97 / 45.21 ft. It is arithmetic correct to its printed rounding. It is a
  nominal-parameter calculation: C, K, flow and diameter carry no tolerance. Friction formula and the 6.0 in diameter
  are textbook approximations, not verified against a pipe table.

## WHERE THE UNCERTAINTY COMES FROM
Only two quantities, both ranges of operating conditions stated in the problem text of Example 3 (p. 29):
- wet-well level ELw in [4.0, 6.0] ft ("the water level varies from EL 4.0 to 6.0")
- force-main tie-in pressure Pd in [9, 13] psi ("discharge tie-in pressure varies from 9 to 13 psi")
Everything else (flow 400 gpm, 400 ft, 6 in, K sum 7.37, C = 140, tie-in EL 12.0, 2.31 ft/psi) is a single number in
the source. NOT in the source, added by me: variant A only, C in [120, 150] (the ends are the source's list values for
cast iron and PVC, p. 28). The main brick has no added tolerance.

## PUBLISHED ANSWER vs STAND
| quantity | published | stand (work and --dev, flat) | |
|---|---|---|---|
| highest TDH (pump must give 400 gpm at this) | 45.2 ft | smallest Hp that works for the whole box: 45.21 (grid 0.01); 45.20 REFUTED at ELw=4, Pd=13; hand value 45.2076 | AGREE |
| lowest TDH | 34.0 ft | largest Hl that always holds: 33.96 (33.97 REFUTED); hand value 33.9676; ZTL's guaranteed range for TDH: [33.9676, 45.2076] | AGREE |
The published numbers are the rounded form of these. Static heads 26.8 / 38.0: ZTL range of Hst [26.79, 38.03], same.
Variant A (C in 120..150, my addition; the source has no number to compare): stand 46.81 and 33.38; hand 46.8001 (C=120,
high static) and 33.3894 (C=150, low static). AGREE with my hand check. Variant B (extra, mine): largest flow a 45.2 ft
head still covers at the high static head: stand 1513.3 L/min proved, 1513.4 REFUTED; hand (scipy root) 1513.33 L/min
(399.78 gpm). AGREE. No disagreement anywhere.

Honest scale: with the source's data only Hst moves, and TDH is Hst plus two constants. The verdict here is close to
interval arithmetic on one addition, and the stand adds no information beyond what the author's own two-case
"extreme conditions" method gives. It is a check that the formulas, units and find work on this form of problem.

## EXPRESSED FAITHFULLY
- Both ranges (level, pressure) as independent ranges; all-values-in-the-box proof instead of the author's two corner
  cases (here the same result, since TDH is monotone in both).
- Static head, K-method minor loss with g = 32.2 ft/s2 and V = Q/(pi D^2/4), Hazen-Williams with C = 140 with the exact
  exponents 1.852 and 4.8655 (pow with constant exponents), TDH as the sum. Units checked: "every law's dimensions agree".
- The requirement as pump head Hp >= TDH, with find giving the limiting head; the second find the lowest head.
- Chain version: STATIC, FIT, PIPE components with contracts (static.json, fittings.json, pipe.json) and system.json /
  system_fine.json joining them.

## APPROXIMATED
- No pump: the pump is a required head Hp (found, not chosen). The source gives no pump curve here, so "a pump selected
  so flow meets requirement" is NOT tested. Checked by: nobody; it is a scope reduction.
- gpm to L/min with exact gallon; the source's 448.8 gpm/cfs rounding differs by 0.0003 ft (checker: my hand python).
- Hazen-Williams written with q/(1 gpm), d/(1 in), result times 1 ft (givens `Qg`, `Din`, `Hu`) to keep units on; the
  formula itself is the source's non-SI correlation. The unit check cannot see an error in the 0.2083 constant.
- Find results are on a 0.01 ft grid: "45.21" means the exact limit 45.2076 lies in (45.20, 45.21].
- Component version: only RANGES travel, and the flow arrives as one exact value, so the flow input must be cut into
  bands. With bands 1500..1530 L/min the limits are 45.36 / 33.84 (looser than flat 45.21 / 33.96); with bands
  1514..1515 L/min 45.22 / 33.96. Sound (enclosures), but the band width decides the looseness; I chose the edges by
  hand (first 1500..1530, then a finer pair to see the effect); the stand gave no guidance.
  Beyond the proved value the verdict is OPEN (not REFUTED), as the manual says for systems.
- K sum entered as the single number 7.37, not nine separate K givens.

## COULD NOT EXPRESS
- A pump chosen from a list by its curve and the operating point of pump curve meeting the system curve, for this
  source: the source has no curve numbers (the curve in Example 7 is a picture only). Not tested at all.
- Tolerances on C, K, diameter: the source gives none. Variant A is only my reading of its list of C values.
- Cross-component correlation: the component version lost nothing here because the heads share no datum, but it would
  for one shared quantity (e.g. one C in two pipe runs); not exercised.

## TOOL OUTPUT
Command as required (heavy -m 3G --cores 1, OPENBLAS_NUM_THREADS=1, timeout 900); wall times include the wrapper.
No run was killed or erred. Output files are in this folder (out_*.txt).
| brick | work | --dev | verdict |
|---|---|---|---|
| brick.json (flat, 2 finds) | 0.76 s | 1.2 s | EARNED, EARNED; Hp 45.21, Hl 33.96; dev same |
| brick_crange.json (C 120..150) | 1.0 s | 2.1 s | EARNED; 46.81, 33.38; dev same |
| brick_qlimit.json (largest Q) | 0.65 s | 0.93 s | EARNED; 1513.3 L/min; dev same |
| system.json (bands 1500-1530) | 0.42 s | 0.51 s | EARNED; 45.36, 33.84; beyond is OPEN; dev same |
| system_fine.json (bands 1514-1515) | 0.37 s | 0.51 s | EARNED; 45.22, 33.96; beyond is OPEN; dev same |
Work (ZTL) and --dev (independent checker) agreed on every run; no STAND FAULT. The `how` line for TDH in the flat
brick reads "ZTL, interval reading of the definition (sound, may be wide)", the numbers are tight anyway.
The flat and component versions agree in verdict; the component ranges are wider as the manual says.

## DOC GAPS
- BRICKS 7a: for `smallest` the tried range [a, to] means the "proved" value is on a grid from `from`+k*precision, and
  the output prints "45.21" where the exact limit is 45.2076. Explained in the text but easy to read as the limit.
- BRICKS 7d: not said that a component with no inputs needs `"inputs": {}` (it worked), nor how to cut a single exact
  input value into bands (a value on a band edge touches two bands); I had to guess where to put the edges.
- BRICKS 5: no US gallon / gpm unit (inches and feet exist); flow in gpm needs a hand conversion into L/min.
- `find` inside a system with its own `requirements` per item works (system.json) but 7d does not say so
  (the doc says `find` over a system works; per-item requirements were assumed).
