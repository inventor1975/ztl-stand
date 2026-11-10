# SEALED outcomes — do not show to the predictor

All sources are arXiv preprints first posted 2026-07-02 .. 2026-10-29 (read in full by the scout from the arXiv PDFs on 2026-11-09). Case 5 campaigns were in 2023/2025 but the paper is Oct 2026. Scout's own quick checks are labelled "SCOUT CHECK".

---

## 1. Hand-struck tube — speed of sound
- Source: arXiv:2609.31131 (physics.ed-ph), submitted 2026-09-25. https://arxiv.org/abs/2609.31131 (Echegorri, Monteiro, Stari, Martí; Montevideo).
- Measured: 19 harmonics, linear fit f_n vs (2n−1) slope c/4L′ = **57.09 ± 0.02 Hz**; L′ = 1.5093(13) m; c_exp = **344.7 ± 0.3 m/s**. (Fundamental 57.09 Hz, 19th ≈ 2112 Hz.)
- Paper's reference: c_ref = 343.7(6) m/s from an online humid-air calculator (T 19.2(5) °C, 101.325 kPa, RH 65(5)%); dry formula 342.9(6). Measured − reference = +1.0 m/s (0.30%).
- Paper reports: agreement (0.30% above accepted value; "within 0.5%" of the dry linear formula).
- Quote: "differs from the accepted one by only 0.30%".
- Extra input taken from elsewhere: none (humid-air c computed by scout from ideal-gas mixture).
- SCOUT CHECK: c(19.2 °C, 65% RH) = 343.56 m/s (range 343.2–343.9 for ±0.5 °C); L′ = 1.50935 m → f₁ = 56.90 Hz (56.85–56.96), f₁₉ = 2105 Hz; measured slope 57.09 is +0.33% above. Ballpark: yes, within ~0.3%; the prediction uncertainty (±0.6 m/s ⇒ ±0.17%, plus ±0.05 cm radius ⇒ ±0.003%) is slightly smaller than the offset.

## 2. PSR J1856−0039 orbital decay
- Source: arXiv:2607.27333 (astro-ph.HE), v1 2026-07-29 (v2 later). https://arxiv.org/abs/2607.27333 (Han group, FAST).
- Measured: Ṗ_b = **−1.284 ± 0.019 ×10⁻¹² s/s**; ω̇ = 17.5859(7) deg/yr; γ = 0.445(11) ms; i = 133.2(1.1)°; M_tot = 2.48841(15) M☉; M_p = 1.304(22), M_c = 1.185(22) M☉ (DDGR).
- Paper's model prediction: observed/predicted GR Ṗ_b ratio = **1.009 ± 0.014** (68%), i.e. agreement with GR (after kinematic corrections judged negligible).
- Quote: "consistent at a level of Ṗorb,obs/Ṗorb,pred =1.009(14)".
- Input from elsewhere: none (mass split from ω̇+γ by scout; the paper's DDGR masses also used DDGR which in principle uses all data — note the fit may weakly involve Ṗ_b; the mass split barely affects the prediction).
- SCOUT CHECK: M_tot from ω̇ = 2.4885 M☉ (matches); m_c from γ = 1.196 (1.173–1.218), m_p = 1.292; Ṗ_b^GW = **−1.2735 ×10⁻¹² s/s** (insensitive to the split: −1.2705…−1.2748). Shklovskii +1.1×10⁻¹⁵ (1.3 kpc) to +1.6×10⁻¹⁵ (2.0 kpc) ⇒ predicted observed ≈ −1.272×10⁻¹². Measured −1.284(19): +0.9% from prediction, 0.6σ. Ballpark: yes, agrees.

## 3. Variable-mass spring oscillator
- Source: arXiv:2609.16845 (physics.ed-ph), submitted 2026-09-15. https://arxiv.org/abs/2609.16845 (Milbrandt, Suñer, Castro-Palacio, Muñoz-Pérez, Monsoriu).
- Measured: independent balance values α = 0.01460(4) and 0.05572(18) kg/s. Fit of the acceleration trace: α_fit = 0.014660(2) and 0.05377(5) kg/s (differences 0.4% and 3.5%). Period-squared analysis: α_fit = 0.0146(4) and 0.054(5) kg/s ⇒ slopes d(T²)/dt = −4π²α/k = −0.0256(7) and −0.095(9) s²/s (differences 0.0% and 3.1%). Discharge durations: >35 s (small outlet; trace shown 20–55 s) and ~10 s (large outlet; trace 12–22 s). Damping b = 0.0153 and 0.0448 kg/s (fitted, not needed). Plot axes of T² vs t span ~0.4–1.8 s².
- Paper's model: T² = (4π²/k)(m₀−αt) linear; reports agreement (linear T² observed, α consistent).
- Quote: "in good agreement with those obtained independently from the discharge measurements".
- SCOUT CHECK: m₀ = 0.227+0.670+0.019 = 0.916 kg, T₀ = 1.268 s (T² = 1.61), final m = 0.302 kg, T_end = 0.728 s (T² = 0.53); slopes −0.0256 and −0.0978 s²/s; durations 42 s and 11.0 s. Ballpark: yes. The T² axis maximum 1.8 in the paper's plot is somewhat above the 1.6 computed for the stated masses (maybe the plot starts with extra mass or sample of an earlier time); not a contradiction of the slope.

## 4. Skin effect in steel rods at 50 Hz
- Source: arXiv:2609.04326 (physics.ed-ph), submitted 2026-09-03. https://arxiv.org/abs/2609.04326 (Platten, Wenz; Düsseldorf).
- Measured: stainless R_DC = 5.19(1) mΩ, |Z_AC| = 5.16(2) mΩ, ratio 0.998(5); S235JR R_DC = 1.39(1) mΩ, |Z_AC| = **3.36(4) mΩ**, ratio **2.42(3)**, R_AC/R_DC = 1.71(2) (assuming |Z| = √2 R_AC). DC resistivities 0.734(5) and 0.196(2) Ω mm²/m.
- Paper's model prediction: handbook values give r₀/δ ≈ 6 for structural steel with μ_r ~10³, δ ≈ 1 mm, asymptote R_AC/R_DC ≈ r₀/2δ; the paper says the behaviour is "well-approximated" by the high-frequency expansion; for stainless |Z| = R_DC (r₀/δ ≈ 0.1).
- Quote: "|ZAC | = 3.36(4) mΩ, exceeding its static resistance by a factor of 2.42(3)".
- Extra input: the DC resistances were measured in the same experiment (separate DC data, not the AC quantity).
- SCOUT CHECK (exact Bessel solution): stainless |Z|/R_DC = 1.000005 (agrees). Structural steel ρ = 0.196 µΩ·m: μ_r = 200 → 2.07; 300 → 2.51; 500 → 3.19; 1000 → 4.44; 2000 → 6.20 (phase 39–43°). With ρ = 0.16: 2.28 (μ_r 200), 3.51 (500), 4.89 (1000). A measured 2.42 corresponds to μ_r ≈ 277 (ρ=0.196) or 226 (ρ=0.16). So with the nominal μ_r = 10³ the prediction (4.4–4.9) overshoots the measurement by ~2×; the wide μ_r range 100–2000 contains it. The paper's "well-approximated" statement is loose (asymptote at μ_r = 10³ would give |Z|/R ≈ 4.2).

## 5. Optical clocks tracking tidal potential
- Source: arXiv:2610.39635 (astro-ph.EP), submitted 2026-10-29. https://arxiv.org/abs/2610.39635 (PTB, NPL, INRiM, LNE-SYRTE, LPL, RIKEN et al.).
- Measured: amplitude scaling factor A (measured/model, Kalman filter): **A = 1.42(35)** INRiM–PTB; **A = 1.12(24)** NPL–PTB; weighted mean over all comparisons **Ā = 1.00(12)**. Model differential RRS up to ~5×10⁻¹⁸ peak-to-peak; each station's own RRS variation ≈ 4×10⁻¹⁷ (paper: "up to 5×10⁻¹⁷" at a fixed location). Clock instabilities 4.7×10⁻¹⁶/√(τ/s) (INRiM–PTB), 3.8×10⁻¹⁶/√(τ/s) (NPL–PTB). Detected within <1 day of data; significance >4σ for each.
- Paper's model: full tide model (celestial potential + solid Earth tide + ocean loading); reports agreement in time domain, spectra and amplitude.
- Quote: "agreeing with model predictions".
- Inputs from elsewhere: equilibrium-tide amplitudes (Stewart/Wahr tables), Love numbers (IERS 2010 nominal), site coordinates (public). Ocean loading omitted in the cases file (a few % effect on the potential; the paper includes it).
- SCOUT CHECK: with factor (1+k₂−h₂)=0.69, differential amplitudes (×10⁻¹⁸) INRiM–PTB: M2 2.42, S2 1.13, N2 0.46, K2 0.31, K1 0.62, O1 0.44, P1 0.21, Q1 0.08 (RSS 2.9 ⇒ pk-pk ≈ 6; all-in-phase upper bound 11); NPL–PTB: M2 2.62, S2 1.22, N2 0.50, K2 0.33, K1 1.95, O1 1.39, P1 0.65, Q1 0.27 (diurnal parts significant). Single-site M2 amplitude 6.8×10⁻¹⁸. Ballpark: consistent with the paper's "~5×10⁻¹⁸ pk-pk" differential and "~4×10⁻¹⁷" per station (sum of constituents). Note the INRiM–PTB scout calc has diurnal K1/O1 amplitude 0.6/0.4 although the paper says it neither expects nor observes substantial diurnal oscillations for INRiM–PTB; the paper's statement is relative to noise/the dominance of the semidiurnal part — a solver giving small diurnal terms for INRiM–PTB is fine.

## 6. EMF on a rod in a Helmholtz coil
- Source: arXiv:2609.06548 (physics.class-ph), submitted 2026-09-06. https://arxiv.org/abs/2609.06548 (Shao, Gao, Li, Mu, Li; Huzhou).
- Measured (Table I, rod 15 cm along x, 220 Hz, 30 mA rms, 400 turns, R = 10.5 cm): ε(y=0) = 0.000 mV; y=2.0 cm 0.195; 4.8 cm 0.526; 6.9 cm 0.694; **9.8 cm 0.807 mV (maximum; y/R = 0.933)**; 15.1 cm 0.628; 18.0 cm 0.460; 25.0 cm 0.285 mV. Also measured B at centre 0.1097 mT (detection coil), uniform to <4% within r < R/2.
- Paper's model: four simplified radial B-field models (step, linear, exponential, six-piece fit) of the Biot–Savart Helmholtz field; all reproduce trend and peak position; the piecewise model "quantitatively in good agreement with the experimental data".
- Quote: "quantitatively in good agreement with the experimental data".
- Extra input: none (the paper's model fits profiles to the Biot–Savart field, not to the EMF data).
- SCOUT CHECK (full Biot–Savart + Faraday as in the cases file): ε(y) rms in mV: 0.2 cm… y=2: 0.211, 4.8: 0.495, 6.9: 0.677, 9.8: 0.804, 15.1: 0.607, 25: 0.261; maximum 0.805 mV at y ≈ 10 cm. Deviations from measured: +8%, −6%, −2%, −0.4%, −3%, −8%. Step-model (uniform field inside R) gives max 0.979 mV at y = 10.2 cm (+21%). Ballpark: yes, excellent agreement. Note the theoretical central B (0.1028 mT rms) is 6% below the measured 0.1097 mT, yet the EMF matches the theory.

## 7. Peas in rapeseed oil
- Source: arXiv:2607.02625 (physics.ed-ph), submitted 2026-07-02. https://arxiv.org/abs/2607.02625 (Mossige; Oslo).
- Measured U_pea (cm/s) for groups 1–5: **1.90, 5.54, 7.01, 7.32, 7.91** (cylinder D = 11, 18, 20, 20, 27 mm). Inferred apparent viscosities (Stokes, no wall correction) 865, 196, 102, 195, 124 mPa·s; wall-corrected µ′ = 127, 66, 35, 75, 64 mPa·s (K_p = 7.58, 2.97, 2.89, 2.58, 1.94) vs literature 73 mPa·s (Brodin et al. 2025, plate–plate rheometer, 20 °C). Reynolds numbers 0.8, 5.1, 11.7, 5.4, 6.7.
- Paper's reading: values "differ from the literature value", expected for kitchen tools; wall effects explain the trend with cylinder diameter; Stokes law is violated (Re > 1) and Oseen would bring closer. So: partial agreement with large scatter (factor ~2), not quantitative.
- Quote: "the data for the sedimentation speed, Upea, vary much more".
- Input from elsewhere: viscosity 73 mPa·s is quoted in the paper (cited to a separate rheometer paper).
- SCOUT CHECK: Stokes/K_p predicted U = 3.09, 5.16, 3.67, 7.29, 7.12 cm/s (Stokes without wall: 23.4, 15.3, 10.6, 18.8, 13.9); with Oseen on top: 2.36, 3.38, 2.63, 4.46, 4.41. Measured/(Stokes/K_p) = 0.61, 1.07, 1.91, 1.00, 1.11. Group 3 data are internally inconsistent (ρ_pea = 1.10 g/mL, buoyancy-corrected weight small) and Group 1 is at the largest wall correction. Ballpark: yes for groups 2, 4, 5; Oseen correction makes it worse for 2, 4, 5.

## 8. Venus through a two-hole mask
- Source: arXiv:2609.27055 (physics.ed-ph), submitted 2026-09-22. https://arxiv.org/abs/2609.27055 (Friedman, Goman). (Companion paper arXiv:2610.30669 uses a flashlight; not used.)
- Measured (May 2026, Venus ≈13″ in the figure caption): d = 6 mm — fringes clear ("diameter less than 18″"); d = 10 mm — near first null, fringes "somewhat visible", corresponding to 11″; d = 14 mm — complete lack of fringes, corresponding to 8″. Inferred size ≈ **11″** ("reasonably close to the true value"; true ≈ 12–13″). Airy radius observed ≈ 60″ vs 69″ theory (2 mm hole). Other statement: null baseline for 10″ is ≈13 mm.
- Paper's model: V(d) = 2J₁(x)/x, d_null = 1.22λ/α; the observations are qualitative visual judgments. Reports rough agreement.
- Quote: "the measured size is approximately 11″, reasonably close to the true value".
- Extra input: Venus apparent diameter taken by scout from low-precision mean-element ephemerides (11.6″ on 1 May, 12.3″ on 15 May, 13.1″ on 30 May 2026; ≈1.27–1.44 AU); the paper quotes "about 13″" and "12″".
- SCOUT CHECK: d_null (550 nm) = 12.3 mm for 11.6″, 11.3 mm for 12.3″, 10.6 mm for 13″; so fringes clear at 6 mm, marginal around 10–11 mm, gone by 14 mm — consistent with the report. Note the data are visual and qualitative; a solver's inferred α from the 10–14 mm bracket = 8–11″ underestimates the true 12–13″ by ~15–30% per the paper itself.

## 9. Tank on a cart on a 2.4° ramp
- Source: arXiv:2610.33049 (physics.ed-ph), submitted 2026-10-18. https://arxiv.org/abs/2610.33049 (D. & P. Marasco, Foothill College / SJSU).
- Measured: oil edges move ~1 cm up/down, 2 cm over the 46 cm width ⇒ a ≈ 0.4 m/s² (g·2/46); slope of the sensor v(t): **0.38 m/s²** (release from rest); push-up run: surface-alignment 0.4, v(t) slope **0.39 m/s²**, constant through the turning point (no change at the peak); constant-velocity case: surface horizontal.
- Paper's model: a = g sin 2.4° = **0.41 m/s²**; reports agreement ("compares well").
- Quote: "This compares well with 0.38 m/s2".
- Extra input: none.
- SCOUT CHECK: g sin 2.4° = 0.4108 m/s²; tan 2.4° = 0.0419 ⇒ edge height change over 46 cm = 1.93 cm. Measured 0.38–0.39 is 5–7% below (rolling friction). Ballpark: yes.

## 10. Specific-heat experiment with a copper calorimeter
- Source: arXiv:2609.15124 (physics.ed-ph; v3 posted later), first submitted 2026-09-14. https://arxiv.org/abs/2609.15124 (Kushida, Oda, Yamaguchi; Osaka Kyoiku Univ.).
- Measured: model-construction data fit **Γ = 4.38 ± 0.04 J g⁻¹ K⁻¹**; independent test data (200 g water, 13 and 19 W) slope **4.35 ± 0.08**. Separate-mass analysis: c_w = 4.56 ± 0.24 J g⁻¹ K⁻¹ (2-parameter, limited precision) vs tabulated 4.18; C_cal difference between 170 g and 240 g data: −0.07 ± 0.08 J g⁻¹ K⁻¹ vs 0.07 expected (their estimated C_cup ≈ 42 J/K).
- Paper's model: Γ = c_w + C_cal/M_w with C_cal ≈ 42 J/K (0.25 J g⁻¹K⁻¹ at 170 g, 0.18 at 240 g); reports consistency (Γ slightly above c_w mainly due to the cup; other effects within precision).
- Quote: "fit gives Γ = 4.38 ± 0.04" (the paper writes the unit J g⁻¹ K⁻¹).
- Extra input: none.
- SCOUT CHECK: Γ = 4.43 (170 g), 4.39 (200 g), 4.36 (240 g); mean ≈ 4.39. Measured 4.38(4) and 4.35(8): within ~1σ of the zero-heat-loss prediction. Ballpark: yes.

---

## Honest notes
- Weakest cases as "predictions": #8 (visual, qualitative), #7 (large kitchen-scale scatter, Stokes beyond its validity), #9 (nearly trivial). Strongest, sharp, precision numbers: #1, #2, #6, #10, #5 (needs tide-potential calculation), #4 (strongly dependent on μ_r).
- Possible discrepancy-type cases: #4 (nominal μ_r overshoots by ~2×), #7 (scatter), #1 (measured speed 0.3% above reference, near 1σ of the reference).
- Dates all verified from arXiv submission dates (2026-07-02 to 2026-10-29). Case 5 data were taken earlier but first published in the Oct 2026 preprint. Case 2 v1 date 2026-07-29.
- A Roemer-eclipse paper (arXiv:2607.28512) was considered and rejected because its journal publication (Eur. J. Phys. 47 (2026) 025802) probably predates 30 June 2026; a ship-borne cosmic-ray paper (2607.04197) rejected for the same reason (Sci. Rep. 2025).
