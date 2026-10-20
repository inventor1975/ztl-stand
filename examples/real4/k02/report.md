# k02 report: worst-case error budget of an amplifier + 12-bit ADC chain

## SOURCE
https://ecircuitcenter.com/EBA/ADC/amp-ADC-1.html ("Error Budget Analysis - Basic Amplifier and ADC", eCircuit Center,
2002). An engineering-education tutorial page with a companion spreadsheet (not downloaded; I read its picture on the
page). Not a manufacturer note. Trust: the gain table is internally consistent and reproduces 1.4 %. The offset total
(2.2 mV) is reproducible only after choosing among the page's own inconsistent inputs (prose table: op-amp voff 1 mV,
Ib 5 nA; sheet picture: 0.1 mV, 10 nA; ADC offset drift 0.05 LSB/C in the table, 0.04 in the text). So: usable as a
check, but the offset inputs are ambiguous. Full statement: PROBLEM.md.

## WHERE THE UNCERTAINTY COMES FROM
All from the page (no tolerance added by me). Drift boxes = tempco x 30 C, in either sign.
| quantity | range in brick | place in source |
|---|---|---|
| R1 10 k, R2 40 k | +-0.1 % each, plus drift +-0.3 % each (dR1, dR2) | table "Gain errors": 0.1 %, 100 ppm/C; dT = 30 C |
| Vref 5 V | +-0.5 %, drift +-0.15 % (dVref) | table: 0.5 %, 50 ppm/C |
| ADC gain eg | +-(2 + 0.08*30) LSB / 4095 = +-0.1074 % | table: 2 LSB, 0.08 LSB/C |
| ADC offset oadc | +-(3 + 0.05*30) = +-4.5 LSB | table: 3 LSB, 0.05 LSB/C |
| ADC resolution ores, INL oinl | +-0.5 LSB, +-1 LSB | table |
| op-amp voff | main: +-(0.1 mV + 10 uV/C*30) = +-0.4 mV; prose variant +-1.3 mV | sheet picture / prose table |
| op-amp ibn, ibp | main: +-(10 nA + 1 nA/C*30) = +-40 nA each; prose variant +-52.5 nA | sheet picture / prose table (Ib +- Ios/2: my reading) |
| Rs 500 ohm, Vref nominal, N | exact | page gives no tolerance |
Chosen by me, not from the source: the evaluation points vin = 0 V and 1 V (1 V is the page's full scale); the band edges
of the component version; the loosened bounds 20/25/35/50 mV in the sys-total* files (marked in their `why`). I
did not run "without added tolerances" separately because I added none.

## PUBLISHED ANSWER vs STAND
| item | published | stand (work mode) | verdict |
|---|---|---|---|
| offset RTI at 0 V, budget 5 mV | 2.2 mV, PASS | [-2.2148, +2.2148] mV, EARNED | AGREE (2.2 vs 2.215: the stand includes second-order terms, e.g. ibn*R2 with R2 at its extreme) |
| gain error at 1 V, budget 1 % | 1.4 %, FAIL | offsets zeroed: [-1.3859, +1.4091] %, REFUTED (witness 14.09 mV) | AGREE on verdict; 1.4 vs 1.386/1.409 (the true extremes are asymmetric, the page's sum is symmetric first-order) |
| combined at 1 V, budget 5 mV + 1 % = 15 mV | not stated; 2.2 + 14 = 16.2 mV implied by its own formula | [-16.058, +16.306] mV, REFUTED | AGREE with the implied value |
| prose-table amp values (voff 1 mV...) | no published total | offset [-3.235, +3.235] mV by my hand calc, combined +-17.3 mV; brick-prose REFUTED | NOT COMPARABLE (no published number) |
| largest Vref tolerance that still meets 1 % gain (find) | not stated; first-order sums imply exactly 0.100 % | proved 0.096 %, REFUTED from 0.097 %; my hand bisection: 0.09697 % | NOT COMPARABLE (derived by me); shows the page's "0.1 % Vref" fix is a hair short: exact worst error at 0.1 % is 1.0031 % |
| component version (amp + ADC as COMPONENTs), offset, vin = 0 | -- | EARNED, [-4.227, +4.227] mV | sound, 1.9x wider than flat |
| component version, combined at 1 V | -- | OPEN for bounds 15, 20, 25 mV; EARNED at 35 and 50 mV, range [-32.06, +32.32] mV | sound but ~2x wider than the flat answer |
Where I checked by hand (hand.py, exact fractions, all 2^13 corners of the box; the error is monotone in every given):
offset +-2.21485 mV, gain-only -13.8594/+14.0911 mV, total -16.0551/+16.3059 mV. The stand's ranges equal these except
the lower end of the combined range, -16.0577 (stand, outer bound, sound) vs -16.0551 (true). No disagreement.

## EXPRESSED FAITHFULLY
- The full chain as one flat brick: non-inverting gain 1 + R2e/R1e on (vin + voff + ibp*Rs), minus ibn*R2e; ADC code
  4095*vo1/Vrefe*(1+eg) + offset + resolution + INL; reading = code/4095 V; error = reading - vin. All 14 uncertain
  quantities independent boxes; R2e and Vrefe share the nonlinear coupling exactly (no first-order shortcut).
- Three modes (offset at 0 V; gain with offsets zeroed at 1 V; combined at 1 V) with the page's budgets.
- The "largest tolerance" question via `find` over a named tolerance (separate brick, no modes).

## APPROXIMATED
- Initial tolerance and drift added into one box where they act on the same quantity linearly (voff, ib, ADC gain,
  ADC offset): the source also adds them. Checker: none needed (identical to the source's sum). For R1, R2, Vref they stay
  two separate factors (1+tol)(1+drift), as in reality.
- Drift as a free box +-(tempco*30) per part: equal to the true set if each tempco may have either sign up to its limit;
  unsafe only if the real parts' tempcos were correlated (the page says nothing). Nobody checks this; assumption.
- Bias currents: the page's prose gives Ib and Ios; I read Ibn/Ibp as Ib +- Ios/2 (variant only).
- Reading referred to input by dividing by the NOMINAL gain 5 (the page's RTI definition).
- ADC input range, saturation and quantization are not modelled beyond the page's three ADC offset terms (the page
  doesn't either); the ADC component's `assume` range [-0.1, 5.5] V and the empty ratings are mine (no rating exists in the source).
- The component version: bands (amp vin [0, 1e-5], [1e-5, 0.99999], [0.99999, 1]; ADC vo1 [-0.1, -0.005], [-0.005, 0.005],
  [0.005, 4.96], [4.96, 5.04], [5.04, 5.5]) chosen by me so the arriving ranges fall inside one band. The ADC's
  output is the reading in volts (vrec = code*5/4095) so that input and output have the same dimension and an affine contract applies.

## COULD NOT EXPRESS
- The source's own rule "sum of |sensitivity x error|" cannot be asked for; the stand judges the TRUE worst case of the
  nonlinear law, which is the stricter and different question (that difference is what the table above shows).
- The two figures (offset total, gain total) as ONE requirement "offset + gain x reading": the bound would read vin,
  which also moves the error (the BRICKS.md warns of the lost correlation), so I judged at fixed vin = 1 V instead of
  over vin in [0, 1]; the budget as a function of the reading is not proved over the whole range.
- A sensor stage: the source has none (a 500 ohm source impedance only). It is an amp + ADC chain, not a sensor chain.
- The component version could not keep the input-output correlation across the ADC (the remainder of an affine
  contract is the plain range of out - k*in, so a band's width is paid in the error); the system answered OPEN or
  looser by ~2x on the combined error, never wrong.
- RSS / "probable" error: the page doesn't use it here; not asked.

## TOOL OUTPUT
Command (all runs): `OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand <file>`.
No run was killed. Files out-*.txt are the full outputs.
- brick.json (3 modes), work: REFUTED, `failing_modes: [gain_only_vin1, total_vin1]`, witness Err 16.306 mV (the true corner); about 0.2 s. `--dev`: REFUTED, same failing modes, "ZTL + the independent checker", 56 s.
- mode-offset_vin0 work: EARNED +-2.21485 mV, `how`: "outside ZTL: ZTL left it unbounded (a product of toleranced quantities); interval bound by the stand, every corner checked inside" (the offset verdict is the stand's interval bound, not ZTL's). `--dev` EARNED, same range, 14 s.
- mode-gain_only_vin1: REFUTED (witness 14.0911 mV), 0.5 s; `--dev` REFUTED, 1 s. range-gain_only_vin1 (window +-1 V) EARNED with range [-13.8594, +14.0911] mV, `how` again "outside ZTL ... every corner checked inside".
- mode-total_vin1: REFUTED, 26 s; range-total_vin1 EARNED [-16.0577, +16.3059] mV.
- brick-prose.json: REFUTED, 26 s.
- brick-find.json: EARNED, `proved` 0.00096, `beyond` 0.00097 REFUTED, 2.4 s; `--dev` same, 5 s.
- sys-offset.json: EARNED [-4.227, +4.227] mV (`how`: "ZTL, exact at the corners"), <1 s; `--dev` EARNED. sys-total.json (15 mV), -total20, -total25: OPEN ("the system fails at a point of the components' guaranteed ranges, but those ranges enclose ... not a refutation"); -total35, -total50: EARNED [-32.06, +32.32] mV.
- Work vs --dev: no disagreement anywhere; no STAND FAULT, no BRICK ERROR, no STAND ERROR in the final files. (Earlier iterations of mine had unit/format slips only; the first system try gave remainders of +-5.6 V because my ADC bands were far too wide.)

## DOC GAPS
- BRICKS.md 7d does not say that an affine contract's remainder is the plain range of (out - k*in) over the band, so a band
  costs width x |k - actual slope| in the output; it took trial to see that the error budget needs band widths below the budget.
- Not said how a system's `Err == Vmeas - vin` correlates vin with a contract output from a TWO-stage chain (it worked:
  EARNED at vin = 0 uses the chain of both affine laws), nor whether a system may carry modes (it can't; I used separate files).
- "outside ZTL ... interval bound by the stand" appears for a plain product of two toleranced givens in a law; sec. 4 lists "ZTL, interval reading" for that
  case but not when ZTL leaves it unbounded. The verdict is then the stand's, which the doc's section 9 mentions only in general.
- Section 7b: unclear whether a mode may override a toleranced given by a plain `value` (it works; offsets zeroed this way).
- `find` is "not with modes", so the gain-only question needed a second brick; one could have expected a mode-wise find.
