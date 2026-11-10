# zpy AI experiment — protocol (written 2026-11-09, BEFORE any model ran)

**Question.** Does a model write decision code that decides unverified inputs SILENTLY less often when it writes over
zpy (ZTL as a layer of Python: ZTL/zpy.py) than in plain Python?

**Tasks.** TASKS.md — six decision functions; inputs verified / claimed / unknown; three outputs; one rule for all
(positive only if the condition holds whatever the unverified inputs are). Every rule is read-once, so a correct
plain-Python solution is fully possible (a hand-written three-valued solution scores 6250 / 6250 — checked).

**Arms.** A: plain Python. B: the same, over zpy (the model reads ZTL/zpy.py). Two independent runs per arm (A1, A2,
B1, B2), model Sonnet, identical prompts except the arm's line. Each writes runs/<run>/solutions.py and nothing else.

**Grader (sealed with this commit).** grade.py: every case enumerated (6250), CLASSICAL ground truth by completions,
independent of ZTL. Validated before the runs on three references: hand three-valued 6250/6250; naive "a claimed value
is true" 2134 correct / 4116 SILENT; zpy reference 6250/6250.

**Measures.** SILENT (definite where the truth is needs_check — the defect the layer targets), WRONG, CAUTIOUS, BAD,
correct; zpy_lint findings.

**Limits said now.** 2 runs per arm is a SCOUT, not statistics. The tasks are read-once — the case where a correct
hand-written solution is easiest; a difference here is a lower bound on the layer's effect, not its size. The model
sees the rule stated precisely — a vaguer specification is a different, later experiment.
