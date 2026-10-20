# Blind test 4 of the input format — results (2026-10-11)

**Setup.** Same protocol as rounds 1-3, on twelve domains that appear in none of them (36 domains excluded by name):

- A separate agent (Sonnet) that never saw the format wrote 12 problems (`PROBLEMS.md`), asked to include regimes,
  exponential/logarithmic physics and near-zero denominators, implicit operating points, tables, continuous amounts,
  large combination spaces, coupled linear balances, worst-case cost, hidden shared variables and possibly
  conflicting requirements. It checked its own data in scratch scripts and designed 7, 11 and 12 to be impossible.
- Twelve blind authors (Sonnet) each got BRICKS.md, the example bricks and one problem; no access to the code, the
  tests, GAPS.md or rounds 1-3; each kept scratch files in its own `work_cNN/`.
- Each ran the stand under 3 GB and 15 minutes, wrote `cNN.json` and `cNN.report.md`.
- The stand was frozen during the test (universal-stand 39d5eea, ZTL 5f645aa). All 12 bricks were re-run by
  Logik1 afterwards: the same 12 verdicts (9 EARNED, 3 REFUTED), 1 s to 899 s each.

## Outcome

| # | domain | verdict | the author's own check | done OUTSIDE the stand |
|---|---|---|---|---|
| 1 | vaccine shipper (insulation + PCM mass) | EARNED VIP-40, PCM 6.37 kg, 109.405 EUR, optimal on the 0.01 kg grid | own model to 9 digits; continuous optimum 6.367 kg | PCM mass as a grid (non-affine); `abs` by a sign trick |
| 2 | sacrificial-anode cathodic protection | EARNED Mg-S-32 x 4, 680 EUR, optimal | scipy root grid, 4-6 digits | the implicit law rearranged by hand (the literal form went OPEN / timed out) |
| 3 | UV disinfection (chambers, count, dimming) | EARNED U2 x 19, 114 467.18 EUR; Farkas refuted 400 of 480 combinations | own scan, same optimum and the same 80 feasible | regimes as copies (a continuous value per mode has no form) |
| 4 | workboat propeller + gear | EARNED P3 + G4, 12 300 EUR, optimal on 12 designs | own solver, 4 digits | the full 40 x 4 catalog killed at 900 s twice; cheaper designs judged one by one; a second implicit unknown eliminated by hand |
| 5 | soft-clay wick drains + surcharge | EARNED A / 0.9 / 1.1 m, surcharge 0.18 m, 150 075 EUR, optimal in a window | own 16-corner model | surcharge as a grid (non-affine), window from an earlier coarse run |
| 6 | solvent recycle loop (5x5 balance) | EARNED 3 x M4, purge 0.0109, 138 060 EUR/yr | own numpy solve, same numbers | purge as a grid; p = 0 (no steady state) dropped by hand |
| 7 | NTC thermistor front end | REFUTED on a CUT catalog (126 of 331 128): conflict {R3 BOM <= 2.20, R1 0.4 K band} | own scan of all 331 128: cheapest 2.38 > 2.20 | the catalog cut; every error item derived by hand (the literal chain went OPEN) |
| 8 | supercapacitor ride-through | EARNED S6, 12 x 2, 237.6 EUR, optimal; 116 of 800 earned | Euler ODE on all 800: the same 116 | the hold time as a hand-derived integral |
| 9 | bus mountain-descent brakes | EARNED D6/D6/PA/R1, 5040 EUR, optimal; 1 of 900 | own model of 900: the same one | mu(T), h(v) tables as nested `if` |
| 10 | micro-hydro penstock + turbine | EARNED H315-10/H355-16/T1, 81 940 EUR, optimal; 24 of 980 earned | own reference: the same 24 | six flow bins as six copies by script; K squared (no fractional unit powers) |
| 11 | steam sterilisation program | REFUTED, all 31 860 designs (R4 weekly time) | own calculation agrees | the lethality integral as a Riemann sum (its bound direction checked only by the author) |
| 12 | pension liability matching | REFUTED with a Farkas proof: R1 under stress vs the budget | own LP/MILP: LP bound 2 306 284 matches to 10 digits | integer lots as continuous (the relaxation); duration ratio linearised |

**One wrong verdict class — J1, fixed.** The c12 author's variants without the stress scenario came out REFUTED
("no mix the solver found was earned") although a feasible mix exists: the stand itself EARNED an integer portfolio
in the same box. Cause, measured: the robust LP's vertex had a binding R2 margin; after rounding the mix to
rationals the margin was -1.7e-7, the stand refuted THAT mix at a concrete point, and the run reported REFUTED for
the whole problem. A refuted solver mix proves nothing about the other mixes. Fixed the same night: REFUTED only
where "no mix exists" is proved (Farkas) in every combination, otherwise OPEN; the LP's inner margin is scaled by
the row's size and retried further inside (search side). The variant is now EARNED at 2 268 373 EUR (below the
author's integer 2 271 690), kept as `examples/tasks/t25-pension-tight-vertex.json` in the tests.

**Otherwise no wrong verdict.** Every verdict the authors checked independently agreed with the stand, usually to
the printed digits, including whole earned SETS (c08 116 of 800, c09 1 of 900, c10 24 of 980). Problems 7, 11 and 12
were designed impossible, and the stand refuted them for the designed reasons.

## New gaps (J for round 4)

| gap | problems | kind |
|---|---|---|
| J1. A refuted solver mix reported as REFUTED for the whole continuous problem | 12 | **wrong verdict class — fixed (above)** |
| J2. "Outside ZTL": laws with `exp`/nested `if`/derived products were bounded by the stand's own interval reading, ZTL proved nothing (c09: no quantity) | 1, 3, 9 | kernel coverage — to investigate first |
| J3. Continuous amounts only when the requirements are affine and every law explicit: PCM mass, surcharge, purge, dimming per regime went to grids | 1, 3, 5, 6, 12 | search — a nonlinear continuous choice with a certificate |
| J4. Speed and silence: 2-182 s per design with an implicit law and nested tables; full catalogs killed at 900 s with NO output (no progress, no partial result) | 2, 4, 7, 11 | search / output |
| J5. No table / piecewise-linear interpolation: every table is a hand-typed nested `if` | 4, 8, 9, 10 | vocabulary |
| J6. Correlation lost: a quantity read through repeated toleranced defines or a derived current goes OPEN "cannot bound" (sqrt of a negative-looking argument; the literal implicit form) | 2, 7, 8 | kernel reading (dependency) |
| J7. Units: no year, `kEUR` unknown, no fractional powers (m^2.5/s), a degC fed to a dimensionless table; a factor error `*1000` in a law with unit L passed silently | 1, 2, 3, 5, 6, 10, 12 | vocabulary / doc |
| J8. No sum over modes or scenarios (annual energy over flow bins, wet+dry life): copies by script | 2, 10 | vocabulary |
| J9. Output: `optimal: false` at a 0.00093 EUR gap (exact equality asked); `ties` lists designs not judged and infeasible; `closest_design` compares overshoots in different units; `guaranteed` shows the certificate's bound, not the value; OPEN reasons without the search range / the domain | 1, 3, 7, 8, 9, 10, 11 | output |
| J10. `minimal_conflicts`: skipped over 8 requirements, timed out at 7 on 31 860 designs; none in continuous mode (no multipliers printed) | 11, 12 | output |
| J11. Smaller: two coupled implicit unknowns; integrals / ODE; `abs`; `^`; an optional part "or none"; `where` without exp/ln; no point-range modes (a factor range only as point modes); the singular p = 0 OPEN without a named cause | 1, 4, 6, 7, 8, 9, 10, 11 | small |

**Reading.** Four rounds, 48 domains: the brick held, and the physics went in — exp, ln, sqrt, implicit operating
points, tables as branches, coupled balances. The new territory this round was the continuous side (Farkas proved
"no mix" in 3 and 12) and it produced the one wrong verdict class, now closed. The frontier is J2 (the kernel should
read what the stand had to bound itself), J3/J4 (search: nonlinear continuous amounts, speed, partial output) and J5.

## Cost

13 agents, 1 685 771 tokens: the problem writer 216 606; 12 blind authors 1 469 165 (from 96 511 to 197 132 each).
