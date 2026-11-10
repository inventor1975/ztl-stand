# Z3 against ZTL + ztl-stand — feature by feature (2026-11-09)

Z3's side: Z3-CAPABILITIES.md (Sonnet scout, 2026-11-09; [V] verified from a fetched source, [M] memory). Ours: the
code at ZTL 9dce6f3 / ztl-stand be29574, and the duel re-run of today (bench/competitors/results.jsonl, rows after the
18.10 round; stand vs Z3 on corners_peak and chain).

| | Z3 (5.3.3) | ZTL + stand | who leads |
|---|---|---|---|
| Linear real arithmetic | simplex, complete | exact, complete (linear systems by ZTL's own zlin) | par |
| Nonlinear polynomial reals | nlsat/CAD, "not complete", "very expensive" [V] | interval + exact readings, cover trees, corners + critical points | Z3 on speed; MEASURED today: our polynomial corners 0.16–0.73 s vs Z3 0.01–0.07 s (10–30×) |
| exp, ln, sin, cos, atan, Bessel, integrals | "incomplete, numerical, no decision procedure"; an UNSOUND answer (`exp x <= 0` sat) fixed in 5.3.x [V] | proved brackets, every reading checked against Lean witnesses (exp/ln/sin/cos/atan); Bessel/Kelvin and nested integrals by certified series/quadrature (premises said, no Lean witnesses yet) | **ours** |
| Counterexamples | the model of the negated property [V] | REFUTED with a concrete point recomputed exactly; MEASURED today: chain refute 2–128 all REFUTED (0.3–26.7 s) vs Z3 SAT (0.02–3.7 s) | Z3 on speed (7× at 128), par on capability (the 18.10 "OPEN" is gone) |
| Optimization | νZ: lexicographic/box/Pareto, MaxSMT; no general optimality guarantee for nonlinear [V] | single objective; `optimal: true` only when every cheaper design is refuted; continuous: a PROVED lower bound (LP weak duality, its rule in Lean ZLP) | ours on guarantee; Z3 on multi-objective (Pareto, MaxSMT) — **a gap of ours** |
| Explanations | unsat cores (minimisation not default) [V]; interpolants [unverified] | minimal conflicts by deletion (complete to 8 requirements); zdiagnose: proved conflicts → diagnoses (zbackward) | ours (minimal, named, physics-level); Z3 interpolants we lack |
| Proofs | Lean reconstruction only for UF + linear Int/Real fragments; "not end-to-end soundness" [V]; nothing found for nlsat or transcendentals | Lean theorems, zero axioms, for requirements incl. nonlinear, exp/ln/sin, tables, implicit roots (ZBound*, ZBoundIf); 22 of 23 in blind round 7 | **ours** |
| Software theories (bit-vectors, arrays, strings, datatypes, quantifiers, FP) | yes | no | **Z3** — not our field |
| Complex arithmetic | native since 5.3.1 [V] | no (Kelvin functions as real series instead) | Z3 — a small gap |
| Provenance / trust of inputs, cures, IF STABLE, expiry | no [reading] | yes (EARNED / ON CREDIT / OPEN, what to check, dirty parameters) | **ours, alone** |
| Physical units, tolerances as data | no [reading] | yes (unit check; worst case over tolerance boxes) | **ours** |
| Engineering formats | SMT-LIB / APIs | bricks, SPICE netlists, BEAM4 decks, voxel volumes | ours (for engineering) |
| Speed overall | C++, 20 years | Python + exact checks; compiled Lean searches since today | **Z3**: 7–30× on today's axes |

## What to take from it
- Our real gaps against Z3 in OUR field: SPEED (a constant factor 7–30×, profiling + compiling hot paths), and
  MULTI-OBJECTIVE optimization (Pareto fronts, soft requirements à la MaxSMT). Complex arithmetic is small.
- Where Z3 is weak, we are strong by construction: transcendental soundness (Z3 shipped an unsound exp answer), proof
  certificates for nonlinear results, provenance.
- Not to chase: Z3's software-verification theories (bit-vectors, strings, quantifiers) — a different field.
