# SEALED outcomes, round 2

Do not show to the predictor. Dates are arXiv v1 submission dates (all after 30 June 2026). All numbers are as the papers report them; "1σ" unless stated. Numbers marked (fig.) were read off a plotted figure by me, not tabulated by the authors.

Notes on sharpness (honest ranking, sharpest first): Cases 1, 2, 7 are sharp (inputs good to about 1–2 %). Cases 4, 6 (FSR) are sharp in the law but the measured quantity has large or small error bars as stated. Cases 5, 8, 9, 10 are moderate (stellar spectrum or modulus adds 10–25 % room). Case 3 is the weakest: the prediction range from the stated inputs spans about a factor of 2 (membrane-only against plate-with-tension), and the stress sign and the blister shape are not pinned. Case 6 Brillouin shift uses a bulk acoustic velocity for a 660 µm fibre.

---

## 1. Free-edge resonance of circular metal discs

- **Source:** https://arxiv.org/abs/2610.29194 , submitted 2026-10-21 (eess.AS). Table VI (specimen inventory, f1) and Sections III-A, III-B, IV-B.
- **Measured f1 (Hz), strike-to-strike SD 0.02–0.07 %, between-session reproducibility RMS 0.15 %:**
  - A (d 25.05, t 3.181): 24821.2
  - B (d 48.00, t 6.581): 13728.9
  - C (d 68.00, t 3.163): 3525.1
  - D (d 68.00, t 6.579): 7111.3
  - E (sterling Ag, d 51.17, t 0.818): 887.1 (from a lowered-floor re-run: split doublet at 886.4 and 896.9 Hz)
- **Paper's own model:** uncorrected thin-plate (Kirchhoff) prediction with fitted constant C = 1182.8 Hz·m gives residuals of +8.9, +5.6, +3.5, +1.6 and −3.6 % in order of increasing t/a. A one-parameter finite-thickness correction (β = 0.895 ± 0.047, fitted on the five aluminium discs themselves) reduces the worst case to 0.75 %. The aluminium calibration discs in the paper are Al1…Al5 (the residuals above cover all five, including Al2, d 34.00 mm, t 6.581 mm, which is not used here); here A, B, C, D are Al1, Al3, Al4, Al5.
- **Agreement as reported:** thin-plate theory over-predicts the thick (low a/t) discs; the thin disc agrees.
- **Quote:** "reduces the worst-case departure from thin-plate theory from 8.9 % to 0.75 %"
- **Inputs taken from elsewhere:** E, ν ranges from handbooks (Table II of the same paper). Dimensions and densities are the paper's Table VI.
- **My check (Kirchhoff, exact free-edge λ²(2,0) from J_2/I_2, E = 69 GPa, ν = 0.34 for Al; E = 80 GPa, ν = 0.37 for Ag):** A 26289 Hz (+5.9 % vs measured), B 14687 (+7.0 %), C 3526 (0.0 %), D 7338 (+3.2 %), E 890 (+0.3 %). Over the E, ν ranges the Al predictions move by about ±0.6 %, Ag by about ±2 %. My λ² values reproduce the paper's table (5.196 at ν = 0.35, 12.109 for (3,0)).

---

## 2. Mass deposited in series electrolysis cells

- **Source:** https://arxiv.org/abs/2609.28221 , submitted 2026-09-23 (physics.ed-ph). Table I and surrounding text.
- **Measured deposit masses (g), mass uncertainty 1.0 mg each:** Fe 0.1027, Ni 0.1099, Cu 0.1331, Zn 0.1220 (I = 0.205 A, t = 1800 s). Derived e (C): Fe 1.67e-19, Ni 1.64e-19, Cu 1.46e-19, Zn 1.64e-19 (each ±0.03e-19); mean e = (1.60 ± 0.081)e-19 C; standard value 1.602176634e-19.
- **Paper's own prediction:** Faraday's law with the standard e and N_A (the experiment is posed as a measurement of e).
- **Agreement as reported:** Fe, Ni, Zn within one or two error bars; Cu outside 3 error bars and attributed to a systematic error (a Cu plate put back into CuSO4 without current gained mass). Mean e within 1 % of the standard value.
- **Quote:** "This is within 5% margin of the standard value of the charge of electron."
- **Inputs from elsewhere:** molar masses (IUPAC standard values), F exact SI value. Paper's table uses A/z = 27.9225, 29.3467, 31.773, 32.69.
- **My check:** Q = I t = 369.0 C → 3.8244 mmol of electrons. Predicted masses: Fe 0.1068, Ni 0.1122, Cu 0.1215, Zn 0.1250 g. Uncertainty per cell about 1.9 % (current 1.7 % from ΔI = 0.0034 A, mass 0.9 %) ≈ 2.3 mg. Deviations measured − predicted: Fe −4.1 mg (−1.8σ), Ni −2.3 mg (−1.0σ), Cu +11.6 mg (+5σ), Zn −3.0 mg (−1.3σ). Three of four are low by 2–4 %, and Cu is high by 9.5 %.

---

## 3. Fundamental frequency of laser-formed SiO2 micro-membranes (WEAKEST CASE)

- **Source:** https://arxiv.org/abs/2611.07742 , submitted 2026-11-05 (physics.app-ph / optics). Fig. 5(f) and Fig. 6(c); Sec. 2.5.
- **Measured fundamental frequencies (fig.), ±0.2 MHz quoted instrument error plus ±0.3 MHz reading error:**

| r (µm) | 10.3 | 12.7 | 15.8 | 18.75 | 20.3 | 23.8 |
|---|---|---|---|---|---|---|
| f (MHz) | 18.8 | 13.2 | 9.6 | 8.3 | 7.9 | 7.8 |

  The text confirms the extremes: maximum 18.8 MHz, minimum 7.8 MHz; and 13.2 MHz for a cavity made at 403 mJ/cm².
- **Paper's own model:** ideal clamped membrane, f = 0.3828/r · sqrt(T/(ρ t)); T was a free parameter, T = 550 N/m for all radii "agrees astonishingly well" (a 335 N/m curve is given as lower bound). Using the quoted literature residual stress σ = 320 MPa (T = 320 N/m) they say gives "excellent agreement" with the fitted tension values. They also note the mode assignment is ambiguous ((1,1) with T = 215 N/m gives the same curve).
- **Agreement as reported:** good agreement with a single fitted T; the experimentally observed rise at small radius is stronger than the model's.
- **Quote:** "astonishingly good for this very basic model"
- **Inputs from elsewhere:** t = 1.00 ± 0.05 µm (wafer datasheet), ρ = 2.2 g/cm³, σ = 320 MPa (their ref. 39). E, ν for fused silica are mine (not in the paper).
- **My check:** membrane-only with T = 320 N/m: 14.2, 11.5, 9.24, 7.79, 7.19, 6.13 MHz, i.e. −25, −13, −4, −6, −9, −21 % against the measured. Clamped plate with tension (E = 73 GPa, ν = 0.17, same T): 30.1, 21.1, 14.9, 11.5, 10.2, 8.2 MHz, i.e. +60, +60, +55, +38, +30, +5 %. The measurement lies between the two models at every radius, and bending is not negligible (D/(T r²) = 0.2 at the smallest radius). With ±30 % on the stress, the membrane-only prediction moves by about ±15 %. A flat model with a tensile stress is itself questionable (thermal oxide is usually compressive; the blister is domed).

---

## 4. Slope of optical path length against pulse delay in a time-of-flight bench

- **Source:** https://arxiv.org/abs/2610.12614 , submitted 2026-10-08 (physics.ed-ph; accepted by The Physics Teacher). Fig. 2(b) and Results section.
- **Measured:** slope of the L-versus-Δt line (3.2 ± 0.2) × 10⁸ m/s (standard error of the fit); intercept −4.8 m, i.e. a systematic delay (15 ± 2) ns. Path lengths 0.35–5.14 m (seven points), length uncertainty 1–4 cm.
- **Paper's own prediction:** the expected speed of light in air.
- **Agreement as reported:** "compatible" with the expected value.
- **Quote:** "compatible with the expected value of the speed of light in air"
- **Inputs from elsewhere:** c = 299 792 458 m/s exact; n_air ≈ 1.00027 (mine; the paper uses the exact conventional value and does not state n_air).
- **My check:** c/n_air = 2.9971e8 m/s. The measured slope is +6.8 % above, i.e. +1.0σ of the quoted standard error; no inconsistency with c/n_air. Rise times quoted (5 ns photodiode, 4 ns generator) are consistent with a constant offset of order 10–15 ns.

---

## 5. Transverse wave dispersion on a pre-tensioned soft silicone rod

- **Source:** https://arxiv.org/abs/2611.05414 , submitted 2026-10-30 (physics.class-ph). Fig. 5, Table 1, Sec. "Transverse wave observation".
- **Measured phase velocities at 100 Hz (fig.; scatter about ±0.2 m/s):** T = 0.12 N: 3.4; 0.24 N: 3.7; 0.48 N: 4.8; 0.90 N: about 7.2 m/s. At low frequency (about 20–30 Hz) the data are scattered; the lowest-tension curve starts near 1.7–2 m/s.
- **Paper's own model:** coupled tension–Timoshenko model, inverted per tension level. Fitted effective E = 155, 155, 158, 176, 190, 226, 231 kPa and fitted T = 0.10, 0.19, 0.25, 0.38, 0.39, 0.54, 1.00 N for applied 0.12, 0.18, 0.24, 0.32, 0.38, 0.48, 0.90 N.
- **Agreement as reported:** fitted tensions consistent with applied ones (inset: along the equality line); fitted E much larger than the static one (59 kPa), interpreted as an effective dynamic modulus (viscoelastic rod, Zener model).
- **Quote:** "much larger than the reference value obtained from our stress-strain experiments"
- **Inputs from elsewhere:** E_static = 59 kPa from the authors' earlier study (Zhu et al. 2025); κ = 0.9 from Cowper 1966.
- **My check (tensioned Timoshenko, r = r_0/sqrt(1+ε), E = 59 kPa):** c(100 Hz) = 2.81, 3.26, 4.32, 6.57 m/s for T = 0.12, 0.24, 0.48, 0.90 N; string limits sqrt(T/ρA) = 1.86, 2.74, 4.15, 6.56 m/s. Against the figure readings the E = 59 kPa model is low by 17 %, 12 %, 10 % and 9 %. Using the fitted E (155–231 kPa) raises c(100 Hz) to 3.5, 3.8, 4.6, 6.7: within about 5 % of the readings. The string limit alone uses T, r, ρ with no modulus and is within about 10–15 % of the low-frequency data.

---

## 6. Mode spacing and Brillouin shift of a silica-fibre whispering-gallery resonator

- **Source:** https://arxiv.org/abs/2609.22629 , submitted 2026-09-18 (physics.optics). Methods, Results (comb spacing, Brillouin shift), Supplement.
- **Measured:** azimuthal comb spacing 100.2 ± 0.1 GHz; Brillouin pump–Stokes separation 9.6 GHz (spectrum), resonance-pair spacing 9.60 ± 0.01 GHz; pump at 1576.069 nm, first Stokes line at 1576.150 nm.
- **Paper's own prediction:** expected azimuthal FSR c/(π n D) = 98.5 ± 0.9 GHz for D = 660 ± 6 µm (index not stated; implies about 1.468). For the Brillouin shift only the statement that 9.6 GHz is the expected value for backward SBS in silica resonators (no number given).
- **Agreement as reported:** FSR "in good agreement with the value expected from the fiber diameter" (measured 1.7 % above 98.5, 1.9σ of the 0.9 GHz diameter-driven uncertainty); Brillouin shift said to be consistent with silica.
- **Quote:** "in good agreement with the value expected from the fiber diameter"
- **Inputs from elsewhere:** Malitson Sellmeier index of fused silica (mine); V_L = 5900–5970 m/s (mine, bulk fused silica).
- **My check:** n = 1.4437, n_g = 1.4628 → FSR 98.84 ± 0.89 GHz with the group index (100.15 GHz if the phase index were used). Measured 100.2 is +1.4 GHz (+1.5σ) above the group-index value. Brillouin shift 2nV_L/λ = 10.81–10.94 GHz; the measured 9.60 GHz is 11–12 % lower than the bulk-silica estimate, a difference the paper does not discuss (the acoustic wave in a 660 µm fibre cavity may not have the bulk longitudinal velocity).

---

## 7. Energy-crossing time in an overdamped series RLC circuit

- **Source:** https://arxiv.org/abs/2609.33277 , submitted 2026-09-27 (quant-ph, pedagogical). Experimental section and Fig. 2.
- **Measured:** energy crossing at t_× ≈ 1.9 ms with E_× ≈ 166 µJ (deterministic records; linear interpolation of the sign change of E_f − E_s; 2500 samples per trace). Initial energies 1.993 mJ (fast) and 0.220 mJ (slow). No statistical uncertainty is given for t_×.
- **Paper's own prediction:** with R_comp = 27.9 Ω, a predicted crossing near 2.18 ms; a fit-window analysis of the transients gives an effective R_dyn = 33.08 Ω (16–84 %: 32.49–33.52 Ω), with which the crossing is reproduced. The paper states that small additional losses (switches, contacts, winding details) shift the crossing noticeably.
- **Agreement as reported:** crossing reproduced when the dynamically inferred resistance is used; the component-based value gives a later crossing.
- **Quote:** "using the component value Rcomp = 27.9 Ω gives a predicted crossing near 2.18 ms"
- **Inputs from elsewhere:** none; L, C, R_comp, R_ext are the paper's.
- **My check (pure-mode formula given in CASES):** R = 27.9 Ω: λ_s = −92.6 s⁻¹, λ_f = −535.8 s⁻¹, t_× = 2.49 ms, E_× = 139 µJ. R = 26.9 / 28.9 Ω: t_× = 2.68 / 2.32 ms. R = 33.08 Ω: t_× = 1.85 ms, E_× = 167 µJ, matching the measurement (1.9 ms, 166 µJ). My pure-mode value for 27.9 Ω (2.49 ms) is later than the paper's 2.18 ms because the paper presumably includes mixed-mode terms; the measured 1.9 ms lies below both.

---

## 8. 15 µm secondary-eclipse depth of a hot rocky planet around an M dwarf

- **Source:** https://arxiv.org/abs/2609.30552 , submitted 2026-09-24 (astro-ph.EP; A&A). Abstract, Sec. 4.1, Table A.1.
- **Measured:** occultation depth 200.5 ± 12.7 ppm in MIRI/F1500W; T_b(15 µm) = 923 (+39, −38) K. Independent reductions: 197 ± 17 and 179 (+17, −16) ppm.
- **Paper's own prediction:** zero-Bond-albedo, no-redistribution, disk-integrated bolometric reference T = 686 ± 14 K (their own zero-albedo grey airless-surface model with a stellar model spectrum gives a much shallower eclipse); table values T_eq = 537.0 K (full redistribution).
- **Agreement as reported:** discrepancy: the depth differs from the tested zero-albedo grey airless-surface model by 5.2σ ("anomalously hot dayside"); also inconsistent with the high-mean-molecular-weight atmospheres tested (pure CO2, pure H2O, N2 with 100 ppm CO2).
- **Quote:** "differs from the tested zero-albedo, grey airless-surface model by 5.2σ"
- **Inputs from elsewhere:** T_* = 3540 ± 51 K, R_* = 0.3382 R☉, a/R_* = 21.75 (+0.59, −0.60) and R_p/R_* = 0.03123 ± 0.00018 are the paper's Table A.1 (its global analysis combines TESS, NIRSpec transit, the MIRI eclipse, RVs and Gaia; a/R_* and R_p/R_* are transit-dominated, but strictly the eclipse is in the joint fit). Table also gives T_eff,SED = 3396 K.
- **My check:** T_day = 685.9 K (f = 2/3) and 536.7 K (f = 1/4). With a blackbody star at 3540 K the depths are 99 ppm and 61 ppm; with the SED temperature 3396 K they are 103 and 63 ppm. Back-converting the paper's own T_b and depth suggests its stellar model implies about 120 ppm at 686 K (the M-dwarf 15 µm flux is below the Teff blackbody). Measured 200.5 ppm is therefore about 1.7–2 times any bare-rock value, i.e. about 6–8σ above 99–120 ppm.

---

## 9. Mid-infrared eclipse depth of an ultra-short-period rocky planet around a K dwarf

- **Source:** https://arxiv.org/abs/2609.03029 , submitted 2026-09-02 (astro-ph.EP). Abstract, Sec. 3.1–3.2, Table 2.
- **Measured:** MIRI/LRS white-light (5.06–10.55 µm) partial-eclipse depth 81 ± 16 ppm; T_b = 1967 (+237, −253) K; brightness-temperature ratio R = T_b/T_max = 0.81 ± 0.10. A second reduction (Eureka!) gave 73 ± 21 ppm; a different fit 77 ± 15 ppm. Earlier Spitzer 4.5 µm: 33 ± 22 ppm.
- **Paper's own prediction:** for R = 1 (zero albedo, no redistribution) the white-light depth is 112 (+5, −4) ppm and the dayside temperature 2400 ± 50 K.
- **Agreement as reported:** measured depth is lower than the bare-rock value by 1.8σ; interpreted as evidence for an atmosphere (higher albedo and/or heat redistribution). 1.2σ higher than the Spitzer-derived value.
- **Quote:** "we find that our results are best explained by the presence of an atmosphere"
- **Inputs from elsewhere:** a/R_* = 3.35 (+0.10, −0.13) and R_p/R_* = 0.0161 ± 0.0002 are the paper's (Tables 1, 2). T_* is not stated in the paper; I used 4850 ± 75 K recalled as the literature value; the paper's own T_max = 2400 ± 50 K with a/R_* = 3.35 implies T_* ≈ 4861 K, consistent. T_eq = 1875 (+45, −39) K in Table 2 (full redistribution).
- **My check:** T_day = 2394 K (f = 2/3) and 1874 K (f = 1/4). Blackbody-star depths over 5.06–10.55 µm: 99 ppm and 67 ppm. The paper's model-star number for f = 2/3 is 112 ppm. Measured 81 ± 16 ppm is 1.1σ below my blackbody f = 2/3 value, 1.8σ below the paper's, and 0.9σ above my f = 1/4 value; the data do not separate the two cases decisively.

---

## 10. Optical and near-infrared eclipse depths of an ultra-short-period rocky planet

- **Source:** https://arxiv.org/abs/2609.31966 , submitted 2026-09-25 (astro-ph.EP). Abstract, Sec. 3 (equations 4–6), Fig. 3.
- **Measured:** planet-to-star flux ratio 37 ± 10 ppm (TESS) and 69 (+14, −13) ppm (HST/WFC3 G141, 1.127–1.570 µm). Brightness temperatures T_b,TESS = 2566 (+94, −110) K, T_b,HST = 2497 (+110, −119) K, joint T_b = 2524 (+77, −84) K (thermal-only blackbody).
- **Paper's own prediction:** zero-albedo no-redistribution limit T_p,max = 2574 (+36, −35) K; full redistribution 2015 (+28, −29) K. A geometric albedo A_g = 0.1 would add about 11 ppm per band (temperature then 2407 K).
- **Agreement as reported:** joint brightness temperature ratio R = 0.980 (+0.032, −0.034): consistent with the zero-albedo, no-redistribution limit; HST-only R = 0.970 (+0.044, −0.048), TESS-only 0.996 (+0.039, −0.044). The authors caution that thermal and reflected light are degenerate in these bands.
- **Quote:** "consistent with the zero-albedo, no-redistribution limit"
- **Inputs from elsewhere:** T_*, R_*, M_*, P, R_p/R_* from the discovery paper (arXiv 2507.08464): T_* = 4109 (+28, −27) K, R_* = 0.651 ± 0.012 R☉, M_* = 0.661 (+0.021, −0.024) M☉, P = 0.22419577 d, R_p/R_* = 0.02133 (+0.00033, −0.00031). The discovery paper does not state a/R_*; I computed it from Kepler's law.
- **My check:** a/R_* = 2.078, a = 0.00629 au; T_day = 2576 K (f = 2/3), 2016 K (f = 1/4), reproducing the paper's 2574 and 2015 K. Blackbody-star depths: TESS band 34.5 ppm and 5.5 ppm; G141 band 89.4 ppm and 27.9 ppm. Reflected light A_g (R_p/a)² = 10.5 ppm for A_g = 0.1 (paper: about 11 ppm). Measured TESS 37 ± 10 ppm agrees with f = 2/3 (0.25σ) and not with f = 1/4 (3σ, without reflected light). Measured G141 69 (+14, −13) is 1.5σ below my blackbody f = 2/3 value (the paper's PHOENIX-based treatment gives agreement), and 3σ above f = 1/4.
