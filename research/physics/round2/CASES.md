# Blind prediction test, physics, round 2: ten cases

Each case is a quantity that was measured and first reported after 30 June 2026. The inputs below do not depend on the measured quantity. Where the question says "range", give a central value and an honest interval. Where it asks whether the measurements agree, answer from your own predicted interval and the stated measurement uncertainty.

Origin tags: **indep.** = independent measurement made alongside but not derived from the target quantity; **lit.** = literature value; **datasheet** = manufacturer or handbook; **geom.** = geometry measured on the apparatus.

---

## 1. Free-edge resonance of circular metal discs (acoustics / vibration, Bessel plate modes)

**System.** Flat circular discs, free edge, supported only at the centre (a nodal point of the mode), struck by hand; the audio spectrum is recorded and the lowest peak is taken as the (2,0) mode (two nodal diameters, no nodal circle). Five discs: four machined aluminium discs of different aspect ratio and one machined sterling-silver disc.

**Laws.**
- Kirchhoff thin plate, free edge: f(n,s) = λ²(n,s) / (2π a²) · sqrt( D / (ρ t) ), with bending rigidity D = E t³ / (12 (1 − ν²)), radius a = d/2, thickness t, density ρ.
- λ² = (k a)² is the s-th root of the free-edge characteristic equation for deflection w = [A J_n(kr) + C I_n(kr)] cos nθ (J_n Bessel, I_n modified Bessel), with M_r = 0 and the Kirchhoff effective shear V_r = 0 at r = a. For n = 2, the lowest root depends weakly on Poisson's ratio: λ² ≈ 5.358 (ν = 0.30), 5.26 (ν = 0.33), 5.196 (ν = 0.35), 5.128 (ν = 0.37). Compute your own if you prefer.
- Equivalent: f = λ² t c_p / (2π a² √12) with plate wave speed c_p = sqrt( E / (ρ (1 − ν²)) ).
- Corrections to thin-plate theory scale with powers of t/a. Whether they matter at the stated aspect ratios is for you to judge.

**Inputs.**

| Disc | material | diameter d (mm) | thickness t (mm) | density ρ (kg/m³) | origin |
|---|---|---|---|---|---|
| A | Al | 25.05 | 3.181 | 2679 | geom.; mass and caliper volume |
| B | Al | 48.00 | 6.581 | 2725 | geom. |
| C | Al | 68.00 | 3.163 | 2712 | geom. |
| D | Al | 68.00 | 6.579 | 2709 | geom. |
| E | sterling Ag (92.5 % Ag) | 51.17 | 0.818 | 10140 | displacement (Archimedes) density |

- Uncertainties: thickness by calipers ±0.01 mm (mean of 3–4 positions); diameter ±0.1 mm; density ±0.5 % (silver disc: ±0.7 %).
- Aluminium: alloy and temper unknown; handbook E = 68–70 GPa, ν = 0.33–0.35 (datasheet / lit.).
- Sterling silver: handbook E = 76–83 GPa, ν = 0.37 (lit.).

**Question.** What fundamental free-edge frequency f(2,0), in Hz, do these laws and inputs give for each of the five discs? Give a range for each. Do the measured frequencies agree with your ranges?

---

## 2. Mass deposited in series electrolysis cells (electrochemistry, Faraday's laws)

**System.** Four electrolytic cells in series (so the same current flows through each): 20 % by weight aqueous sulphates of Fe, Ni, Cu and Zn, with a plate cathode in each cell. Constant-current supply. Cathode plates were weighed on an analytical balance before and after, dried between weighings.

**Laws.** m = (A/z) · I t / (N_A e) = (A/z) · I t / F, with molar mass A, valence z (the divalent ion in each sulphate), F = N_A e = 96485.33 C/mol (exact SI value).

**Inputs.**
- Current I = 0.205 A, set in constant-current mode and monitored; uncertainty ΔI = 0.002·I + 3 mA (supply specification) (datasheet).
- Time t = 1800 s (stopwatch, timing uncertainty not stated).
- Molar masses (lit.): Fe 55.845, Ni 58.693, Cu 63.546, Zn 65.38 g/mol. Valence z = 2 for all four.
- Balance resolution 0.1 mg; the source states an effective mass uncertainty of 1.0 mg per weighing (reading drift).

**Question.** What mass (g) of Fe, Ni, Cu and Zn do Faraday's laws predict on the four cathodes, with uncertainty? Do the four measured masses agree with Faraday's law at the stated uncertainties? Say whether you expect any systematic effect for any of the four cells, and in which direction.

---

## 3. Fundamental frequency of laser-formed SiO2 micro-membranes (micromechanics, drum and plate modes)

**System.** A single ultrashort laser pulse delaminates the thermal-oxide layer from a silicon wafer, leaving a circular blister (cavity) whose cover is a thin SiO2 membrane. Low-fluence re-excitation makes the membrane ring, detected as reflectivity oscillations on a fast photodiode; the dominant FFT peak is taken as the fundamental mode. Six cavities of different radius were measured.

**Laws.**
- Ideal membrane (tension T in N/m, clamped at radius r): f_0n = ( j_0n / (2π r) ) · sqrt( T / (ρ t) ), with j_01 = 2.405 (first zero of Bessel J_0) and T = σ_0 t.
- Clamped circular plate under tension (includes bending): D ∇⁴w − T ∇²w + ρ t ∂²w/∂t² = 0, D = E t³ / (12 (1 − ν²)). For w(r) e^{iωt}: w = A J_0(k_1 r) + B I_0(k_2 r), with k_1² = [ −T + sqrt(T² + 4 D ρ t ω²) ] / (2D) and k_2² = [ T + sqrt(T² + 4 D ρ t ω²) ] / (2D). Clamped condition (w = w' = 0 at r): k_2 J_0(k_1 r) I_1(k_2 r) + k_1 J_1(k_1 r) I_0(k_2 r) = 0.

**Inputs.**
- Membrane thickness t = 1.00 ± 0.05 µm (datasheet, wafer vendor).
- Density ρ = 2.2 g/cm³ (lit.).
- Effective tensile stress σ_0 = 320 MPa, i.e. T = 320 N/m. This is the residual-stress value for thermally grown SiO2 films adopted by the source from the literature (lit.); literature spread across wafers is of order ±30 %.
- Young's modulus E = 70–73 GPa, ν = 0.17 (fused silica, lit.).
- Cavity (clamp) radii from optical microscopy, ±0.25 µm; values were read off a plot, so allow ±0.3 µm: r = 10.3, 12.7, 15.8, 18.75, 20.3, 23.8 µm.
- The largest cavities bulge by up to about 1.5 µm (cavity radius 25 µm); whether a flat clamped model applies is for you to judge.

**Question.** What fundamental frequency, in MHz, do these laws and inputs give for each of the six radii? Give a range for each. Do the measured fundamental frequencies agree with your ranges?

---

## 4. Slope of optical path length against pulse delay in a time-of-flight bench (optics / metrology)

**System.** An IR laser diode is driven by a square pulse (1 kHz, 10 % duty cycle, 0 to 4.0 V). Light travels in room air over a folded path (lens, three plane mirrors, lens) to a PIN photodiode. The delay is the time between the half-height crossings of the diode drive signal and the photodiode signal, read off a digital oscilloscope in 4-pulse average mode. Delays were recorded for seven path lengths, and path length L was fitted against delay Δt by a straight line L = s·Δt + L_0.

**Laws.** Group velocity of light in air v = c / n_air with c = 299 792 458 m/s (exact) and n_air ≈ 1.00027 at 850 nm and room conditions (lit.). A constant electronic and rise-time offset in the delay only shifts the intercept L_0. The standard error of an ordinary least-squares slope follows from the per-point scatter and the spread of the delays; you must estimate it from the specifications below.

**Inputs.**
- Seven path lengths (m): 0.35, 0.99, 1.88, 2.28, 3.43, 4.39, 5.14 (geom.), uncertainty about 1 cm for the short paths rising to about 4 cm for the long ones (increases with the number of reflections).
- Laser diode: rise time 0.1 ns, emission 850 nm (datasheet).
- Photodiode: PIN silicon, typical rise time 5 ns at 20 V reverse bias (operated at 30 V, 68 Ω load) (datasheet).
- Waveform generator: edge time about 4 ns in square mode; oscilloscope: 200 MHz bandwidth.
- Cables: all coaxial runs 50 cm.
- Per-point timing uncertainty is not given by the source: estimate it from the instrument specifications.

**Question.** What slope s (m/s) of the L-versus-Δt fit do these laws and inputs give, with a plausible standard error for a seven-point fit? Does the measured slope agree with c/n_air?

---

## 5. Transverse wave dispersion on a pre-tensioned soft silicone rod (mechanics / elastic waves)

**System.** A cylindrical Ecoflex 00-20 rod (nearly incompressible) clamped at the top, stretched by a hanging load, excited transversely by a mechanical vibrator (pulse centred at 200 Hz, content below 200 Hz). Transverse motion is imaged by a high-speed camera (3030 frames/s) and phase velocity versus frequency is obtained by space-time correlation.

**Laws.**
- Incompressible stretch: radius r = r_0 / sqrt(1 + ε); density unchanged; cross-section A = π r², I = π r⁴/4; shear modulus G = E/3.
- String limit (low frequency): c_0 = sqrt( T / (ρ A) ).
- Tensioned Timoshenko beam (transverse displacement w, rotation φ, shear coefficient κ): ρA w_tt = κGA (w_xx − φ_x) + T w_xx; ρI φ_tt = E I φ_xx + κGA (w_x − φ). A plane wave of angular frequency ω = 2πf and wavenumber k satisfies [(T + κGA) k² − ρAω²] [E I k² + κGA − ρIω²] − (κGA)² k² = 0; phase velocity c = ω/k (take the propagating root).

**Inputs.**

| applied strain ε (%) | applied axial force T (N) |
|---|---|
| 1.9 | 0.12 |
| 6.8 | 0.18 |
| 10.7 | 0.24 |
| 15.6 | 0.32 |
| 20.6 | 0.38 |
| 27.5 | 0.48 |
| 69.6 | 0.90 |

- Density ρ = 1070 kg/m³ (datasheet).
- Unstretched radius r_0 = 3.25 mm (geom.).
- Timoshenko shear coefficient κ = 0.9 (lit., cylinder).
- Quasi-static tensile Young's modulus E = 59 kPa (indep., stress–strain test on the same material; no dynamic modulus measurement is available).
- Force T: indep. measurement (static load), uncertainty about ±0.02 N.

**Question.** What phase velocity c (m/s) do these laws and inputs give at f = 100 Hz for T = 0.12, 0.24, 0.48 and 0.90 N, and what is the low-frequency (string) limit for each? Give ranges. Do the measured phase velocities at 100 Hz agree?

---

## 6. Mode spacing and Brillouin shift of a silica-fibre whispering-gallery resonator (photonics / nonlinear optics)

**System.** A silica optical fibre of nominal diameter D = 660 ± 6 µm, locally heated to form a surface nanoscale axial photonics resonator, is pumped by a CW tunable laser at 1576.07 nm through a tapered fibre. The generated spectrum contains frequency comb teeth separated by the azimuthal free spectral range, plus Stokes lines from stimulated Brillouin scattering (backward, first order), whose separation from the pump is measured on an optical spectrum analyser and by resonance spectroscopy.

**Laws.**
- Azimuthal FSR of a whispering-gallery mode near the equator: Δν_φ = c / (π n_g D), with group index n_g = n − λ dn/dλ.
- Backward Brillouin shift: ν_B = 2 n V_L / λ, with longitudinal acoustic velocity V_L.

**Inputs.**
- D = 660 ± 6 µm (datasheet).
- Pump wavelength λ = 1576.07 nm (set).
- Fused-silica refractive index at 1576 nm: n = 1.4437, dn/dλ = −0.0121 µm⁻¹ (lit., Sellmeier).
- Bulk fused-silica longitudinal velocity V_L = 5900–5970 m/s (lit.).

**Question.** What azimuthal FSR (GHz) and what first-order Brillouin shift (GHz) do these laws and inputs give? Give ranges. Do the measured FSR and Brillouin shift agree?

---

## 7. Energy-crossing time in an overdamped series RLC circuit (electronics / dynamics)

**System.** Series RLC loop released at t = 0 from an initial state (capacitor voltage V_C(0), current I(0)). Two preparations are released one after the other: a "fast" state prepared with I(0) = λ_f C V_C(0) and a "slow" state prepared with I(0) = λ_s C V_C(0), where λ_f, λ_s are the two (real, negative) decay rates of the circuit. The fast state starts with the larger stored energy. Energy is reconstructed from the measured capacitor voltage and the current (voltage across a sensing resistor): E(t) = C V_C² / 2 + L I² / 2.

**Laws.**
- q̈ + (R/L) q̇ + q/(LC) = 0; with α = R/(2L), ω_0 = 1/sqrt(LC), the rates are λ_{s,f} = −α ± sqrt(α² − ω_0²), overdamped for α > ω_0.
- Pure-mode states decay as E_{s,f}(t) = E_{s,f}(0) exp(2 λ_{s,f} t). The two energies cross at t_× = ln[E_s(0)/E_f(0)] / [2 (λ_f − λ_s)], at which E_× = E_s(t_×).

**Inputs.**
- L = 44.4 ± 1.2 mH, C = 454 ± 8 µF (component specifications / bench measurement, indep.).
- Total series resistance from component-level measurement R = 27.9 ± 1.0 Ω (indep.; includes inductor winding 5.7 ± 0.5 Ω and the 22.2 ± 0.7 Ω sensing resistor).
- Initial energies from voltages measured just before release: E_f(0) = 1.993 mJ, E_s(0) = 0.220 mJ (assume ±2 %).
- Time origin: the release instant (a common fixed offset is removed).
- Switches, contacts and wiring may add resistance not counted in the component-level R; treat that as an unknown you must bound.

**Question.** What crossing time t_× (ms) and what crossing energy E_× (µJ) do these laws and inputs give, with uncertainty? Do the measured values agree?

---

## 8. 15 µm secondary-eclipse depth of a hot rocky planet around an M dwarf (astronomy, thermal emission)

**System.** A transiting rocky planet (radius about 1.15 R⊕, period 3.93 d) around a nearby M dwarf (distance 9.43 pc). A JWST/MIRI imaging eclipse observation in the F1500W filter (central wavelength 15.0 µm, passband roughly 13.5–16.5 µm) measures the planet's dayside flux relative to the star.

**Laws.**
- Dayside equilibrium temperature: T_day = T_* sqrt(R_*/a) · [f (1 − A_B)]^{1/4}, with f = 2/3 (no heat redistribution, instantaneous re-emission) up to f = 1/4 (full redistribution), Bond albedo A_B.
- Eclipse depth: F_p/F_* = (R_p/R_*)² · ∫ B_λ(T_day) W_λ λ dλ / ∫ F_{*,λ} W_λ λ dλ, with Planck function B_λ and filter throughput W_λ. Brightness temperature T_b: the temperature at which the Planck formula reproduces the depth in the band.

**Inputs.**
- Stellar effective temperature T_* = 3540 ± 51 K (stellar parameters from photometry plus parallax, independent of the eclipse).
- Stellar radius R_* = 0.338 ± 0.009 R☉ (same origin).
- a/R_* = 21.75 ± 0.60 and R_p/R_* = 0.03123 ± 0.00018 (from the transit light curves, not from the eclipse).
- The stellar flux in the band: treat the star as a blackbody at T_*, but allow for a systematic of 10–25 % because M-dwarf spectra depart from a blackbody near 15 µm (or use any model atmosphere you trust).

**Question.** What eclipse depth (ppm) and brightness temperature at 15 µm do these laws and inputs give for the bounding cases A_B = 0 with f = 2/3 and f = 1/4? Do the measured depth and brightness temperature agree with the bare-rock bounds?

---

## 9. Mid-infrared eclipse depth of an ultra-short-period rocky planet around a K dwarf (astronomy, thermal emission)

**System.** A transiting rocky planet (radius about 1.29 R⊕, orbital distance about 0.0112 au) around a K dwarf. A JWST/MIRI low-resolution-spectrometer observation covers a secondary eclipse; the white-light eclipse depth is taken over 5.06–10.55 µm.

**Laws.** Same as Case 8 (T_day formula; band-integrated Planck ratio; brightness temperature). The throughput W_λ over 5.06–10.55 µm may be taken as flat.

**Inputs.**
- Stellar effective temperature T_* = 4850 ± 75 K (lit.: the K-dwarf discovery paper; this value is quoted from memory of that source, not verified here).
- a/R_* = 3.35 (+0.10, −0.13) and R_p/R_* = 0.0161 ± 0.0002 (from transit fits to TESS photometry plus radial velocities and a stellar-density prior, not from the eclipse).
- Stellar flux: blackbody at T_* with a 5–15 % systematic allowance (or a model atmosphere).

**Question.** What white-light eclipse depth (ppm) and brightness temperature do these laws and inputs give for A_B = 0 with f = 2/3 and with f = 1/4? Does the measured depth agree with either bound?

---

## 10. Optical and near-infrared eclipse depths of an ultra-short-period rocky planet (astronomy, thermal plus reflected light)

**System.** A transiting rocky planet with a 5.4-hour orbit around a late K dwarf. The secondary eclipse was measured in two bands: the TESS bandpass (600–1000 nm) and the HST WFC3 G141 bandpass (analysis range 1.127–1.570 µm).

**Laws.**
- Eclipse depth in a band: F_p/F_* = (R_p/R_*)² ∫ B_λ(T_day) W_λ λ dλ / ∫ F_{*,λ} W_λ λ dλ + A_g (R_p/a)², where A_g is the geometric albedo (reflected light, Lambertian phase function at secondary eclipse).
- T_day as in Case 8. Kepler's third law: a³ = G M_* P² / (4π²).

**Inputs.**
- Stellar T_* = 4109 (+28, −27) K; R_* = 0.651 ± 0.012 R☉; M_* = 0.661 (+0.021, −0.024) M☉ (stellar SED fit and isochrones from the discovery paper, lit.).
- Orbital period P = 0.22419577 d (lit., transit timing).
- R_p/R_* = 0.02133 (+0.00033, −0.00031) (transit fit, lit.).
- Stellar flux: blackbody at T_* with a 5–15 % systematic allowance (or a model atmosphere).

**Question.** What eclipse depths (ppm) in the TESS band and in the WFC3 G141 band do these laws and inputs give for A_B = 0, f = 2/3, A_g = 0, and for the other limiting combinations you consider physically allowed (f = 1/4; A_g up to 0.1)? Do the measured depths in the two bands agree with your predictions?
