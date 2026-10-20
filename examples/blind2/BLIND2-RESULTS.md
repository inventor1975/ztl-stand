# Blind test 2 of the input format — results (2026-10-10)

**Setup.** Same protocol as blind test 1 (`examples/blind/BLIND-RESULTS.md`), on twelve NEW domains, after gaps
G1–G14 were closed:

- A separate agent that never saw the format wrote 12 problems (`PROBLEMS.md`). It was asked to include, where natural,
  a formula that changes with a regime, a table, two quantities driven by one hidden variable, a requirement at one
  operating point, a worst case to minimise, integer choices — and one LARGE catalog (problem 12).
- Twelve blind authors (Sonnet) each got BRICKS.md, the example bricks and one problem; no access to the code, the
  tests, GAPS.md or round 1.
- Each ran the stand under a memory cap (3 GB) and a 15-minute limit, wrote `cNN.json` and `cNN.report.md`.
- All 12 bricks were re-run afterwards by Logik1 (see the end).

## Outcome

| # | domain | verdict | authors' own check | what the author did OUTSIDE the stand |
|---|---|---|---|---|
| 1 | oil cooler (ε-NTU, U depends on the outlet: implicit) | OPEN — HX-40 not decided; 3 others REFUTED | HX-40 truly passes (scipy, 20 000 points) | Cmin/Cmax written directly (min/max broke the checker); the Cr = 1 branch |
| 2 | bolted joint | EARNED M12 8.8, 75 N·m, optimal | 24 feasible designs = the author's 24, every number | one reading of "preload band considering scatter"; torque range chosen by hand |
| 3 | 18 GHz radio link | REFUTED — the EIRP limit cannot be met (data error in the problem) | matches by hand; relaxed twin EARNED, = the author's scan | dBm and dBi as plain numbers; modulation choice as fixed modes |
| 4 | LED on a vehicle supply (diode law: implicit) | EARNED R = 604 Ω, optimal **false** (6 equal-cost designs OPEN) | all 196 verdicts = the author's model | E96 typed from memory as items (no E96 series); decade chosen by hand |
| 5 | two columns (Euler / Johnson) | EARNED, optimal | 12-digit agreement | the piecewise switch written with min/max by hand; A and I computed outside |
| 6 | buffer pH (Henderson–Hasselbalch) | EARNED $1.16, optimal **false** — the true cheapest ($1.02) stays OPEN | stand's ranges contain the author's | catalog cut after the full one (14 400) was killed at 15 min; HH instead of charge balance (1e-5 pH) |
| 7 | irrigation season | REFUTED — only the water licence, by 0.74 % | every volume and cost matches | the piecewise Kc curve summed by hand into four numbers |
| 8 | spare-part reorder | EARNED, optimal | per-supplier winners = the author's scan of 819 items | safety stock rounded up outside (an equality at the bound through sqrt stayed OPEN); Q enumerated by hand |
| 9 | 12 kWp PV (three modes) | EARNED, optimal | 5 feasible designs = the author's 576-design scan | ceil(strings / inputs) tabulated by hand (a slot cannot depend on another) |
| 10 | two-stage gear reducer | EARNED, optimal | stresses to every digit; 778 feasible pairs | the honest 54 000-design brick was KILLED at 15 min; stage pairs pre-filtered by script |
| 11 | duct and fan (Colebrook) | REFUTED — velocity limit at 4 400 m³/h | velocity, margin, power match | Colebrook as two fixed-point steps (a second implicit unknown is refused); operating point by a monotonicity argument |
| 12 | Sallen–Key filter, E96 × E12/E24 (LARGE) | EARNED $1.16, optimal — **over a hand-thinned catalog** (110 592 of ~6.6e9) | the author's own full numpy scan finds nothing cheaper | E96 from memory; 9 M and 307 k designs both killed with NO output; finite op-amp gain ignored |

**No author found a wrong verdict.** Every EARNED and REFUTED that an author checked by an independent calculation
agreed. Where the stand fell short, it was by not proving, never by a false claim: in c01 the one passing design
stayed OPEN (so no answer), in c04 and c06 passing designs stayed OPEN and the stand said `optimal: false`.

Compared with round 1 — in 9 of 12 problems the hard physics was then approximated outside the stand. Now the hard
physics went in as stated in most problems (exp diode law, log10 link budget, Swamee-type friction, implicit outlet
temperature, Euler/Johnson, sqrt EOQ, worst-case costs); what authors did outside is mostly **search-space
preparation** (catalogs too large, series missing, slots that depend on each other) and **branches** (piecewise laws).

## What the test says about the format

**The STRUCTURE held again in all 12 new domains.** No author lacked a place for quantities, choices, laws,
requirements, modes or the objective.

**New gaps** (H for round 2), by how many problems hit each:

| gap | problems | kind |
|---|---|---|
| H1. SCALE: catalogs of 10⁴–10⁹ combinations killed at 15 min with no output at all (and 2.1 GB at 9 M) | 6, 10, 12 (and 4 at 12 min) | performance — ~70 % of the time per design in modes is overhead (re-parsing laws, reasons for every refuted design, re-loading the brick), measured on c10 |
| H2. A loose interval leaves a TRULY passing design OPEN (a derived quantity of an implicit one; a peak inside the box) → `optimal: false` or no answer | 1, 4, 6, 8 | precision — certificates do not reach these cases yet |
| H3. Branches: a formula that changes with a regime (Euler/Johnson, Cr = 1, the Kc curve) — only through min/max tricks | 1, 5, 7 | vocabulary |
| H4. E96 (and other series) missing | 4, 12 | vocabulary (a table entry) |
| H5. A choice that depends on another slot (strings per input from NP; pairs of stages; per-system integer windows) | 6, 9, 10 | vocabulary |
| H6. The 200-line `designs` cap hid exactly the EARNED or OPEN designs the author needed; no count of earned | 2, 6, 9, 10 | output |
| H7. A define named like a catalog field (`Uc` vs `HX.Uc`, `SS` vs `POL.SS`) is substituted INSIDE the field; the error blames an unrelated law | 1, 8 | **bug** |
| H8. `min` inside an implicit law: `STAND ERROR ... NoDerivative` | 11 | **bug** |
| H9. A design whose implicit law has no root is OPEN even when a requirement that does not depend on it already refutes it; the checker's message says "cycle" | 11 | bug / output |
| H10. `by` for a REFUTED design is the overshoot at the witness found, not the worst case (978 vs 19 658 m³; 0.58 vs 79 kN) | 5, 7 | output (documented nowhere) |
| H11. Units: dB, dBm and dBi indistinguishable; witness points and `how` printed in SI, not in the author's units | 3, 7, 11 | output / vocabulary |
| H12. A nominal value of a toleranced quantity cannot be named (a requirement at nominal, "nominal Sy 355 with 330..380") | 2, 5 | vocabulary |
| H13. A second implicit unknown (Colebrook's f next to Q) | 11 | vocabulary |
| H14. Smaller: ties in the objective not flagged; a timeout gives no partial result; `"1.46/100000"` refused as a number; conditional requirements ("only for 42CrMo4"); half-power units (√MPa) | 2, 10, 11, 12 | small |

**Reading.**

- The core shape is universal across 24 domains now (12 + 12). Nothing in round 2 asks to change what a brick IS.
- The weight moved: round 1 was about the expression language (functions, units); round 2 is about the SEARCH
  (scale, slots that depend on each other, branches) and about PRECISION (designs that pass but are not proved).
- Two real bugs (H7, H8) and one wrong-OPEN (H9) — no wrong verdict.

## Cost

13 agents, about 1.48 M tokens: the problem writer 77 431; 12 blind authors 1 398 736 (from 88 037 to 156 901 each).
Not counted: Logik1's own context and the re-runs.

## Re-run by Logik1 (2026-10-10 16:04, ZTL 96b7e17, stand abbe0d4, 12 in parallel, 1 core and 3 GB each)

All 12 verdicts and objective values reproduce the authors' runs exactly:

| # | verdict | optimal | objective | time |
|---|---|---|---|---|
| c01 | OPEN | — | — | 63 s |
| c02 | EARNED | true | 5.6 | 2 s |
| c03 | REFUTED | — | — | 3 s |
| c04 | EARNED | false | 0.17 | 704 s |
| c05 | EARNED | true | 203.9 | 1 s |
| c06 | EARNED | false | 1.16 | 469 s |
| c07 | REFUTED | — | — | 1 s |
| c08 | EARNED | true | 137 712.3 | 8 s |
| c09 | EARNED | true | 6380 | 20 s |
| c10 | EARNED | true | 0.0236975 | 131 s |
| c11 | REFUTED | — | — | 142 s |
| c12 | EARNED | true (over the thinned catalog) | 1.16 | 204 s |
