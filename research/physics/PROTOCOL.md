# Physics — ZTL's conclusion BEFORE the physical fact, then the check (protocol, written 2026-11-09 19:20 IST)

**The curator, 2026-11-09:** «Давай в физику пойдём… искать будем так: вывод ZTL до физического факта. И сверка так ли
это. Так мы набьём руку и получим метод предсказания.» — «С соннетом и заморозкой принято, делаем.»

**Scope (Logic1's choice, said):** applied physics with stated laws and uncertainties — materials, heat, mechanics,
orbits, optics, nuclear decay, fluids, electromagnetism. Not quantum foundations: there ZTL names a condition, it
predicts no outcome (Hardy, Kochen–Specker, 2026-10).

**Blindness.** Logic1's knowledge ends in June 2026, so every case is a measurement first published AFTER 2026-06-30.
A Sonnet scout (internet) finds the cases and writes them in two parts: `CASES.md` — the system, the laws, the inputs
with their uncertainties and sources, the question; NO measured outcome, NO conclusion of the paper — and
`SEALED/outcomes.md` — the measured values, the paper's own model prediction if any, the source. Its sha256 is
recorded at the moment the scout finishes; Logic1 does not read it until the predictions are frozen.

**No circularity.** An input fitted to, or derived from, the measurement it would predict is NOT an input; the scout
marks every input's origin (independent measurement / literature value / datasheet / fitted-to-this-data) and the
fitted ones are excluded.

**The prediction.** Logic1 writes each case as a brick (ztl-stand), runs it with `--prove`, and freezes, per case:
the verdict on each stated claim (EARNED / REFUTED / OPEN), the guaranteed range of each predicted quantity, and the
Lean theorems. Frozen = committed (hash) BEFORE SEALED/outcomes.md is opened.

**The score, fixed now.**
- HIT: the measured value (its central value) inside an EARNED range. MISS: outside — our error, or the inputs'.
- CONFIRMED REFUTATION: we said the stated laws and inputs cannot reach the measured region and the measurement lies
  outside our range — the model is missing physics (as Giessen BM03, 2026-11-02). Said with what is missing, if known.
- OPEN: no call; it counts as no information, never as a success.
- SHARPNESS: the width of each EARNED range against the measurement's own uncertainty — a range that always hits by
  being wide is worth nothing (materials batch A, 2026-11-01: "everything OPEN, 0 errors, 0 use").
- After the opening nothing is changed in retrospect; a changed model is a new version and a new blind case.

**Cost said before the run:** the scout ~0.3–0.5 M tokens (an estimate).

## Round 2 (written 2026-11-09 20:35 IST, before the scout ran)
- **The HIT rule, corrected after round 1 (not applied to round 1 in retrospect):** HIT iff our range meets the
  measurement's ±1σ interval; SHARP iff our range is narrower than that interval; MISS otherwise. A point prediction
  (no range) is HIT iff within the measurement's ±1σ.
- **ZTL now reads** Bessel J0, J1, Kelvin ber/bei (+ derivatives) and nested integrals with constant inner limits
  (ZTL 268f9c3) — these cases are ZTL's certified floor (Python, sound brackets, premises said in zseries.py), not
  Lean theorems; Lean only where the law is closed-form XE (zbound2lean).
- Files: round2/CASES.md, round2/SEALED/outcomes.md, round2/SEAL.txt; predictions round2/PREDICTIONS.md.
