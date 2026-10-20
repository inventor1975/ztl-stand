# s10 report: TPS25221 current-limit resistor (pick RILIM under guaranteed current-limit curves and 1% resistor tolerance)

## SOURCE
TI datasheet TPS25221, SLVSDT3D (rev. 12/2019), https://www.ti.com/lit/ds/symlink/tps25221.pdf : sec 9.5.1 eq.(1), sec 10.2.1.2.1-10.2.1.2.3, Table 3.
A manufacturer's datasheet design example. Arithmetic is easy to reproduce (I did, see below), and the two curves are the
vendor's own guaranteed limits. Trust: good for the numbers; the datasheet's own text, however, states that A and B ignore the
resistor tolerance, so its headline picks are not "guaranteed" answers unless read together with sec 10.2.1.2.3.

## WHERE THE UNCERTAINTY COMES FROM
| quantity | range | place |
|---|---|---|
| RILIM (resistor) | nominal x (1 +- 1%) | sec 10.2.1.2.3 text ("assuming 1% resistor values"), Table 3 columns "1% LOW/HIGH" |
| IOS (device spread: temperature + process) | between curve 56850/R^1.033 and curve 52640/R^0.97 mA | sec 9.5.1 eq.(1); text says Fig. 24 "includes tolerance ... temperature and process" |
| allowed RILIM | 20 .. 210 kohm | sec 7.3 "Recommended Operating Conditions" (used as the catalog window) |
Added by me: none. Runs "without tolerance" (brickE_*_exact) are the datasheet's own sec 10.2.1.2.1/2 assumption, not an invention.

## PUBLISHED ANSWER vs STAND
| question | published | stand (work) | verdict |
|---|---|---|---|
| A, exact resistor, E96 20..210 k, IOS_min >= 1000 | 49.9 k (IOS_max 1186) | 39 pass, largest 49.9 k (IOS_min 1001.37); 51.1 k fails | AGREE |
| B, exact resistor, IOS_max <= 500 | 124 k (IOS_min 391) | 23 pass, smallest 124 k (IOS_max 490.57); 121 k fails | AGREE |
| A with the 1% resistor (sec 10.2.1.2.3 applied) | not stated; Table 3 method implies check at high bound | 38 pass, largest 48.7 k; 49.9 k REFUTED | NOT COMPARABLE to a published pick; stand says the published 49.9 k does not hold with 1% |
| B with the 1% resistor | not stated | 23 pass, smallest 124 k | AGREE (consistent) |
| largest nominal R with IOS_min >= 1000, +-1% (find) | not published | 49.47 k (beyond 49.48 k REFUTED) | NOT COMPARABLE; my hand value 49.4712 k |
| smallest nominal R with IOS_max <= 500, +-1% (find) | not published | 122.82 k (122.81 k REFUTED) | NOT COMPARABLE; hand value 122.8167 k |
| Table 3 rows (17), exact +-1% bounds, claim IOS_min >= table, IOS_max <= table | 17 rows | 11 EARNED, 6 REFUTED (rows 110, 90.9, 68.1, 46.4, 39.2, 34.8 k) by 0.10..0.49 mA | AGREE up to rounding of the table (see below) |
Hand check (python): IOS_min(49.9 x 1.01 = 50.399 k) = 991.1 mA < 1000, so the published A pick fails by 9 mA when the 1% resistor is counted;
the stand is right. 48.7 k x 1.01 = 49.187 k gives 1016 mA. Largest R_high = 56.85^(1/1.033) = 49.966 k, /1.01 = 49.4712 k;
smallest R_low = 105.28^(1/0.97) = 121.589 k, /0.99 = 122.8167 k. The stand's find limits equal these to the 0.01 k grid.
Table 3 refutations: row 110 k: IOS_max at exactly 110 x 0.99 is 556.415 mA vs table 556 (the table rounds, and also rounds the resistor
bounds to 0.1 k). Others: 669.49 vs 669, 718.83 vs 719, 1285.37 vs 1285, 1271.75 vs 1272, 1699.10 vs 1699.
All six misses are < 0.5 mA, i.e. table rounding, not a real disagreement.
Side finding (not stand output): the equation's IOS_min at 30 k is 1693.8 mA, below the electrical-characteristics table's 1700 mA
guarantee, and IOS_max(20 k) = 2879.5 vs table 2880 - the curve is a slightly conservative fit of the table.

## EXPRESSED FAITHFULLY
- Both guaranteed curves as two laws with a non-integer power (pow(R/1kohm, 1.033) and 0.97); constants 56850 / 52640 as givens.
- 1% resistor: exact +-1% (catalog tolerance 0.01, or s in [-1,1] times 1% in the find brick).
- E96 catalog restricted to 20..210 k (the datasheet's range) through `where` on nominal values.
- The two requirements (>= 1000 mA, <= 500 mA) and Table 3's row claims (bounds as slot fields).

## APPROXIMATED
- "Closest 1% resistor" = E96 series; the datasheet never names the series (all its values are E96). Checked: every picked/listed value is E96.
- The guaranteed device spread enters only through the two curves; the curves are the vendor's fit and slightly conservative vs the
  electrical-characteristics table (see side finding). I used the curves because the worked example does.
- Find precision 0.01 kohm; "largest/smallest" limits are on the nominal R grid, not on exact reals (hand values given above).
- The `find` brick takes the tolerance as `Rn*(1+s/100)`, s in [-1,1], shared between the two curves (one resistor), as in reality.
Nothing was widened or narrowed for fitting; IOS_min/IOS_max are read by ZTL's interval reading ("sound, may be wide"); here it was tight
(at the proved limit 49.47 k the guaranteed IOS_min low end is 1000.03 mA, against my hand value 1000.026).

## COULD NOT EXPRESS
- Nothing material. The device spread is two one-sided curves in the source and two one-sided claims here; a single joint statement
  about IOS between the curves was not needed.
- Table 3's own rounded resistor bounds (54.4/55.4 etc.) cannot be used as the data (tolerance is relative); so the stand judges the
  exact +-1%, and the six sub-0.5 mA misses follow.

## TOOL OUTPUT
- brick.json (find list, work): EARNED; largest Rn 4947/100 (49.47) kohm, beyond 49.48 REFUTED; smallest Rn 6141/50 (122.82), 122.81 REFUTED;
  17 + 17 tries; ~0.3 s. --dev: same finds, `checked_by` "ZTL + the independent checker"; no fault.
- brickE_A_exact / B_exact (work): verdict EARNED, designs 39 EARNED / 60 REFUTED and 23 / 76. brickE_A_tol1 / B_tol1: 38 / 61 and 23 / 76.
  excluded_by_where 93 of 192 E96 values (outside 20..210 k). Each run < 0.3 s. --dev (A_tol1, B_tol1): identical counts, no STAND FAULT.
- brickT3_table_check (work and --dev): 11 EARNED, 6 REFUTED, identical in both.
- One BRICK ERROR on the way (my mistake): `where` with `RL.R` of a toleranced item -> "RL.R has no exact value here (a tolerance, a range
  or a derived quantity) - this word reads exact values only"; fixed with `nominal(RL.R)`.
- Run limits followed (heavy -m 3G --cores 1, timeout 900); no run was killed.
- Files in this folder: brick.json (main), brickE_{A,B}_{exact,tol1}.json, brickT3_table_check.json, out_*.txt, summ.py (output summary helper).

## DOC GAPS
- `where` with a toleranced catalog field: BRICKS.md says `where` reads exact values and mentions `nominal(X)` in computed/where, but does not
  warn that a plain `RL.R` fails for a toleranced item; I found out by the error.
- Series decades are in the field's unit (decade 10 for kohm, not 10000): implied by "decade multiplies the series value" but not stated;
  a unit of kohm with decade 10000 would silently mean 10 Mohm.
- Not clear whether two finds may search the same quantity (one largest, one smallest); it worked.
- Negative exponents: I wrote `K/pow(x,1.033)`; BRICKS.md does not say if `pow(x,-1.033)` is allowed.
