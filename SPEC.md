# ztl-stand — specification for AI agents and evaluators

This page is written for two readers:
- an AI model that will call the stand as a tool, turning an engineering question into a JSON "brick" and reading
  the verdict back;
- a person who has to evaluate what the stand does and does not establish.

The full syntax reference is **BRICKS.md**; this page says what the contract is, how to use it, and what was
measured. Every number below is a measurement recorded in `bench/` or `examples/`, with its file named.

## 1. What it is

A design stand. You give it requirements, the physical laws that relate the quantities, the tolerances of what the
world gives, and the catalogue of what may be picked (resistors, beams, mounts, cables, any amount within a
range). The stand answers with one of three things:
- **a design that provably meets every requirement for every value the tolerances allow**;
- **proof that no design in the catalogue can**, with a concrete failing point and the minimal sets of
  requirements that conflict;
- **open**: neither could be shown.

The judge underneath is **ZTL** (Zero-Trust Logic, github.com/inventor1975/ZTL): exact rational arithmetic, sound
interval readings, and certificates (partitions of the box, Farkas multipliers, HC4 contraction) that ZTL's kernel
checks. A claim is never earned from a float, a sample or a solver's say-so.

## 2. The contract

**In.** One JSON file, the brick (§4 below; BRICKS.md for every field).

**Out.** One JSON object on stdout; the field to read first is `verdict`.

| `verdict` | What it means | What to read with it |
|---|---|---|
| `EARNED` | `design` meets every requirement for every value the tolerances allow | `design`, `guaranteed` (a range per required quantity, in `guaranteed_unit`), `how` each range was obtained, `rests_on` |
| `REFUTED` | every design in the catalogue fails at a concrete point | `closest_design`, `its_violating_point`, `value_there`, `overshoot`, `reasons`, `minimal_conflicts`, `each_requirement` |
| `OPEN` | some design could not be decided, none was earned | `designs` (why each one is open) |
| `BRICK ERROR` | the JSON is wrong | the reason and its place (`quantities.Vin.unit`, `laws[2]`) |
| `STAND FAULT` | the judge and the independent checker disagree | never use the result; report it |
| `STAND ERROR` | the stand failed on this brick | a bug in the stand, never a verdict about the design |

**What EARNED rests on.** The tolerances, ranges and catalogue values are the brick's data, taken as stated
(`rests_on` says so: ZTL's disposition is ON CREDIT). The stand proves the consequence of the data, not the data.
A datasheet that lies makes an EARNED design fail in the world. That is the boundary, and the output names it.

**What "proved" covers.**
- Every range used to EARN is a sound outer range: never narrower than the truth. Exactness is needed only to
  refute.
- A refutation's witness point is recomputed exactly in rational arithmetic.
- When the worst case lies inside the box, the stand searches a certificate (a partition) and ZTL checks each
  piece exactly. The search is untrusted; only the check counts.
- `--dev` adds an independent checker on every design. It shares no code with the judge, parses the laws itself and
  does its own exact arithmetic.
- ZTL's kernel rules are kernel-checked in Lean 4 with zero axioms (ZTL/lean; for example `lean/ZConflict.lean`
  for the conflict search's rules and `lean/ZContract.lean` for HC4 contraction). The stand's Python is not
  verified in Lean; its tests are in `tests/`.

## 3. Install and run

    git clone https://github.com/inventor1975/ZTL
    git clone https://github.com/inventor1975/ztl-stand
    cd ztl-stand
    pip install numpy scipy sympy mpmath
    python3 -m ustand.stand examples/divider-1pct-req-1pct.json     # EARNED
    python3 -m tests.test_stand                                      # the suite

- ZTL is found beside this repository (`../ZTL`), or wherever `USTAND_ZTL` points.
- `--jobs N` judges designs in N worker processes. The verdict is the same, only faster.
- `--dev` adds the independent checker on every design and every certificate (slower).
- Developed and tested on Python 3.12.

## 4. The brick, in one screen

```json
{
  "stand": "ztl-stand/1",
  "quantities": {
    "Vin":  {"role": "given", "value": "5", "unit": "V", "ground": "psu"},
    "I":    {"role": "derived", "unit": "A"},
    "Vout": {"role": "derived", "unit": "V"}
  },
  "slots": {"R1": {"from": ["res_1pct"]}, "R2": {"from": ["res_1pct"]}},
  "laws": [
    {"zfl": "Vin - Vout == I*R1.R", "source": "Ohm's law, R1"},
    {"zfl": "Vout == I*R2.R",       "source": "Ohm's law, R2"}
  ],
  "requirements": [{"quantity": "Vout", "op": "within", "value": ["2.475", "2.525"], "why": "2.5 V +-1%"}],
  "catalog": {
    "res_1pct": {"series": "E24", "decades": [1000, 10000], "ground": "datasheet",
                 "fields": {"R": {"series": true, "tolerance": "0.01", "unit": "ohm"}}}
  }
}
```

This is `examples/divider-1pct-req-1pct.json` without its power field. Its answer is EARNED: R1 = R2 = 1 kΩ, with
Vout guaranteed in [2.475, 2.525] V.

| Block | Carries | BRICKS.md |
|---|---|---|
| `quantities` | `given` (fixed by the world, a value or a range, with a `ground`), or `derived` (follows from the laws); always a unit | §1 |
| `slots`, `catalog` | a place in the design and the catalogues it may take an item from; items with fields, each field with its own nominal and tolerance; E-series generated; continuous amounts in a range | §2 |
| `define` | names for expressions of given and catalogue quantities | §3 |
| `laws` | one equality each, ZFL syntax, with its source; `exp ln log10 sin cos tan atan pow sqrt min max` are allowed; implicit laws (an operating point where two curves meet) too | §4 |
| `requirements` | a derived quantity, `within` / `<=` / `>=`, and a bound: a number, a given quantity, a catalogue field or an expression of them | §6 |
| `objective` | `minimize` an expression (a price, a mass): designs are tried cheapest first; `optimal: true` only when every cheaper design was REFUTED; `"case": "worst"` minimises the worst case over the box | §7 |
| `find` | the limiting value of one given quantity (for example, the coldest ambient for which a design still exists) | §7a |
| `network`, SPICE netlist, ANSYS truss deck | resistor networks and plane trusses read directly | §7c, §7f, §7g |
| `components`, `modes` | systems of devices each proved once; requirements that must hold in every operating mode | §7d, §7b |

Numbers are written as strings and read as exact fractions (`"0.01"` is 1/100, not a float).

## 5. How an AI should use it — the loop

1. **Extract** quantities with units and tolerances from the documents (datasheet, drawing, specification). Give each
   given quantity a `ground` that names its source. A value you inferred rather than read is a range you are
   unsure of: write the range, not a guess.
2. **Write the laws** as equalities with their `source`. One physical law per entry.
3. **Write the requirements** with a `why` each.
4. **Run** the stand and read `verdict` first.
5. **Act on the verdict:**
   - `EARNED`: report the design, the `guaranteed` ranges and `rests_on` (what the guarantee depends on).
   - `REFUTED`: read `minimal_conflicts.sets`. Each set must be relaxed or dropped as a whole; a requirement present
     in every set is the cheapest to change. `reasons.largest_contributors` says which tolerance hurts most;
     `verdict_on_window` says when the spread alone is wider than the requirement, so no centring helps. Propose a
     change (a tighter part, another catalogue, a relaxed bound), edit the brick and run again.
   - `OPEN`: say so. Do not report it as a yes or a no. Its `designs` entries say what was undecided.
   - `BRICK ERROR`: fix the JSON at the place named.
   - `STAND FAULT` or `STAND ERROR`: do not use the output; report it.
6. **Before trusting a new brick**, check BRICKS.md §9:
   - `units` should say "checked";
   - every `how` line marked "outside ZTL" is the stand's bounding, not the judge's;
   - a surprising witness can be recomputed by hand, since it is exact.

## 6. What was measured

All on one machine (i9, 24 cores), often with other jobs alongside. Times are an order of magnitude, not a
benchmark. Sources: `bench/competitors/RESULTS.md`, `examples/*/…-RESULTS.md`.

**Round 1: synthetic axes against Z3 5.3.1, cvc5 1.4.2 and dReal 4.21.** 37 instances × 2 (prove / refute), 120 s
each. These are the stand's own home axes: the generators were written around what it does.
- Decided: the stand 74 of 74 after the 2026-10-19 work (70 before), Z3 51, cvc5 40, dReal 19.
- **Wrong verdicts: 0 for every tool.**
- Z3 is far faster on polynomial corners.
- The stand decides rational and transcendental laws, coupled linear systems and networks (grids up to 20×20) where
  the SMT tools time out.

**Round 2: twelve blind bricks written by an independent writer.**
- Full answers: the stand 6 of 6 discrete bricks (design plus optimality, or a proved refutation); Z3 2 (one 10×
  slower, one 3× faster); cvc5 0; dReal 0.
- On the continuous bricks as the full ∃∀ problem ("round B"): the stand 6 of 6; Z3 2; dReal 1; cvc5 0.
- Disagreements: 0.
- On bare refutations the solvers are faster: dReal 0.4 s against the stand's 1.05 s on c07; Z3 0.6 s on c11.

**SCIP 10 (MINLP), posed the usual engineering way.**
- At nominal values it picks a cheaper design on every brick, and the stand refutes every one, because the
  tolerances were ignored.
- At every corner it finds the stand's optimum on the blind bricks, where every worst case lies at a corner,
  usually faster. It lands about 1e-9 outside the bound, and gives no proof.

**The worst case inside the box** (`examples/interior`, `interior_duel.py`):
- i01: power into a load, peaking at RL = Rs.
- i02: a beam with the load anywhere, peaking mid-span.
- i03: mounts, with a resonance inside the speed band.

SCIP-at-the-corners picks a wrong design on all three (the beam 2.4× overstressed). The stand and Z3 find the
optimal design on all three; dReal and cvc5 find designs without proving them optimal.

**Real tasks from published datasheets and application notes** (`examples/real1..4`): no wrong verdict. Disagreements
with the documents' own rounded figures are listed with the exact values, for example ASME B31.3 tube pressure
5106.9 psig proved against 5100 printed.

## 7. Limits — said, not hidden

- **The data is on credit.** EARNED is relative to the tolerances in the brick (§2).
- **Speed.** Most bricks take seconds; the heaviest blind bricks took minutes (up to about 900 s before the
  2026-10-19/20 work, 28–79 s after). Z3 and dReal are faster where their theories fit.
- **OPEN happens.** An interval reading can be too wide to decide, and a certificate search can give up. The stand
  says OPEN instead of guessing.
- **Designs are enumerated** over the catalogue (with grouping and pruning). A very large catalogue is slow.
- **`minimal_conflicts` has a budget** (default 4 runs per requirement, at least 24). `complete: false` means there
  may be other conflicts.
- **Known gaps:** GAPS.md. One example: in `examples/interior/i03`, a catalogue field's tolerance on k is not applied
  by the reader (k is read exact); the resonance is inside the band without it.
- **The stand's own Python is tested, not proved.** The kernel rules it relies on are proved in ZTL's Lean files.

## 8. Reproducing

- `python3 -m tests.test_stand`: the suite (examples and blind bricks with their expected verdicts).
- `bench/competitors/duel.py`, `blind_duel.py`, `round_b.py`, `scip_duel.py`, `interior_duel.py`: the duels. They
  need `z3-solver`, `cvc5`, dReal and `pyscipopt`; raw rows are in `bench/competitors/*.jsonl`.
- Very large run outputs (over 1 MB) were left out of this repository.

## 9. Provenance

Idea, direction and every decision: Vitaly Reznik. The code, the Lean proofs and these documents were written by
Claude (Anthropic, an AI model) under his curation. The blind bricks were written by separate AI sessions that had
no access to the stand's code: they had BRICKS.md and the examples only (`examples/blind*/`). Licence: Apache-2.0 OR MIT (NOTICE).
