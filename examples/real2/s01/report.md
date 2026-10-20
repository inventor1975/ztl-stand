# s01 report: O-ring face seal, squeeze and gland fill over stated tolerances

## SOURCE
https://jlcmc.com/blog/o-ring-groove-design-guide, section 11 (worked example) with formulas and limits from sections 4 and 6. A supplier's blog, unsigned. Published numbers are internally consistent: I recomputed 20.69 %, 29.03 %, 83.68 % and they match the text's 20.7, 29.0, 83.7. The limits (20-30 %, 60-85 %) are labelled by the source as starting points, not specifications. Trust: arithmetic yes, limits moderate. The page text lost its formulas, so the fill formula is my reconstruction (it reproduces two published numbers).
Note: this is squeeze (an interference measure), not a plain gap between faces; it is the same kind of dimension chain (a gland height against a ring cross-section).

## WHERE THE UNCERTAINTY COMES FROM
All from the source's own table in section 11:
- d, O-ring cross-section: 2.90 to 3.10 mm.
- h, groove depth: 2.20 to 2.30 mm.
- w, groove width: 4.10 to 4.30 mm.
Nothing added in the main brick (brick.json). Added by me only in brick_swell.json / brick_find.json: swell 0 to 0.10 (the source's illustrative 10 % swell, a case, not a tolerance).

## PUBLISHED ANSWER vs STAND
| claim | published | stand (work) | |
|---|---|---|---|
| squeeze range | 20.7 to 29.0 % | [20.6897, 29.0323] % | AGREE |
| max fill | 83.7 %, below 85 % | 83.6771 % | AGREE |
| min fill | not given | 66.7866 % | NOT COMPARABLE (source gives no number) |
| squeeze within 20-30 %, fill within 60-85 % | implied pass | EARNED | AGREE |
| 10 % swell: fill could exceed 90 % | exceeds 90 % | brick_swell.json (swell in [0,0.1], fill*(1+swell) <= 90): REFUTED, witness d=3.1, h=2.2, w=4.1, swell=0.1, value 92.0448 % | AGREE |
Control: squeeze bound set to 29.0 (the published rounded number) in brick_tight.json: REFUTED at d=3.1, h=2.2, overshoot 0.0323 %. Right, since the exact maximum is 29.0323 %.
Extra: brick_find.json, largest swell keeping fill <= 85 % (my criterion): proved 0.0158 (fill 84.9992 %), beyond 0.0159 REFUTED. Hand check (python): 85/83.6771 - 1 = 0.01581. AGREE.
Hand check of the main numbers by enumerating all corners in python: squeeze 20.6897..29.0323, fill 66.7866..83.6771. Identical to the stand. No disagreement.

## EXPRESSED FAITHFULLY
- The three ranges as `range` givens in mm, exactly as in the table.
- Squeeze as `1 - h/d` (algebraically (d-h)/d, written so each variable appears once, which keeps the interval reading exact), fill as `pi*d*d/(4*w*h)`.
- The three source limits as requirements. Units mm, % checked by the stand ("every law's dimensions agree").

## APPROXIMATED
- `(d-h)/d` rewritten as `1 - h/d`: equal as functions; ZTL's interval reading of the original would use d twice and widen. Checker in --dev recomputed corners, so it is covered.
- pi: the stand uses a bracket 1e-15 wide. Harmless here (margins are tenths of a percent).
- Fill formula reconstructed (assumed above); checked against two published numbers.
- Empty `slots` and `catalog` ({}): accepted by the stand, there is no choice in this problem.
- Swell variant: `fill*(1+swell)` is my law, and in brick_find the stand bounded it "outside ZTL" (its own interval bound, every corner checked). Not ZTL's verdict.

## COULD NOT EXPRESS
- The source's "choice" is not there; no part list. Stretch, temperature, thermal expansion, groove corner radii are named by the source but without numbers, so not modelled.
- "Approximately" limits (20-30 %, 60-85 %) are soft; the stand needs hard bounds, so I took the end values.

## TOOL OUTPUT
- brick.json, work mode: EARNED. guaranteed squeeze [600/29, 900/31] %, fill [~66.7866, ~83.6771] %; how: "ZTL, outer range" for both. Run time "0 s" per the stand.
- brick.json with --dev: EARNED, "every corner of the tolerance box recomputed exactly and inside; exact ranges equal". Work and dev agree. No STAND FAULT.
- brick_tight.json: REFUTED (witness above). brick_swell.json: REFUTED. brick_find.json: EARNED find, proved 79/5000.
- No errors, no run killed by limits (all well under 3G, 1 core).

## DOC GAPS
- BRICKS.md does not say whether `"slots": {}` and `"catalog": {}` are allowed for a problem with no choices; it worked, but I had to try it.
- Nothing says that writing `(d-h)/d` versus `1 - h/d` changes how tight the interval reading is; only the "quotient of toleranced quantities" paragraph hints at it. I wrote the second form on my own judgement and did not test the first.
- A percent unit for derived quantities works (values come back in %), but the doc lists `%` only in the unit list, with no example for a dimensionless ratio expressed in %.
