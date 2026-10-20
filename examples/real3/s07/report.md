# s07 report: working pressure of a 1/2 in Type 904L tube at 200-400 degF (Swagelok MS-06-117)

## SOURCE
Swagelok "Tubing Data - Engineered Combinations", MS-06-117 Rev D (2021), manufacturer datasheet:
https://www.swagelok.com/-/media/distributor-media/o-s/pittsburgh/pdfs/catalogtubing-data-ms06117-revd.ashx
Pages 3 (basis, Table 1, Examples 1-2) and 5 (Table 4, 904L). Trust: the table values are the maker's own, but the sheet says "for reference only" and not for design work. I could reproduce 26 printed Table-4 entries (1/2 in and larger) from the stated basis, so the table is internally consistent. The hot number for 904L is NOT printed; it is my application of the printed rule (see PROBLEM.md). The column of Table 1 for 904L was read from PDF text extraction (positions), confirmed only indirectly: the printed Examples fix the 6Mo, 316 and 2507 columns.

## WHERE THE UNCERTAINTY COMES FROM
| quantity | range | place in source |
|---|---|---|
| OD, 1/2 in tube | 0.500 +-0.005 in | p.3, bullet "Calculations are based on maximum OD and minimum wall", ASTM A269 example |
| wall, 0.065 in | +-10 % (0.0585..0.0715 in) | same bullet |
| service temperature | 200..400 degF | the two Table 1 knots; the RANGE is my choice of an operating condition |
| temperature factor on S | 0.82 at 200, 0.68 at 400 (904L) | Table 1 |
| S | fixed 20 000 psi ("maximum S value", Table 4 text) | p.5; a cap, taken as the value |
ADDED BY ME: linear interpolation of the factor between knots (run also with T = 400 exactly: same result); Y = 0.4 (B31.3, not in the sheet); E = W = 1. The 100 degF -> 1.00 knot is the sheet's room-temperature range end.

## PUBLISHED ANSWER vs STAND
Question: largest design pressure P (psig) for 1/2 x 0.065 in, worst-case dimensions.
| case | published (sheet's rule) | hand calc, exact | stand (find, precision 1 psi) | verdict |
|---|---|---|---|---|
| -20..100 degF (brick_room) | 5100 (Table 4) | 5106.9 | proved 5106, refuted at 5107 | AGREE (table is the exact value rounded down to 100) |
| 200..400 degF (brick) | 5100 x 0.68 = 3468 (my application) | 3472.7 | proved 3472, refuted at 3473 | AGREE with exact; differs from 3468 only by the sheet's rounding down. NOT COMPARABLE as a printed number (the 904L hot value is not printed) |
| T = 400 exactly (brick_t400) | same | 3472.7 | 3472 / 3473 | same as above, so interpolation did not matter |
| 3/4 x 0.109 in, room (brick_room_34x109) | 5800 (Table 4) | 5800.27 | proved 5800, refuted 5801 | AGREE (a 0.27 psi margin) |
Choice (brick_choice_3470, P = 3470 psig, 200..400 degF, walls 0.035/0.049/0.065/0.083): stand EARNED 0.065 and 0.083, REFUTED 0.035 and 0.049. The sheet's rule with its rounded 5100 gives 3468 < 3470, so it would force 0.083. This P was chosen by me inside the 3468..3473 gap; the disagreement is rounding in the table, not physics; the hand check (hand_check.py) agrees with the stand (0.065 gives 3472.7). At P = 3400 both pick 0.065 (brick_choice_3400).
The stand's refuting witness was recomputed by hand: P = 3473, T = 400, OD = 0.505, wall = 0.0585 gives margin -4.29e-6 in; at P = 3472 the margin is +1.1e-5 in.

## EXPRESSED FAITHFULLY
- B31.3 pressure design thickness t = P*D/(2(S*E*W + P*Y)) as a law, with D = OD, worst corner OD +0.005, wall -10 % from the tolerances.
- Wall and OD tolerances as stated; S = 20 000 psi; the temperature factor as a table over T.
- The limit as a find (largest P) rather than a bracketing catalog; the wall choice as a 4-item catalog.

## APPROXIMATED
- Interpolated Table 1 between knots: mine, not in the source. Safe here because the factor falls monotonically, so the worst point is T = 400, a knot; confirmed by brick_t400.
- Table 1 factor applied to S (the sheet derives it from allowable stress; P is proportional to S, so equal to scaling P). Checked by hand.
- psi as the unit "6894.757293168Pa", inch as "25.4mm", degF as a bare number (no such units): no unit check on the temperature; psi value is rounded at the 13th digit. Checked by me only.
- find precision 1 psi, so the limit is bracketed in a 1 psi cell, not exact.
- "psig" read as plain pressure (law has no gauge/absolute distinction).

## COULD NOT EXPRESS
- OD tolerance differing by tube size (the printed 1/4 and 3/8 in values do not follow the 1/2 in basis); I used 1/2 in and 3/4 in only.
- The sheet's second basis (repeated pressure testing with a 4:1 design factor, used for 6Mo/825/2507 and others) is a test result, not a formula.
- Corrosion, bending, welds: the sheet makes no allowance either.
- Ovality (the sheet notes double OD tolerance for some austenitic tube): not modelled.
- Using the max OD together with the min wall is the sheet's worst-case convention; the stand proved it as "for every OD and wall in the box" and found the same corner.

## TOOL OUTPUT
All runs: `OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand <brick>`; no limit hit, no error after the first fix of my own typo (a law repeated by my script: "BRICK ERROR ... repeats laws[0]").
- brick.json (work): EARNED, `proved: 3472`, `beyond: 3473` REFUTED with witness; judge ZTL 2a24683; the margin was proved by "ZTL, certificate checked exactly (3 pieces)"; wall time about 0.7 s.
- brick.json --dev: same verdict, `checked_by: ZTL + the independent checker (dev mode)`, about 1 s, no STAND FAULT.
- brick_choice_3470: work and --dev agree (0.035 and 0.049 REFUTED, 0.065 and 0.083 EARNED), well under 1 s.
- brick_room: 5106/5107; brick_t400: 3472/3473; brick_room_34x109: 5800/5801 (work only). Outputs in out_*.json.

## DOC GAPS
- psi, inch and degF are not in the unit list; the "number as a unit" trick (6894.757293168Pa) works but is mentioned only for kWh/100km-style units; the output prints the odd unit string everywhere.
- 7a says "a placeholder value" for the found quantity; it does not say the placeholder must satisfy nothing (P = 0 worked) - fine, but unstated.
- Not stated whether `table` knots may be dimensionless temperatures in degF while the unit is empty (it works).
- For `find` with `precision`, whether the reported `proved` is on a grid anchored at `from` (it is) took a read of the tries to confirm.
