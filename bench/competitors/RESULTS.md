# The duel, round 1 — ztl-stand vs Z3 5.3.1, cvc5 1.4.2, dReal 4.21 (2026-10-18)

Harness `duel.py`, raw rows `results.jsonl`.

**Setup.** The stand's OWN synthetic axes (bench/scale.py) — home ground: the generators were written around what the
stand does. 37 instances x 2 variants (PROVE: the axis' true bound -> EARNED / UNSAT; REFUTE: the bound just inside
the true extreme -> REFUTED / SAT), 4 tools, 120 s each, 16 runs in parallel on the i9 (times are upper bounds).
SMT generated from the same brick. dReal (delta 1e-3) cannot refute by design: DELTA-SAT is no counterexample.

**Decided (right verdict in time) / 74:** stand 70, Z3 51, cvc5 40, dReal 19. **Wrong verdicts: 0 for every tool.**

| axis | stand | Z3 | cvc5 | dReal |
|---|---|---|---|---|
| corners_lin (4..128) | all, <= 10 s | all, ~0 s | all | proves all |
| corners_peak (polynomial, interior peak, 1..24) | all, <= 15 s | **all, ~0 s** | proves to 4, refutes to 8 | proves to 4 |
| corners_rational (x/(1+x^2), 1..24) | **all, <= 20 s** | proves only 1-2, refutes all | proves 1-2 | proves to 4 |
| corners_mono (exp, 2..32) | **all, <= 49 s** | not expressible (no exp) | time-out | proves all, no refute |
| lin_system ladder (2..12) | **all, <= 9 s** | to 8 (94 s), not 12 | proves 12, refutes to 4 | none |
| network grid (3..20) | **all, <= 39 s** | only 3x3 | only 3x3 prove | none |
| chain (2..128) | proves all; **refute: OPEN** | all | to 32 / refutes 128 | proves all |

**Where we lose:** Z3 on polynomial corners is orders faster; chain REFUTE — the stand says OPEN (interval bands lose
the correlation), every SMT finds the counterexample. **Where we win:** rational and transcendental laws, coupled
linear systems and networks of size — the SMT tools time out at 5x5 grids and 12-node ladders.

**Caveats.** Home axes; next: the blind-round bricks (written by an independent writer) and outside tasks. Solvers'
UNSAT here carries no checked certificate (Z3/cvc5 can emit proofs; not checked here); the stand's EARNED is a
certificate checked by its kernel. One machine, parallel load.

## Round 2 — blind bricks, option A (2026-10-18)

`blind_duel.py`: the 12 blind-round bricks (independent writer). Each law goes through the stand's own reading
(`compile_expr`), so translation errors would be shared, not the solvers' fault. Discrete bricks (6): designs in cost
order, each checked in every mode ("some box point violates a requirement" UNSAT = holds); first HOLDS with no cheaper
UNDECIDED = optimal. Continuous bricks (6): only the stand's pinned answer is checked (the full ∃∀ problem = round B).
60 s per check, 900 s per brick/tool, 16 jobs in parallel.

| brick | stand | Z3 | cvc5 | dReal |
|---|---|---|---|---|
| c02 cables | EARNED 2825.5 opt, 32 s | **same, opt, 313 s** | budget (5 checked) | same design, not opt (δ-sat) |
| c03 battery | EARNED 70 opt, 0.5 s | no exp | budget | budget (88 checked) |
| c04 heat trace (as given, Ta = -40) | REFUTED: every design, minimal conflict R1-R3, 1.5 s | no ln | budget | none proved |
| c05 compressed air | EARNED 13880 opt, 1.8 s | non-int pow | budget | same design, not opt |
| c08 gas cylinders | EARNED 625 opt, 2.1 s | **same, opt, 0.6 s** | same, not opt | same, not opt |
| c09 straps | EARNED 311 opt, 1.4 s | no tan | budget | same design, not opt |
| c01 pinned | EARNED, 4 s | non-int pow | timeout | HOLDS |
| c06 pinned | EARNED, 61 s | HOLDS | HOLDS | δ-sat |
| c10 pinned | EARNED, 101 s | no exp | timeout | HOLDS |
| c12 pinned | EARNED, 17 s | no exp | timeout | δ-sat |
| c07, c11 | REFUTED (no design) | — round B | — | — |

**Correction (same day).** c04 is a "find the smallest Ta" brick; the solvers got it without the find, at Ta = -40,
where the stand REFUTES every design (its "decision"); the first version of this table showed the stand's answer for
the found limit (Ta >= -37.86: EARNED 3108) — another question. No solver found a design there (consistent), none
proved the refutation.

**Disagreements: 0.** Every design a solver found is the stand's design at the stand's cost. Full answer (design +
optimality proof, or a proved refutation) on the discrete bricks: stand 6/6, Z3 2/6 (c02 10x slower, c08 3x faster), cvc5 0/6, dReal 0/6
(finds the right design on 4, cannot refute the cheaper ones: δ-sat is not a counterexample). Pinned answers confirmed
by some solver on 3 of 4 (c12 by none).

**Caveats.** The solvers only face the stand's own encoding; no tuning (cvc5 options, dReal precision) was tried;
c07/c11 (stand REFUTED) and the continuous search are not yet compared (round B).

## Round B — the continuous bricks as the full problem (2026-10-18)

`round_b.py`: per combination of the discrete slots, exists amounts in their ranges, forall data in the box, laws =>
requirements (and nominal cost <= C); bisection on C. z3/cvc5 `sat` is exact; a dReal delta-sat amount counts only
after dReal proves it (round A's check, UNSAT). dReal precision 1e-6 (MEASURED: 1e-10 times out). 60 s per query,
1800 s per brick/tool.

| brick | stand | Z3 | cvc5 | dReal |
|---|---|---|---|---|
| c01 | 1484.39 [lb 1484.38], 4 s | no non-int pow | nothing | 1632.9 (W-12, +10%), lb 967.6 |
| c06 | 270.657 [lb 270.653] kEUR, 61 s | **270.667 [lb 270.647], 132 s** | nothing (1082 s) | 272.14 [lb 267.05] |
| c07 | REFUTED, 507 s | nothing (300 s) | nothing | **REFUTED, 0.4 s** |
| c10 | 51.669 [lb 51.669], 101 s | no exp | nothing | nothing (960 s) |
| c11 | REFUTED (Farkas; run hit 900 s in the conflict search) | **REFUTED, 0.6 s** | 19 of 20 refuted | nothing |
| c12 | 12.380 [lb 12.380], 17 s | no exp | nothing | 14.86 (+20%), no bound |

Full answer (cost + proved bound, or a proved refutation): stand 6/6; Z3 2 (c06, c11); dReal 1 (c07); cvc5 0.
**Where we lose:** refutations — dReal 1000x faster on c07, Z3 on c11.

## SCIP 10 (MINLP) on all 12 (2026-10-18)

`scip_duel.py`: binaries per catalog item, amounts continuous; no "forall", so two usual postings — NOMINAL (box
middles) and CORNERS (every requirement at every box corner; k > 10: 1024 sampled). Requirements normalised by their
bound (the stand's SI made "Dm <= 0.1/year" 3e-9/s, under SCIP's tolerance — MEASURED, c01), feastol 1e-9. Every answer
judged by the stand.

* NOMINAL: a cheaper design on every brick — the stand REFUTES every one (tolerances ignored = a wrong design).
* CORNERS: the stand's optimum on c02 c03 c05 c08 c09 (EARNED by the stand), and on c01 c06 c10 c12 to 6-7 digits —
  but SCIP's float point sits ON the boundary: the stand refutes it by 1e-16..1e-9 (a float tolerance, not a design
  error). Infeasible on c04 and c11 (the stand refutes them too; SCIP's is no proof). c07: out of memory at 16 GB.
  Seconds each, except c08 (230 s, 34.6 GB RSS) and c06 (900 s limit, gap 1e-7).

**The honest reading.** In these 12 bricks every worst case lies at a corner, so the standard engineer's posting
(SCIP + corners) finds the same answers, mostly faster. What it lacks: a proof that the worst case is at a corner (the
round-1 axes corners_peak / corners_rational are exactly where it is not), an exact point (it lands 1e-9 outside), a
proved refutation, and memory on a 180-design catalog. The blind bricks do not exercise the stand's real edge.

## The weaknesses, worked (2026-10-18, stand bdce7d4)

Measured first (cProfile), then fixed — the slow refutations were not the logic:
* **c11** — 870 of 987 s were the reasons/each-requirement listing of candidate mixes thrown away. Candidates now judged
  brief: the verdict **312 -> 42 s**; every answer of the 6 continuous bricks identical (c12 16.7 -> 6.0 s, c01 4.2 -> 2.9).
* **conflict search** (98 % of c07's time) — monotone inference (a subset of an EARNED set is EARNED, a superset of a
  REFUTED one REFUTED, no run) and the proof's CORE (Farkas multipliers, zmin failing leaves, each design's failing
  requirement). c04: 6 runs -> 3 + 3 inferred. **c11: the complete list {R1, R4} in 644 s** (before: nothing in 900 s).
  c07: still ~600 s and incomplete — its zmin core is wide (7 of 10, checked: REFUTED on its own in 3.5 s — a second
  conflict family R1+R3+R4 the budget never reached). Not fixed: the core is the first failing row per piece; a
  narrower choice would make it depend on the search's order (speculative workers) — determinism kept.
* **chain REFUTE (round 1)** — OPEN was honest (a point inside the components' ranges may be no component's). Witness
  lifting: each component at its real input, its own corner or middle, outputs exact; the system judged there.
  **REFUTED at 2, 8, 32, 128 components** (0.3 / 1.0 / 1.3 / 16.8 s); prove variants stay EARNED.
Remaining gap: a bare refutation verdict — c07 ~10 s against dReal's 0.4 s. Tests: 307 ok (W1-W3 new).
Times on a shared machine (another job and the test suite alongside) — order of magnitude, not a benchmark.

### Conflict search, second pass (2026-10-18 late)
Per-subset timing on c07 showed the cost was not refutations (3-6 s) but EARNED subsets: a single requirement 57 s,
{R2, R4} 285 s — 637 of 640 s proving a lower bound on the cost nobody reads, then 635 s trying to prove that one
plate has no mix before the next plate gave one at once. Now a conflict-search subset is EXISTENCE ONLY (no bound) and
SEARCHES FIRST (every combination's mix, a proof only when none is found); the zmin core is a pass over the finished
tree (a leaf a core row already fails is covered), the search untouched. **c07 507 -> 56 s, c11 900 s (nothing) ->
257 s (complete {R1, R4})**; bare verdict c07 5.9 s (dReal 0.4 s). c07's list is still cut by the subset budget (a
count, 2 per requirement).

### Third pass (2026-10-18, night): floats guide the search, complement probes, the budget raised
* zmin's search reads each row in machine floats first: a row met at a sample of the piece by a clear margin cannot be
  failed by the exact reading (its lower end is at most that value) — the exact reading is skipped (always sound: a
  certificate is made only of exact failures); the hardest data point is chosen in floats. Same answers and bounds;
  **c06 54 -> 13.6 s, c10 92 -> 34.8 s, c12 6 -> 3.3 s, c01 2.9 -> 1.7 s, c07 bare verdict 5.9 -> 3.4 s** (0.5 s of it
  imports; dReal 0.4 s).
* Conflict search: for each member e of a conflict found, the whole set without e is judged — EARNED there means every
  conflict holds e. **c07's complete list — 6 conflicts (R3 at 3600 s with each of the six Qpeak limits) — 22 runs +
  515 inferred, 68 s** (full enumeration before: 529 runs, 530 s); c11 complete in 6 runs. Default budget 2 -> 4 runs
  per requirement (min 16 -> 24), the curator's "да".

### A search bug found by the duel (2026-10-19)
c07's subset {R2, R4} left plate O80 "no earned mix, no proof" — and O80 HAS robust mixes (A = 500 m^2 EARNED). The
local solver kept every row "a hair inside" its bound; "PL.d >= 80" for the 80 mm plate is 0.08 >= 0.08 at every
mix — unmeetable with a slack, so the whole box looked infeasible. Rows the amounts do not move are now read at the
centre and two corners and, met, left out of the search (the stand judges the mix exactly anyway). {R2, R4}: EARNED
O80 at 10.42 in 1.3 s (was O100 at 24.95, 113-260 s, marked optimal: false with O80 "not covered" — honest, not
false). The 12 blind answers are unchanged (the bug bit only conflict-search subsets). c07 with HC4 in the search:
bare verdict 2.3 s; complete conflict list 65 s. Suite 307 ok.

## The stand after the work (rerun 2026-10-19, stand 93591cb, ZTL c11d8d1)
Round 1 (synthetic axes, stand rows only; `results_stand2.jsonl`): **decided 74 of 74 (was 70)** — the four chain
REFUTE rows, OPEN before, are REFUTED (witness lifting); every other verdict unchanged.
Round 2 blind bricks (`blind2/`): every answer identical to the first run (same value, same verdict); times:

| brick | before | after |
|---|---|---|
| c07 (verdict + complete conflict list) | 507 s | **79 s** |
| c11 | 900 s (time-out) | **233 s** (complete list) |
| c06 | 61 s | **11 s** |
| c10 | 101 s | **33 s** |
| c12 | 17 s | **3.4 s** |
| c01 | 4.2 s | 1.9 s |
| discrete c02-c09 | 0.5-32 s | 1.2-38 s |

The rerun ran 22 processes on 24 cores at once: the small discrete bricks' ~1 s more is that load, not the stand
(their code path did not change). Against the solvers: Z3 still proves c08 in 0.6 s and c11's refutation in 0.6 s,
dReal c07's in 0.4 s (our bare verdict 2.3 s alone); the stand stays the only tool with a full answer on all twelve.

### Cheap proof first; a contraction-edge split measured and dropped (2026-10-19)
* Before a combination's mix is searched, a split of at most 64 pieces (readings, float skip, contraction) tries
  "no mix" — closed, no search is spent. **c07 bare verdict 2.3 -> 1.05 s** (0.5 s imports; dReal 0.4 s), c07 with its
  complete conflict list 79 -> 44 s, c10 33 -> 19 s, c06 11 -> 6.5 s; values, bounds and conflict lists identical.
* Cutting a piece at a contraction's edge instead of halving it — MEASURED and dropped: fewer pieces (c10 114 -> 67,
  c12 21 -> 19, c06 61 -> 61) but slower every time (c10 18.0 -> 21.9 s, c06 6.0 -> 11.1 s, c07 0.9 -> 1.5 s): the
  contraction before every split costs more than the pieces it saves at this size.

## The interior showcase (2026-10-20) — the worst case INSIDE the box (`interior_duel.py`, examples/interior)
The twelve blind bricks all had their worst case at a corner. These three do not; each tool's design judged by the
stand on the brick pinned to it:

| brick | stand | SCIP nominal | SCIP corners | Z3 | dReal | cvc5 |
|---|---|---|---|---|---|---|
| i01 load power (peak at RL = Rs) | **R 11, optimal** | R 10 - REFUTED at RL 13.4 | R 10 - REFUTED at RL 13.4 | R 11, optimal | R 11, not proved optimal | R 11, not proved optimal |
| i02 beam, load anywhere (peak mid-span) | **IPE220, optimal** | IPE200 - REFUTED at a = 3 | IPE140 - REFUTED: 388 MPa vs 160 | IPE220, optimal | IPE220, not proved | IPE220, not proved |
| i03 mounts, speed band (resonance inside) | **M25, optimal** | M15 - REFUTED at f = 40 | M20 - REFUTED at f = 27.5 | M25, optimal | M25, not proved | M35 (dearer) |

**SCIP posed the usual robust way (every corner) picks a WRONG design on all three** — the beam 2.4x overstressed.
Z3 is right too here (polynomials and ratios are its home), equally fast; the stand's edge over Z3 stays what the
blind bricks showed (exp, ln, non-integer powers) and a certificate the ZTL kernel checks. Found on the way: a design
whose definition could not be bounded (a denominator read as touching zero) was left OPEN without trying a point —
now a witness is searched first (i03's M15, failing at a CORNER, was OPEN). Note: i03's catalog "tolerance" on k is
not applied by the stand's catalog reader (k read exact) — the resonance is inside the band without it.

### Points 2 and 3 of the weaknesses (2026-10-20)
* **Many tolerances (round 1's 16-variable axes).** 94 % of the time was the 2^16 = 65 536 exact corners — read before
  a certificate that then decided in 0.4 s, and again for the refutation's EXPLANATION (the spread). Now the certificate
  comes first when there are more than 8 tolerances (the corners only if it leaves a requirement unshown — the same
  witnesses, later), and an explanation's spread is computed up to 2^10 corners (said, not estimated, beyond).
  Interior peak prove 17.7 -> 0.84 s, refute 17.7 -> 0.21 s; rational prove 14.8 -> 1.7 s; monotone refute
  52.8 -> 0.29 s. All 74 round-1 verdicts unchanged (work mode).
* **c11 (the scenario-cut path).** 727 of 848 profiled seconds were EXACT readings choosing data points (the worst at a
  mix, the hardest ends) — search side, where any point of the box keeps a certificate sound. Now chosen in floats
  (the exact choice where the floats cannot read a row). **c11 with its complete conflict list 217 -> 28 s**;
  c01 c06 c07 c10 c12: values, bounds and conflict lists identical. Suite 307 ok.

## Rerun on ZTL with IF STABLE (2026-10-31, stand abee4f8, ZTL 0897d54)
The judge gained EARNED/REFUTED IF STABLE on 2026-10-29 (ZTL 1ae8a5c). Rerun of the stand rows on 24 cores (round 1:
`duel.py --tools stand --jobs 12` -> `results_stand3_20261031.jsonl`; the 12 blind bricks one process each ->
`blind_rerun_20261031/`), compared with the 2026-10-19 rows:
* Round 1: **74 of 74 verdicts identical** (total wall 283 s -> 144 s).
* Blind bricks: **12 of 12 identical** — verdict, objective value and optimality flag; c11 233 -> 38 s, c07 79 -> 53 s,
  the rest within load noise. The stand test suite on the same ZTL: 307 ok, 0 failed.
