# zpy AI experiment — results (2026-11-09)

Sealed before the runs: TASKS.md, grade.py, PROTOCOL.md (commit 8d80763). Model Sonnet, four independent runs.
One harness fix after the runs: the grader was called with relative paths it resolves from the run's own directory
(FileNotFoundError on all four); re-run with absolute paths — the grader's code and ground truth untouched.

| run | arm | lines | correct / 6250 | SILENT | WRONG | CAUTIOUS | BAD | zpy_lint |
|---|---|---|---|---|---|---|---|---|
| A1 | plain Python | 83 | 6250 | 0 | 0 | 0 | 0 | 0 |
| A2 | plain Python | 86 | 6250 | 0 | 0 | 0 | 0 | 0 |
| B1 | over zpy | 60 | 6250 | 0 | 0 | 0 | 0 | 0 |
| B2 | over zpy | 59 | 6250 | 0 | 0 | 0 | 0 | 0 |

**What it says.** NO DIFFERENCE in correctness: with the rule stated precisely and every rule read-once, Sonnet wrote
a correct three-valued (Kleene) solution by hand in plain Python, both times. The protocol said this was the easy
case and a lower bound; the bound is zero. The one measured difference is size: over zpy the code is ~30 % shorter
(59-60 vs 83-86 lines) — the arm A runs each re-wrote the three-valued connectives that zpy carries.

**What it does not say.** Nothing about a vague specification, a rule with a repeated input (where hand-written
Kleene is NOT exact and the completions are needed), code that is modified later, or many modules — the places where
silent decisions are expected to creep in. Two runs per arm.

**Cost.** 243 k subagent tokens (58 + 58 + 63 + 64) — above the estimate given (150-200 k).
