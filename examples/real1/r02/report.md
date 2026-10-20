# r02 report: package / heatsink choice for a linear regulator, worst-case Tj

## SOURCE
ON Semiconductor application note "Thermal Management for Linear Regulators" (K. O'Malley, 1999),
https://www.thierry-lequeu.fr/data/SR006AN.pdf (mirror). Manufacturer app note, worked examples with step-by-step numbers.
Trust: moderate. The arithmetic of ex.1 is right (checked). Ex.2 states 200 mA but computes with 250 mA (1.83 W instead of
1.467 W), so its 35.5 C/W is for a different current than stated; the dual-output example also uses 12 V against a 10 V
Vin_max. The heatsink curve value (about 10 C/W) is not given numerically; I inferred it. Details in PROBLEM.md.

## PUBLISHED ANSWER vs STAND
| Claim | Published | Stand (work mode, brick.json) | Verdict |
|---|---|---|---|
| Ex.1: TO220 ok | yes (PD 1.0625 W, limit 61.2 C/W) | TO220 EARNED in mode Vin<=10 (standalone brick_ex1only.json: Tj worst 138.1 C by my hand calc) | AGREE |
| Ex.1: SO14 (125), PDIP (100) fail | fail | both REFUTED, witness over by 67.8 C / 41.25 C | AGREE |
| Ex.2: bare TO220 fails at 12 V | fails (needs sink) | REFUTED in mode ex2_Vin12, over by 8.35 C (hand: 85 + 50*1.467 = 158.35) | AGREE |
| Ex.2: AAVID 504222 sink works | works | the design with RthJA 13.521 +-20 % EARNED (but that value is MY reading of the curve) | AGREE, weak: input is mine |
| Ex.2: limit RthJA 35.5 | 35.5 | with the stated 200 mA the stand's line is between 44 (EARNED) and 45 (REFUTED), matching my hand limit 44.3; with the note's own 250 mA (brick_published_arith.json, all other values at the corner) 35.5 EARNED, 36 REFUTED, hand limit 35.58 | AGREE with the note's arithmetic; DISAGREE with its stated inputs. Hand check: the stand is right, the note's 35.5 does not follow from 200 mA |
Overall chosen design (cheapest holding in both modes, with my invented prices): the 44 C/W probe item; the realistic one is the TO220+AAVID. The "cheapest" is an artifact of invented prices, not a finding.

## EXPRESSED FAITHFULLY
- P = (Vin-Vout)*Iout + Vin*IQ and Tj = Ta + P*Rth, Tj <= 150 C.
- Package thermal resistances 50/125/100 C/W as exact catalog values.
- Two operating cases as two modes (Vin_max 10 V and 12 V), the design must hold in both.
- Worst case is now a proof over the box (ranges), instead of the note's single corner.

## APPROXIMATED
- Ranges for Vin, Vout, Iout, Ta: the note gives only the worst end; I invented the other end (does not change the worst case; nobody checks it; safe for the verdict, but the "box" is not the source's).
- IQ as range 1.7..2.25 mA (from the curve readings; the note uses 2.25 for all).
- Heatsink: the note gives a curve, not a number. I used one fixed total RthJA 13.521 C/W +-20 % (my guess; the tolerance is my invention). Not checked by anyone; any value below 44 passes, so the verdict is insensitive to it, but the "AAVID works" agreement carries little weight.
- Packages and sink combined in ONE catalog (the combination "TO220 + sink" is a single item with a total RthJA) instead of series RthJC+RthCS+RthSA with a heatsink slot. Safe here; loses the structure.
- Prices invented only to give the stand an order.
- Boundary probe items 44/45 (and 35.5/36 in the scratch brick) are mine.
- Units: no "not checked" message appeared in the output, so I take units as checked (the output has no explicit units line either way).

## COULD NOT EXPRESS
- The heatsink performance curve (temperature rise vs dissipated power, nonlinear): only a single resistance. A `table(...)` with the true curve would be possible but the curve is only a figure I cannot read numerically.
- Dependence of IQ on temperature and load (IQ is just a range here, not linked to Ta or Iout).
- Dropout limit (Vin must exceed Vout + dropout): not in the note, not modelled; a Vin of 7 V with Vout 5.2 V would be unphysical for some parts.
- The dual-output and copper-foil examples: not attempted.

## TOOL OUTPUT
- brick.json, work mode: verdict EARNED (one design reported, cheapest by my prices), 6 designs tried, 0 undecided, 4 REFUTED, 2 EARNED; "how": "ZTL, exact at the corners"; time "0 s" in the progress line, rc 0, nothing killed by the limit. Exact output in out_work.json.
- brick.json --dev: same verdicts for all 6 designs (REFUTED, REFUTED, REFUTED, EARNED, REFUTED, EARNED); checked_by "ZTL + the independent checker (dev mode)"; no STAND FAULT; out_dev.json.
- brick_ex1only.json (no modes): EARNED, designs: SO14 REFUTED, PDIP REFUTED, TO220 EARNED, rest EARNED.
- brick_published_arith.json (250 mA, point values): SO14, PDIP, bare TO220 REFUTED; 35.5 EARNED; 36 REFUTED (over by 0.772 C; hand 85+36*1.827 = 150.77).
- Witness values all match my hand calculations (158.35, 151.015, 149.548, 138.125).
- No errors, no OPEN. Note the first scratch variants were run with the same limit command.

## DOC GAPS
- "report": "all" and "conflicts": false are described only in prose; fine. With modes and a cheapest-first objective, the single "design" reported is the cheapest, and with report all the per-design list shows only the FIRST failing mode, so the TO220 failing in ex.2 but passing in ex.1 is visible only through the mode name (okay, but I needed a second brick to see ex.1 alone).
- BRICKS.md does not say whether a mode that overrides a range for one given is allowed to give only `range` (it worked).
- It is not said that output has no "units:" line when all units check; I had to infer.
- No guidance for a physical curve given only as a figure (what to do: table with guessed knots, or a single value).
