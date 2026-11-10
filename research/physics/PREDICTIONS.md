# Physics blind round 1 — PREDICTIONS (from CASES.md only; frozen before SEALED/outcomes.md is opened)

## 1. Open–closed tube resonances — ZTL
- humid-air mole fraction of water x_v in [0.0127, 0.0158] (Magnus); c = (331.4 + 0.6 t)(1 + 0.16 x_v)
- speed of sound c in [343.32, 344.09] m/s
- f_1 in [56.816, 57.042] Hz  (Lean: theorem)
- f_10 in [1079.509, 1083.806] Hz  (Lean: theorem)
- f_19 in [2102.202, 2110.570] Hz  (Lean: theorem)
- slope c/(4L') in [56.8163, 57.0424] Hz; a straight line through the origin in (2n−1)  (Lean: theorem)
- the measured peaks are consistent with these laws iff the c they imply lies in [343.32, 344.09] m/s

## 2. Binary-pulsar orbital decay — NUM (closed forms over the corners in Python; NOT proved in Lean)
- total mass M in [2.48832, 2.48863] M☉ (from ω̇); companion m_c in [1.1734, 1.2183] M☉ (from γ)
- Ṗ_b(GW) in [-1.2750e-12, -1.2712e-12] s/s; Ṗ_b(Shklovskii) in [5.276e-16, 2.849e-15] s/s
- PREDICTED observed Ṗ_b in [-1.2745e-12, -1.2684e-12] s/s (GW + Shklovskii; Galactic term neglected as the case says)
  (the range is dominated by γ's ±2.5 % through m_c, and by the distance's factor ~3 in the kinematic term)

## 3. Spring with emptying mass — ZTL
- outlet 11.60 mm: T initial in [1.2633, 1.2722] s, final in [0.7235, 0.7324] s, discharge 41.80–42.31 s, d(T²)/dt in [-0.02580, -0.02543] s²/s (Lean |slope|: theorem)
- outlet 19.55 mm: T initial in [1.2633, 1.2722] s, final in [0.7235, 0.7324] s, discharge 10.95–11.09 s, d(T²)/dt in [-0.09852, -0.09702] s²/s (Lean |slope|: theorem)
- T² linear in t (WKB, slowly varying mass); α from the slope equals the balance α exactly, by the same law

## 4. AC resistance of steel rods at 50 Hz — NUM (complex Bessel; outside ZTL)
- stainless 304: |Z|/R_DC in [1.000004, 1.000006], phase 0.133–0.150°; |Z| ≈ 5.19 mΩ (R_DC measured)
  S235JR ρ=0.16 µΩm μr=100: |Z|/R_DC = 1.615, phase 35.7°, |Z| = 2.245 mΩ
  S235JR ρ=0.16 µΩm μr=200: |Z|/R_DC = 2.281, phase 39.6°, |Z| = 3.171 mΩ
  S235JR ρ=0.16 µΩm μr=500: |Z|/R_DC = 3.511, phase 41.6°, |Z| = 4.880 mΩ
  S235JR ρ=0.16 µΩm μr=1000: |Z|/R_DC = 4.891, phase 42.7°, |Z| = 6.799 mΩ
  S235JR ρ=0.16 µΩm μr=2000: |Z|/R_DC = 6.843, phase 43.4°, |Z| = 9.512 mΩ
  S235JR ρ=0.20 µΩm μr=100: |Z|/R_DC = 1.453, phase 33.1°, |Z| = 2.020 mΩ
  S235JR ρ=0.20 µΩm μr=200: |Z|/R_DC = 2.044, phase 38.9°, |Z| = 2.842 mΩ
  S235JR ρ=0.20 µΩm μr=500: |Z|/R_DC = 3.160, phase 41.1°, |Z| = 4.393 mΩ
  S235JR ρ=0.20 µΩm μr=1000: |Z|/R_DC = 4.394, phase 42.4°, |Z| = 6.108 mΩ
  S235JR ρ=0.20 µΩm μr=2000: |Z|/R_DC = 6.139, phase 43.2°, |Z| = 8.534 mΩ
- S235JR over μr 100–2000 and ρ 0.16–0.20: ratio in [1.453, 6.843] (|Z| 2.02–9.51 mΩ); a measured ratio implies μr through this monotone curve (at ρ fixed by R_DC: ρ = R_DC·π r0²/l = 0.1965 µΩm)
  at the measured R_DC's ρ: μr=100: 1.465; μr=300: 2.509; μr=500: 3.187; μr=1000: 4.431; μr=2000: 6.192

## 5. Differential tidal rate shift between clock sites — NUM (outside ZTL)
- INRiM–PTB: amplitudes (×1e-18) M2 2.43, S2 1.13, N2 0.46, K2 0.31; K1 0.62, O1 0.44, P1 0.21, Q1 0.08; peak-to-peak bound (all in phase) 11.4×1e-18
- NPL–PTB: amplitudes (×1e-18) M2 2.62, S2 1.22, N2 0.50, K2 0.33; K1 1.95, O1 1.38, P1 0.64, Q1 0.27; peak-to-peak bound (all in phase) 17.9×1e-18
- INRiM–PTB: noise averaged over a week ≈ 0.85×1e-18; a fitted scale factor A ≈ 1 with uncertainty of order that noise over the model's amplitude (≈ 0.1–0.3, sharper on the larger baseline signal)
- NPL–PTB: noise averaged over a week ≈ 0.69×1e-18; a fitted scale factor A ≈ 1 with uncertainty of order that noise over the model's amplitude (≈ 0.1–0.3, sharper on the larger baseline signal)
- expectation: A consistent with 1 (elastic-Earth model, ocean loading neglected — a few % effect)

## 6. EMF along a rod in a Helmholtz field — NUM (outside ZTL)
- ε_rms (mV): y=2 cm: 0.2105, y=5 cm: 0.5141, y=7 cm: 0.6847, y=9.8 cm: 0.8040, y=15 cm: 0.6121, y=25 cm: 0.2609
- maximum ε ≈ 0.8051 mV at y ≈ 10.1 cm; ε(0) = 0 by symmetry (E_φ ⟂ rod)

## 7. Peas sedimenting in rapeseed oil — ZTL (Stokes × Haberman–Sayre, Oseen noted)
- group 1 (D 11 mm): Stokes+wall U nominal 3.09 cm/s, range [1.71, 5.25] cm/s; Re ≈ 2.2 — NOT small: with the Oseen factor U ≈ 2.36 cm/s (Oseen itself is rough above Re ~ 1)
- group 2 (D 18 mm): Stokes+wall U nominal 5.16 cm/s, range [2.65, 8.75] cm/s; Re ≈ 4.3 — NOT small: with the Oseen factor U ≈ 3.38 cm/s (Oseen itself is rough above Re ~ 1)
- group 3 (D 20 mm): Stokes+wall U nominal 3.67 cm/s, range [1.58, 6.63] cm/s; Re ≈ 3.0 — NOT small: with the Oseen factor U ≈ 2.63 cm/s (Oseen itself is rough above Re ~ 1)
- group 4 (D 20 mm): Stokes+wall U nominal 7.29 cm/s, range [4.26, 11.51] cm/s; Re ≈ 5.5 — NOT small: with the Oseen factor U ≈ 4.46 cm/s (Oseen itself is rough above Re ~ 1)
- group 5 (D 27 mm): Stokes+wall U nominal 7.12 cm/s, range [3.71, 11.77] cm/s; Re ≈ 5.3 — NOT small: with the Oseen factor U ≈ 4.41 cm/s (Oseen itself is rough above Re ~ 1)
- expected spread: the net weight m − ρV is a small difference of kitchen-scale numbers (±0.01 g of ~0.05 g),
  so the prediction itself spans a factor of several; measurements scattered over such a range are 'near'

## 8. Venus fringes through a two-hole mask — NUM (Bessel J1; outside ZTL)
- d = 6 mm: V at 550 nm 0.514–0.579; over 450–650 nm 0.341–0.684
- d = 10 mm: V at 550 nm 0.046–0.127; over 450–650 nm 0.044–0.289
- d = 14 mm: V at 550 nm 0.116–0.132; over 450–650 nm 0.021–0.132
- null baseline d_null = 1.22 λ/α: 11.5 mm at α = 12.0″ (λ 550 nm)
- null baseline d_null = 1.22 λ/α: 10.6 mm at α = 13.1″ (λ 550 nm)
- expected: 6 mm clearly visible, 10 mm marginal (low contrast), 14 mm beyond the first null — absent/very faint;
  vanishing between 10 and 14 mm implies α = 1.22 λ / d in [9.9, 13.8]″ (λ 550 nm)

## 9. Oil in a tank on a cart on a 2.4° ramp — ZTL
- frictionless a = g sin θ in [0.3937, 0.4279] m/s² down the ramp (Lean: theorem); with rolling friction μ_r:
  down: a = g(sin θ − μ_r cos θ) < g sin θ; up and slowing: |a| = g(sin θ + μ_r cos θ) > g sin θ —
  the acceleration keeps its direction (down the ramp) at the turning point; its MAGNITUDE steps down there
- release from rest (frictionless): the surface turns from horizontal to parallel to the ramp — the edges move by W tan θ in [1.85, 2.01] cm relative to the tank base; with friction slightly less
- slope of v(t) = a: ≈ 0.394–0.428 m/s² frictionless, somewhat less going down with friction

## 10. Calorimeter, Γ = c_w + c_Cu m_cup / M_w — ZTL
- M_w = 170 g: Γ = 4.4291 J/(g K) (Lean: theorem)
- M_w = 200 g: Γ = 4.3918 J/(g K) (Lean: theorem)
- M_w = 240 g: Γ = 4.3565 J/(g K) (Lean: theorem)
- over 170–240 g: Γ in [4.3565, 4.4291] (Lean: theorem); a common fit ≈ 4.39 — ABOVE c_w by ≈ 4–6 %
- heat losses (not in the laws) would push a measured slope higher still

## Lean theorems
- ZPhys1f1: theorem
- ZPhys1f10: theorem
- ZPhys1f19: theorem
- ZPhys1slope: theorem
- ZPhys3s11_60: theorem
- ZPhys3s19_55: theorem
- ZPhys9a: theorem
- ZPhys10M170: theorem
- ZPhys10M200: theorem
- ZPhys10M240: theorem
- ZPhys10range: theorem
