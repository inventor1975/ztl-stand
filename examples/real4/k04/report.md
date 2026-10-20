# k04 report: smallest output inductor of a 3 A buck converter (TI TPS54331 design example)

## SOURCE
Texas Instruments TPS54331 datasheet (SLVS839H, Oct 2023), https://www.ti.com/lit/ds/symlink/tps54331.pdf, section 8.2 design example
(Table 8-1, Eq. 5, 8-11), sections 6.5 / 6.6 for the min/max values. A manufacturer datasheet design example.
Trust: its inductor numbers (Lmin 5.7 uH, 6.8 uH chosen, peak 3.47 A, RMS 3.01 A) I reproduced exactly by hand (5.675 uH, ILPP 0.939 A,
3.469 A, 3.012 A). Its output-capacitor numbers (ESR max 43 mohm, RMS 161 mA) I could NOT reproduce (I get 33.7 mohm and 136 mA), and its Eq. 13
carries a (D-0.5) term that is negative here. So: inductor part reliable, capacitor part not. The published answer is a nominal point calculation, not a worst case.

## WHERE THE UNCERTAINTY COMES FROM
| quantity | range | place in the source |
|---|---|---|
| Vin | 7 to 28 V | Table 8-1 "input voltage range" |
| Vref | 0.772 to 0.828 V (typ 0.8) | 6.5, "Voltage reference" row |
| fsw | 456 to 684 kHz (typ 570) | 6.6, "Switching frequency" row |
| kL (inductance factor) | 0.8 to 1 | factor 0.8 in Eq. 9 -- MY READING of what it means (an interpretation, not stated). Run also without it (brick_nokL.json) |
| Isat 3.84 A, Irms 3.6 A, Iout 3 A, R5 10.2k, R6 3.24k, Co 94 uF, ESR 1 mohm | exact | 8.2.2.3, 8.2.2.5.1, 8.2.2.6 (no tolerance stated; none added) |
Added by me: nothing except the reading of 0.8 (listed above, with a run without it) and the capacitor formula substitution (chain only).

## PUBLISHED ANSWER vs STAND
| case | published | stand (work mode, smallest L that works on the whole range [L,30] uH, grid 0.01 uH) | verdict |
|---|---|---|---|
| nominal point: Vin 28, Vout 3.3, fsw 570, KIND 0.3 (brick_nominal) | 5.7 uH (exact Eq. 8: 5.675) | proved 5.68, REFUTED at 5.67 | AGREE |
| source ranges, ripple ratio <= 0.3 (brick) | none given (point calc only) | 9.18 uH (hand: 9.178) | NOT COMPARABLE with the source; stand = hand |
| source ranges, peak <= 3.84 A | none; 6.8 uH is shown to satisfy it at nominal (3.47 A) | 4.92 uH (hand: 4.917) | NOT COMPARABLE; consistent: 6.8 > 4.92 |
| source ranges, RMS <= 3.6 A | none | 1.20 uH | NOT COMPARABLE |
| without the kL factor, ripple / peak (brick_nokL) | none | 7.35 / 3.94 uH (hand 7.342 / 3.933; grid 0.01) | = hand |
Hand check (own python, scratchpad k04calc.py, a grid of Vin and corners of Vref, fsw, kL): 9.178, 4.917, 7.342, 3.933 uH. The stand agrees to its 0.01 grid in every case, no disagreement.
Reading: the published 6.8 uH meets the peak and RMS ratings over the whole spread (hand: peak 3.607 A at the worst corner) but NOT KIND = 0.3 (worst ratio 0.405, needs 9.18 uH) -- the datasheet's 5.7 uH is smaller than the 9.18 uH the same rule needs once its own spread in fsw and its own 0.8 factor are counted.
CHAIN (system.json, FB -> inductor stage -> output capacitor, bands, work mode): ripple 9.75, peak 5.25, RMS 2.125, 30 mV ripple 2.125 uH (grid 0.125; hand: RMS 1.2 and 30 mV about 1.1 uH, so those two are limited by my coarse L bands below 4 uH, 1 uH steps). Compared with the flat brick (9.18 / 4.92): the system answers are larger (coarser), never smaller. Sound, but loose: 5.25 vs 4.92 and 9.75 vs 9.18, and only after bands of 1 V in Vin, four in Vout, 0.125 uH in L (21 x 4 x 70 band boxes). With coarse bands (2 Vin bands x 1 Vo band, L step 0.5 uH) the same peak question gave 15.5 uH; Vin 2 V steps, 3 Vo bands -> 5.75 uH; the finest cut -> 5.25 uH (the true value is 4.92); an intermediate cut gave 6.5 uH. So the system answer depends strongly on how finely the contract is cut.

## EXPRESSED FAITHFULLY
- Eq. 5, 8-11 as laws, Vin / Vref / fsw ranges from the tables, requirement set, "smallest L" as a find, L continuous (no catalog), L's nonlinear (1/L) entry.
- The nominal reproduction (brick_nominal) is exactly Eq. 8.

## APPROXIMATED
- 0.8 in Eq. 9 read as kL in [0.8, 1] on the inductance (interpretation; both versions run). Checked by me (hand calc), not by the tool.
- Vout is derived from Vref range and exact R5/R6 instead of the fixed 3.3 V of the table (range 3.20-3.43 V; the source itself says 3.31 V). Wider than the source's point value, from the source's own Vref range.
- Eq. 9's 0.8 applies to the ripple only (as in the source); RMS/peak use that ILPP.
- Chain: output-capacitor stage uses ILPP*(1/(8 fsw C)+ESR) instead of the source's Eq. 13 (substitution; by my hand calc it binds only below about 1.1 uH: worst ILPP 8.3 A at 1 uH x 3.9 mohm-equivalent = 32 mV). Its fsw is a separate copy of the range (contracts carry ranges, so fsw in the inductor stage and in the capacitor stage are independent -- conservative).
- Continuous-conduction assumption of Eq. 9 (valid at light load fails) not checked; the source does not either.
- find grid: results on a 0.01 uH grid (flat) and 0.125 uH (system) are the proved side of the limit.

## COULD NOT EXPRESS
- A continuous parameter (L) inside a component (BRICKS 7d: "not yet"), so the system carries L as a system quantity fed into the inductor stage as an input; the contract then needs L-bands, and the answer is band-limited.
- Requirement of "the contract of one band over its whole box": the stand uses the whole band box, not the arriving sub-range, so bands must be cut finely.
- The datasheet's own output-capacitor numbers (43 mohm, 161 mA, Eq. 13): not reproducible by me from the text, so not tested.
- Conduction mode (CCM/DCM), temperature dependence of L or Vref (only the min/max), inductor saturation roll-off of L with current (kL covers it only if that is what the 0.8 means).

## TOOL OUTPUT
Command as required: `OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand <brick>`. No run was killed.
| brick | work | --dev |
|---|---|---|
| brick_nominal.json | EARNED (find proved 5.68), 0.15 s | agrees (checked_by: ZTL + independent checker), 0.15 s |
| brick.json (find list x3) | EARNED: 9.18 / 4.92 / 1.20 uH; `how`: "ZTL, certificate checked exactly (312 / 339 / 288 pieces)"; 15.6 s | agrees, same numbers, 16.7 s |
| brick_nokL.json | EARNED: 7.35 / 3.94 / whole range (1 uH); 4.7 s | not run |
| system.json (3 components, find x4) | EARNED: 9.75 / 5.25 / 2.125 / 2.125 uH, `how` "ZTL, exact at the corners", 34 s; every beyond value OPEN ("the stand could not decide the range ... the limit lies between"), never REFUTED | agrees, same numbers, 105 s |
| system_one / system_f2 / system_f3 (also an intermediate cut, files deleted) | peak only, band study: 15.5 / 5.75 / 5.25 uH, 0.5 / 6.5 / 30 s | not run |
No BRICK ERROR, STAND ERROR or STAND FAULT occurred. First try of the brick files worked.
Note: the system verdict EARNED means "every limit was FOUND", as BRICKS 7a says; the numbers are in `finds`.

## DOC GAPS
- 7d does not say that a band is judged over its WHOLE box (not the arriving part) and that outputs are outer interval ranges there; with a repeated variable (Vo*(Vin-Vo)/Vin) this loses a factor ~3 at coarse bands. I learned it from the output (`bands_used`).
- 7d: an interface with `"inputs": {}` (a component with no inputs) works, but the text does not say so.
- 7a with a system: the find's `precision` and the bands interact (the answer lands on band edges); not mentioned.
- `"how": "ZTL, exact at the corners"` for the system's quantities: unclear whether this is the component contracts (ranges, outer) or the system's own law; the system answer is not "exact" in the sense of the flat brick.
- 6/8: whether the unit `uH`/`kohm`/`mohm`/`uF` prefix forms are accepted is only implied; they worked.
