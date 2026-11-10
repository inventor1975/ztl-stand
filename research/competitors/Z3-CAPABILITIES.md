# Z3 capabilities and limits — inventory (research, 2026-11-09)

Legend: **[V]** = read from a source fetched in this session (URL given); **[M]** = from memory / not re-verified now.
Caveat: pages were read through a summarising fetcher, not raw; quotes are as reported by it. Version facts below come from
Z3 RELEASE_NOTES.md (master) and the GitHub releases page: latest tagged release seen = z3-5.3.3 (published 29 Oct 2026); RELEASE_NOTES already has a 5.4.0 section (so master is ahead of the last tag). Release pages themselves carry no feature text; features come from RELEASE_NOTES.

Primary sources:
- Z3 guide: https://microsoft.github.io/z3guide/ (pages Arithmetic, Strings, Quantifiers, Bitvectors, IEEE Floats, combining objectives)
- RELEASE_NOTES: https://raw.githubusercontent.com/Z3Prover/z3/master/RELEASE_NOTES.md
- Releases: https://github.com/Z3Prover/z3/releases ; repo: https://github.com/Z3Prover/z3
- Z3 internals draft: https://z3prover.github.io/papers/z3internals.html
- nlsat paper: Jovanović, de Moura, "Solving Non-linear Arithmetic", IJCAR 2012, https://leodemoura.github.io/files/nlsat.pdf

## 1. Theories and logics
| Area | Status | Source |
|---|---|---|
| Linear real/int arithmetic | Supported; simplex-based LRA, branch/cut for LIA. Release 5.3.2: "Faster QF_LRA simplex and bound propagation". | [V] RELEASE_NOTES |
| Nonlinear real (NRA) | Guide: "Nonlinear real arithmetic is very expensive, and Z3 is not complete for this kind of formula"; may return unknown/loop. Methods listed: "Model based CAD, Incremental Linearization". The nlsat engine (MC-SAT-guided CAD, Tarski fragment) is decidable in theory; source header: complete for NRA, "limited support for integers". NLSAT used one-shot and as end-game solver inside CDCL(T). | [V] guide Arithmetic; [V] Z3 internals; [V] nlsat_solver header via search. Note the tension: algorithm complete, product "not complete" in practice (resource limits, tactic routing) — my reading. |
| Nonlinear integer (NIA) | Undecidable (guide); Z3 answers many, but "there will always be some formula it fails to answer". | [V] guide Arithmetic |
| Transcendental (exp, sin, log...) | **Incomplete, numerical, no decision procedure.** Guide: transcendental reasoning "does not provide an exact, complete decision procedure"; may return unknown. Guide warns the default QF_NTA route in 5.3.1 returned `sat` for `(<= (exp x) 0.0)` (mathematically false) while the `smt` tactic refuted it ("Do not treat a result from one route as validation of another"). Release notes: 5.3.0 corrected bounds; 5.3.1 "Fixed unsound nonlinear exponentiation bounds (with F* soundness proofs)"; 5.3.3 "Fixed incorrect transcendental results"; 5.4.0: "General transcendental solving remains incomplete." So support is recent, still maturing, and has had soundness bugs. | [V] guide Arithmetic; [V] RELEASE_NOTES |
| Complex numbers | Native Complex arithmetic reduced to Real pairs (5.3.1). | [V] RELEASE_NOTES |
| Bit-vectors | Arbitrary width, SMT-LIB BV; int<->BV mixing has "significant overhead". (Bit-blasting + SAT core is how it is solved — [M]; the guide page does not say.) | [V] guide Bitvectors; [M] |
| Floating point | SMT-LIB IEEE-754 theory, rounding modes; algebraic laws fail (non-associativity). Solving by bit-blasting to SAT [M]; guide gives no method. | [V] guide IEEE Floats; [M] |
| Arrays, datatypes, UF | Supported (arrays, ADTs, EUF with congruence closure). | [V] internals TOC |
| Strings/sequences/regex | Unicode strings, regex, replace variants, `str.power` (5.3+). Default `seq` solver; also `z3str3` (no sequence extensions). Guide: string equalities solved by an incomplete heuristic solver, "far from a decision procedure"; length+sequence+regex combination undecidable in general. | [V] guide Strings |
| Quantifiers | E-matching with patterns/multi-patterns (NP-complete matching, term indexing, matching-loop heuristics); MBQI (counterexample-guided; models returned as functions). Decision procedure only on fragments: EPR, stratified sorts, array property fragment, list fragment, essentially-uninterpreted, quantified BV (finite expansion). Otherwise undecidable; satisfiable-only-by-infinite-model formulas "will likely diverge". Higher-order instantiation off by default. | [V] guide Quantifiers |
| Recursive functions | `define-fun-rec` etc. exist (unfolding-based, incomplete); also Horn clauses via Spacer. Not covered by the page I fetched. | [M] |
| Quantifier elimination | `qe` tactics exist; 5.4.0: "QE before optimization". | [M]/[V] RELEASE_NOTES (5.4.0 line) |

## 2. Engines and speed techniques
- CDCL(T) core with own SAT solver; theory solvers; model-based theory combination; relevancy filtering; dynamic Ackermann; iterative deepening for finite models. [V] internals TOC.
- NLSAT (MC-SAT), SPACER (Horn/CHC), QSAT (quantified). [V] internals TOC. nlsat progress: single-sample cell projection (4.13.1), "Level wise algorithm for projection" (4.15.5), more tuning 5.0.0, resource limits on common-factor exploration (5.3.2). [V] RELEASE_NOTES.
- Tactics/preprocessing + tactic combinators; incrementality (push/pop, assumptions) [V] internals TOC lists "incrementality" and "incremental tactics"; details [M].
- Parallel: cube-and-conquer `parallel.enable=true` for select theories e.g. QF_BV (4.8.0); "shared search tree" for `smt.threads=k` (4.15.4); shared backbones (5.0.0). [V] RELEASE_NOTES. No built-in portfolio over *different solvers* — portfolio is via tactics/`par-or` [M].
- Known weak spots: guide says NRA "very expensive"; nonlinear with many variables, non-linear integer, strings with length+regex, quantifier-heavy problems (matching loops, divergence), mixed BV/Int. Quantitative benchmarks not fetched — **not verified**; general SMT-COMP knowledge [M]: cvc5/Yices often beat Z3 on NRA families; Z3 strong on BV/UF/LIA/Horn.

## 3. Optimization (νZ)
- Objectives: maximize/minimize arithmetic terms (incl. BV), MaxSMT soft constraints with weights/groups. [V] guide combining objectives; MaxSAT algorithms (core-guided, MaxRes, etc.) [M].
- Combination: **lexicographic** (default, by declaration order), **box** (`opt.priority=box`, each independently), **pareto** (`opt.priority=pareto`). [V] guide.
- Nonlinear: from 5.3, nlsat-backed Pareto enumeration for pure nonlinear real problems (`opt.pareto_nlsat`); guide notes it "does not make every nonlinear Pareto front finite" and search may not exhaust a continuous front. Comparisons use exact algebraic values. [V] guide.
- 5.4.0: Pareto points on continuous Real fronts, "unbounded curve certification" (integer/mixed objectives along polynomial curves, `opt.optsmt_unbounded_curve`), QE before optimization; 5.3.3: MaxSMT bounded by LP relaxation. [V] RELEASE_NOTES.
- Guarantee: for linear (and exact-solved) problems optimum is exact, with infinitesimals/infinity for open/unbounded [M]. For nonlinear/transcendental objectives no general optimality guarantee; "unknown"/timeout possible [V by inference from section 1; guide's optimization page for unbounded/infinitesimals not fetched — unverified].

## 4. Models / counterexamples
- `sat` returns an explicit model (values per constant, function interpretations); internals: "Models are explicit and mainly value-based", few knobs over model values. [V] internals TOC.
- Reals: nonlinear models can contain algebraic numbers (root objects with rational isolating intervals; guide notes this). `eval` with `model_completion`. Counterexample for ∀ property = `sat` of the negation (∃ of violation) — model *is* the violating point (standard use) [M]. Quantified `sat` models are via MBQI [V].
- CEGAR-style: used internally (MBQI, QSAT; Spacer is IC3/PDR-style with CEGAR flavour) [V/M]; external CEGAR loops are user-written with push/pop+assumptions [M].
- Model quality: no "minimal" or "central" point guarantee; for boxes the point can be on a boundary [M].

## 5. Explanations
- Unsat cores: via assumptions (`check(assumptions)` / `unsat_core`) [M]. Minimisation is *not* default: options `core.minimize` / `sat.core.minimize` / `smt.core.minimize` (names have changed across versions; per search: 4.8.3 notes use `smt.core.minimize`/`sat.core.minimize`, later config lists `core.minimize`, `core.minimize_partial`) — current accepted name **not verified**. Result is "small", not guaranteed minimum [M].
- Proofs: legacy proof objects (`proof=true`, `Z3_solver_get_proof`) — coarse format; clausal proof logging `sat.smt.proof`/`solver.proof.save` (older) and, new in 5.3.2, opt-in `smt.clause_proof`. [V] RELEASE_NOTES + search.
- Independent checking — the picture as of 5.4.0 per RELEASE_NOTES [V]:
  - Built-in clause-proof checker (4.11.2), self-validators for EUF, Tseitin, arithmetic (4.12.0); **bit-vector inferences trusted without validation**.
  - Lean reconstruction: began QF_LRA and QF_UF (5.3.0), UF + linear Real/Int (5.3.2), mixed Int/Real, remainder, pseudo-Boolean (5.4.0). So Lean proofs exist only for fragments.
  - "Cherry" standalone checker and F*/Pulse proof-DAG checker (Farkas certificates, finite fields, BV, arithmetic, total Real exponentiation spec). RELEASE_NOTES states these additions "do not establish unconditional end-to-end SMT-LIB soundness"; unsupported steps stay as explicit obligations.
  - Reading: checkability is real but partial and new (2026); nonlinear (nlsat) and transcendental refutations are not covered by anything I found. Not verified beyond RELEASE_NOTES text.
- Contrast cvc5: emits proofs in Alethe, Lean 4 and LFSC; Alethe has independent checker Carcara and reconstruction in Isabelle/Coq (Isabelle-dev Oct 2025 report: cvc5/Alethe route still behind an experimental flag). Isabelle's older Z3 proof reconstruction exists for an old Z3 version (may not work with recent Z3). [V] search: https://arxiv.org/pdf/2107.02354 , https://drops.dagstuhl.de/storage/00lipics/lipics-vol352-itp2025/html/LIPIcs.ITP.2025.26/LIPIcs.ITP.2025.26.html , https://mailman46.in.tum.de/pipermail/isabelle-dev/2025-October/018199.html
- Interpolants: Z3 had `Z3_compute_interpolant` removed in ~4.8; Spacer gives CHC-based interpolation [M, not verified].

## 6. Interfaces and licence
- Licence: MIT. Bindings: .NET, C, C++, Java, Go, OCaml, Python (`pip install z3-solver`), Julia (Z3.jl), JS/TS/WASM (npm `z3-solver`), Smalltalk; Rust via external z3.rs. Input: SMT-LIB2, plus Horn/datalog and OPB/WCNF-style files [M]. [V] https://github.com/Z3Prover/z3 (12.9k stars).

## 7. Engineering use
- Verified-from-sources: nothing specific fetched on tolerance analysis/CAD/FEA. Treat as **not verified**.
- [M] Known uses: Windows/Azure (network config, SLAM/SDV driver verifier), Dafny/Boogie, Viper, SAW/Cryptol, Alive2 (named in internals as a tactics use case [V]), AWS Zelkova/Tiros, symbolic execution (KLEE variants, angr), Lean/Isabelle hammers, F*, hybrid-systems front ends via encodings (bounded model checking of hybrid automata is usually done with dReal/KeYmaera X, not Z3).
- Worst-case over a box of real parameters: expressible as ∃ violation within ∀-free bounds (QF_NRA, nlsat) or as optimisation (box/lex) for polynomial functions; with exp/sin only incomplete numerics (section 1). Quantified (∀ over box) NRA possible via QSAT/qe-nlsat, expensive [M].

## 8. What Z3 does NOT do (support noted)
1. No sound, complete handling of transcendentals; had unsound answers fixed in 5.3.x, still "incomplete" [V].
2. No guaranteed numeric enclosures / interval certificates for exp/sin/log (contrast dReal, MetiTarski) — my reading; consistent with [V] guide text.
3. Proof checking partial: Lean/F*/Cherry cover fragments; BV trusted; no certificate story for nlsat found [V RELEASE_NOTES; absence = my reading, "not found" ≠ "absent"].
4. No notion of provenance/trust/source of inputs, no physical units/dimensions — inputs are untyped numbers in Int/Real sorts (my reading; nothing in docs about either).
5. No built-in tolerance/uncertainty-propagation semantics; "unknown" is an answer for resource/incompleteness, with no degree of confidence (my reading).
6. Strings and quantifiers: heuristic, may diverge [V].
7. Results can differ between tactics/routes [V guide warning].
8. Optimality for nonlinear objectives: no general guarantee, Pareto fronts may not be exhausted [V].

## 9. Competitors (one line each; [M] unless link)
- **cvc5**: transcendental theory (`QRAT`/append `T`: sin, cos, tan, exp via incremental linearization), proofs in Alethe/Lean4/LFSC, SyGuS, finite-model finding; https://cvc5.github.io/docs/latest/theories/transcendentals.html [V]
- **Yices 2**: MCSAT incl. NRA; 2026 arXiv prototype of MCSAT modulo transcendentals (sin, exp) in Yices2 vs MathSAT/cvc5/dReal: https://arxiv.org/pdf/2606.00697 [V]; often fast on QF_BV/LIA.
- **MathSAT 5**: incremental linearization for transcendentals, interpolation, AllSMT.
- **dReal**: delta-complete decisions over nonlinear incl. sin/exp via interval constraint propagation (answers "unsat" soundly or "delta-sat"); the thing Z3 lacks for enclosures; https://libraries.io/pypi/dreal/4.19.3.1 [V that sin is accepted].
- **MetiTarski**: proves real inequalities with special functions (exp, ln, sin, cos) by reducing to RCF via polynomial bounds, with QEPCAD/Z3 backends; proof-oriented.
- **Ibex**: interval-arithmetic constraint solver with rigorous enclosures for global optimisation/continuous CSP.
- **KeYmaera X**: deductive hybrid-systems prover (differential dynamic logic), proves safety of continuous dynamics (ODEs), small trusted kernel; Z3 has no ODE concept.
- **Gurobi / SCIP (MINLP)**: global optimisation with certified bounds (spatial branch-and-bound), orders-of-magnitude faster on large linear/MIP optimisation, dual bounds proven; no logic/theory combination.

## Honest gaps in this inventory
Not verified: benchmark numbers; guide optimization page on unbounded/infinitesimals (404 on guessed URLs); current core-minimization option names; interpolation status; industrial-user list (memory); exact semantics of the 5.4.0 items beyond RELEASE_NOTES one-liners.
