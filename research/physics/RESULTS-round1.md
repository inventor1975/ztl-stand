# Physics blind round 1 — results (2026-11-09)

Ten post-cutoff measurements (arXiv 2026-07-02 … 2026-10-29), outcomes sealed (sha256 2ed15cb1…, aaf3132) before any
prediction; predictions frozen (856aad9) before opening; the seal matched at opening. Scored by PROTOCOL.md's rule as
fixed beforehand: HIT = the measured CENTRAL value inside our range.

| # | case | how predicted | our prediction | measured | by the rule | said plainly |
|---|---|---|---|---|---|---|
| 1 | tube resonances, c | **ZTL (Lean)** | slope [56.816, 57.042] Hz; c [343.32, 344.09] m/s | slope 57.09(2) Hz; c 344.7(3) | **MISS** | sharp prediction; the measurement sits 0.6 m/s (≈2σ of its own error) above what the stated laws and input ranges can give. The paper calls the +0.30 % "agreement"; sound propagation says it is NOT inside the stated uncertainties — something beyond them (e.g. the air in the tube warmer than the room by ~1 °C) |
| 2 | pulsar Ṗ_b | NUM | [−1.2745, −1.2684]·10⁻¹² | −1.284(19)·10⁻¹² | MISS by the letter | our range (0.5 % wide) is SHARPER than the measurement (1.5 %); the measurement overlaps it within 0.6σ — agreement with GR, as the paper says. The rule is wrong for a range narrower than the measurement error (below) |
| 3 | spring, d(T²)/dt | **ZTL (Lean)** | small outlet [−0.02580, −0.02543]; large [−0.09852, −0.09702] s²/s | −0.0256(7); −0.095(9) | HIT; MISS by the letter | small outlet in range; large: within the measurement's ±0.009, but the paper's own sharper fit gives α 3.5 % below the balance — a real difference the law (mass leaving with zero relative velocity) does not carry. Durations 42 / 11 s vs ">35" / "~10" s: consistent |
| 4 | skin effect | NUM | stainless 1.000005; S235JR ratio 1.45–6.84 over μr 100–2000 | 0.998(5); 2.42(3) | HIT; HIT (wide) | stainless sharp and right; structural steel: in range but the range is worthless (×4.7 wide); the implied μr ≈ 270–280 (from our curve at the measured ρ) — not committed before |
| 5 | clock tides, scale A | NUM | A ≈ 1, uncertainty 0.1–0.3 | 1.42(35), 1.12(24), mean 1.00(12) | HIT | amplitudes equal the scout's check to the digit; our noise guess somewhat optimistic for INRiM–PTB (0.35) |
| 6 | Helmholtz EMF | NUM | 0.211 … 0.804 … 0.261 mV; max 0.805 at 10.1 cm | 0.195 … 0.807 … 0.285; max at 9.8 cm | HIT (no ranges) | point predictions within −8 … +8 %; the peak 0.4 % off |
| 7 | peas in oil | corners (not proved) | five ranges, each ×3 wide | 1.90, 5.54, 7.01, 7.32, 7.91 cm/s | 4 of 5 | the four hits carry little information (wide); group 3 above (its data inconsistent per the scout); Oseen makes it worse |
| 8 | Venus fringes | NUM | 6 clear, 10 marginal, 14 absent; α in [9.9, 13.8]″ | clear, "somewhat visible", absent; 11″ (true 12–13″) | HIT | qualitative |
| 9 | cart on a ramp | **ZTL (Lean)** for g sin θ | a [0.394, 0.428] frictionless, less going down; up: larger, a step down at the turning point; Δh [1.85, 2.01] cm | 0.38 down, 0.39 up, constant through the turning point; Δh ~2 cm | HIT (Δh, sign); **MISS** (the step) | the friction step was NOT seen: going up the magnitude was also below g sin θ — the ramp angle a little under 2.4° fits both runs better than friction does |
| 10 | calorimeter Γ | **ZTL (Lean)** | [4.3565, 4.4291]; 200 g: 4.3918; above c_w by 4–6 % | fit 4.38(4); 200 g test 4.35(8) | HIT; MISS by the letter | the common fit in range; the 200 g point within 1σ |

## What the round says
- **ZTL's own conclusions** (Lean-proved ranges, cases 1, 3, 9, 10): the ranges are what the stated laws and inputs
  give — no arithmetic error anywhere. Where the world fell outside (1, 3-large, 9-step), it is the MODEL or the INPUT
  UNCERTAINTIES that fall short, not the proof. Case 1 is the one sharp, honest tension: the paper's "0.30 % —
  agreement" is outside what its own stated uncertainties allow.
- **Six of ten cases were not ZTL** (Bessel, field integrals, tides, pulsar closed forms done in Python). ZTL's
  kernel lacks Bessel functions and integrals over fields; the method needs them before most of physics is "ZTL's".
- **The HIT rule fixed beforehand is wrong for sharp predictions**: with our range narrower than the measurement's
  error, "central value inside" fails by noise (2, 3-large, 10-test). Not changed in retrospect; for round 2 the rule
  becomes: HIT iff our range meets the measurement's ±1σ interval; SHARP iff our range is narrower than that interval.
- Wide ranges (4 structural, 7) hit and say nothing, as materials batch A showed.

**Scout cost:** 349 k tokens.
