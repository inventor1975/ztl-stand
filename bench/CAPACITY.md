# Stand capacity — what it carries in reasonable time (2026-10-13)

**Machine.** i9-14900F: 8 P-cores (CPUs 0-15 with hyper-threads, 5.5-5.8 GHz), 16 E-cores (CPUs 16-31), 62 GB.
Python 3.12.3, ztl-stand fcfbeb2 + this bench's fixes, ZTL 154fee5. Every run: `bench/scale.py`, ONE P-core
(`taskset`), `~/bin/heavy -m 8G`, wall time and peak RSS by GNU time; work mode (not --dev) unless said.
**MEASURED caveat:** the axes ran 8-10 at a time on separate P-cores; the same bricks alone on a quiet machine
were 25-45 % faster (c02 48 -> 33 s, c06 78 -> 55 s, c10 153 -> 122 s). Read the times below as upper bounds.

## Synthetic axes (generators in `bench/scale.py`, raw rows in `bench/results/*.jsonl`)

| axis | what grows | < 1 s | < 1 min | < 10 min | memory at the top |
|---|---|---|---|---|---|
| corners_lin | toleranced quantities, linear law | 128 (0.15 s) | — | — | 16 MB |
| corners_mono | monotone nonlinear (exp·x) | 128 (0.1 s) | — | — | 19 MB |
| corners_peak / corners_rational | quantities with an INSIDE peak (certificate per term) | 12 | 16 (12 s), 24 (1 s) | — | 50-110 MB |
| designs | discrete combinations (3 slots, window + cost) | 10^4 | 10^6 (15 s) | 10^8 (438 s) | 1.1 GB at 10^8 |
| modes | operating modes of one choice | 128 (0.6 s) | — | — | 17 MB |
| chain | components in series (arriving bands) | 32 | 128 (5 s) | — | 27 MB |
| lp_amounts | continuous amounts, robust LP (rows n/2+2) | 10 | 40 (3 s), 80 (21 s) | 160 (175 s), 240 (588 s) | 470 MB at 240 |
| nl_amounts | continuous amounts entering nonlinearly (zmin) | 1 | 5 (38 s) | 16 (223 s) | 150 MB |
| lin_system | coupled linear unknowns (general laws) | 4 | 6 (9 s) | **cap: 7+ is OPEN** | 67 MB |
| network | n x n resistor grid (`network`) | 5 | 20 (29 s) | 30 (136 s), 40 (489 s) | 80 MB; 50x50 = 1099 s |

Three things in this table are walls, not slopes:
- **The corner wall at 16 toleranced quantities per group** (`checker.MAX_CORNER_PARAMS = 16`): up to 16 every corner
  is enumerated (2^16 = 65 536 exact evaluations, ~12 s PER DESIGN), above it a greedy walk — so 16 is the SLOWEST
  size and 20-32 are fast again. In a catalog of many designs with ~14-16 tolerances this multiplies.
- **General linear systems: 6 unknowns SYMBOLICALLY** (`certify.MAX_SYSTEM = 6`, sympy) — the formula grew ~3x per
  unknown (MEASURED 2026-10-15: 33 k chars at 6, 114 k at 7, ZTL's reader overflowed at 8). **Above 6 since
  2026-10-15: `zlin`** (a certificate over the box, checked exactly; see below). Before that: 7 and more were OPEN. The OPEN now says
  so (it said only "no proved range"); a resistor/conductance network of any size goes by `network` instead.
- **chain at 256 is OPEN** by the generator, not by the stand: ±1 % gain over 150 stages widens the arriving range
  past a component's `assume` — a true OPEN.

## The real bricks of blind round 6 (one core; quiet-machine times where re-measured)

| brick | verdict | time | peak |
|---|---|---|---|
| c03, c04, c05, c08 | EARNED | 0.4-2.2 s | 16-20 MB |
| c01, c09 | EARNED | 8-10 s | 20-80 MB |
| c07 | REFUTED (zmin split) | 18 s verdict, 28 s with conflicts | 80 MB |
| c02, c12 | EARNED | 33 s, 33 s | 21-83 MB |
| c06 | EARNED | 55 s | 108 MB |
| c10 | EARNED | 122 s | 80 MB |
| c11 | REFUTED (Farkas) | **298 s verdict**; the minimal-conflict search after it: {R1, R4} (the writer's answer) found, the list still not complete at 3000 s | 230 MB |

Ten of twelve under a minute, all twelve verdicts under 5 min. The slowest thing measured on a real brick is not a
verdict but `minimal_conflicts` after a REFUTED: subsets of the requirements, exponential in their number (c11).
A stop there keeps the verdict and says the list is incomplete (checked: `timeout 300` gave REFUTED + "stopped").

## More cores (`--jobs`, P-cores 2-15, then all 30 CPUs)

| brick | j1 (quiet) | j2 | j4 | j7 (P physical) | j14 (P + HT) | j30 (all) |
|---|---|---|---|---|---|---|
| c02 (discrete designs) | 33.2 s | 19.4 | 11.2 | 8.1 | 8.4 | 6.3 |
| c06 (continuous amounts) | 54.9 s | 55.0 | 55.1 | 55.0 | 55.2 | 55.2 |
| c10 (continuous + discrete) | 122.4 s | 122.5 | 121.5 | 123.8 | 123.4 | 123.7 |

`--jobs` parallelises the per-design judging only: a discrete search gains ~4x on the 8 P-cores, ~5x on all;
**the continuous path (LP, zmin, scenario cuts) is serial — more cores give nothing.** Memory per worker is the
single-run peak (GNU time reports the largest process, not the sum).

**Update 2026-10-13 (lever 1, the curator's "да"):** the nonlinear search's visits are now computed ahead by the
workers (`lp._Speculation`), output byte-identical. MEASURED on 8 jobs (P-cores 4-15), quiet machine: c06 54 -> 28 s,
c10 120 -> 85 s. Deeper look-ahead did not help (c06: 28 s at 2 or 4 pieces per worker, 32-48 s with grandchildren —
the queue fills with pieces never visited). What remains serial: `_worst_point` (exact rational search, c10 ~40 %),
the mix search `mix_of`, and the best-first chain itself.

**Update 2026-10-13 (lever 2, the curator's "да"):** `_worst_point` searches with the row's FLOAT function (the
search side; any point is a sound scenario). All 12 blind-6 bricks: output byte-identical to before (the grid and
golden-section points are rationals either way). MEASURED, quiet machine, before both levers -> now:

| brick | 1 job | 8 jobs |
|---|---|---|
| c06 | 54 -> 49 s | 54 -> 23 s |
| c10 | 120 -> 74 s | 120 -> 41 s |
| c12 | 35 -> 13 s | 35 -> 12 s |

**Update 2026-10-13 (lever 3, the curator's "да"): minimal conflicts.** One minimal set by deletion (n runs, any n —
the cap of 8 is gone), then subsets by size within a COUNT budget (default max(2n, 16) runs; not a clock, so the
listing does not depend on the machine), `complete` stated; with `--jobs` the subsets of one size go to the workers.
MEASURED, blind 6 c07 (10 requirements; refused before): 20 runs, 783 s on 1 job, 286 s on 8, identical listings;
40 runs took 37 min and listed the author's three sets. c11 (5 requirements, each subset run 2-3 min) stays slow: its
cost is per run, which no count budget changes — `"conflicts": false` or a small N is the answer there.

## Fixed during the bench
- `network` ignored `timeout` (a 50 x 50 grid ran 1099 s under `timeout 600`): the network judging now runs in an
  interruptible window; under `timeout 8` a 40 x 40 grid answers OPEN "stopped ... before any verdict" in 8.0 s.
- The general-linear cap is named in the OPEN (test added; USTAND 255/0, ROBUST 17/0).
- Two generators were wrong at scale (a fixed window and an ambient ramp became impossible); the stand's REFUTED was
  right both times — fixed in the generators, the old rows kept in `bench/results/old/`.

## What would move the limits (not done; each its own decision)
- Parallel continuous path (scenario cuts / candidate combinations in workers) — c06, c10, c11 are all here.
- `minimal_conflicts` with a budget by default, or only on request.
- The corner wall: a lower enumeration cap (12?) trades exhaustive witness search for speed; EARNED does not depend
  on it (certificates decide), REFUTED may need more search.
- General linear systems above 6: a numeric elimination with a checked certificate (as `network` does).

## Large linear systems: zlin (2026-10-15)

The ladder of `bench/scale.py lin_system(n)` (n coupled unknowns, 2n+1 tolerances), the target u_{n-1}; "exact worst
case" = the extreme found by descent (a witness's exact value as the next bound) and then PROVED at that very bound
(no slack) — one core per run, MEASURED:

| n unknowns | tolerances | each +-1 % | each +-0.1 % |
|---|---|---|---|
| 10 | 21 | 0.1 s (3 pieces) | — |
| 20 | 41 | 0.6 s (3) | — |
| 30 | 61 | 0.8 s (4) | — |
| 50 | 101 | 4.8 s (11) | 0.9 s (2) |
| 100 | 201 | **not decided** (the search went deeper than 200) | 4.4 s (2) |
| 200 | 401 | not run | 34 s (3); u ~ 1e-77 on a 2^-320 grid |

The wall is not the number of unknowns but the SPREAD: at 100 nodes and 1 % the output moves by a factor of several
over the box, and a first-order (mean value) reading of the derivatives cannot prove their signs on the whole box.
Through the stand (work mode): ladder 8 EARNED in 0.2 s, 20 in 1.6 s, 30 REFUTED (true: u29 ~ 1e-9) in 3.8 s.
`--dev` stops at its corner wall (16 tolerances per coupled group) — work mode decides.
What made it fast (each MEASURED at 10-30 unknowns): integer fixed point instead of fractions (37 s -> 1.6 s -> 0.1 s
at 10), the parametric form (per-tolerance, mean value) met with the interval form (20 unknowns: no certificate in
2000 pieces -> 3 pieces), verified vectors instead of refinement rounds (30: 4.9 s -> 0.8 s), the grid chosen by the
target's scale (50: gave up -> 4.8 s).

### Wide tolerances on every part (2026-10-15 evening, zlin step 6)

Before: every part +-2 % passed up to 20 unknowns, +-5 % up to 5, +-10 % none (the sign of d x_k / d p read as one
enclosure over a wide piece). Now, for quantities that enter by one layer (proved by an exact identity on a grid):
the sign as -g * y_k * (mu^T b - kappa), each factor enclosed on its own (A y = u, A^T mu = v, both with the
parametric form — without it beta was 0.67 and nothing passed), and vertex branches. MEASURED, the exact worst case:

| unknowns | every part | before | now |
|---|---|---|---|
| 5 | +-10 % | no certificate in 2000 pieces | 0.1 s (4 pieces) |
| 10 | +-5 % | no certificate | 0.2 s (2 pieces) |
| 20 | +-5 % | no certificate | ~10 s (26 pieces) |
| 10 | +-10 % | no certificate | 71 s, 2588 pieces (598 vertex branches) — the search budget was raised to 20000 |
| 5 | +-50 % | — | not decided (beta >= 1 over the box) |

The checker re-checks step 6 with its own means (its own identity test, derivatives, enclosures): 20 unknowns +-5 %
in 21.5 s.
