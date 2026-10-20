# s03 report: amplifier + 12-bit ADC error budget (offset 5 mV, gain 1 %)

## SOURCE
https://www.ecircuitcenter.com/EBA/ADC/amp-ADC-1.html (eCircuit Center, "Error Budget Analysis, Basic Amplifier and
ADC"; formulas for ib/iboff from https://www.ecircuitcenter.com/EBA/amp1/amp_advanced1.html). A tutorial web page
by a small educational site, not a manufacturer note. Trust: the method is textbook worst-case analysis and I
reproduced both published totals by hand (2.203 mV; 1.4 % linear sum), but the page has typos (offset voltage 1 mV
vs 0.1 mV, ADC drift 0.05 vs 0.04 LSB/C) and the published gain total is a first-order sum, not the exact worst case.
Moderate trust.

## WHERE THE UNCERTAINTY COMES FROM
All from the page's device-error table ("Device Errors") and "Conditions"; all +- ("All errors can be either
polarity"). Nothing added by me.
- voff U1: +-0.1 mV (table says 1 mV; see PROBLEM.md), voffTC +-10 uV/C.
- ib: +-5 nA, +-1 nA/C; iboff: +-5 nA, +-1 nA/C.
- ADC offset +-3 LSB, drift +-0.04 LSB/C (table 0.05); resolution +-1/2 LSB; INL +-1 LSB.
- R1, R2 tolerance +-0.1 %, tempco +-100 ppm/C each (independent).
- ADC gain +-0.05 % (2 LSB), +-20 ppm/C (0.08 LSB/C); Vref +-0.5 %, +-50 ppm/C.
- dT = 30 C ("Max change"), a fixed given. 8 uncertain quantities in the gain brick, 10 in the offset brick.

## PUBLISHED ANSWER vs STAND
| check | published | stand (work) | verdict |
|---|---|---|---|
| offset <= 5 mV | 2.2 mV, PASS | EARNED, guaranteed +-2.20319 mV | AGREE (hand exact 2.2032 mV) |
| gain <= 1 % | 1.4 %, FAIL | REFUTED, witness gives 1.41172 % | AGREE on verdict; 1.41 vs 1.4 differs by second-order terms (hand corner search: 1.4117 %) |
Variants (my own, source "TRY IT" hints): U1 voff 1 mV: EARNED, +-3.10319 mV (hand 3.1032). Vref tol 0.1 %: REFUTED,
witness 1.00567 % (hand 1.00567 %) - the linear sum would say exactly 1.00 %, i.e. borderline; the exact formula
says it just fails. `find` largest Vref tolerance meeting 1 %: proved 0.094 %, failing at 0.095 %; hand bisection
0.09439 %. The source gives no number for this, so it is a check against my hand calc only.

## EXPRESSED FAITHFULLY
Offset: RTI sum as an exact linear law (voff + drift, ib and iboff with the source's sensitivities divided by K, ADC
terms in LSB x 5/4095 V divided by K). Gain: nonlinear law Eg = (1+R2T/R1T)/Knom * ADC gain / Vref factor - 1 with
each part's tolerance and tempco as independent ranges. This is the exact physical formula, stricter than the
source's linearised sum. Requirements: |Eoff| <= 5 mV, |Eg| <= 1 %.

## APPROXIMATED
- Gain as exact nonlinear formula vs the source's first-order sums: safe, only makes the stand's number 0.0117 %
  larger; the stand's interval bounds and exact witness check it, my corner script also.
- dT fixed 30 C, tempco symmetric: safe, equals the source's worst case.
- Offset uses nominal R1, R2, K (as the source): small neglected effect (not quantified), unchecked by the stand.
- Percent roundings (ADC gain 0.05 %, 20 ppm/C) taken from the source's own conversion.
- Two source typos resolved by choosing the values that reproduce the published total (see PROBLEM.md).
- Offset "<= 5 mV" read as a two-sided |E| <= 5 mV window.
- Combined brick.json has both requirements; the REFUTED verdict only names the gain budget, so for the per-budget
  results I used brick_offset.json and brick_gain.json (same laws, split).
- find uses vt in [-1,1] times a magnitude vtm (product of two toleranced givens) because find searches one range.

## COULD NOT EXPRESS
- Op-amp open-loop gain error (the companion page, 0.1 %) - not in this page's budget, not added.
- "Referred to input" vs the output-referred budget ambiguity: the brick cannot say which the source means.
- Nothing else failed to fit.

## TOOL OUTPUT
- brick.json (both budgets), work mode: REFUTED, 0.66 s, value_there 0.0141172, overshoot 0.00411721, minimal
  conflict = gain budget only. No errors or kills; limits unchanged (3G, 1 core).
- brick_offset.json: EARNED, 0.07 s, how "ZTL, outer range", +-2.20319 mV. brick_gain.json: REFUTED, 0.58 s.
- --dev: brick.json REFUTED 15.1 s, brick_gain REFUTED 1.0 s, brick_offset EARNED 1.3 s ("every corner recomputed
  exactly and inside"). Work and dev agree on all three. In dev the REFUTED witness is a different point
  (1.0269 % instead of 1.4117 %): still a valid violation, but the worst-case point reported differs.
- Variants: voff1 EARNED 0.07 s; vref 0.1 % REFUTED 0.56 s; find 4.4 s (proved 47/50000, beyond 19/20000).
- Files: brick*.json, out_*.txt, gen.py (generates bricks), hand.py (hand calculations).

## DOC GAPS
- BRICKS.md does not say that `slots: {}` and `catalog: {}` are fine for a brick with no parts (t28 shows it).
- With a combined brick, the REFUTED output does not show which other requirements pass; the guidance to split
  bricks is missing.
- Unit "1/C" times a "C" given and "ppm/C" worked, but this is not stated explicitly; units for LSB counts
  (dimensionless "") worked.
- The `find` example only shows a point value; it does not say how to search a symmetric +- tolerance (I used a
  magnitude times a [-1,1] range).
- The --dev REFUTED witness differs from work mode's; the doc doesn't say the witness may differ.
