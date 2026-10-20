# s04 report: register-to-register setup/hold with min/max delays and skew (UCSD CSE140 lecture 10)

## SOURCE
https://cseweb.ucsd.edu/classes/sp17/cse140-a/slides/lec10timing.pdf, CK Cheng, UC San Diego, CSE 140, spring 2017,
slides 34-44. Lecture slides with a worked example (numeric answers on the slides). Trust: moderate. The arithmetic
is checked by my hand script (handcheck.py); the numbers are textbook-style, not a real datasheet, and the source is
slides, not a handbook. The slides do not say how the min/max were obtained.

## WHERE THE UNCERTAINTY COMES FROM
All from the source's own min/max table (slides 34-40); nothing added by me except the reading of skew.
- clock-to-Q tcq in [30, 50] ps: "tccq = 30 ps, tpcq = 50 ps".
- each gate delay in [25, 35] ps: "tcd = 25 ps, tpd = 35 ps" (3 independent gate quantities on the long path,
  1 or 2 on the short path).
- skew sk in [-50, 50] ps: the slide gives "tskew = 50 ps" as a worst case. The two-sided range is MY reading
  (added; the sign is chosen by the worst case in the slides too, so the numbers coincide).
- tsetup = 60, thold = 70: single values in the source, kept exact.
- Tc: the quantity searched (find), 150-400 ps.

## PUBLISHED ANSWER vs STAND
All runs are `work` mode; `--dev` agrees where run (brick, v4, v5, v6).

| question | published | stand | |
|---|---|---|---|
| min Tc, no skew (v1) | 215 ps | proved 215, 214 REFUTED | AGREE |
| min Tc, skew (brick.json, main) | 265 ps | proved 265, 264 REFUTED (witness tcq=50, 3 gates 35, sk=-50, slack -1) | AGREE |
| hold, 1-gate short path, no skew (v2) | violated, 55 vs 70 | REFUTED, sh=-15 at tcq=30, gate=25 | AGREE |
| hold, 2-gate short path, no skew (v3) | satisfied, 80 > 70 | EARNED, sh in [10, 50] | AGREE |
| hold, 2 gates, skew 50 (v4) | violated, 80 vs 120 | REFUTED, sh=-40 at sk=50 | AGREE (the stand's -40 = 80-120) |
| largest skew, 2 gates (v5) | not stated; implied <10 | proved 10, 11 REFUTED | AGREE (derived from the source's formula) |
| whole buffered design, Tc=215 / 214, no skew (v6, v7) | 215 ok | EARNED ss in [0,50], sh in [10,50] / REFUTED ss=-1 | AGREE |

Hand check (handcheck.py, brute force over corners): min Tc 215 (no skew), 265 (skew 50); worst hold slack
-15 (1 gate), +10 (2 gates), -40 (2 gates + skew 50). Same as the stand.

## EXPRESSED FAITHFULLY
- Setup and hold laws as linear equalities of given quantities; every min/max of the source as a range.
- The "worst case" that the slides pick by hand (max on the long path, min on the short path) is found by the stand
  itself from the ranges. Each gate is independent, so a 3-gate path gets [75, 105].
- The smallest period and the largest skew as `find`, with no invented catalog.

## APPROXIMATED
1. Skew modelled as a symmetric range [-50, 50] with the sign chosen by the worst case (my reading). Checked by hand
   (handcheck.py) only.
2. Strict ">" of the slides replaced by ">=" (slack >= 0). Differs only exactly at the boundary: the largest skew is
   reported as 10 ps (works), where the slides' strict inequality would give "below 10". Not checked by anyone.
3. Setup/hold slack is the only model; no jitter and no clock-tree detail (the source has none).
4. Hold was judged in separate bricks from setup (the `find` needs a pass/fail brick and hold is independent of Tc);
   the only combined run is v6/v7. The unused long-path gates still appear in hold-only witnesses (harmless).
5. `find` on integers of 1 ps (grid), so "215" means "215 works, 214 fails", not a continuous limit.

## COULD NOT EXPRESS
- Nothing needed from the source was inexpressible. The gate-level network (which inputs have which path) is not
  modelled; only the two paths' gate counts, as the source reduces it.
- The verdict ">" (strict hold rule) cannot be expressed as `>=`-certificate; see 2 above.

## TOOL OUTPUT
- brick.json: `EARNED`, find smallest Tc, proved 265, beyond 264 REFUTED; 10 tries; real 0.2 s (work), 0.34 s (--dev);
  `checked_by` "ZTL + the independent checker (dev mode)"; no STAND FAULT.
- guaranteed setup slack at Tc=265: ss in [0, 285] ps, `how`: "ZTL, outer range".
- v1..v7: see out_*.txt; each under 0.2 s. v2 REFUTED sh=-15, v3 EARNED, v4 REFUTED sh=-40, v5 proved 10, v6 EARNED,
  v7 REFUTED ss=-1.
- --dev run on brick, v4, v5, v6: same verdicts, no disagreement, no certificates_unconfirmed.
- No errors, no OOM or time-limit kill.

## DOC GAPS
- BRICKS.md does not say whether `ground`/`why` are allowed on a ranged given (they were accepted).
- `find` on a quantity that sits in a ranged given: unclear whether `range` or `value` is replaced; I gave
  `value` ("0") for the searched ones, as in t28, and it worked. For a `smallest` search the brick's `value` is
  irrelevant.
- No example of a brick with `slots: {}` and `catalog: {}` besides t28, and a "conflicts": false note exists only
  at the end of section 8.
- The strict `<`/`>` is documented ("certificates prove only <= and >="), but not that a `find` limit then lands ON
  the boundary for `>=`.
