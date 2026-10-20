# ztl-stand

(Named universal-stand until 2026-10-11; renamed by the curator. The package stays `ustand`, and bricks
written as `universal-stand/1` are read as before.)

**Start with SPEC.md** — the contract, how an AI agent should call the stand, what was measured against Z3, cvc5,
dReal and SCIP, and the limits. The full brick syntax: **BRICKS.md**. Licence: Apache-2.0 OR MIT (NOTICE). Needs ZTL
(github.com/inventor1975/ZTL) cloned beside this repository, or `USTAND_ZTL` pointing to it.

A foundation, not a product aimed at one goal. The far horizon: "here are the requirements and the factory's
capabilities — give me a realisation, or tell me why it is impossible". The start is the minimum that can be
leaned on.

## Bricks in (JSON)

The full reference for writing them, with pitfalls: **BRICKS.md**. Gaps found so far: **GAPS.md**.

| Brick | Carries |
|---|---|
| quantity | a name, a unit and a role: `given` (fixed by the world, optionally with a tolerance — must hold for every value in it) or `derived` (follows from the laws) |
| slot | a place in the design (`R1`) and the catalogs it may take an item from — the choice (there exists) |
| catalog | what the factory has: ITEMS, each with several FIELDS, each field with its own nominal and tolerance (resistance 1k ±1%, power rating 0.25 W). An item in a slot creates the quantities `R1.R`, `R1.P`. Rows are listed, or generated from an E-series |
| law | one equality in ZFL syntax, with its source (`"Vin - Vout == I*R1.R"`, "Ohm's law"; `"P1 == I*I*R1.R"`, "Joule heating") |
| requirement | a derived quantity, `within` / `<=` / `>=`, and a bound: a number, or a quantity such as `R1.P` (its least favourable value; at a witness point, its value there) |

Numbers are strings read as exact fractions.

## Verdict out (JSON)

- **EARNED**: a design (an item in every slot) whose required quantities stay inside the requirements for every value
  the tolerances allow, shown by SOUND ranges (a sound outer range suffices; exactness is needed only to refute), and
  confirmed by the checker: every corner inside, exact ranges equal, each nonlinear definition inside by its own bound.
- **REFUTED**: every design fails at a concrete point (its nominal, or a corner of its box). The closest design, its
  violating point and the overshoot are returned, and the point is recomputed by the checker.
- **OPEN**: neither could be shown.
- **STAND FAULT**: the judge and the checker disagree. The stand reports it instead of a verdict.

## Who does what

- **Judge: ZTL** (`ustand/judge_ztl.py` calls `ZTL/znumsolve.py` as it is). Its ranges are sound (never too narrow),
  which is enough to EARN; a range ZTL itself marks exact is also attained, which a refutation relies on. Whatever
  mathematics ZTL learns to prove, the stand inherits.
- **Checker** (`ustand/checker.py`) shares no code with the judge. It parses the laws itself and does exact rational
  arithmetic.
  - It always confirms a witness point.
  - It confirms a range by enumerating corners. That is the true range only in the class where every derived
    quantity is monotone in each single toleranced quantity, which is the judge's own exact class.
  - Corner enumeration is 2^n, so it is for small cases only.
- **Definitions** (`P1 == I*I*R1.R`): since ZTL 3a296b5 the judge bounds them itself (interval reading, sound, may be
  wide). The stand sends ZTL the linear laws first, then the definitions with the linear unknowns as the boxes ZTL
  gave them.
- **Forward step** (`ustand/forward.py`): a fallback, used only where ZTL leaves a quantity unbounded. It bounds by
  interval arithmetic and labels the result "outside ZTL". It is written separately from the checker.
- **Stand** (`ustand/stand.py`):
  - enumerates designs over the catalog;
  - drops a design whose nominal point already fails (that point is its witness);
  - judges the rest and compares the result with the requirements.

## Limits

The first version (2026-10-09) was linear-only and named no conflicts; both have changed (nonlinear laws
with functions, implicit laws, continuous amounts, certificates for an extreme inside the box, `minimal_conflicts`,
optimality). The current limits are in SPEC.md §7 and GAPS.md.

## Run

    python3 -m ustand.stand examples/divider-1pct-req-1pct.json
    python3 -m tests.test_stand            # USTAND GREEN

The examples are a 5 V → 2.5 V divider from the E24 series:

| Requirement | Parts | Verdict |
|---|---|---|
| ±1% | 1% | EARNED |
| ±0.5% | 1% | REFUTED |
| ±0.5% | 1% or 0.1% | EARNED on 0.1% parts |
| ±1%, ≥ 24 mA, each R within its power rating | 1% at 1/16 W | REFUTED: at R1 = R2 = 99 Ω, P1 = 25/396 W > 1/16 W |
| the same | 1% at 1/16 W or 1/4 W | EARNED: 27 Ω / 27 Ω at 1/4 W, P ≤ 0.2385 W |
