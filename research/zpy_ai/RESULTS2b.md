# zpy AI experiment — round 2b results (2026-11-10)

Sealed before the runs: PROTOCOL2b.md (35b15bc, zpy.py sha256 4e8cabf4a339a22a…); grader grade2.py unchanged (9d49a65).

| run | arm | lines (code only*) | classical correct / 2550 | SILENT | how it decided |
|---|---|---|---|---|---|
| A1, A2 (round 2) | plain | 65, 65 (48, 50) | 2550, 2550 | 0, 0 | brute force over completions |
| B1, B2 (round 2) | zpy, old API | 76, 84 (59, 62) | 2550, 2550 | 0, 0 | routed around the layer (hand label reading / own enumeration) |
| **B3, B4 (round 2b)** | **zpy, named path** | **83, 71 (62, 46)** | **2550, 2550** | **0, 0** | **zpy.decide(..., if_stable="classical") — the named path, no bypass, no hand enumeration; zpy_lint 0** |

\* code only = without comments, docstrings and blank lines (round 1, for comparison: plain 55, 55; zpy 41, 38).

**What it says.** With the classical path legal and named, both models used it as intended — the workaround of
round 2 is gone, every answer right, each decision's path on record (`.path`). Size: comparable to plain Python, not
smaller (46 and 62 code lines against 48 and 50). Round 1's advantage (~28 % fewer code lines) came from the
three-valued connectives the layer carries; with repeated inputs a plain brute force over completions is as short.

**So far, over three rounds (2 runs each, a scout):** no silent decision in either arm; the layer's gain measured is
size on read-once rules and NAMED PROVENANCE of each decision (which path settled it); its cost was a workaround,
removed by the named path. **Cost:** 133 k subagent tokens (66.5 + 66.5).
