# zpy AI experiment — round 3 results (2026-11-10): MODIFYING working code

Sealed before the runs: CHANGES3.md, grade3.py, bases, PROTOCOL3.md (63e4f7e). Sonnet, four runs, graded once.

| run | arm | lines after | classical correct / 14500 | SILENT | WRONG | CAUTIOUS |
|---|---|---|---|---|---|---|
| A3 | plain (base: brute force, hand-listed numbers) | 71 | 14500 | 0 | 0 | 0 |
| A4 | plain | 74 | 14500 | 0 | 0 | 0 |
| B5 | zpy (base: named path) | 92 | 14500 | 0 | 0 | 0 |
| B6 | zpy | 92 | 14500 | 0 | 0 | 0 |

The trap the grader was validated on (a threshold region forgotten in a hand-listed candidate list: 10 SILENT) was
NOT fallen into: both plain runs added the new thresholds (20000, 10000, 750) to their lists.

## The verdict over all three rounds (ten runs graded, 2 per arm per round — a scout, not statistics)

- **Correctness: NO DIFFERENCE.** Not one silent decision in any run of either arm, in writing from a formula, in
  writing from prose with repeated inputs, or in modifying working code. Sonnet, told the policy plainly, keeps it
  in plain Python as well as over zpy.
- **Size:** zpy shorter only on read-once rules (round 1, ~28 % fewer code lines); comparable or LONGER elsewhere
  (rounds 2, 2b, 3: plain 48-74 vs zpy 46-92).
- **What zpy did give, measured:** each decision's PATH on record (`Decision.path`: ztl / classical / check), a
  refusal that cannot read as "no", and a lint that found 10 latent conflation sites in our own kernel and the
  bypass of round 2. What it did NOT give: fewer errors from a capable model with a clear policy.
- **Not tested** (where a difference may still live): a vague or unstated policy, a weaker model, large multi-module
  code, long edit histories. The diamond, if any, is there; on what was measured, a stone for error prevention and a
  useful tool for provenance.

**Cost:** round 3 255 k subagent tokens (60 + 60 + 67 + 67); all rounds ≈ 880 k.
