# Physics blind round 2 — PREDICTIONS (from CASES.md only; frozen before SEALED/outcomes.md is opened)

## 1. Free-edge discs, f(2,0) — ZTL (thin plate, the stated law) + MODEL (Mindlin thickness correction)
- disc A (Al, t/a 0.254): thin plate f in [25485.9, 27107.4] Hz (ZTL judge: EARNED both); MODEL thick-plate factor 0.940 -> [23193.7, 26294.8] Hz
- disc B (Al, t/a 0.274): thin plate f in [14316.1, 15062.1] Hz (ZTL judge: EARNED both); MODEL thick-plate factor 0.931 -> [12836.7, 14543.3] Hz
- disc C (Al, t/a 0.093): thin plate f in [3435.2, 3617.2] Hz (ZTL judge: EARNED both); MODEL thick-plate factor 0.991 -> [3390.3, 3601.5] Hz
- disc D (Al, t/a 0.194): thin plate f in [7160.9, 7515.6] Hz (ZTL judge: EARNED both); MODEL thick-plate factor 0.964 -> [6772.6, 7379.8] Hz
- disc E (Ag, t/a 0.032): thin plate f in [850.7, 924.6] Hz (ZTL judge: EARNED both); MODEL thick-plate factor 0.999 -> [849.3, 924.1] Hz

## 2. Faraday's law, four cells in series — ZTL (+ Lean) + MODEL (current efficiency)
- Fe: m in [105.01, 108.56] mg (central 106.79); weighing ±1.4 mg (two weighings) on top; ZTL judge: EARNED both; Lean: theorem
- Ni: m in [110.37, 114.10] mg (central 112.23); weighing ±1.4 mg (two weighings) on top; ZTL judge: EARNED both; Lean: theorem
- Cu: m in [119.49, 123.53] mg (central 121.51); weighing ±1.4 mg (two weighings) on top; ZTL judge: EARNED both; Lean: theorem
- Zn: m in [122.94, 127.10] mg (central 125.02); weighing ±1.4 mg (two weighings) on top; ZTL judge: EARNED both; Lean: theorem
- MODEL, said before opening: Cu at Faraday (~100 % efficiency from sulphate); Fe, Ni, Zn BELOW Faraday —
  hydrogen evolution at the cathode takes part of the charge (Zn and Fe most), so their masses fall short

## 3. SiO2 micro-membranes — NUM (clamped tensioned plate: a J0/J1/I0/I1 root) and the membrane limit
- r = 10.3 µm: membrane f in [11.52, 16.64] MHz; tensioned clamped PLATE f in [25.96, 34.05] MHz (the plate is the stated full law; the bulge is not modelled)
- r = 12.7 µm: membrane f in [9.40, 13.42] MHz; tensioned clamped PLATE f in [18.25, 23.76] MHz (the plate is the stated full law; the bulge is not modelled)
- r = 15.8 µm: membrane f in [7.59, 10.74] MHz; tensioned clamped PLATE f in [12.85, 16.72] MHz (the plate is the stated full law; the bulge is not modelled)
- r = 18.75 µm: membrane f in [6.41, 9.02] MHz; tensioned clamped PLATE f in [9.89, 12.92] MHz (the plate is the stated full law; the bulge is not modelled)
- r = 20.3 µm: membrane f in [5.93, 8.32] MHz; tensioned clamped PLATE f in [8.80, 11.52] MHz (the plate is the stated full law; the bulge is not modelled)
- r = 23.8 µm: membrane f in [5.07, 7.08] MHz; tensioned clamped PLATE f in [7.02, 9.24] MHz (the plate is the stated full law; the bulge is not modelled)

## 4. Time-of-flight slope — NUM (c/n_air; the OLS standard error from the specifications)
- per-point timing σ 0.1 ns, path σ 2 cm: slope SE ≈ 2.503e+06 m/s (0.8 %)
- per-point timing σ 0.3 ns, path σ 3 cm: slope SE ≈ 6.585e+06 m/s (2.2 %)
- per-point timing σ 0.5 ns, path σ 4 cm: slope SE ≈ 1.078e+07 m/s (3.6 %)
- PREDICTED slope s = c/n_air = 2.997115e+08 m/s; expected measured within ~2 SE of it, SE 1–4 % (σ_t 0.1–0.5 ns)

## 5. Pre-tensioned silicone rod, phase velocity at 100 Hz — NUM (the tensioned Timoshenko quartic)
- T = 0.12 N (ε 1.9 %): string limit c0 in [1.694, 2.004] m/s; Timoshenko c(100 Hz) in [2.743, 2.881] m/s (E = 59 kPa quasi-static: a dynamic modulus would be higher and push c up)
- T = 0.24 N (ε 10.7 %): string limit c0 in [2.619, 2.847] m/s; Timoshenko c(100 Hz) in [3.191, 3.338] m/s (E = 59 kPa quasi-static: a dynamic modulus would be higher and push c up)
- T = 0.48 N (ε 27.5 %): string limit c0 in [4.064, 4.237] m/s; Timoshenko c(100 Hz) in [4.248, 4.398] m/s (E = 59 kPa quasi-static: a dynamic modulus would be higher and push c up)
- T = 0.9 N (ε 69.6 %): string limit c0 in [6.483, 6.629] m/s; Timoshenko c(100 Hz) in [6.498, 6.641] m/s (E = 59 kPa quasi-static: a dynamic modulus would be higher and push c up)

## 6. Silica WGM resonator — ZTL (+ Lean): FSR and Brillouin shift
- n_g = 1.46277; FSR in [97.954, 99.751] GHz (ZTL judge: EARNED both; Lean: theorem)
- Brillouin shift in [10.809, 10.937] GHz (bulk V_L; ZTL judge: EARNED both; Lean: theorem)

## 7. Overdamped RLC energy crossing — ZTL (+ Lean)
- extra contact resistance 0.0 Ω: t_× in [2.176, 2.884] ms; E_× in [120.8, 154.4] µJ
- extra contact resistance 2.0 Ω: t_× in [1.939, 2.478] ms; E_× in [137.7, 165.4] µJ
- with the component R only: t_× in [2.176, 2.884] ms (ZTL judge: lo OPEN, hi OPEN; Lean: theorem)
- an unmeasured contact resistance (R larger) shortens t_× and lowers E_×: the measured values, if they differ,
  should sit on the SHORT/LOW side

## 8. 15 µm eclipse, M dwarf — NUM (Planck band integrals); the star's band flux ±10–25 % systematic
### F1500W 13.5–16.5 µm
- f = 2/3 (bare rock, no redistribution): T_day in [667, 706] K; depth in [75.3, 138.0] ppm
- f = 1/4 (full redistribution): T_day in [522, 552] K; depth in [45.6, 85.1] ppm

## 9. MIRI LRS 5.06–10.55 µm, K dwarf — NUM; band flux ±5–15 %
### white light
- f = 2/3 (bare rock, no redistribution): T_day in [2323, 2480] K; depth in [81.9, 123.8] ppm
- f = 1/4 (full redistribution): T_day in [1818, 1941] K; depth in [55.1, 84.2] ppm

## 10. TESS and WFC3 eclipses, 5.4 h K dwarf — NUM; a from Kepler III; band flux ±5–15 %
- a/R* from Kepler III in [2.016, 2.140]
### TESS 600–1000 nm, A_g = 0
- f = 2/3 (bare rock, no redistribution): T_day in [2522, 2633] K; depth in [26.0, 47.1] ppm
- f = 1/4 (full redistribution): T_day in [1973, 2060] K; depth in [4.0, 7.8] ppm
  reflected light with A_g = 0.1 adds 10.5 ppm
### WFC3 G141 1.127–1.570 µm, A_g = 0
- f = 2/3 (bare rock, no redistribution): T_day in [2522, 2633] K; depth in [70.3, 116.7] ppm
- f = 1/4 (full redistribution): T_day in [1973, 2060] K; depth in [21.4, 37.3] ppm
  reflected light with A_g = 0.1 adds 10.5 ppm

