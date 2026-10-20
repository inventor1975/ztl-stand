# n02 report: largest continuous MOSFET current under five thermal set-ups (IRL3713, DigiKey TechForum worked example)

## SOURCE
- https://forum.digikey.com/t/a-thermal-management-example-part-2-when-datasheets-attack/13252 (with part 1,
  .../a-thermal-management-example-part-one/13243). A distributor's engineering forum article (author rick_1976);
  the inputs are screenshots of the IRL3713 datasheet (IR, 2013), the Bergquist Sil-Pad 900S table and an Aavid chart.
- Trust: the arithmetic is simple and I re-derived all five answers (below) - they hold to rounding. The inputs are
  as good as those vendor pages; two are chart readings ("a bit under 7", 19 C/W), and RDS(on) at hot is the author's
  reading of a normalized curve. Not peer reviewed; no tolerance band is claimed by the source.

## WHERE THE UNCERTAINTY COMES FROM
Honest summary: the source's own uncertainty is thin. It is almost entirely one-sided "MAX" values, and the question
is a worst-case limit, so the worst case is simply "everything at its max". Quantity - range - place:
- RthJC (junction-case, TO-220): [0, 0.45] C/W - IRL3713 datasheet p.1 thermal table, "Max 0.45" (screenshot in source,
  part 2 Fig. 2). The lower end 0 is MINE (the datasheet gives no min); it cannot change a worst-case verdict.
  (The footnote "end of life 0.50" is for D2PAK/TO-262 only, so not applied to the TO-220 chains.)
- RthJA PCB mount (s6): [0, 40] C/W - same table, "Max 40". Lower end 0 mine.
- RDS(on) at Tj_max: [0, 4.9] mohm (175 C) and [0, 4.5] mohm (150 C) - built in the source on the datasheet MAX 3.0 mohm
  (Fig. 6) times the curve factor (Fig. 7), so these are upper bounds. Lower end 0 mine.
- Sink-air, forced air (s2-s4): [0, 7] C/W - source text, "a bit under 7" at 500 ft/min (part 1). Lower end 0 mine.
- Held exact: Ta = 40 C (source's design assumption); interface 0.5 C/W (datasheet TYP, greased) and 2.9 C/W
  (Sil-Pad table, 50 psi, TO-220 column); natural-convection sink 19 C/W (source table); Tj_max 150/175 C (datasheet).
- ADDED BY ME (only in brick_added.json): clamp pressure range [25, 100] psi, pad resistance by `table` over the
  datasheet's five columns, linear between them. The table values are the source's; the pressure RANGE is my invention
  (the source's operating-condition range would be the full 10-200 psi column set; its design point is 50 psi).
  Main brick.json contains none of this.

## PUBLISHED ANSWER vs STAND
Largest ID (A). Stand = "proved" value from `find` (grid step 0.01 A, every value up to it EARNED; the next grid point
REFUTED with a witness). Hand = my sqrt((Tj_max-Ta)/(RDS*sum R)).

| set-up | published | hand | stand brick.json (max values) | stand brick_nominal.json | verdict |
|---|---|---|---|---|---|
| s2 forced, grease, 175 | 58.9 | 58.869 | 58.86 | 58.86 | AGREE |
| s3 forced, pad, 175 | 51.6 | 51.594 | 51.59 | 51.59 | AGREE |
| s4 forced, pad, 150 | 48.6 | 48.598 | 48.59 | 48.59 | AGREE |
| s5 natural, pad, 150 | 33.1 | 33.071 | 33.07 | 33.07 | AGREE |
| s6 D2PAK, 150 | 24.7 | 24.721 | 24.72 | 24.72 | AGREE |

AGREE: the source rounds to one decimal; the stand's proved value is the grid point below the exact limit. The stand
verdict is "EARNED, several limits"; the weakest-of-five is EARNED (every find has a proved value and a REFUTED step
just above it, with a failing point, e.g. s6: ID 24.75 A gives Tj 150.26 C). Because the uncertain parts are one-sided
ranges [0, max], the main brick and the nominal brick give identical limits - the stand's worst-case machinery was not
really exercised by the source's own uncertainty; it only confirms the arithmetic and that the worst corner is the max.

brick_added.json (my invented pressure range 25-100 psi, worst case 3.41 C/W at 25 psi): s2 58.86 (no pad, unchanged),
s3 50.36 (hand 50.368), s4 47.44 (hand 47.443), s5 32.70 (hand 32.700), s6 24.72 (unchanged). NOT COMPARABLE with the
source (it states no such range); it only shows that a pad-pressure range costs about 2.4 % of current at s3.

## EXPRESSED FAITHFULLY
- The series chain and Tj = Ta + I^2 * RDS * (sum of R), for all five set-ups, with the datasheet maxima as ranges.
- "Largest ID that works": five `find` items in ONE brick, each with its own requirement (Tj_k <= limit).
- Units checked ("every law's dimensions agree"); no "outside ZTL" lines in `how`.

## APPROXIMATED
- RDS(on) held constant at its Tj_max value for every ID in the searched range (the real one falls at lower current
  because the junction is cooler). Conservative below the limit, exact at it, so the limit is unaffected. Checked by
  my hand formula only (it uses the same constant).
- Five scenarios share Ta but each has its OWN copies of RthJC, RDS, sink (RJC_s2, RJC_s3, ...): the brick treats the
  same part's tolerance as independent between scenarios. Harmless here (each find reads one chain), unsafe if one
  requirement spanned two chains. Not checked by anyone.
- Lower ends of all ranges set to 0 (datasheet gives only max). Safe for a worst-case limit (monotone), unsafe for
  any "must not be too cold" question.
- Heat-sink 7 C/W (forced) taken as an upper range end from "a bit under 7"; 19 C/W natural convection held constant
  although the real chart is power-dependent (concave: constant is conservative below the limit, exact at it).
- Pad pressure table (added variant only): linear interpolation between datasheet columns = my choice.
- Placeholder given ID_k = 0 in each brick; each find searches [0, 100] A, step 0.01 A (published numbers have 0.1).

## COULD NOT EXPRESS
- RDS(on) as a function of the junction temperature (feedback loop P -> Tj -> RDS -> P) - would be an implicit law with a
  `table`; I removed it by evaluating RDS at Tj_max (valid for a limit, not for "what is Tj at 30 A").
- Power-dependent natural-convection sink (delta-T read off a vendor chart as a function of watts): possible with a
  `table` on P, but I did not digitise the chart; I held 19 C/W.
- The `network` section (BRICKS 7c): not usable. It only returns branch heat flows for a fixed source temperature
  difference; here the unknown is a junction temperature driven by a current-dependent heat source (I^2 * RDS). The chain
  is series only, so no parallel/wall path was involved.
- The source's headline claim (datasheet 260 A needs -196 C ambient, 333 W) was not encoded.

## TOOL OUTPUT
Commands exactly as ordered (`OPENBLAS_NUM_THREADS=1 timeout 900 ~/bin/heavy -m 3G --cores 1 python3 -m ustand.stand ...`).
No run was killed; no BRICK ERROR, STAND ERROR or STAND FAULT.
- brick.json, work mode: verdict EARNED ("several limits ... the verdict is the weakest of theirs"), 10 s;
  checked_by "ZTL (work mode; a refutation's witness recomputed exactly)".
- brick.json --dev: same verdicts and same proved/beyond values for all five, 13.6 s; checked_by "ZTL + the independent
  checker (dev mode)". Work and --dev AGREE.
- brick_nominal.json (all exact values), work: EARNED, 1.4 s, same limits as brick.json.
- brick_added.json, work: EARNED, 4.9 s; limits as listed above. (--dev not run on the two variants.)
- `how` for the finds' judged ranges: "multilinear, exact at the corners" (and one "interval reading, sound, may be wider
  than the truth" for s2 at the shared end). 0 "outside ZTL". Outputs: out_brick.txt, out_brick_dev.txt,
  out_brick_nominal.txt, out_brick_added.txt. Bricks are written by gen.py; hand.py is my check.

## DOC GAPS
- `psi` (and inch/lb) are not in the BRICKS.md unit list; I made pressure dimensionless. `mohm` (prefix m + ohm) worked
  though not shown.
- 7a does not say how several scenarios with different givens fit one find list; I used per-scenario copies of every
  quantity and per-item requirements. The top-level `requirements` is required but is replaced inside every find item -
  I put one (the first scenario's) there without testing whether it can be empty; the doc does not say.
- 7a: the grid is "from + k*precision" and the answer `proved` is the last grid point, not the true limit; the doc does
  not say the limit is only located to within `precision` (here visible as 58.86 vs exact 58.869).
- `table` knots vs a dimensionless "derived" quantity times a unit given (my `Rint == table(...)*Ru`) is not described.
- Table y-values given as bare numbers are dimensionless (3.96 ...), so I multiplied by a 1 C/W given; I did not test
  whether a bare-number table can be assigned straight to a C/W quantity.
