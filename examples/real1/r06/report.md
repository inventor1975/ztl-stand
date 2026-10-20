# r06 report: hypochlorite dilution strength and metering-pump feed rate (CA Water Board handout)

## SOURCE
- California State Water Resources Control Board, Division of Drinking Water, "Example Calculations of Chlorine
  Dosage", Feb 2018 (PDF, URLs in PROBLEM.md).
- A regulator's operator-training handout: equations, two worked dosage examples, a 33-row table of solution strength
  vs bleach volume, a table of feed rates. Trust: the strength table and Table 2 reproduce from first principles to
  4 digits (my python). Eq. 1C does NOT agree with Table 2 (5 %, see below), so the handout is not internally
  consistent. It makes no design claim: the pump and the choice question are mine.

## PUBLISHED ANSWER vs STAND
| item | published | stand / my hand check | verdict |
|---|---|---|---|
| strength of 20 oz in 10 gal | 0.2307 % w/v | 0.2308 % (python, exact fractions) | AGREE (4th digit, rounding) |
| Example 2 feed rate, 40 gpm, 1.5 mg/L, 20 oz | 103 mL/min | stand (point box, scratch_ex2): 103.329 | AGREE |
| Table 2 row 20 oz, 1 mg/L, 10..60 gpm | 17.2 .. 103.4 | python 17.2 .. 103.3 | AGREE |
| Table 2 rows 32/36/40 oz at 1.5 mg/L, 60 gpm | 65.2/58.2/52.4 x1.5 = 97.8/87.3/78.6 | stand (no tolerances, scratch_exact): max 97.765 (32 oz) | AGREE |
| Eq. 1C (no 0.9525 factor) on Example 2 | would give 98.4, handout says 103 | stand with fCl=1 gives different EARNED set (below) | handout INTERNALLY DISAGREES; Table 2 / Eq. 1A side is the physically consistent one (dose as Cl2, strength as NaOCl) |
| which row(s) a pump 8..100 mL/min can use over the box | none published | EARNED: 36 oz, 40 oz (with my tolerances); 32, 36, 40 oz (no tolerances) | NOT COMPARABLE (my question) |

Hand check of the choice verdicts (brick.json, tolerances on): python over all 16 corners of (D, Q, w/w, SG) per row
gives 36 oz: 9.130 .. 92.652 mL/min, 40 oz: 8.242 .. 83.640, 32 oz: 10.240 .. 103.917 (REFUTED, over 100 by 3.917, the
stand's witness overshoot is 3.91684), 44 oz: 7.516 .. 76.267 (REFUTED, under 8). The stand's guaranteed range for
36 oz, [9.13013, 92.6521], equals mine. Stand and hand agree on all 33 rows (31 REFUTED, 2 EARNED).

Variant with Eq. 1C's missing factor (fCl = 1, scratch_eq1c.json): EARNED = 32 oz and 36 oz, 40 oz REFUTED. So a
designer following Eq. 1C instead of Table 2 would accept a row (32 oz) that overruns a 100 mL/min pump by 4 % at the
corner, and reject 40 oz.

## EXPRESSED FAITHFULLY
- Strength from bleach volume: s = V_b rho w/(V_w + V_b), V_b per table row (33 listed items, in mL from oz).
- Cl2 mass balance Q_f = D Q /(0.9525 s), units checked ("units: checked").
- Flow and dose ranges; the choice of one row; "for every value in the box" is what the stand proves.
- Exact unit constants (US gal, US fl oz) as exact decimals.

## APPROXIMATED
- Bleach strength +-4 % and SG +-2 % are my ADDITION (handout has none); they are what make 32 oz fail. Anyone can
  check: change the two "tolerance" lines; scratch_exact.json is the zero-tolerance run.
- Pump 8..100 mL/min is invented; the verdicts depend on it directly. Checked by the reader of the requirement text.
- Additive volumes (reproduces Table 1 to 4 digits); no bleach decay in storage; no pump-accuracy tolerance.
- Operating box = full cross product of flow 10..60 gpm and dose 1.0..1.5 mg/L (handout's own columns/examples, not
  stated as an envelope). The stand treats Q and D as independent; if real dose is set per flow, the box is wider than
  reality (conservative).
- `report: "all"` used so every row gets a verdict (no objective, no ranking).

## COULD NOT EXPRESS
- Nothing in the handout was left out. Not expressible and not attempted: a pump catalogue with real vendor data,
  storage-tank decay of hypochlorite, and the handout's polynomial fits Eq. 1B/2B (strength vs oz; I used the physics
  instead, and the table values agree).

## TOOL OUTPUT
- work mode (brick.json): `designs_count {"REFUTED": 31, "EARNED": 2}`, EARNED 36 oz and 40 oz, `how`: "ZTL, outer
  range", guaranteed Qf [9.13013, 92.6521] mL/min (36 oz). units: "checked: every law's dimensions agree".
  `failed_at_nominal: 11`, `judged: 22`. No errors, no warnings. Wall time about 0.1-0.2 s per run (3 GB / 1 core cap
  was never an issue); the progress line said "0 s".
- --dev: same counts and same two EARNED designs; `checker`: "every corner of the tolerance box recomputed exactly and
  inside; exact ranges equal; definitions bounded by the checker's own interval arithmetic". No STAND FAULT.
- scratch variants (work mode): zero tolerance -> EARNED 32, 36, 40 oz ("ZTL, exact at the corners", guaranteed
  [10.8628, 97.765] for 32 oz); Example 2 point box -> Qf = 103.329; fCl = 1 -> EARNED 32, 36 oz.

## DOC GAPS
- BRICKS.md says `"stand": "ztl-stand/1"`; the example bricks I opened say `"universal-stand/1"`. Both seem to be
  accepted (mine ran with ztl-stand/1) but the doc never says so.
- BRICKS.md says a quotient/product of toleranced givens is bounded by the stand and labelled "outside ZTL" (GAPS Z2).
  My `Qf == D*Q/(fCl*SW)` came back as "ZTL, outer range" with a judge_log "interval reading, sound", not "outside
  ZTL". Either the doc is stale or my law fell in a different class; the doc does not say which.
- `failed_at_nominal` and `judged` counts are not explained (11 of 33 rows failed at nominal and were still all listed
  as REFUTED with witnesses; I had to infer that).
- `rests_on: "ZTL disposition OPEN: tolerances are the catalog's (datasheet) word"` appears for an EARNED design whose
  tolerances came from MY givens, not a catalog; BRICKS.md does not say what it means or whether it is a weakness.
- With `report: "all"` the top-level `verdict`/`design`/`guaranteed` show only the first EARNED design; the other
  EARNED designs' ranges are not listed (only "EARNED"). I recomputed the second one's range by hand. Not stated.
- `define` mixes a catalog field with givens fine; the doc says defines are "expanded in place", but does not say
  whether a define with a division by a toleranced given is the recommended way versus a derived quantity (it worked).
