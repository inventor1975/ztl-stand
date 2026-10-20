# Real problems, round 4 — results (2026-10-12)

**Setup.** As round 3 (six Sonnet agents, one real published problem each, the uncertainty from the source itself),
with the areas chosen for CHAINS of devices and continuous amounts: components (BRICKS 7d: interface, bands,
choose, a component's own slots as parameters, affine contracts) and nonlinear continuous amounts. A chain was to be
expressed both as components and as one flat brick. The stand was frozen at ztl-stand 74aa32a, ZTL fd6593d.

| # | area | source | published answer vs the stand | who is right |
|---|---|---|---|---|
| k01 | regulator output tolerance | TI SNVA112A (AN-1378) | AGREE: of 12 Vref x resistor grade pairs, exactly the 5 the table puts within +-3 % are EARNED; Table 5 (largest R2) six of six exact; inverted Table 1 by `find`: 2.02 % / 1.02 % (table 2.0 / 1.0) | **the stand** on the table's cells: the printed worst cases are 0.001-0.28 points ABOVE the exact worst case of their own formula (3.29 printed, 3.26 exact; hand.py), one apparent misprint |
| k02 | amplifier + ADC error budget | eCircuit Center, Error Budget Analysis | AGREE: offset 2.2 mV PASS (stand +-2.215), gain 1.4 % FAIL (stand -1.386 / +1.409); `find`: largest Vref tolerance 0.096 % — the page's suggested 0.1 % reference gives 1.0031 %, just short | — (the page sums first-order sensitivities; the stand proves the true worst case) |
| k03 | regulator thermal stack | ADI/LT LT1083 datasheet | AGREE on the verdict (both junctions pass); the printed 118 C for the control section is 115.8 by the sheet's own numbers (75 + 24 x 1.7; checked by Logic1) — 118 matches the K package's 0.6 C/W | **the stand** on the 118 C |
| k04 | buck inductor, 1/L | TI TPS54331 datasheet | AGREE at the nominal point (5.68 vs 5.7 uH); over the sheet's own spreads (Vref, fsw, Vin) the chosen 6.8 uH meets peak and RMS ratings but misses the 0.3 ripple ratio (worst 0.403; 9.18 uH needed) | NOT COMPARABLE (the sheet gives a nominal point only); Logic1's rough check 0.403 / 9.13 uH (simpler model) |
| k05 | motor + gearhead + conveyor | Oriental Motor sizing reference | AGREE on ratio 50 / 7.3 in/s — but only near the no-load speed (the agent's own straight-line assumption); the source's ratio range 39.5-51.5 read as "any speed 1450-1550" is wrong: the window is 42.16-48.20 (checked by Logic1), 50 outside | **the stand** on the ratio range (the source pairs the slowest motor with the slowest drum) |
| k06 | pump TDH | PDH Academy, Centrifugal Pump Selection, Ex. 3 | AGREE: 45.2 / 34.0 ft (stand 45.21 / 33.96, hand 45.2076 / 33.9676) | — (nearly trivial: only the static head moves) |

**No wrong verdict.** Work and --dev agreed on every brick run in both. Three published numbers are wrong by the
sources' own data (k01 table cells, k03 118 C, k05 ratio range read as a guarantee); Logic1 re-checked k03 and k05
by hand, k01 by the agent's hand.py.

**What this round shows — components are sound but LOOSE.**
- Every component version was EARNED where the flat brick was, never REFUTED wrongly — but wider: k02 about 2x,
  k04 9.75 vs 9.18 uH and 5.25 vs 4.92 uH, k01 0.00013 V, k06 45.36 vs 45.22 ft.
- The cause, found by k01, k02 and k04 independently: a band's output range and an affine contract's remainder are
  the stand's OUTER reading of the expression over the whole band. A name that appears twice (R1 in
  Vr*(R1+R2)/R1, Vo*(Vin-Vo)/Vin, out - k*in) does not cancel. k01: remainder +-0.19 V where +-0.02 V is true —
  every candidate OPEN until the law was rewritten and the bands cut to the answer.
- Bands are cut by hand, and the answer depends on the cut (k04: 15.5 / 5.75 / 5.25 uH for coarse / medium / fine).
- A band that only shares an EDGE with the arriving range counts as touched (k01, k03, k05): it adds a band and
  loses the affine form.

**Gaps found.**
- COMPONENTS (fix before anything else):
  - contracts by an outer reading: certify the outputs' and the remainders' ranges (tight), not read them;
  - edge-touching bands: touched only with a positive overlap;
  - bands chosen by hand: no help from the stand (an "auto" band = the arriving range itself?);
  - a component's chosen part reaches the system only through `cost` (k05 put cost = ratio);
  - a continuous parameter inside a component (v2; k03, k04 moved it to the system);
  - when every combination is OPEN, the reason is cut short (k01).
- STAND: a continuous brick refuses a requirement bound that names a field (`DEV.Tc`), though section 6 allows it
  (k03); `find` with modes (k02).
- UNITS: `oz`, `gpm` missing; `rpm` works as 1/60 s^-1, undocumented (k05, k06).
- DOCS (BRICKS.md 7d): a component with no inputs works, undocumented (k01, k05, k06); a band is judged over its
  whole box, not over what arrives (k04); what an affine contract buys and when it does not apply.

**Cost.** 6 agents, 943 520 tokens (145 115 to 173 831 each), 6.7 to 9.3 min each.
