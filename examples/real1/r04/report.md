# r04 report: Deep groove ball bearing selection for a radial + axial load (JTEKT/Koyo worked example 6)

## SOURCE
- https://koyo.jtekt.co.jp/en/support/bearing-knowledge/5-7000.html , "Applied calculation examples", Example 6 (JTEKT/Koyo
  manufacturer's technical guide). Details and the numbers used: PROBLEM.md.
- Trust: moderate. The method is standard (ISO 281). The text reproduces and my recomputation confirms the quoted figures
  (required Cr 58 700 N from P = 6080 N; e = 0.283, Y = 1.54 for 6309; L10h about 11 500 h for 6308). Weak points: the page puts
  several results into images I could not read (the 6309 life itself), and the 6309 dynamic rating is not stated in the text (see
  APPROXIMATED, item 1). Distributor catalogues disagree with the page's rating generation.

## PUBLISHED ANSWER vs STAND
| | Published | Stand (work mode) |
|---|---|---|
| Choice | 6309 is the smallest 63-series bearing meeting 15 000 h | EARNED design: 6309; "optimal: true, every cheaper design was refuted" |
| 6308 | L10h about 11 500 h, fails | REFUTED, witness overshoot 3505.87 h -> L10h = 11 494.1 h |
| 6309 life | not readable (image); required Cr > 58 700 N | guaranteed L10h = 18 283.4 h (point value, no tolerance) |
| 6307 | not published | REFUTED, L10h = 6908.7 h |

**AGREE** on the selection and on the 6308 life (11 494 vs "about 11 500"). Hand check (own python: ISO table interpolation,
P = 0.56*Fr + Y*Fa, L10h = (Cr/P)^3 * 1e6/(60 n)): 6307 6908.7 h, 6308 11 494.1 h, 6309 18 283.4 h, identical to the stand to the
digit shown. The agreement on 6309 holds only with my inferred Cr = 61.1 kN; with the distributors' 48.9 kN, 6309 would give
about 9 400 h and fail, and the published conclusion would be impossible, so the inference is consistent with the source but
not confirmed by it.

Extra runs (my additions, no published answer), load tolerance on both Fr and Fa:
- plus/minus 5 %: 6309 EARNED, guaranteed L10h in [15 493.8, 22 256.4] h. Hand check of the box corners: minimum 16 094 h, so the
  stand's bound is sound but wider than the truth (an outer range), still enough to EARN.
- plus/minus 10 %: all three REFUTED; 6309 fails with overshoot 734.095 h -> 14 265.9 h; my own corner/grid search of the box gives
  the same minimum 14 265.9 h (at Fr and Fa both +10 %). Correct.

## EXPRESSED FAITHFULLY
- The selection among three catalogue items (slot with listed items), objective minimise bore.
- Equivalent load with the Fa/Fr > e branch (`if`), X = 0.56 constant, e and Y by linear interpolation tables (`table`) of
  f0*Fa/C0r, the cubic life law (`pow`), unit conversion by the stand (rpm, h, kN, N).
- The requirement L10h >= 15 000 h.
- Units checked by the stand ("every law's dimensions agree").

## APPROXIMATED
1. 6309 Cr = 61.1 kN is **inferred** (x1.25 from the distributor's 48.9 kN), not published. Nobody checks it; it is the weakest
   point and decides the published answer. A second ground: the source itself says Cr(6309) > 58.7 kN.
2. The source's sizing shortcut (P = 6080 N with a guessed Y = 1.6, then verification) is not modelled; the brick evaluates the
   exact equivalent load for each candidate directly. Both lead to the same choice here. Safe; stand judges it.
3. The e/Y table values are the standard ISO table, checked against the source's two interpolated examples (0.283/1.54 and
   Y 1.82) but I did not see the source's own table. X is held at 0.56 (true for this table whenever Fa/Fr > e).
4. Catalogue values are taken exact (no tolerance); real ratings are nominal figures. The 5 %/10 % load tolerances are my
   extension only.
5. 6307 added by me (Cr by the same x1.25 inference).
6. "Cost" = bore in mm (a proxy for size).

## COULD NOT EXPRESS
- Nothing needed for the nominal problem. Not modelled (not in the source): reliability factors, the alpha-ISO modified life,
  clearance, a load spectrum.

## TOOL OUTPUT
- Work mode (default): `verdict EARNED`, design 6309, `designs_tried 3, failed_at_nominal 2, judged 1`; how: "ZTL, interval reading
  of the definition (sound, may be wide)". 0.09 s wall (limit 3G/1 core, never close). Note: 6307 and 6308 were dropped at the
  nominal point before ZTL judging (`failed_at_nominal`), and their REFUTED witnesses were recomputed exactly by the stand.
- `--dev`: same verdicts, `checker: every corner of the tolerance box recomputed exactly and inside; exact ranges equal;
  definitions bounded by the checker's own interval arithmetic`. 0.08 s. Work and dev AGREE on all four bricks (nominal, 5 %, 10 %).
- Tolerance variants: 5 % EARNED (work and dev), 10 % REFUTED (work and dev), both about 0.1 s.
- First attempt failed: `BRICK ERROR: 'Pr == if(Fa > (table(...))*Fr, ...)' is not a readable expression`. See DOC GAPS.
- No kill, no STAND FAULT, no STAND ERROR. Outputs in out_work.txt, out_dev.txt, out_brick_tol5*.txt, out_brick_tol10*.txt.

## DOC GAPS
1. A `table(...)` placed inside the condition of an `if(...)` (directly or through `define`) gives the BRICK ERROR "is not a
   readable expression" with no reason. BRICKS.md says tables compile to an `if` chain, but does not say that a table
   cannot nest in an `if` condition. Workaround (used): compute the table value as its own derived quantity
   (`ee == table(zz, ...)`), then write `Pr == if(Fa > ee*Fr, ...)`. I confirmed a table in a define works when it is used as
   `ee == e` (outside `if`). The same error text appears with a defined e, a derived ee and an inline table; only the
   derived-quantity route works.
2. A label field (`name`) in a listed catalog gave "units: not checked: no unit for B.name" until I added `"name": {"unit": ""}` to
   the catalog fields; BRICKS.md says a non-numeric field is a label and its units are not mentioned there.
3. `rpm` with a dimensionless `Mrev` (10^6) giving hours worked as hoped (result matched 11 494 h), but BRICKS.md does not say
   what rpm means (revolutions are dimensionless); I verified only by the numerical result.
4. `"report": "all"` was set, but with `failed_at_nominal` designs the listing seems to include them anyway; the doc does not say
   whether `failed_at_nominal` designs are judged by ZTL or only by nominal evaluation (the output shows `judged: 1`).
