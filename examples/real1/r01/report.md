# r01 report: worst-case output accuracy of an adjustable regulator with 1% divider (TI SLVA423)

## SOURCE
- Robertson, "Effect of Resistor Tolerances on Power Supply Accuracy", TI Application Report SLVA423 (2010),
  https://www.ti.com/lit/slva423 . Manufacturer application note, freely readable, example in Section 4
  (TPS79901, 3.3 V and 1.8 V rails). Trustworthiness: the formula is exact algebra, but the printed numbers use a
  stated small-T approximation (drops 1+-T denominators) and then ADD the device accuracy linearly. So the
  published number is a first-order estimate labelled as maximum error. (A WebFetch summary of the page was wrong
  in its details - invented example values; I used the PDF text only.)

## PUBLISHED ANSWER vs STAND
| | published | exact worst case (by hand, python Fractions) | stand (work and --dev) |
|---|---|---|---|
| 3.3 V rail, total | +-2.28% | +2.303% / -2.252%  (Vo in [3.22569, 3.37599] V) | claim Vo within +-2.28%: REFUTED, witness R1 +1%, R2 -1%, Vref +1%, Vo = 3.37599 V (overshoot 0.000751 V) |
| 1.8 V rail, total | +-1.674% | +1.688% / -1.661%  (Vo in [1.77010, 1.83039] V) | claim within +-1.674%: REFUTED (Vo = 1.83039 V, overshoot 0.000253 V) |
| looser bound +-2.31% / +-1.69% (exact worst case just inside) | - | holds | EARNED, guaranteed ranges equal my hand values to all printed digits |
| resistor part alone, 3.3 V | +-1.28% | +1.290% / -1.264% | (not asked separately) |

Verdict: **DISAGREE, narrowly.** The published +-2.28% / +-1.674% are exceeded on the positive side by ~0.02 and
~0.014 percentage points (about 0.75 mV on 3.3 V; 0.25 mV on 1.8 V). The cause: the note's own approximation
(1+T ~ 1-T ~ 1, and linear addition of the two 1% terms; the exact product is (1.01)(1+2T/(1-T)(1-Vref/Vo))). Checked by
hand (python, Fractions): 1.01*(1+ r*1.01/0.99)*1.193 = 3.3759913 V > 3.3*1.0228 = 3.37524 V. The stand is right,
the printed number is a rounded first-order estimate; the note's qualitative claim (error shrinks as Vo -> Vref) is
confirmed (2.30% vs 1.69%). Negative side: the published bound holds (-2.252% inside 2.28%; -1.661% inside 1.674%).
Extra tightness probes (scratch): Vo within [3.2256, 3.3760] -> EARNED; within [3.2257, 3.3759] -> REFUTED
(witness 3.22569, overshoot 5.5e-6 V) - so the stand's ranges are not loose here.

## EXPRESSED FAITHFULLY
- Vo = (1 + R1/R2)*Vref (the note's Eq. 1), R1, R2, Vref with +-1% box, "for all" values in the box.
- The two rails as two modes with different R1 value (nominal ratio), same part and tolerances.
- Both published claims as requirements `within`.

## APPROXIMATED
- Device accuracy +-1% turned into Vref +-1% (relative). Not checked by anything; it is my reading of "rated
  accuracy". If the datasheet accuracy was meant to include something else, the result changes. Unsafe in the
  sense that it is an interpretation, not a rounding.
- Absolute resistor values (R2 = 10 kOhm, R1 non-standard, 6 decimals) - only the ratio matters; ratio error
  from rounding R1 is < 1e-10 relative, irrelevant. Checked by hand.
- Statistical (RSS) analysis is not in this note; nothing to compare there.
- Strictly: "published bounds" brick uses decimal bounds 0.0228 / 0.01674 as given; the note's 1.674% for rail B is
  0.674% + 1% printed with rounding.

## COULD NOT EXPRESS
- Nothing needed from the note failed to fit. Not tested: a choice among catalog parts (the note has none); the
  slot catalog is a single item. Resistor TC, ageing, bias current (note only mentions them).

## TOOL OUTPUT
- brick.json (published claims), work mode: `REFUTED`, "failing_mode": "rail_1v8", witness R1=5138.89, R2=9900,
  Vref=1.20493, Vo=1.83039, overshoot 0.000253253 V. Only the first failing mode is reported; the 3.3 V mode
  failing was seen by running it as a separate scratch brick (REFUTED, Vo=3.37599, overshoot 0.000751313 V).
  The "checker" line: the violating point recomputed exactly.
- brick.json with --dev: same REFUTED, "checked_by": "ZTL + the independent checker (dev mode)"; no STAND FAULT.
- brick_exact.json (bounds 2.31% and 1.69%), work: EARNED; --dev: EARNED, no disagreement. `how`: "ZTL, outer range"
  for Vo in both modes; `guaranteed` Vo [3.22569, 3.37599] and [1.7701, 1.83039], equal to my exact hand values.
- No BRICK ERROR / STAND ERROR; no "units: not checked" line. Run time reported as 0 s; wall ~0.05-0.06 s per run
  via ~/bin/heavy (no limit hit). Files: out_*.txt in this folder.

## DOC GAPS
- Not stated that an empty `requirements` list plus `modes` is fine (it worked); not stated that `slots` may not
  be skipped (I used a single-item catalog for the device) - I did not test empty slots.
- A mode overriding a `given` that has a `tolerance` must repeat the tolerance (I did; unclear what happens if
  omitted).
- With modes, REFUTED reports only the first failing mode; the doc does not say whether other modes also fail
  (I had to split the brick to know).
- Unclear how decimals such as the requirement bounds are printed back (fractions like 80619/25000) - fine but
  surprising.
- "ZTL, outer range" in `how` for a product of two toleranced quantities: BRICKS.md says outer range may be wider
  than the truth; here it was exact (checked).
