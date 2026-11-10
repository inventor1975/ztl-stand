# Blind prediction cases (applied physics) — ten cases

Each case: system, laws, inputs (value, uncertainty, unit, origin), question.
Origin codes: **IM** = independent measurement; **LIT** = literature / handbook / standard value; **DS** = datasheet / nominal specification; **NOM** = nominal value stated by the experimenters, not fitted to the quantity asked. No input below is fitted to the quantity asked about.

---

## 1. Resonances of a hand-struck open–closed tube (acoustics)

**System.** A straight cylindrical PVC tube, open at one end, closed at the other by the palm of a hand pressed on the rim. A short pressure pulse excites its normal modes; a microphone records the spectrum and the resonance peaks are read from it.

**Laws.**
- Open–closed pipe: f_n = (2n−1) c / (4 L′), n = 1, 2, 3, … (Hz).
- Effective acoustic length L′ = L + δ, with the unflanged-pipe end correction δ = 0.6133 a (Levine–Schwinger), a = tube inner radius.
- Speed of sound in humid air from the ideal-gas adiabatic law, c = sqrt(γ R T / M), with M and γ of the moist-air mixture (dry-air approximation: c ≈ 331.4 + 0.60 t m/s, t in °C).

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| L (geometric length) | 1.498 ± 0.001 | m | IM (tape) |
| a (radius) | 1.85 ± 0.05 | cm | IM |
| air temperature t | 19.2 ± 0.5 | °C | IM |
| pressure | 101.325 | kPa | NOM |
| relative humidity | 65 ± 5 | % | IM |

**Question.** What are the frequencies f_1, f_10 and f_19 of the resonances (Hz), and what slope c/(4L′) (Hz) would a straight-line fit of f_n against (2n−1) give? Is it a straight line through the origin, and with what speed of sound c would the measured peaks, if they follow these laws, be consistent?

---

## 2. Orbital decay of a compact binary pulsar (astronomy, general relativity)

**System.** A double-neutron-star binary: one radio pulsar timed over about a year; orbital period P_b = 0.09851259274(5) d (2.364 h), eccentricity e = 0.106322(11). A secular change of the orbital period, Ṗ_b, is measured by timing.

**Laws.** (Peters 1964; Damour–Deruelle post-Keplerian formalism, general relativity; T☉ = G M☉/c³ = 4.925490947 µs.)
- Periastron advance: ω̇ = 3 (P_b/2π)^(−5/3) (T☉ M)^(2/3) / (1−e²), M = m_p + m_c in M☉.
- Einstein delay: γ = e (P_b/2π)^(1/3) T☉^(2/3) M^(−4/3) m_c (m_p + 2 m_c).
- Gravitational-wave orbital decay: Ṗ_b^GW = −(192π/5) (P_b/2π)^(−5/3) (1 + 73e²/24 + 37e⁴/96) (1−e²)^(−7/2) T☉^(5/3) m_p m_c / M^(1/3).
- Kinematic (Shklovskii) contribution: Ṗ_b^Shk = P_b μ² d / c; the Galactic-potential term is small and may be neglected at the 1% level.

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| P_b | 0.09851259274 ± 0.00000000005 | d | IM (timing) |
| e | 0.106322 ± 0.000011 | – | IM (timing) |
| ω̇ | 17.5859 ± 0.0007 | deg/yr | IM (timing; independent of Ṗ_b) |
| γ | 0.445 ± 0.011 | ms | IM (timing; independent of Ṗ_b) |
| proper motion μ_α, μ_δ | −1.5 ± 0.5, −6.1 ± 0.9 | mas/yr | IM (timing) |
| distance d | 1.3 (YMW16 model) to 2.0 (NE2025 model), ±30% | kpc | LIT (dispersion-measure models) |

(The two component masses follow from ω̇ and γ via the formulas above; do not use Ṗ_b to obtain them.)

**Question.** What value (and range) of the observed Ṗ_b (s/s) do general relativity and these inputs give, including the kinematic correction? Does a measured value of order 10⁻¹² s/s with ~1.5% precision agree with it?

---

## 3. Spring oscillator with a steadily emptying mass (mechanics, vibration)

**System.** A smartphone in a holder hangs from a vertical spring; a plastic bottle filled with granulated sugar is hooked under it. The sugar leaves through a round hole at an approximately constant mass rate α, so the oscillating mass decreases linearly in time while the system oscillates vertically. The phone accelerometer records the vertical acceleration.

**Laws.** m(t) = m₀ − α t. Equation of motion for the open system (spring k, weight and momentum balance; mass leaves with zero velocity relative to the body): d(m ẋ)/dt = m g − k(x₀ + x) − b ẋ. For slowly varying mass (WKB regime) the instantaneous angular frequency is ω(t) = sqrt(k/m(t)), i.e. T(t)² = (4π²/k)(m₀ − α t). Oscillation amplitude of acceleration grows as m^(−5/4) (undamped).

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| k (spring constant) | 22.5 ± 0.1 | N/m | IM (separate calibration) |
| spring mass | 57 ± 1 | g | IM (effective mass = ⅓ of it) |
| phone + holder | 227 ± 1 | g | IM |
| empty bottle | 56 ± 1 | g | IM |
| bottle full of sugar | 670 ± 1 | g | IM |
| α, outlet diameter 11.60 mm | 0.01460 ± 0.00004 | kg/s | IM (sugar collected on a balance vs time, separate run) |
| α, outlet diameter 19.55 mm | 0.05572 ± 0.00018 | kg/s | IM (same method) |

**Question.** For each outlet, what are the initial and final oscillation periods, the duration of the discharge, and the slope d(T²)/dt (s²/s) of the square of the period against time? Is the T²(t) relation linear, and does the slope-derived mass-loss rate α = −k/(4π²)·d(T²)/dt agree with the balance measurement?

---

## 4. AC resistance of solid steel rods at 50 Hz (electromagnetism, skin effect)

**System.** Two solid cylindrical rods of equal radius and length, one austenitic stainless steel (AISI 304), one ferromagnetic structural steel (S235JR). Four-wire (Kelvin) voltage–current measurements over a gauge length l, with DC and with 50 Hz sinusoidal current (RMS values), currents up to 3 A, 24 °C.

**Laws.**
- DC: R_DC = ρ l/(π r₀²).
- Skin depth δ = sqrt(2ρ/(ω μ₀ μ_r)), ω = 2π f.
- Exact solid-cylinder internal impedance: Z = R_DC · (k r₀/2) J₀(k r₀)/J₁(k r₀), with k = (1 − i)/δ (J₀, J₁ Bessel functions of complex argument). Limits: r₀/δ ≪ 1: Z → R_DC; r₀/δ ≫ 1: R_AC ≈ R_DC r₀/(2δ), ωL_int ≈ R_AC.
- Measured quantity |Z| = U_rms/I_rms.

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| r₀ | 6.00 ± 0.02 | mm | IM (caliper) |
| l (gauge length) | 80.0 | cm | IM |
| f | 50 | Hz | NOM |
| ρ, stainless 304 | 0.73 (±5%) | µΩ·m | LIT (handbook) |
| ρ, S235JR | 0.16 (batch dependent, up to +25%) | µΩ·m | LIT (handbook) |
| μ_r, stainless | ≤ 1.02 | – | LIT |
| μ_r, S235JR (initial, low field ≲ 50 mT) | nominal ~10³; plausible range 100–2000 | – | LIT (handbook, unspecific) |
| R_DC measured, stainless | 5.19 ± 0.01 | mΩ | IM (DC four-wire) |
| R_DC measured, S235JR | 1.39 ± 0.01 | mΩ | IM (DC four-wire) |

**Question.** What are |Z_AC| (mΩ), the ratio |Z_AC|/R_DC and the phase angle of Z for each rod at 50 Hz? Over the stated μ_r range, what range of the ratio do the laws give for the structural steel, and what μ_r would a measured ratio imply?

---

## 5. Tidal modulation of optical-clock frequency ratios between distant sites (geophysics, relativistic time dilation)

**System.** Optical lattice clocks (Sr, Yb; fractional instability ~5×10⁻¹⁶/√(τ/s)) at national metrology institutes, compared over phase-stabilised fibre links, in campaigns of about one week (2023 and 2025). Two baselines of ~750–850 km: Turin (INRiM) – Braunschweig (PTB), and Teddington (NPL) – PTB. The comparison measures the difference of gravitational redshift, i.e. of the gravity potential W at the two clock sites.

**Laws.**
- Relativistic rate shift of a clock at potential W (relative to a distant reference): Δν/ν = −ΔW/c² (a time-varying part ΔW_t is the tidal potential).
- Degree-2 equilibrium tide-generating potential, height-equivalent V/g = Σ_k H_k × {cos²φ cos(2λ + χ_k(t)) for semidiurnal; sin 2φ cos(λ + χ_k(t)) for diurnal species}, φ latitude, λ east longitude, χ_k(t) the Doodson argument of constituent k (period of M2: 12.42 h; S2: 12.00 h; N2: 12.66 h; K2: 11.97 h; K1: 23.93 h; O1: 25.82 h; P1: 24.07 h; Q1: 26.87 h).
- Elastic Earth: for a clock fixed to the crust, ΔW_t = (1 + k₂ − h₂) V (Love numbers h₂, k₂); ocean tidal loading adds a further smaller correction (neglect or take from an ocean-tide model).
- g = 9.81 m/s²; c = 2.998×10⁸ m/s.

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| H_M2, S2, N2, K2 | 0.2423, 0.1128, 0.0464, 0.0307 | m | LIT (equilibrium-tide amplitudes) |
| H_K1, O1, P1, Q1 | 0.1416, 0.1005, 0.0468, 0.0193 | m | LIT |
| h₂, k₂ | 0.608, 0.298 | – | LIT (IERS conventions, nominal) |
| PTB site | 52.3 °N, 10.46 °E | | IM |
| INRiM site | 45.0 °N, 7.64 °E | | IM |
| NPL site | 51.4 °N, 0.34 °W | | IM |
| comparison instability | 4.7×10⁻¹⁶ (INRiM–PTB), 3.8×10⁻¹⁶ (NPL–PTB), ×(τ/s)^(−1/2) | | IM (noise level of the same campaigns) |

**Question.** What are the amplitudes (in units of 10⁻¹⁸ of fractional frequency) of the main semidiurnal and diurnal constituents of the *differential* tidal rate shift for INRiM–PTB and for NPL–PTB, and the typical peak-to-peak variation over a week? If the measured oscillation is fitted as A × (model), what values of A (with uncertainty reflecting the stated clock noise over about one week with partial uptime) would you expect, and would an optical-clock network agree with the model?

---

## 6. EMF induced along a copper rod in a Helmholtz-coil field (electromagnetism)

**System.** A Helmholtz pair (two coaxial coils, radius R, separation R) carries a sinusoidal current. A straight copper rod lies in the mid-plane z = 0, parallel to the x axis, its centre on the y axis at offset y from the coil axis; lead wires run parallel to the coil axis (they do not contribute). The RMS EMF between rod ends is measured with a millivoltmeter.

**Laws.**
- Biot–Savart field of a circular loop of radius R at (ρ, z) (axial component): B_z = (μ₀ I/4π) ∫₀^{2π} (R² − Rρ cosθ) dθ / (ρ² + R² + z² − 2Rρ cosθ)^{3/2}; sum over the two coils; N turns multiply the field.
- Faraday: by axial symmetry the induced electric field in the mid-plane is E_φ(r) = −(1/2πr) dΦ/dt, Φ(r) = ∫₀^r B_z(ρ, 0) 2πρ dρ (B_z changes sign outside the coil; use the full B_z).
- EMF of the straight rod of half-length l: ε = ∫_{−l}^{l} E_φ(r) (y/r) dx, r = sqrt(x² + y²), with B ∝ sin ωt (ε_rms from I_rms).

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| R (effective coil radius) | 10.5 | cm | DS (nominal) |
| coil separation | 10.5 | cm | DS |
| turns per coil N | 400 | – | DS |
| I (RMS) | 30 | mA | IM |
| f | 220 | Hz | IM |
| rod length 2l | 15.0 | cm | IM |
| rod diameter | 1.0 | cm | IM (negligible) |

**Question.** What is the RMS EMF ε(y) (mV) at y = 2, 5, 7, 9.8, 15 and 25 cm, at what offset y_max does ε reach its maximum, and what is that maximum? Is ε = 0 at y = 0?

---

## 7. Sedimentation speed of peas in rapeseed oil in a measuring cylinder (fluid mechanics)

**System.** A dried pea (treated as a sphere of equivalent diameter d) sediments at constant speed in rapeseed oil at 20 °C inside a vertical measuring cylinder of inner diameter D. Five groups used cylinders of different D.

**Laws.**
- Force balance at constant speed: (m_pea − ρ_oil V_pea) g = F_drag.
- Stokes drag in unbounded fluid: F = 3π μ U d. Wall effect (Haberman–Sayre, q = d/D): the drag in a cylinder is K_p times larger, K_p = (1 − 0.75857 q⁵)/(1 − 2.1050 q + 2.0865 q³ − 1.7068 q⁵ + 0.72603 q⁶). Optional inertial (Oseen) correction: F → F (1 + 3Re/16), Re = ρ_oil U d/μ.

**Inputs.**
| symbol | Group 1 | Group 2 | Group 3 | Group 4 | Group 5 | origin |
|---|---|---|---|---|---|---|
| D (mm) | 11 | 18 | 20 | 20 | 27 | IM |
| m_pea (g) | 0.26 | 0.24 | 0.22 | 0.24 | 0.22 | IM (kitchen scale, ±0.01) |
| ρ_oil (g/mL) | 0.85 | 0.95 | 0.84 | 0.86 | 0.82 | IM (±0.03) |
| V_pea (mL) | 0.19 | 0.18 | 0.20 | 0.18 | 0.19 | IM (±0.01) |
| d (mm) | 6.00 | 6.42 | 7.00 | 6.45 | 6.61 | IM (ruler, ±0.3) |

Oil dynamic viscosity at 20 °C: 73 mPa·s (plate–plate rheometer on rapeseed oil), LIT (uncertainty ~±10%). g = 9.81 m/s².

**Question.** What sedimentation speed U (cm/s) do these laws predict for each group (state which corrections you apply)? Over the five groups, do kitchen-scale measurements of U lie near these predictions, and what spread would you expect?

---

## 8. Fringe visibility of a planetary disc seen through a two-hole mask (optics, astronomy)

**System.** A 150 mm amateur reflector is covered by an opaque mask with two circular holes (diameter h = 2 mm each, centre separation d). Venus, seen in unfiltered white light in May 2026 (about 28–34° east of the Sun, rising from ≈11.6″ to ≈13.1″ apparent diameter during the month), is observed through the mask. Masks with d = 6, 10 and 14 mm were tried; the observer judges whether interference fringes are visible.

**Laws.**
- A uniform disc of angular diameter α has fringe visibility V(d) = |2 J₁(x)/x|, x = π d α/λ (van Cittert–Zernike). First null at x = 3.832, i.e. d_null = 1.22 λ/α.
- Fringe spacing Δθ = λ/d; Airy envelope radius 1.22 λ/h; number of fringes within the central lobe ≈ 2.44 d/h.
- Representative wavelength for white light λ = 550 nm (range 450–650 nm). 1″ = 4.848×10⁻⁶ rad.

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| α (Venus) | 11.6–13.1 (≈12–13 around the observing nights) | arcsec | LIT (planetary ephemeris; computed from Venus radius 6051.8 km and Earth–Venus distance ≈1.27–1.44 AU) |
| h | 2 | mm | IM |
| d tried | 6, 10, 14 | mm | IM |
| λ | 550 (450–650) | nm | NOM |

**Question.** What are V(6 mm), V(10 mm), V(14 mm), and the null baseline d_null? At which of these spacings are fringes expected to be clearly visible, marginal, or absent, and what angular diameter would an observer infer if the fringes first vanish between 10 and 14 mm?

---

## 9. Oil surface in a tank on a cart rolling on a ramp (mechanics, accelerated frame)

**System.** A rectangular transparent tank of width 46 cm, part-filled with canola oil, is mounted on a low-friction dynamics cart that rolls on a ramp inclined at 2.4° to the horizontal. A velocity sensor on the cart records v(t); a camera on the cart records the oil surface against a rubber band stretched parallel to the tank base (and to the ramp). Cases: released from rest down the ramp; given a push up the ramp and left to slow, reverse and return.

**Laws.**
- Frictionless acceleration down an incline: a = g sin θ.
- In the cart frame the effective gravity is g_eff = g − a; the free surface settles perpendicular to g_eff. Tilt of the surface relative to the horizontal: tan φ = a_x/(g − a_z) (x horizontal, z vertical components of the acceleration); relative to the ramp the surface is parallel to the ramp when the cart is frictionless.
- Rise/fall of the oil edges over the tank width W: Δh = W tan φ.

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| θ (ramp angle) | 2.4 (±0.1) | deg | IM |
| tank width W | 46 | cm | IM |
| g | 9.81 | m/s² | LIT |
| cart | ball-bearing dynamics cart with ordinary rolling friction | | NOM |

**Question.** What acceleration along the ramp (m/s²) do the laws give for a cart that is rolling down, and for a cart that is rolling up and slowing? Does the acceleration change sign at the turning point? What total change of height of the oil edges across the tank (cm) accompanies release from rest, and what slope of v(t) would the sensor show?

---

## 10. Specific-heat experiment: effective heat capacity per gram of water in a copper calorimeter (thermodynamics, heat transfer)

**System.** A calorimeter consists of a 110 g copper cup in 1.5 cm of expanded polystyrene insulation; a coiled nichrome heater (constant electric power P, 9–25 W, from measured current and voltage), a stirrer and a thermometer are immersed in M_w = 170–240 g of water. The temperature rise ΔT(t) is recorded from t = 0 (room temperature, rise of a few kelvin). Students plot Q/M_w against ΔT, Q = P t, and fit a straight line through the origin: Q/M_w = Γ ΔT.

**Laws.** Energy balance, no heat loss: Q = (c_w M_w + C_cal) ΔT, hence Γ = c_w + C_cal/M_w, with C_cal ≈ c_Cu m_cup (other immersed parts neglected).

**Inputs.**
| symbol | value | unit | origin |
|---|---|---|---|
| c_w (water, 20 °C) | 4.18 | J g⁻¹ K⁻¹ | LIT |
| c_Cu | 0.385 | J g⁻¹ K⁻¹ | LIT |
| m_cup | 110 | g | IM |
| M_w | 170, 200, 240 | g | IM |

**Question.** What values of Γ (J g⁻¹ K⁻¹) do the laws give for M_w = 170, 200 and 240 g, and for a single common fit over this range of masses? Would a straight-line fit to measured Q/M_w versus ΔT give a slope above or below c_w, and by roughly how much?
