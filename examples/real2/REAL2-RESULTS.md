# Real problems, round 2 — results (2026-10-12)

**Setup.** As round 1 (six Sonnet agents, one area each, one real published problem each, restated in their own
words, a brick written from BRICKS.md and the examples only), with ONE new requirement: the uncertainty must come
from the source itself (datasheet min/max, stated tolerances, accuracy classes) — no invented tolerances. The new
`find` (inverse questions) was available. The stand was frozen at ztl-stand 6f8e34b, ZTL 2a24683.

| # | area | source | published answer vs the stand | who is right |
|---|---|---|---|---|
| s01 | O-ring groove stack-up | JLCMC blog, O-ring groove guide, sec. 11 | AGREE: squeeze 20.7-29.0 % (stand 20.69-29.03), max fill 83.7 % | — (a squeeze bound at the rounded 29.0 is REFUTED: exact max 29.032) |
| s02 | bolt preload, friction range | Wuerth handbook ch. 6 (VDI 2230), Tab. 3/5, ex. 6.7 | DISAGREE as posed: over the class's friction 0.14-0.24 the guaranteed clamp load is 25.89 kN, not 29.92 | NOT A SLIP: the source's 29.92 rests on alpha_A = 1.4, a method choice; friction alone gives 1.62 (the source's own Tab. 2 band 1.6-2.0) |
| s03 | amplifier + ADC error budget | eCircuit Center, Error Budget: Amp + ADC | AGREE: offset 2.2 mV PASS (stand 2.2032), gain 1.4 % FAIL (stand 1.4117 exact, the source's sum is first order) | the source has a table typo (offset 1 mV vs 0.1 mV used) |
| s04 | register timing, setup/hold | UCSD CSE 140 lecture 10 (slides) | AGREE on every question: Tc 215 / 265 ps, hold fails/passes, largest skew 10 ps | — (strict ">" read as ">=") |
| s05 | NTC on a charger TS pin, trip temperatures | TI SPVA059 (2026), ex. 1, sec. 4.2 | AGREE within rounding: stand 47.36 / 42.60 / 6.82 / 13.10 C, published 48 / 42 / 6 / 14 (outward to whole degrees) | — (four `find` bricks, one per limit) |
| s06 | LDO thermal over input range | Microchip TC1264 datasheet, sec. 5.2 | 260 mW / 508 mW AGREE; the closing "max VIN 4.6 V" DISAGREES: stand 4.535 V (at 4.6 V Tj = 126.05 C) | **the stand** (hand arithmetic in fractions, and Logik1: 30/59/0.275 + 2.6865 = 4.5355 V) |

**No wrong verdict.** Every agent checked by hand (a script over the corners, or fractions); every number agrees with
the stand. The disagreements are the source's: s06's 4.6 V is optimistic, s02's 29.92 kN is a method's factor, not
the friction class. **`find` was used in five of six** (s01 swell, s02 clamp load and friction, s03 Vref tolerance,
s04 Tc and skew, s05 all four limits, s06 VIN) and each limit matched the author's hand bisection.

**What real problems with stated uncertainty show.**
- They exist and fit: datasheet min/max (s05, s06), handbook ranges (s02), an error table (s03), slide min/max (s04).
- Inverse questions are the NATURAL form ("max VIN", "largest skew", "trip temperatures"): `find` carried them.
- Formulas are often missing from the sources (s01 page extraction, s02 no formulas): the authors reconstruct and
  calibrate against the source's numbers — the brick is then as good as that reconstruction.

**Gaps found — to fix:**
- FIXED: --dev was weaker than work on s02's failing end (work REFUTED with an exact witness, mu 0.24: F 25.8914 <
  25.9; --dev OPEN, "no corner violates it"). Cause: Fneed, named only in the requirement's bound, belonged to no
  law's corner group and sat at its low end. A requirement's bound names now move with its quantity.
- One `find` per brick: s05 needed four bricks for four limits; s03 split a combined brick because REFUTED hides
  which requirements pass.
- FIXED (1aa3edc): BRICKS.md on empty `slots`/`catalog` (s01, s03); `find`'s placeholder value and shared end
  (s05, s06); `table()` y-values need units (s06); a symmetric +- range for `find` (s03); the --dev witness may
  differ (s03); a quotient of decimals ("76.8/1000000") now reads exactly (s05).

**Cost.** 6 agents, 695 190 tokens (109 877 to 131 141 each).
