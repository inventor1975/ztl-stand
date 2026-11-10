# Blind test 7 — setup (written 2026-11-09, before any author ran)

**Asked by the curator, 2026-11-09:** "12 слепых задач соннетом с интернета" — the stand tested on REAL published
problems, now with `--prove`: how many earned requirements become Lean theorems.

**Frozen.** ztl-stand 9a398b7, ZTL 5627be6 (lean build as of that commit). Nothing in either changes until the twelfth
report is in and every brick has been run with `--prove`.

**The writer (Sonnet, internet).** Twelve real published problems with published answers, in areas excluded from every
earlier round (blind 1–6, real 1–4). It never saw the format or the tool. `PROBLEMS.md`: statements only — no
sources, no answers. `work_writer/ANSWERS.md`: sources, published answers, anything the writer added (tolerances,
tightened requirements), its own reference answers and scripts — SEALED: its sha256 is recorded below at the moment the
writer finished; Logic1 does not read it until the stand's verdicts are frozen (feedback_build_blind).

**The authors (twelve Sonnet agents, no internet).** Each gets BRICKS.md, the shipped examples (examples/*.json,
examples/tasks/, examples/components/) and ONE problem; no code, no tests, no GAPS.md, no earlier rounds, no
ANSWERS.md. Each writes `cNN.json` (one brick or more), runs the stand by the prescribed command (3 GB, 900 s per run),
and writes `cNN.report.md` with the sections of round 6.

**Then Logic1** runs every brick with `--prove` at the frozen commits, freezes the table of verdicts and proof counts
(commit), and only then opens ANSWERS.md and compares.

**What is measured.** (1) Verdict agreement with the writer's reference for the problem as written; (2) the proof
count k of n per EARNED verdict, and why each unproved requirement is unproved; (3) what the authors could not express.

**Cost (an estimate, said before the run).** Round 6 measured 1.89 M tokens for the same shape; expect ~2 M.

## Seal
- ANSWERS.md sha256: 4ef250aea1b912104b3064ff5ea4c64a37cd22046fec0a0c43eed76bb67eafe7 (recorded 2026-11-09 18:17 IST, the moment the writer finished; also work_writer/ scripts p1..p12)
