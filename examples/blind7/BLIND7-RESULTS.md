# Blind test 7 — results (2026-11-09)

**Setup** — SETUP.md. Twelve real published problems found on the internet by a Sonnet writer (sources, published
answers, its own reference and scripts sealed in `work_writer/ANSWERS.md`, sha256 4ef250ae… recorded before any author
ran); twelve blind Sonnet authors with BRICKS.md, the shipped examples and one problem each, no internet, no code. The
stand frozen at 9a398b7, ZTL 5627be6; every brick run with `--prove`; the table of verdicts and proof counts committed
(134e98c, VERDICTS-FROZEN.md) BEFORE ANSWERS.md was opened. The seal checked at opening: the hash matched.

**Said about the problems themselves.** The laws and the questions are the sources'; every RANGE and every CATALOG
(parts, grades, prices) was added by the writer (listed per problem in ANSWERS.md). Only 7 of 12 sources publish an
answer the writer's script reproduces (p1, p3, p5, p8, p9, p10, p12); the reference for the problem AS WRITTEN is the
writer's own computation. Two sources (p6, p11) were read only in search summaries.

## Outcome — 12 of 12 agree, no wrong verdict

| # | problem | the stand | the writer's reference | proofs |
|---|---|---|---|---|
| 1 | steel grade, fracture | REFUTED (no steel meets 2.5 in); find: largest requirement 2.283 proved / 2.284 beyond, A572 | impossible; largest 2.284 (A572; exact 2.28379) | find 1/1 |
| 2 | signal yellow / red clearance | REFUTED with the 6.4 s budget, conflict {Y rule, R rule, budget}; without it EARNED Y 5.4 / R 1.1 | impossible; smallest (5.4, 1.1) = 6.5 s | 2/2 |
| 3 | two trucks, different lives | EARNED older truck; worst EAA 17539.3 vs newer 16681.2 (< 17000) | older; 17539 / 16681 | 1/1 + finds 2/2 |
| 4 | hearing protector, four stations | EARNED P4, worst dose 13.60 %; unprotected 136.4–225.4 % | P4, 13.60 %; 225.4 % | 1/1 + 2/2 |
| 5 | embroidery machine, NPV | EARNED heavy-duty, worst NPV 1169.85; crossover 11.926 % | heavy, 1169.85; 11.93 % | 1/1 + find 1/1 |
| 6 | insert grade + cutting speed | EARNED grade B, V 148.0, worst cost 4.0312 | B, ~148, 4.031 | 2/2 |
| 7 | office luminaires | REFUTED, conflict {illuminance, power density}; fallback L2 × 2 = 45.26 fc | impossible; L2 × 2 45.26 fc | 1/1 |
| 8 | capacitor bank | EARNED 250 kvar | 250 kvar only | **0/2** (below) |
| 9 | posted speed on a downgrade | EARNED 80 km/h, worst d_s 168.647 | 80 km/h, 168.65 | 1/1 |
| 10 | air-source heat pump | EARNED U4; find: smallest eta 0.5392 proved, 0.5391 refuted | U4; "0.5391" | 1/1 + **find 0/1** |
| 11 | curve radius | EARNED 450 m | 450 m | 2/2 |
| 12 | capital rationing | EARNED {A, E, F}, worst NPV 74.1 vs 74.0 (0.135 %) | {A, E, F}, 74.1 | 1/1 |

**p10's one difference is the writer's rounding.** The exact smallest eta is 30875/57267 = 0.539141 (the author's
own exact check); as "the smallest that works" it rounds UP: 0.5391 does not work, 0.5392 does. The stand is right.

## Proofs — 20 of 23 earned requirements are Lean theorems (zero axioms)

The three that are not, and why (diagnosed after the freeze):
- **p8, both requirements: ZTL's ln reading stops near 1e6–1e9.** The stand reads kW as W (SI), so P² ≈ 1.6e11 sits
  under a square root; zbound2lean writes sqrt(x) as exp(ln(x)/2), and `ivX` of `ln` returns none from about 1e9 on
  (MEASURED: ln 1e6 read, ln 1e9 and ln 1e11 none) — the quotient's denominator is "not proved positive", so the
  translator refuses. A limit of ZTL's kernel reading, not of the brick.
- **p10's find (smallest eta): no proof attached.** The proved end ([0.5392, 0.8] EARNED) carries no `proof`; the
  stand attaches proofs to the find's `decision`, and for a "smallest" find that decision is shown at the refuted end.
  A stand gap.

## Fixed after the round (the curator's «На все да», 2026-11-09)
- **ZTL 0d90b42 — ln read past ~1e9**: `ivLn` retries with wider margins (2⁻⁴⁰, then 2⁻²⁰, 2⁻⁸), each still checked by
  the exponential. **c08: `pfc >= 0.95` is now a theorem (1 of 2).** Its payback stays "no tree" — a difference of two
  square roots of correlated terms (kVA0 − kVA1, both in P); depth 18 and 22 measured, no help. (kVA0 is P/pf exactly;
  the brick writes it as a root, and the stand proves the brick as written.)
- **Stand — a find proves its own claim**: with `--prove` the PROVED RANGE (the brick with the searched quantity set to
  it) gets its own `proof` and `proof_covers` ("every eta in [0.5392, 0.8]"), besides the decision's. **c10b: 1 of 1.**
- **After the fixes: 22 of 23 earned requirements are Lean theorems.** The one left rests on ZTL's verdict, said why.

## What the authors could not express (their DOC GAPS, condensed)
- the unit `ksi*in^0.5` (p1: carried by a given Lu = 1 in; the unit check no longer certifies that dimension);
- a range asked for without a pass/fail limit (p4: dummy `>= 0` requirements to read it out);
- a derived quantity's worst case not listed under `guaranteed` when it is only an intermediate (p10, p11: read from
  margins / the judge log; p10's U4 bound 3.984 is sound but looser than the true 3.921);
- "maximise the worst case" as an objective (p12: nominal objective, same ranking because every NPV carries ±5 %);
- a crossover asked as "largest r where A is still at least as good" — equal to the crossover only if the difference
  changes sign once (p5: checked by the author, not by the stand).

## Cost
Writer 173 k tokens, paradox scout 60 k, twelve authors 1 197 k (93 k to 122 k each): **≈ 1.43 M** (estimated ~2 M).
