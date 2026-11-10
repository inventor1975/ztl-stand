# zpy AI experiment — round 3 protocol (written 2026-11-10, BEFORE any model ran)

**Question.** When a model MODIFIES working code — the place silent decisions usually creep in — does it decide an
unverified input silently less often over zpy than in plain Python?

**Setup.** CHANGES3.md: six change requests (new inputs, new tiers/thresholds, overrides). Starting code, copied into
each run directory before the runs: plain arm — round 2's A1 solution (Sonnet's own; brute force over completions
with HAND-LISTED candidate numbers per input); zpy arm — round 2b's B3 solution (Sonnet's own; zpy, named path).
Runs: A3, A4 (plain), B5, B6 (zpy). Model Sonnet. The model edits solutions.py in place and nothing else.

**Grader (sealed with this commit).** grade3.py — grade2's machinery, the CHANGED rules; 14,500 cases; two truths
(classical; ZTL). Validated before the runs: a correct brute force 14500/14500; the same with ONE threshold region
forgotten in a hand-listed candidate list (the plain base's natural failure) 10 SILENT.

**Limits.** Two runs per arm; the two bases differ in style (the plain one enumerates hand-listed numbers, the zpy one
names atoms) — that difference IS part of what is measured, and said.
