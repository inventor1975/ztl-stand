# Blind test 5 of the input format — results (2026-10-11)

**Setup.** Same protocol as rounds 1-4, on twelve domains that appear in none of them (48 domains excluded by name):

- A separate agent (Sonnet) that never saw the format wrote 12 problems (`PROBLEMS.md`) as client briefs. It was
  asked for scenario sums, optional parts, lifetimes in years and kEUR, fractional powers, exp/log physics, implicit
  operating points, tables, continuous amounts, large spaces, coupled balances, worst-case cost, shared quantities,
  absolute values and singular parameter values. It checked every problem with its own scripts (answers in
  `work_writer/ANSWERS.md`, closed to the authors) and designed 6, 7 and 9 to be impossible, 1 and 12 to pass by
  under 1 %. Its reference is its own code only (grids and corners, no proofs).
- Twelve blind authors (Sonnet) each got BRICKS.md, the example bricks and one problem; no code, no tests, no GAPS,
  no earlier rounds; scratch in their own `work_cNN/`. Each ran the stand under 3 GB and 15 minutes.
- The stand was frozen at universal-stand 654a939, ZTL 7606b70. **One breach, said here:** for about two minutes
  (13:43-13:45) the working tree carried a fix of the stop flag (only what happens on SIGTERM); reverted, the fix
  kept as a patch until the round ended. No verdict path was touched.
- All 12 bricks were re-run by Logik1 afterwards on the frozen stand: the same 12 verdicts and answers, 6 s to 929 s.

## Outcome

| # | domain | verdict | the writer's reference | done OUTSIDE the stand |
|---|---|---|---|---|
| 1 | crusher bearing, oil, kit | EARNED R-60F / VG150 / no kit, 1.70 kEUR, optimal; life 56 403 h vs 56 000 | same, 0.72 % margin | nothing (10/3 as a given) |
| 2 | transformer + optional bank, 30 years | EARNED amorphous 1000 kVA + 150 kvar, optimal (1 of 72) | same, the only admissible | the 30-year sum as closed-form constants; kvar as kW |
| 3 | solar hot water, four seasons | EARNED F2 x 5, 750 L, no upgrade, 4.62 kEUR (in a price window) | same | **totals used blind**; full 220 timed out — 16 cheap designs refuted only by the author's python |
| 4 | gravity sewer, two reaches | EARNED PVC, A 250 @ 0.5 %, B 300 @ 0.35 %, 191.573 kEUR (in a 48-design cut) | same | catalog cut from 3675 by the author's scan; sin/cos by a tan substitution; a surcharge clamp |
| 5 | cooling tower, three seasons | EARNED Town / P2 / 70 %, blowdown 0.165 / 0.290 / 0.415, 54.089 kEUR (bound 54.080) | same | requirements cross-multiplied to affine (J3); worst cost as hand-typed range tops |
| 6 | strip footing | REFUTED, best FS 2.62 vs 3 with B <= 2 m; conflict [R1] | impossible, 2.62 | R4 as `where`; degrees as a number |
| 7 | radiography wall shielding | REFUTED, conflict {dose, mass}; best dose 0.0104 vs 0.005 | impossible, 0.0104 | N*K merged (20 toleranced quantities refused by the checker's corner limit); Gy/Sv as mJ/kg |
| 8 | electric delivery van | EARNED B77 / ultra / full aero / heat pump / no solar, 14.85 kEUR, optimal | same (2 of 216 pass) | kWh/100km converted by hand |
| 9 | warehouse space | REFUTED, conflict {coverage, budget}; minimum 367.195 kEUR vs 355 | impossible, 367.2 | B as a 104-value grid; R1 rewritten (the min/max chain went OPEN) |
| 10 | aquaculture pond aerators | EARNED PW2 x 10, running 1/3/10/3, oxygen unit, 87.95 kEUR (in a narrowed space) | same | design space narrowed by hand (10.7 M combinations); C_ss solved by hand |
| 11 | currency hedge | EARNED strike 1.10, 52.909 kEUR (bound 52.909) | same | 625 scenario modes for the spot ranges; R2 split by hand |
| 12 | call centre staffing | EARNED 25 / 29 / 22 / 13 agents, advanced IVR, 2992 kEUR, optimal in windows | same, 0.64 % margin | Erlang C unrolled; agent windows from the author's python; ratio rewritten as a difference |

**No wrong verdict.** Twelve of twelve agree with the writer's reference and with the authors' own checks —
including the two designed to pass by under 1 % and the three designed impossible, refuted for the designed reasons.
The stand's numbers matched the authors' independent models to the printed digits throughout.

**The new words, used blind.** `totals` (c03: annual back-up over four seasons, with an implicit tank temperature
per season), `optional` (c03, c08, c10), `kEUR` and fractional powers (several). c02 did NOT find `totals` fit: a
30-year sum with discounting is a geometric series over years, not a sum over modes.

## What the round found in the stand (fixed the same day, a70481a + the prune change)

| | found by | what | fix |
|---|---|---|---|
| K1 | c06, c07, c10, c04 | `timeout` not heard: c06 ran 57 min past 900 s, c07 1041 s. Each subset of `minimal_conflicts` called run(), which CLEARED the stop flag; group pruning and the `where` enumeration had no stop check | the outermost run alone resets the flag, a nested run passes the stop up, the conflict list says "stopped"; stop checks in pruning and enumeration. MEASURED: a 2700-combination c04 variant now stops at 120.0 s of 120 |
| K2 | c04, c10 | 5-19 minutes of silence before the first design | one group read of an implicit law ran ZTL's root search over the whole catalog's hull (traceback, 6 min in the first group): pruning is now off with implicit laws, progress from the first second; a progress line while `where` filters |
| K3 | c10 | `optional` with `modes`: BRICK ERROR "OX_none is taken" (my J11 of the same day; its test had no modes) | idempotent |
| K4 | c04 | `pow(x, 2/3)` refused by the unit check | a constant arithmetic exponent is read; Manning with n in s/m^(1/3) checked |
| K5 | c01, c02, c08 | the objective printed in SI (1700 for 1.70 kEUR) | shown in the one unit of its prices, origin said |
| K6 | c02, c07, c09 (and rounds 2-4) | `by` read as the worst overshoot | renamed `by_at_witness` |
| K7 | c11 | `mix_verdict_checker` empty with modes — the checker DID run per mode (an EARNED mode needs it), the label was not carried | per_mode names each mode's checker |

Residual: a stop is heard between designs, so it can come up to ~40 s late while one design with implicit laws is
judged (MEASURED: 282 s for a 240 s limit on full675).

## Open (for the next steps)

- **Scale / speed (J4).** Four authors cut the space by hand: c03 (105-120 s per near-feasible design), c04, c10
  (`where` filters AFTER the product: 10.7 M combinations), c12 (13 min). The per-design cost of implicit laws with
  many toleranced quantities is the bottleneck; `where` cannot prune a product slot by slot.
- **Correlation (J6 family).** The min/max chain (c09: [-944, 944] for a non-negative margin), a ratio of sums
  (c12), the LP taking each coefficient's worst case separately (c11: spot rate in three coefficients — 625 modes),
  a loose total (c03: 698 vs about 1111).
- **Nonlinear continuous amounts (J3).** c05 cross-multiplied by hand; c09 gridded B.
- **Vocabulary the authors asked for — the curator's call:** sin/cos (c04), a degree unit (c06), Gy/Sv (c07),
  VA/var (c02), a unit with a number (`kWh/100km`, c08), a requirement directly on a given or a catalog field
  (c06, c09 — a dummy quantity now), switching `minimal_conflicts` off (c06), "no root of an implicit law means
  the design fails" (c04), `pow` in `computed` (c03), a sum over years (c02), the checker's 2^n corner limit at 20
  toleranced quantities (c07).

## Cost

13 agents, 1 745 944 tokens: the problem writer 235 697; 12 blind authors 1 510 247 (from 98 169 to 191 635 each).
