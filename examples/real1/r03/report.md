# r03 report: heat sink rating for a TO-3 transistor at 15 W and 40 W (LibreTexts / Fiore)

## SOURCE
- https://eng.libretexts.org/Sandboxes/radwana_at_wwu.edu/Electronics_(Final)/04:_BJT_Circuits/4.06:_Heat_Sinks
  ("4.6: Heat Sinks", J. M. Fiore, Mohawk Valley Community College, CC BY-NC-SA 4.0; a sandbox copy in Engineering LibreTexts).
- Kind: open-textbook worked example (two parts). Trust: the arithmetic is the plain series-resistance law and I
  recomputed both answers exactly. The inputs are the author's own choice (the Rcs = 0.35 is read off a graph and
  hedged with "approximately"). Weak point: B's 1.53 is 1.525 rounded up (see below). No tolerances in the source.
- Honest note on the problem: this is a deliberately small, linear problem (one equation per application). The
  "uncertainty" and the "choice from a list" are NOT in the source; I added the catalog (invented) and, in a
  side brick, tolerances (invented).

## PUBLISHED ANSWER vs STAND
| | Published | Stand (brick.json, work and --dev) | |
|---|---|---|---|
| A, 15 W: largest Rsa | 7.15 C/W | sinks 6.5, 7.0, 7.15 EARNED; 7.2, 8.0, 9.5 REFUTED (7.2 by 0.75 C) | AGREE |
| B, 40 W: largest Rsa | 1.53 C/W | sinks 1.2, 1.5, 1.525 EARNED; 1.53, 1.6, 2.0 REFUTED (1.53 by 0.2 C) | DISAGREE on the last digit, stand right |

Hand check (exact fractions): A: (175-40)/15 - (1.5+0.35) = 7.15 exactly; B: 135/40 - 1.85 = 1.525 exactly. A 1.53
sink gives Tj = 40 + 40*(1.5+0.35+1.53) = 175.2 C > 175, so the stand's REFUTED is correct; the text's 1.53 is a
round-UP of 1.525 (rounding down to 1.52 would be the safe direction). This is a rounding in the book, not an
error in the physics; the stand's boundary handling (7.15 and 1.525 pass with "<=", exactly at 175.000) agrees
with the exact value. The author's side remarks (which real sink suffices, 700 ft/min air) are NOT COMPARABLE: they
rest on a graph that the source does not give.
Side brick brick_tol.json (my invented tolerances: Rcs +-15 %, Ta in [40,45] C, P +5 %; catalog with extra sinks
6.35, 6.36, 1.19): only A 6.35 with B 1.19 EARNED. Hand thresholds under those tolerances: A <= 6.3515, B <= 1.1927
(worst corner Ta=45, P up, Rcs=0.4025). Stand agrees: 6.35 passes (Tj max 174.977), 6.36 and 1.2 refuted. No
published answer exists for this variant, so it is only a self-consistency check, not a comparison.

## EXPRESSED FAITHFULLY
- Tj = Ta + P*(Rjc + Rcs + Rsa) for each application, Tj <= 175 C, all numbers of the source (Rjc 1.5, Rcs 0.35,
  Ta 40, P 15 and 40), with units (checked: "every law's dimensions agree").
- The question "which Rsa is acceptable" as a pass/fail over a list whose entries straddle the published limits.

## APPROXIMATED
- The question in the source is "find the maximum Rsa" (an inverse problem). The stand only judges given parts, so I
  turned it into a catalog of invented sinks around the published limits (6.5, 7.0, 7.15, 7.2, 8.0, 9.5 and
  1.2, 1.5, 1.525, 1.53, 1.6, 2.0). The threshold is read off the pass/fail pattern, only to the catalog's
  resolution. Not safe in general: a limit between two entries is only bracketed. Checked by me (hand).
- Two applications in one brick via two slots (HSA, HSB), so the 36 "designs" are pairs of sinks and the earned
  ones are the product 3 x 3 of the two pass sets. The designs are independent; no physical coupling. Safe;
  I checked the product by reading the design list.
- Ta, Rcs exact in brick.json although the source itself hedges Rcs. This is the source's own treatment.
- brick_tol.json tolerances are mine, not from any source; unrelated to the published answer.

## COULD NOT EXPRESS
- "Find the largest Rsa" directly (no solve-for-a-parameter; a continuous slot needs an objective and affine
  requirements; I did not try it, since the catalog route gave the answer and the continuous mode is for choosing
  amounts, not for reading a limit).
- The vendor graph behind Rcs (a curve, and the sink's Rsa-versus-airflow curve) and therefore the "700 ft/min"
  remark. Would need tables; not in the source as data.

## TOOL OUTPUT
- Command as prescribed (heavy -m 3G --cores 1), brick.json, work mode: verdict EARNED, 36 designs tried, 27
  failed at nominal, 9 EARNED, 27 REFUTED, 0 undecided; "how": "ZTL, outer range"; ran in about 0.1 s, rc 0.
  Top-level verdict is for the first earned design (A6.5 + B1.2); the pass sets are in the `designs` list (report: all).
- --dev: same 9/27, "checked_by": "ZTL + the independent checker (dev mode)", no STAND FAULT, no unconfirmed
  certificate; about 0.1 s. Work and --dev agree on every design.
- brick_tol.json, 56 designs: work and --dev both 1 EARNED (A6.35 + B1.19), 55 REFUTED; guaranteed Tj A [156.10,
  174.977], B [153.525, 174.885]; "how": "ZTL, exact at the corners". No errors, no OPEN.
- No BRICK ERROR, no limit kill, nothing simplified for the limit. Raw output: out_work.txt, out_dev.txt,
  out_tol.txt, out_tol_dev.txt.

## DOC GAPS
- BRICKS.md does not say how to read the result for `"report": "all"` with several slots (the top-level `design`
  and `verdict` describe the first earned design only; the pass set has to be collected from `designs`).
- The doc says a label field is shown "in the output"; fine, but it does not say that `name` is a safe label name
  (it worked). Also not stated whether a catalog `ground` may be free text such as "invented" (it worked).
- Not stated how a `<=` bound exactly met (Tj = 175.000) is treated; I found out by running (EARNED). One line
  would help.
- A derived requirement-free "which Rsa passes" (inverse) query is not described as unsupported or supported.
