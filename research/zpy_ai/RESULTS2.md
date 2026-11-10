# zpy AI experiment — round 2 results (2026-11-10)

Sealed before the runs: TASKS2.md, grade2.py, PROTOCOL2.md (commit 9d49a65). Sonnet, four runs, graded once.

| run | arm | lines | classical correct / 2550 | SILENT | CAUTIOUS | ZTL correct / 2550 | how it decided |
|---|---|---|---|---|---|---|---|
| A1 | plain | 65 | 2550 | 0 | 0 | 2523 | brute force over every completion |
| A2 | plain | 65 | 2550 | 0 | 0 | 2523 | brute force over every completion |
| B1 | zpy | 76 | 2550 | 0 | 0 | 2523 | zpy claims, but read `.disposition` itself and mapped EARNED IF STABLE -> the positive outcome |
| B2 | zpy | 84 | 2550 | 0 | 0 | 2523 | its own brute force over completions; zpy.decide called inside each completion (decoration) |

**What it says.**
1. No silent decision anywhere (SILENT 0 in both truths' sense of an unverified input decided as known... the 27
   ztl_SILENT are the classical reading of repeated inputs, which the task text asked for).
2. Every run took the CLASSICAL reading the task text asked. Both zpy runs ROUTED AROUND the layer's semantics to get
   it: B1 upgraded IF STABLE by reading the disposition string — the very upgrade the curator rejected the same night
   («В этом весь ЗТЛ»); B2 enumerated completions itself and used zpy only inside. The layer did not stop either:
   reading `.disposition` is legal, and zpy_lint has no rule for it.
3. Round 1's size advantage REVERSED: plain 65 lines vs zpy 76-84. With repeated inputs a plain brute force over
   completions is short and exact; the zpy runs paid for the layer AND the workaround.

**What follows (for the curator to decide, not done).** When the task's semantics (classical) and the layer's (ZTL)
disagree, a model sides with the task and bypasses the layer. Either the layer forbids the bypass (a lint rule:
mapping an IF STABLE disposition to a positive outcome is LAUNDER), or it offers the classical reading by name, or
the tasks for a ZTL language must be stated in ZTL's terms. Two runs per arm.

**Cost.** 248 k subagent tokens (58 + 58 + 66 + 65).
