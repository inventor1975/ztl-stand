# zpy AI experiment — round 2 protocol (written 2026-11-10, BEFORE any model ran)

**Why a round 2.** Round 1 (RESULTS.md): no difference in correctness, zpy code ~30 % shorter; the tasks were stated as
formulas and read-once. Round 2 (TASKS2.md): rules in prose, inputs REPEATED inside a rule (tiers, selectors,
complementary comparisons).

**Two truths, both reported** (the curator, 2026-11-10: «В этом весь ЗТЛ» — EARNED IF STABLE is not EARNED; zpy keeps
the judge's semantics and does not upgrade it):
- CLASSICAL — what the task text asks ("do not ask for a check that could not change the outcome"): by completions.
- ZTL — the judge's disposition on the rule as one ZTL formula (grade2.py ZTL_RULES).
They differ in exactly 27 of 2550 cases — the repeated inputs (checked on references before the runs: hand Kleene and
a zpy reference 2523 classical / 2550 ZTL; brute force over completions 2550 classical / 2523 ZTL).

**Arms, runs, model, rules for the agents:** as round 1 (A plain, B over zpy; A1 A2 B1 B2; Sonnet; one file each).

**What would be a finding.** SILENT > 0 in either truth (an unverified input decided) — the layer's target. The
27-case split tells which reading a model takes: classical (brute force / reasoning by cases) or per-occurrence (Kleene
/ zpy). Neither split is "wrong" by itself; the task text asks the classical one.

**Limits said now.** Two runs per arm; prose rules can be READ differently by a model (a misreading shows as WRONG or
SILENT, and is reported per task, not explained away).
