# s08 report: RTC backup coin cell (congatec AN9) - lifetime and required capacity

## SOURCE
congatec AN9 "RTC Battery Know-How and Calculations", rev 1.3, 2024. https://www.congatec.com/fileadmin/user_upload/Documents/Application_Notes/AN9_RTC_Battery_Lifetime.pdf
A manufacturer's application note (two worked examples, sec 2.3 and 2.4). Trust in the published answer: the arithmetic
is right (I reproduced 8.4 y and 473.04 mAh exactly), but the note says its example values are "typical" and the formulas
are rules of thumb with empirical allowance factors; nothing is measured or validated in the note. It is a rough sizing, not a proof.

## WHERE THE UNCERTAINTY COMES FROM
All from the source; I added none.
- k (capacity multiplier, eq 2.2): range [1.1, 1.3], centre 1.2. Source sec 2.2, the Note under the formula: factor 1.2 "can vary from 1.1 to 1.3".
- f (life factor, eq 2.1): range [0.7, 0.9], centre 0.8. Source sec 2.1, the Note under the formula: factor 0.8 "can vary from 0.7 to 0.9".
- Everything else is exact: 8760 h/y, 15 y, 3 uA, 230 mAh, 2.5 uA. These are called "typical"/"maximum RTC battery current" in the
  examples; I treated them as exact numbers because the source gives no tolerance for them.
No temperature, cut-off voltage or load profile exists in this source (it only says to measure the current at the highest
ambient temperature). So this is a weaker fit to the "temperature derating, cut-off, load profile" area than asked: it is a
capacity/lifetime check with two source-stated allowance ranges.

## PUBLISHED ANSWER vs STAND
Three questions, all in one brick (find list), each with the source's ranges; plus the same brick at the published point values.

| question | published | stand, source's ranges (work) | stand, point values (work) |
|---|---|---|---|
| smallest C so that eq 2.2 is covered for every k in [1.1,1.3] (15 y, 3 uA) | 473.04 mAh (k=1.2) | 512.46 mAh (proved; 512.45 REFUTED) | 473.04 mAh |
| largest guaranteed lifetime of the 230 mAh cell at 2.5 uA, every f in [0.7,0.9] | 8.4 y (f=0.8) | 64400 h = 7.35 y (64401 h REFUTED) | 73600 h = 8.40 y |
| smallest C for 15 y at 3 uA by eq 2.1, every f in [0.7,0.9] (cross-check of the source's two formulas) | not stated | 563.15 mAh (grid; exact 563.143) | 492.75 mAh |

- At the published point values: AGREE (473.04 mAh; 73600 h = 8.40 y rounds to the published 8.4).
- Over the source's own stated ranges: NOT COMPARABLE in the strict sense (the source publishes point values and never claims
  a guarantee), but the point answers are NOT robust: 473.04 mAh fails at k = 1.3 (needs 512.46); 8.4 y fails at f = 0.7 (7.35 y).
  Hand check (hand_check.py, exact fractions): 512.460 mAh, 7.352 y, and 563.143 mAh. The stand's numbers are right.
- A finding the source does not mention: its two formulas are not the same rule. Eq 2.1 with f = 0.8 gives 492.75 mAh for
  15 y / 3 uA, eq 2.2 with k = 1.2 gives 473.04. The ranges also do not match: 1/f spans 1.11-1.43, k spans only 1.1-1.3.
  The recommendation "473.04 mAh or more" would give only 12.6 y (f=0.7) to 16.2 y (f=0.9) by the note's own eq 2.1.
  The CR2477 suggestion (a 1000 mAh class cell, not in the source) is safe under every reading; the number 473.04 is not a guarantee.

## EXPRESSED FAITHFULLY
- Both formulas as exact laws; both factor ranges as given ranges; 8760 h/y, 15 y, 3 uA, 2.5 uA, 230 mAh; unit check passed
  ("checked: every law's dimensions agree").
- The two "limit" questions via `find` (smallest capacity, largest lifetime), with bisection on the grid (precision 0.01 mAh, 1 h).

## APPROXIMATED
- Lifetime question turned into a charge balance: "life >= T" is written as Cap*f - T*I >= 0, which is the same inequality
  without a division. Safe (algebra); the judge checks it, the hand check agrees.
- Time in hours, not years, to avoid the stand's 365.25-day Julian year. Safe.
- Three separate factor quantities (k, f2, f3) for three separate questions. Each question is judged on its own, so this loses nothing;
  using one f for two laws would be a shared-tolerance case and I did not test how the stand handles it.
- The "typical" examples' currents and capacities treated as exact. NOT safe in general: a real maximum current or capacity has a
  tolerance, and the source gives none. Nobody checks this; it is the brick's data ("ON CREDIT" in the output).
- The 2.4 question asks for a limit (find) instead of the published "pick a part": the source names CR2477 but gives no capacity list.

## COULD NOT EXPRESS
- The 1 %/year shelf loss, the cell's age at installation, the voltage cut-off and any temperature dependence: the source states them
  in words only ("approximately") or not at all, so there is nothing numeric to encode.
- The meaning of the allowance factors (what physical effects they cover) - they are opaque multipliers here.
- Part picking (CR2032 vs CR2477): no catalog in the source; adding one would bring in datasheet data from outside the source.

## TOOL OUTPUT
- `OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand examples/real3/s08/brick.json`
  work mode: verdict EARNED (weakest of the three finds; all three EARNED), 0.6 s, rc 0. Stderr only "[stand] 1/1 designs, 0 s".
  Files: out_work.json, out_nominal_work.json (point-value variant), out_dev.json.
- Each find: `proved` is the limit, `beyond` one grid step away is REFUTED with a concrete point (e.g. Cap1 = 512.45 mAh, k = 1.3, margin -1e-5 Ah).
  19 tries for the first find. `how`: "ZTL, exact at the corners" for every margin; no "outside ZTL" line.
- `--dev` (independent checker): same three limits, same EARNED, 0.7 s; checker line "every corner of the tolerance box recomputed exactly and inside".
  Work and --dev AGREE. No errors, no STAND FAULT, no kill by the limit.
- The overall verdict "EARNED" is easy to misread: it means "each limit was found", not "the published answers hold". The meaningful
  content is in `finds`.
- Honest weight: the whole problem is a product of three numbers. The stand reproduces the hand result; it adds no insight a
  one-line calculation does not, apart from stating the limits as proved with a failing witness one step beyond.

## DOC GAPS
- BRICKS.md does not say what the overall verdict of a find list means when each find answers a different question (the weakest of the
  finds' verdicts: EARNED here even though the published point answers do not survive the ranges). It is in the output only via `finds`.
- It does not say whether a given quantity used in two laws (my f2/f3 temptation) counts as "shared" when the two laws belong to
  different finds; I avoided it by duplicating the quantity.
- Not stated how a find's grid `precision` interacts with an exact limit: the exact 563.143 comes back as 563.15 (next grid point
  that works), so `proved` is a grid value, not the limit; the doc says "tried values sit on the grid" but not that the answer is rounded to the safe side.
- Derived-quantity requirements must be written as "margin >= 0": documented (bound may not be derived), but the pattern for
  "lifetime >= T" with T searched (division-free form) is not in the doc.
