# s06 report: TC1264 LDO, hot-end thermal example and low-end dropout (Microchip DS21375D)

## SOURCE
Microchip TC1264 datasheet DS21375D, section 5.2 worked example (Eq 5-1, 5-2), Table 5-1, DC table in section 1.0. Read through a mirror (https://cdn.eicom.ru/media/PDF/8071246.pdf); the manufacturer's site gave 403. A manufacturer datasheet design example: the arithmetic is simple and reproducible (I redid it, see below), but the closing "VINMAX = 4.6 V" is not consistent with its own formula. The example itself checks only the hot end.

## WHERE THE UNCERTAINTY COMES FROM
| quantity | range | place in the source |
|---|---|---|
| VIN | 3.3 V +-10% (2.97 .. 3.63) | sec 5.2 example, "Given" |
| VOUT | 2.7 V +-0.5% (2.6865 .. 2.7135) | sec 5.2 example, "Given" |
| ILOAD | 275 mA (faithful brick: exact max); extended brick: 0.1 .. 275 mA | example: ILOADMAX. The 0.1 mA lower end is MINE (the datasheet's lowest test load) |
| TA | 95 C exact (max ambient) | example |
| thetaJA | 59 C/W exact | example, Table 5-1 |
| TJmax | 125 C | example; absolute-maximum table |
| IDD (extended brick only) | 130 uA | DC table, supply current, Max column. ADDED BY ME, the example neglects ground current |
| dropout (extended only) | Max column: 30/160/480/800/1300 mV at 0.1/100/300/500/800 mA | DC table, VR >= 2.5 V rows. ADDED BY ME as a check. The linear interpolation between rows is mine |
No tolerance was invented. Added by me: the extended check (IDD, dropout, load lower end). The faithful brick (brick_faithful.json) has none of them.

## PUBLISHED ANSWER vs STAND
| | published | stand (work mode) | |
|---|---|---|---|
| worst PD, hot end | 260 mW | PD range 70.5 .. 259.46 mW (20757/80000 W) | AGREE |
| PD <= PDmax 508 mW / Tj <= 125 C | yes | EARNED, Tj in [99.16, 110.31] C (faithful) | AGREE |
| largest VIN | 4.6 V | find: proved 4.535 V, REFUTED just beyond (4.536 V) | DISAGREE |
| low-end dropout (not in the source) | not checked | REFUTED: at VIN 2.97 V, 275 mA, margin -0.17 V | NOT COMPARABLE (the source says nothing) |

Hand check of the disagreement (python, exact fractions):
- PD = (3.63 - 2.6865)*0.275 = 259.46 mW. Published 260 correct.
- Largest VIN: 0.5084746/0.275 + 2.6865 = 4.5355 V. At 4.6 V: Tj = 95 + 59*(4.6 - 2.6865)*0.275 = 126.05 C, over 125 C. So the stand is right and the datasheet's 4.6 V is about 0.065 V too high (it would be 4.55 V if VOUT were taken as exactly 2.7 V; neither gives 4.6). It is a small error in the source's closing sentence, not a safety margin.
- Low end: VDO(275 mA) = 0.16 + 175/200*0.32 = 0.44 V (interpolated Max column; using the 300 mA row, 0.48 V). VIN - VR - VDO = 2.97 - 2.7 - 0.44 = -0.17 V (-0.21 V with the 300 mA row). The stand agrees to the digit. Meaning: with worst-case dropout the part can fall out of regulation when the 3.3 V rail sags 10% at full 275 mA load. With TYPICAL dropout (about 0.24 V at 275 mA by my interpolation) it would pass; the source's example never mentions this. Caveat: "Max" dropout and "-10% rail" occurring together is the worst case the datasheet's own numbers allow; the datasheet's dropout is measured as 2% output drop, so the output would still be within its 2.5% accuracy band at the margin edge; I did not model what the output voltage is below that.

## EXPRESSED FAITHFULLY
Eq 5-1, Eq 5-2 (as Tj = TA + thetaJA*PD, same as PD <= PDmax), the +-10% input, the +-0.5% output, all given numbers. The largest-VIN question as a `find`.

## APPROXIMATED
1. Tj <= 125 instead of "PD <= 508 mW": the same inequality rearranged. Safe, exact; the stand checks it exactly.
2. Dropout Max column interpolated linearly between rows (table() with five knots). Not safe in principle (the Max column is not guaranteed linear between rows); checked by nobody but the stand's arithmetic. The failing result does not depend on it (the 300 mA row alone gives the same refusal, by hand).
3. In the extended brick the PD formula keeps VOUT fixed at 2.7 +-0.5% even when VIN is so low that the part is in dropout (there the pass drop would be VDO, not VIN - VOUT). Only the low end of the reported PD range is affected; the hot-end maximum is not.
4. `find` over VIN uses lower end 2.97 V (the source's low end) so the swept range is [2.97, a]; VOUT stays toleranced. IDD is 0 there (faithful).

## COULD NOT EXPRESS
- That the output is VIN - VDO (not VOUT) in dropout, as a piecewise physical model (could be a branch; I did not, to keep it small).
- The datasheet's condition "dropout depends on VR >= 2.5 V" is only one row set; not relevant here.
- Correlation between ambient/junction temperature and dropout or IDD (not given in the source).

## TOOL OUTPUT
Command as required, each brick one process, 1 core, 3G cap. None hit the limit; each run took under 0.2 s.
- brick_faithful.json: work: EARNED, Tj [7932937/80000 ~99.1617, 8824663/80000 ~110.308] C, "ZTL, exact at the corners". --dev: EARNED, checker "every corner of the tolerance box recomputed exactly and inside". AGREE.
- brick_find.json: work: EARNED, proved 907/200 (~4.535) V, beyond 567/125 (~4.536) V "REFUTED"; at 4.536: Tj 125.008 C. --dev: same proved/beyond. AGREE.
- brick.json (extended): work: REFUTED, "input must clear setpoint + dropout at the low end of the 3.3 V +-10% range", witness VIN 2.97, IL 0.275 A, margin -0.17 V; minimal_conflicts: that requirement alone (Tj <= 125 holds with IDD added). --dev: REFUTED, same. AGREE.
- No errors. One BRICK ERROR on my first try of brick.json (table() y-values written as bare numbers: "left side is ... right side is dimensionless"); fixed by giving the y-values as given quantities with units (mV).
Output files: out_*.txt, out_dev_*.txt in this folder.

## DOC GAPS
- table(): the text says y-values "may be numbers, given quantities or slot.fields" but does not say that bare-number y-values are dimensionless, so a table producing a voltage needs given quantities with units. I found it from the error.
- find: unclear whether the lower end `from` belongs to the swept range for a toleranced quantity being replaced (it does: [from, a]); the doc says it, but it does not say the quantity's tolerance is dropped, so I set the `value` without a tolerance myself.
- No way to say "the grid answer 4.535 means the true limit lies in (4.535, 4.536]" other than reading `beyond`; the report fields did that, fine.
