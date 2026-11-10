# Physics blind round 2 — results (2026-11-09)

Outcomes sealed (sha256 9e570cf1…, 04b0db1) before any prediction; predictions frozen (bdd400e) before opening; the
seal matched. Rule (PROTOCOL.md, round 2, written before the scout ran): HIT iff our range meets the measurement's ±1σ;
a stated law whose proved range EXCLUDES the measurement is a REFUTATION of that law with those inputs.

| # | case | stated law: our range vs measured | verdict on the stated law | Logic1's MODEL, said before opening | the paper |
|---|---|---|---|---|---|
| 1 | free-edge discs (ZTL judge) | thin plate A [25486, 27107] vs 24821; B [14316, 15062] vs 13729; C [3435, 3617] vs 3525; D [7161, 7516] vs 7111; E [851, 925] vs 887 | C, E HIT; **A, B, D REFUTED** (thin plate too high) | Mindlin factor 0.940 / 0.931 / 0.964 for A / B / D; measured ÷ thin-plate centre = **0.944 / 0.935 / 0.969** — within 0.5 %, with no fitting | thin plate over-predicts thick discs; a fitted correction (β = 0.895) |
| 2 | Faraday, four cells (ZTL + Lean) | Fe [105.0, 108.6] vs 102.7±1.0; Ni [110.4, 114.1] vs 109.9; Cu [119.5, 123.5] vs 133.1; Zn [122.9, 127.1] vs 122.0 | Ni, Zn HIT; Fe, Cu MISS | Fe, Ni, Zn BELOW Faraday (hydrogen) — **3 of 3 right** (−3.8, −2.1, −2.4 %); Cu AT Faraday — **wrong** (+9.5 %) | Cu outside 3σ: a systematic (mass gained in CuSO4 without current) |
| 3 | SiO2 membranes (NUM) | full tensioned-plate law: 5 of 6 radii far ABOVE the measurement; membrane limit: 4 of 6 in range | **plate law REFUTED** with the literature stress | — | one tension fitted (550 N/m); mode assignment ambiguous; bending "not negligible" |
| 4 | time-of-flight slope (NUM) | c/n_air 2.997e8 vs (3.2 ± 0.2)e8 | MISS by the letter at 1.02σ | slope SE 1–4 % from the specifications; the paper's is 6 % — our timing σ too optimistic | "compatible" |
| 5 | silicone rod at 100 Hz (NUM) | Timoshenko with E = 59 kPa: 2.74–2.88 / 3.19–3.34 / 4.25–4.40 / 6.50–6.64 vs 3.4 / 3.7 / 4.8 / 7.2 | **REFUTED** (too slow at every tension) | "a dynamic modulus would be higher and push c up" — right direction | fitted E = 155–231 kPa: a dynamic modulus |
| 6 | silica WGM (ZTL + Lean) | FSR [97.95, 99.75] vs 100.2±0.1; Brillouin [10.81, 10.94] vs 9.60±0.01 | **both REFUTED** | — | FSR "good agreement" (+1.9σ of their own); Brillouin not discussed |
| 7 | overdamped RLC (Lean) | component R: t× [2.18, 2.88] ms vs ≈1.9; E× [121, 154] µJ vs ≈166 | **REFUTED** (component R) | extra contact R → t× shorter: **right**; E× "lower": **wrong in my text** — my own +2 Ω numbers [138, 165] µJ said HIGHER | R_dyn = 33.1 Ω reproduces it; the component value gives a later crossing |
| 8 | 15 µm eclipse, M dwarf (NUM) | bare rock, no redistribution, star flux −25…+25 %: ≤ 138 ppm vs 200.5 ± 12.7 | **REFUTED** — no bare-rock, zero-albedo case reaches it (≈ 4.9σ above our largest) | — | the headline: "anomalously hot dayside", 5.2σ from the bare-rock model |
| 9 | 5–10.5 µm eclipse, K dwarf (NUM) | f = 2/3 [81.9, 123.8], f = 1/4 [55.1, 84.2] vs 81 ± 16 | both HIT — not decisive | — | 1.8σ below bare rock (their model star); "an atmosphere" |
| 10 | TESS / WFC3 eclipses (NUM) | f = 2/3: TESS [26, 47] vs 37 ± 10, WFC3 [70, 117] vs 69 ± 14; f = 1/4 (+A_g 0.1): ≤ 18 / ≤ 48 | bare rock HIT in both bands; **full redistribution REFUTED in both** | — | "consistent with the zero-albedo, no-redistribution limit" |

## What the round says
- **The sound ranges carried no arithmetic error** (ZTL judge / Lean / Logic1's numerics alike). Every miss is a
  MODEL miss, and in six cases (1 A/B/D, 3, 5, 6, 7, 8) the stated law with its stated inputs is REFUTED by the
  measurement — in each the paper itself names (or fits) the missing piece: plate thickness, a dynamic modulus, extra
  losses, an anomalously hot dayside; for case 6 neither the FSR excess (a mode radius inside the fibre? the phase
  index fits 100.15 GHz) nor the 9.6 GHz Brillouin line is explained by the stated law, and the paper does not discuss
  the latter.
- **Refutation is the method's useful output.** The sharpest result is case 8: our largest bare-rock depth with a
  generous ±25 % stellar-flux systematic is 138 ppm; the measurement 200.5 ± 12.7 — the same conclusion as the paper,
  reached before seeing it, from the laws alone.
- **Logic1's a-priori corrections** scored well where physics was clear (Mindlin factors within 0.5 % without fitting;
  hydrogen lowering three of four deposits) and failed where the effect was a systematic of the experiment (Cu).
- **Said:** cases 3, 4, 5, 8–10 are Logic1's numerics, not ZTL; ZTL's floor now reads Bessel and nested integrals,
  but the modal roots and the Planck band integrals were not run through it this round (time).

**Scout cost:** 451 k tokens.
