# k01 report: worst-case Vout of an adjustable regulator, TI AN-1378 (Vref + feedback divider)

## SOURCE
TI Application Report SNVA112A (AN-1378), rev. May 2013, https://www.ti.com/lit/pdf/snva112. Manufacturer application note;
Tables 1 (worst-case error) and 5 (largest R2 for a given Iadj error). Trust: the method is plain interval arithmetic and
I could recompute it, so it is checkable. Table 1 is NOT exactly the worst case of its own Eq. 1/2/3 (see below) and
has one apparent misprint (3.3 V, Vref +-5 %, R 0.5 %: 2.64, repeated from the +-2 % row). Table 5 is a one-line formula.
Full problem and numbers: PROBLEM.md.

## WHERE THE UNCERTAINTY COMES FROM
All from the source, none added:
- Vref = 1.275 V, +-0.5 / 1 / 2 / 5 % : axis of Table 1 (rows), nominal from its caption.
- R1, R2 (17 k, 27 k), +-0.5 / 1 / 5 %, independent each: columns of Table 1. (17 k / 27 k themselves are my choice of an
  ideal pair for exactly 3.3 V; only the ratio matters.)
- Iadj 0.01 / 0.1 / 1 / 10 uA, exact values: Table 5 rows (the note gives no tolerance on Iadj, so none is modelled).
Mine, not tolerances: the +-3 % window of brick.json, the ordinal "cost" ranks 1..4 / 1..3 (the source has no prices;
they only order the search), the band edges of the divider component.

## PUBLISHED ANSWER vs STAND
Files: brick.json (12 designs, flat), brick_find.json (inverse of Table 1), brick_iadj.json (Table 5), brick_system3.json
(chain as components), brick_flat_v2.json (flat, rewritten law). hand.py = my own exact recomputation of all 72 cells.

1. Which of 12 (Vref grade x R grade) combinations keep 3.3 V within +-3 %. Published Table 1 (3.3 V block): passing
   cells (<=3 %) are (0.5,0.5) (0.5,1) (1,0.5) (1,1) (2,0.5); failing: (2,1)=3.29, all 5 % cells, (x,5 %) columns.
   Stand: EARNED exactly those 5, REFUTED the other 7. **AGREE** (work and --dev identical).
2. Inverse of the table, 3.3 V, R +-1 %, window +-3.29 % (published: Vref +-2 %): largest Vref tolerance proved 2.02 %
   (beyond 2.03 % REFUTED). Window +-2.28 % (published: Vref +-1 %, R +-1 %): largest R tolerance proved 1.02 % (beyond 1.03 %).
   My exact hand bisection: 2.026 % and 1.021 %. Stand = hand. Published 2.0 % / 1.0 %: **DISAGREE slightly, the stand is right**:
   hand.py shows the printed Table 1 is never lower than the exact worst case of Eq. 1 with independent +-boxes; it is
   higher by 0.001..0.025 pp (R 0.5 %), 0.002..0.055 pp (R 1 %), 0.03..0.28 pp (R 5 %). E.g. 3.3 V, 2 %, 1 %: printed 3.29,
   exact 3.26. The table is conservative and its method (maybe rounded or linearised resistor limits) is not stated.
   Direction of the error is safe; I could not reproduce its formula (tried three variants).
3. Table 5 (Iadj): six cells, largest R2: stand proved 330 ohm, 3.3 k, 33 k, 330 k (0.1 % at 10/1/0.1/0.01 uA), 16.5 k
   (0.5 %, 1 uA), 33 k (1 %, 1 uA); `beyond` = +1 ohm REFUTED each time. **AGREE, exactly** (also --dev). This is a linear
   one-liner (Iadj*R2/Vout <= share), so it tests the find, not the physics.
4. Chain as components (reference component -> divider component), same 12 candidates, window +-3 %: EARNED the cheapest
   candidate, (Vref 1 %, R 1 %), guaranteed Vout [3.22717, 3.37445]; the cheaper ones are OPEN, not refuted (a system
   cannot refute). Flat brick, same law form (brick_flat_v2): (1,1) EARNED [3.2273, 3.37432] and the same 5 combos earned.
   Verdict **AGREE**; range: system wider by 0.00013 / 0.00013 V (band edges 0.0001 V outside the arriving range).
   Hand: [3.2274, 3.3743]. (The system answer `optimal: false` is a limit of the format, the flat says optimal: true.)

## EXPRESSED FAITHFULLY
Eq. 1 with three independent toleranced givens (brick.json uses the printed form Vout == Vref*(R1+R2)/R1); the 12-way
choice as two slots with listed items; the find over a tolerance named by a given quantity; Table 5 as six scenarios in one
find list.

## APPROXIMATED
- R1=17 k / R2=27 k: ideal pair, no E-series rounding (the source's table also assumes none). Safe for this comparison.
- "cost" ranks and +-3 % window are mine. They decide only which combination is reported first; the verdict per combination
  does not depend on them.
- Chain: the feedback is a LOOP in the real regulator (Vout feeds back to the error amp). I cut it into
  reference -> (R1,R2 gain) -> Vout, because feedback between siblings is refused. Exact here, since the algebra of Eq. 1 is a
  one-way product.
- Divider component bands (1.2 | 1.2494 | 1.2622 | 1.2686 | 1.2814 | 1.2878 | 1.3006 | 1.35 V) were TUNED to the Vref ranges of the
  four grades after two failures (see TOOL OUTPUT). That is tuning to the answer; a user without that knowledge would get OPEN.
  The reported range is therefore a slightly outer one. Checked by --dev and by hand.
- Table 1's interpretation (max deviation from nominal) is mine; I computed the same quantity (max of |Vmax/Vnom-1|, |Vmin/Vnom-1|).

## COULD NOT EXPRESS
- The feedback loop itself (regulation as a fixed point) and Iadj in the same brick as the resistor tolerances with R2 scaled
  to a small value (Table 5 is separate from Table 1 in the source too; I did not couple them).
- Table 4 (six-sigma, statistical) is a probabilistic claim; not expressible, not attempted.
- A continuous catalog was not used: the source's quantities are tolerance grades (discrete) or a find; no continuous amount.

## TOOL OUTPUT
- brick.json (work): EARNED, 12 designs, 5 EARNED / 7 REFUTED, under 1 s. --dev: identical split, `checked_by` "ZTL + the
  independent checker". Every EARNED has "how": ZTL certificate (1 piece). Its guaranteed ranges for the printed law
  form are wider than exact (e.g. (1,1): [3.2023, 3.399] vs exact [3.2273, 3.3743]; the upper end 3.399 is just the bound).
- brick_flat_v2.json (law `Vref*(1 + R2/R1)`, each toleranced quantity once): same 5/7 split, ranges equal my exact corners.
- brick_find.json: EARNED; tv proved 0.0202 (beyond 0.0203 REFUTED), tr proved 0.0102 (beyond 0.0103 REFUTED); work 0.2 s,
  --dev same numbers.
- brick_iadj.json: EARNED; proved 330 / 3300 / 33000 / 330000 / 16500 / 33000 ohm; work and --dev identical.
- Components, first try (comp_div.json + comp_ref.json, single band 1.2..1.35): all 12 OPEN. Cause visible in out_fx.txt: the band's
  Vout range is wide ([3.190, 3.411] V, about +-3.3 %) and the affine remainder [-0.1875, +0.189] V is as wide as the band, not ~+-0.02 V as by hand
  (e = Vr*(G-k) with Vr in [1.245,1.305]); so the affine contract did not tighten anything in this case.
- Second try, finer bands cut at the arriving ranges, divider law `Vr*(R1+R2)/R1`: only (0.5 %, 0.5 %) EARNED; the 4 other
  combinations that the flat brick earns stayed OPEN. Two causes I separated by experiment: (a) per-band ranges of that law form are
  outer (interval reading, R1 twice) -> fix by writing `Vr*(1 + R2/R1)`; (b) a band whose EDGE coincides with the arriving range's
  edge is counted as touched, so the hull widens to the neighbours -> fix by edges 0.0001 V outside. After both, brick_system3.json: EARNED
  (Vref 1 %, R 1 %) in 0.37 s; --dev agrees (same verdict and range). The 7 cheaper candidates OPEN.
- No STAND FAULT, no BRICK ERROR, no STAND ERROR in the final runs. No run hit the memory/time limit.

## DOC GAPS
- 7d: not said that a component's ranges follow the READING of the law (written as `Vr*(R1+R2)/R1` vs `Vr*(1+R2/R1)` gives
  different guaranteed ranges, here the difference decides OPEN vs EARNED). Section 4 says "outer range" exists; section 7d says
  nothing about it, and a user cannot see it in the component output.
- 7d: that a band edge equal to an arriving range's end counts as touched (hull widens); said "bands the arriving range
  touches" only.
- 7d: a component with `"inputs": {}` (a source such as a reference) works; not mentioned.
- 7d: when the combinations are all OPEN the output shows only a truncated "why" (cut at the word "requirement" in the first lines);
  I needed a hand-built fixed-design system (out_fx.txt) to see the ranges. A component-level view per combination would help.
- 7d: affine contract remainders can be as wide as the band (a dependency loss) with no warning; "PROVED" holds but gives nothing.
- 7a: `find` with a tolerance named by a given quantity worked as documented; "tolerance may NAME a given" is in section 1 only.
