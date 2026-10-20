# Blind test 6 — results (2026-10-12)

**Setup.** As round 5, with this evening's vocabulary in play: components (interface, bands, `"arriving"`, choose,
a component's own slots as parameters, affine and tight contracts), nonlinear continuous amounts (zmin), `find`.
- A writer agent (Sonnet) that never saw the format wrote 12 problems (`PROBLEMS.md`) in domains excluded from every
  earlier round (48 + 12 + the real rounds' problems): six CHAINS of devices (three with one source feeding two
  devices), five limit questions, nonlinear continuous amounts (one through coupled linear balances), three
  impossible by design, two tight (< 1 %). Its reference is its own scripts (corners and fine scans, no proofs),
  answers in `work_writer/ANSWERS.md`, closed to the authors.
- Twelve blind authors (Sonnet), each BRICKS.md, the examples (incl. `examples/components/`) and one problem; no
  code, tests, GAPS or earlier rounds. **Unlike round 5 the prompt said**: express a chain with components, a limit
  with `find`, a continuous amount with a continuous catalog. 3 GB, 900 s per run.
- The stand was frozen at ztl-stand b2d83f1, ZTL 7ef9b6f; nothing changed until the twelfth report was in.

## Outcome

| # | domain | stand | the writer's reference | note |
|---|---|---|---|---|
| 1 | hoist rope + drum | EARNED W-10, D 0.2115 m, 1484.39 EUR, L proved (gap 0.0085) | same | two requirements bounded by the stand's interval reading, not ZTL |
| 2 | two motors on a transformer (chain, tight) | EARNED C50/B63 + C16/B40, 2825.5 EUR, optimal; limit 251.5 <= L < 252 m | same; 251.99 m | components: same answer, 13.5 min vs 47 s; a component price at a placeholder length printed 2068 EUR, no warning |
| 3 | cordless saw pack (chain, limit) | EARNED H25 x4 / M60 / heater, 70 EUR, optimal; limits -16.12 / -15.54 C | same | STAND ERROR on a stalled design's sqrt; optional slot inside a component a STAND ERROR; `valid` on a system law a false BRICK ERROR |
| 4 | pipe heat trace (impossible, limit) | REFUTED at -40 C, conflict {R1, R2, R3}; limit -37.86 C, PIR-40 + T15 | same | the stand's witness corrected the author's own worst corner |
| 5 | compressed-air chain (tight) | EARNED K40 / D50 / 50 mm, 13 880 EUR, optimal | same, +0.77 % | components (S3 only, `"arriving"` bands): identical ranges |
| 6 | solvent extraction (coupled balances) | EARNED E3H / SC / G1200, S 1.3747, 270.657 kEUR (by N, three bricks) | same | **the false EARNED below, also here** (N = 4 run); `timeout` not obeyed |
| 7 | detention pond (impossible) | REFUTED (zmin over A x H, every plate), 24.8 s | same | conflicts found by hand (10 requirements > 8); `timeout` not obeyed |
| 8 | twin-patient oxygen (chain) | EARNED CY10 / RB / RC, 625 EUR, optimal | same | the author did not answer the two limit questions (said nowhere) |
| 9 | cargo lashing (limit) | EARNED S2 x9 + M1, 311 EUR, optimal; limit 26 832 kg | same | no sin (tan form: loose ranges); daN missing |
| 10 | maize dryer + fan (chain) | **FALSE EARNED: DR6 without a fan, 44.02 kEUR, "optimal", gap -0.34** | DR8 without a fan, 51.67 kEUR | **the one wrong verdict** — see below |
| 11 | fleet insurance (impossible) | OPEN (19 of 20 combinations proved without a mix; the last REFUTED alone in 82 s) | impossible, {R1, R4} | the same false EARNED in two relaxed variants |
| 12 | standby generator test interval | EARNED TL + monitoring, tau 1376.78 h, 12.380 kEUR; interval 788..1376.8 h by point runs | same | `find` over tau too slow for 900 s; the interval rests on the author's convexity argument |

**ONE WRONG VERDICT in six rounds (c10; also produced in c06's and c11's variants).** With continuous amounts and
DISCRETE slots, the mix found for one combination was judged with the OTHER discrete slots free; the first
combination it passed in lent its EARNED (and its guaranteed ranges) to the combination named and priced. Present
since continuous choices began (2026-10-10), in the LP and the nonlinear path; unseen until now because a mix
usually passes in its own combination. **Fixed after the round**: each combination's discrete slots are pinned
before its mix is judged; a proved lower bound above an earned cost is now a STAND FAULT. Re-run: c10 EARNED DR8
without a fan, 51.669 kEUR, L 51.6687 — the writer's answer; c06's and c11's repros correct.

**Ten of twelve match the writer** (c11 is an honest OPEN where the answer is "impossible"). Every author's hand
check agreed with the stand's numbers wherever the verdict was right.

**What else this round shows.**
- Components were used where they fit (c02, c03, c05) and matched the flat brick; they are slower (c02 13.5 min vs
  47 s, c03 20x) and say `optimal: false` (a system cannot refute).
- Four authors (c03, c04, c09, c12) kept a second brick because `find` hid the decision — now one brick answers both.
- `timeout` did not stop the nonlinear continuous path (c06, c07, c12): no stop checks there — now there are.

**Fixed after the round (ztl-stand, 2026-10-12):** the pinning (the false EARNED); negative gap -> STAND FAULT;
stop checks in the nonlinear path, scenario cuts and contract tightening; ZTL's reader stopping on an unbounded
name -> no range, said (c03's STAND ERROR); an optional slot inside a component; `valid` on a system law; a
component price reading a system-decided input not given as `cost`; `find` returns the `decision` too; scientific
notation as exact fractions; the unit daN.

**Still open.** sin / cos (a ZTL addition — the curator's word first); find over a continuous amount (c12); an
implicit law with a continuous slot (c07); minimal conflicts over more than 8 requirements (c07); worst-case
objective with a continuous amount (c11); a system of components with modes (c05); a quantity present in some
modes only (c05); "pin this design, find its limit" (c03).

**Cost.** 13 agents, 1 890 886 tokens (writer 220 732; authors 108 573 to 173 321).
