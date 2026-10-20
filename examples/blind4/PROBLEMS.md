# Blind test 4: twelve engineering design-choice problems

All data in all twelve problems is FICTIONAL (invented, internally consistent, plausible in magnitude). Each problem asks for a design choice (from catalogs and/or continuous amounts) together with a proof that every requirement holds over the stated uncertainty, OR a demonstration that no admissible design exists and which requirements conflict. "Worst case" always means: every uncertain quantity may take any value in its stated range independently, unless the text says otherwise.

---

## 1. Passive vaccine shipper: insulation panel and phase-change mass (cold-chain packaging / biomedical, fictional)

**Situation.** A passive shipping box carries 8.0 kg (8.0 L) of vaccine vials for 48 h. The outer envelope is fixed by the airline: 0.50 m x 0.40 m x 0.40 m (outside). The payload must stay between +2 degC and +8 degC. Two lanes must be served with the SAME box and the SAME phase-change material (PCM) mass: a hot lane and a cold lane.

**Choices.**
(a) One insulation option, uniform wall thickness t on all six faces (inside dimensions = 0.50-2t, 0.40-2t, 0.40-2t):

| Option | t (mm) | k_eff W/(m K) nominal | k_eff tolerance (absolute, +/-) | price EUR | density kg/m3 |
|---|---|---|---|---|---|
| EPS-30 | 30 | 0.038 | 0.003 | 4.0 | 20 |
| EPS-40 | 40 | 0.038 | 0.003 | 5.5 | 20 |
| EPS-50 | 50 | 0.038 | 0.003 | 7.0 | 20 |
| EPS-60 | 60 | 0.038 | 0.003 | 8.5 | 20 |
| EPS-80 | 80 | 0.038 | 0.003 | 16.0 | 20 |
| PU-25 | 25 | 0.025 | 0.002 | 7.0 | 40 |
| PU-35 | 35 | 0.025 | 0.002 | 9.5 | 40 |
| PU-45 | 45 | 0.025 | 0.002 | 12.0 | 40 |
| PU-55 | 55 | 0.025 | 0.002 | 14.5 | 40 |
| VIP-20 | 20 | 0.0075 | 0.0020 | 38.0 | 180 |
| VIP-30 | 30 | 0.0075 | 0.0020 | 52.0 | 180 |
| VIP-40 | 40 | 0.0075 | 0.0020 | 68.0 | 180 |

(k_eff already includes joints and edge losses at end of life.)
(b) PCM mass m (kg), any real value >= 0 (packs can be cut to any mass). PCM melts/freezes at +5.0 degC; price 6.5 EUR/kg; pack density 0.92 kg/L; sensible heat c_pcm = 3.2 kJ/(kg K) (both phases).

**Uncertain data.**
- Latent heat L of the PCM: 185 to 215 kJ/kg.
- Payload thermal capacity C_p: 30 to 34 kJ/K.
- Hot lane: ambient T_a = 36 degC constant for 48 h (a deliberately bounding profile). Packs are shipped fully conditioned solid, but only a fraction f_s of the latent capacity is actually available, f_s in [0.85, 1.00].
- Cold lane: ambient T_a = -20 degC constant for 48 h. Packs are shipped liquid, fraction f_c in [0.70, 1.00] of latent capacity available.
- k_eff of the chosen option anywhere in nominal +/- tolerance.

**Laws.**
- Conductance: UA = k_eff * A_m / t [W/K], with A_m = sqrt(A_out * A_in) and A = 2(ab + ac + bc) for a box of edges a, b, c (m^2).
- Interior volume V_in [L] = 1000 * (0.50-2t)(0.40-2t)(0.40-2t). It must contain the payload (8.0 L) plus the PCM volume m/0.92 L.
- Phase 1 (interior held at 5 degC while the PCM works): duration t1 = f * m * L / (UA * |T_a - 5|), with L in J/kg, f = f_s (hot) or f_c (cold).
- Phase 2 (if t1 < 48 h): with tau = (C_p + m * c_pcm) / UA,
  hot: T(t) = T_a - (T_a - 5) exp(-(t - t1)/tau); cold: T(t) = T_a + (5 - T_a) exp(-(t - t1)/tau).
  If t1 >= 48 h the interior stays at 5 degC throughout.
- Mass = 8.0 (payload) + 0.6 (shell) + density_ins * (0.50*0.40*0.40 - V_in/1000) + m.

**Requirements.**
R1 Hot lane: T(48 h) <= 8 degC (vial limit).
R2 Cold lane: T(48 h) >= 2 degC (freeze limit).
R3 PCM volume must fit: V_in - 8.0 >= m/0.92 (litres).
R4 Total shipping mass <= 22 kg (carrier limit).

**Decide.** Choose the insulation option and the PCM mass m so that all requirements hold for all uncertain values, at minimum cost = panel price + 6.5*m. If no choice works, say so and name the conflicting requirements.

---

## 2. Sacrificial-anode cathodic protection of a buried tank (corrosion engineering)

**Situation.** A coated steel tank is protected by a group of n identical sacrificial anodes, all connected in parallel, buried in backfill. Required life 30 years. Soil resistivity changes with the seasons and the coating degrades, so the current the steel needs varies widely. The structure potential must stay inside a window: not too weak (corrosion) and not too strong (hydrogen damage and coating disbondment).

**Choices.** One anode type from the catalog and an integer n from 1 to 60 (all anodes identical). Install cost 40 EUR per anode on top of the price.

| Type | mass kg | open-circuit potential magnitude E_a (V vs Cu/CuSO4) | capacity A h/kg | length L m | backfill diameter d m | price EUR |
|---|---|---|---|---|---|---|
| Mg-S-8 | 8 | 1.55 | 1100 | 0.60 | 0.15 | 45 |
| Mg-S-17 | 17 | 1.55 | 1100 | 1.00 | 0.20 | 78 |
| Mg-S-32 | 32 | 1.55 | 1100 | 1.40 | 0.25 | 130 |
| Mg-H-8 | 8 | 1.75 | 1150 | 0.60 | 0.15 | 52 |
| Mg-H-17 | 17 | 1.75 | 1150 | 1.00 | 0.20 | 90 |
| Zn-12 | 12 | 1.10 | 780 | 0.80 | 0.12 | 60 |
| Zn-25 | 25 | 1.10 | 780 | 1.20 | 0.16 | 110 |

**Uncertain data.**
- E_a: nominal +/- 0.05 V.
- Capacity: nominal, but the real value may be 8 % lower (no gain above nominal). Utilisation factor 0.90 (given).
- Soil resistivity rho: wet season 12 ohm m, dry season 140 ohm m, each season exactly half of the 30 years.
- Protection-current demand I_p (the current that polarises the steel to exactly 0.85 V): anywhere in 0.012 to 0.060 A over life (coating ageing, moisture). For the lifetime calculation use the mean value I_p = 0.030 A.
- Tafel slope beta: anywhere in 0.12 to 0.18 V per decade.

**Laws.**
- Resistance of one vertical anode (Dwight): R1 = rho/(2 pi L) * (ln(4L/d) - 1) [ohm].
- Group of n: R_group = (R1/n) * (1 + 0.15 ln n) (R_group = R1 for n = 1). Cable and structure resistance add R_c = 0.2 ohm in series.
- Operating point (IMPLICIT): the anode group current I [A] and the structure potential magnitude E_s [V] satisfy simultaneously
  circuit: I * (R_group + R_c) = E_a - E_s
  steel polarisation: E_s = 0.85 + beta * log10(I / I_p).
- Anode consumption: the anodes deliver whatever current the operating point gives, not just the demand. Life in hours = n * m * capacity * utilisation / I_avg, with I_avg = 0.5*I_wet + 0.5*I_dry, both currents computed at the operating point with I_p = 0.030 A (capacity in A h/kg, m in kg).

**Requirements.**
R1 At every combination of season (rho), demand I_p in [0.012, 0.060], beta in [0.12, 0.18] and E_a tolerance: 0.85 <= E_s <= 1.18 V (below 0.85 the steel corrodes, above 1.18 V hydrogen evolution damages the coating).
R2 Life >= 30 years under the worst case for life (capacity 8 % low, E_a high by 0.05, beta that gives the larger current).

**Decide.** Choose type and n at minimum total cost n * (price + 40), or show no choice works.

---

## 3. UV disinfection plant for reuse water: chambers, count and dimming (water treatment / process)

**Situation.** A reuse-water plant needs a 4-log inactivation of a virus by UV-C (254 nm). Three operating regimes occur over a year. The plant uses n identical single-lamp chambers in parallel (flow splits equally, n integer 1 to 60). Each lamp can be dimmed continuously from 40 % to 100 % of its UV power, and the dimming setting can be changed per regime.

**Choices.** One chamber model and n:

| Model | chamber radius R cm | sleeve outer radius r_q cm | arc length L cm | UV-C output at 100 % (W) | electric power at 100 % (kW) | price per chamber incl. lamp EUR | lamp replacement price EUR |
|---|---|---|---|---|---|---|---|
| U1 | 5.0 | 1.25 | 90 | 60 | 0.22 | 2100 | 60 |
| U2 | 5.0 | 1.25 | 150 | 110 | 0.40 | 2600 | 110 |
| U3 | 7.5 | 1.25 | 150 | 110 | 0.40 | 3100 | 110 |
| U4 | 7.5 | 1.50 | 150 | 180 | 0.62 | 3900 | 160 |
| U5 | 10.0 | 1.50 | 150 | 180 | 0.62 | 4300 | 160 |
| U6 | 10.0 | 1.50 | 200 | 260 | 0.88 | 5200 | 220 |
| U7 | 6.0 | 1.25 | 200 | 200 | 0.70 | 4600 | 190 |
| U8 | 12.5 | 2.00 | 200 | 330 | 1.10 | 6100 | 280 |

Electrical consumption per chamber = kW_100 * dim + 0.03 kW (ballast loss), dim in [0.4, 1.0].

**Regimes (all quantities uncertain within ranges; each regime lasts the stated fraction of the 8760 h year).**

| Regime | flow Q m3/h | UVT of water (per 1 cm path) | water temperature degC | fraction of year |
|---|---|---|---|---|
| Peak (storm) | 40 | 68 to 80 % | 8 to 14 | 0.10 |
| Average | 24 | 76 to 86 % | 12 to 24 | 0.60 |
| Low (dry summer) | 8 | 82 to 90 % | 22 to 30 | 0.30 |

Lamp output factor versus water temperature (piecewise linear between points): 8 degC 0.88; 14 degC 0.96; 20 degC 1.00; 26 degC 0.97; 30 degC 0.93.

**Laws.**
- Inactivation is first order in fluence: log-reduction = k * D / ln 10 with k = 0.23 cm^2/mJ, so 4-log needs D >= 4 ln10/0.23 = 40.04 mJ/cm^2.
- Beer-Lambert attenuation coefficient alpha = -ln(UVT/100) [1/cm].
- Intensity at the chamber wall (worst streamline): I_wall = P_uv[mW] * dim * a_age * f_foul * f_T / (2 pi R L) * exp(-alpha (R - r_q)) [mW/cm^2], with R, r_q, L in cm; a_age = 0.70 (end-of-life lamp), f_foul = 0.90 (sleeve fouling before wiping), f_T from the table above.
- Residence time t = V / (Q/n) with V = pi (R^2 - r_q^2) L [cm^3] and Q in cm^3/s.
- Delivered worst-case fluence D = 0.7 * I_wall * t [mJ/cm^2] (0.7 = reactor validation factor).

**Requirements.**
R1 D >= 40.04 mJ/cm^2 in every regime for every combination of UVT and temperature in the ranges (note the lamp factor is not monotone in temperature).
R2 Electrical connection: total electrical power at the dimming setting used in the Peak regime <= 10 kW.
R3 n <= 60.

**Objective.** Minimise 10-year cost = n * chamber price + 10 * (annual electricity at 0.14 EUR/kWh, using for each regime the lowest admissible dimming, weighted by the regime fractions of 8760 h + annual lamp replacement n * lamp price * 8760/12000). If no design meets R1 to R3 say so.

---

## 4. Workboat: propeller and reduction gear matched to a diesel engine (marine propulsion / transport)

**Situation.** A 300 kW diesel drives a fixed-pitch propeller through a reduction gear. The boat works in several conditions with different hull resistance and must also tow. The engine torque curve and the propeller torque curve meet at an operating point; the pairing must keep the engine neither overloaded nor over-speeding and meet speed and bollard-pull targets.

**Choices.** One propeller and one gear.

| Propeller | D m | K_T0 | J_0 | K_Q0 | price EUR |
|---|---|---|---|---|---|
| P1 | 1.30 | 0.28 | 0.62 | 0.030 | 5200 |
| P2 | 1.30 | 0.33 | 0.78 | 0.036 | 5400 |
| P3 | 1.30 | 0.38 | 0.92 | 0.042 | 5600 |
| P4 | 1.45 | 0.27 | 0.64 | 0.030 | 6900 |
| P5 | 1.45 | 0.32 | 0.80 | 0.036 | 7100 |
| P6 | 1.45 | 0.37 | 0.94 | 0.042 | 7400 |
| P7 | 1.60 | 0.26 | 0.66 | 0.030 | 9100 |
| P8 | 1.60 | 0.31 | 0.82 | 0.036 | 9500 |

| Gear | ratio i = engine rpm / propeller rpm | price EUR |
|---|---|---|
| G1 | 3.0 | 4800 |
| G2 | 3.5 | 5200 |
| G3 | 4.0 | 5900 |
| G4 | 4.5 | 6700 |
| G5 | 5.0 | 7500 |

**Engine full-throttle torque (piecewise linear in rpm; below 800 rpm take 1000 N m; torque is zero at and above 2150 rpm):**

| rpm | 800 | 1000 | 1400 | 1800 | 2000 | 2150 |
|---|---|---|---|---|---|---|
| torque N m | 1000 | 1250 | 1500 | 1450 | 1430 | 0 |

**Hull resistance, fully loaded, clean hull (piecewise linear in speed):**

| V knots | 0 | 4 | 6 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|
| R kN | 0 | 3.0 | 7.0 | 13.5 | 18.5 | 25.0 | 34.0 | 47.0 | 64.0 |

**Conditions.**
- Heavy: fully loaded, fouled hull: resistance = table x f_foul x 1.05, f_foul = 1.30 (worst).
- Light: light draft, clean hull: resistance = table x 0.80 x 0.95.
- Bollard: speed zero, thrust at J = 0.

**Uncertain data / tolerances.** Propeller K_T and K_Q are linear: K_T(J) = K_T0 (1 - J/J_0), K_Q(J) = K_Q0 (1 - 0.75 J/J_0) for J <= J_0, each multiplied by a tolerance factor within +/-3 %. Engine torque is the table times a factor between 0.96 (aged) and 1.00 (new).

**Laws.** rho = 1025 kg/m3; 1 kn = 0.5144 m/s. Propeller revolutions n_p = N/(60 i) [1/s], J = V (1 - w)/(n_p D), w = 0.12. Thrust T = K_T rho n_p^2 D^4; net thrust T (1 - t) must equal resistance, t = 0.10. Propeller torque Q_p = K_Q rho n_p^2 D^5; torque at the engine = Q_p/(i * 0.97). At full throttle the operating point is the engine rpm N and boat speed V for which the net thrust equals the resistance AND the torque at the engine equals the engine torque curve (two equations, two unknowns N and V). Bollard: same with J = 0 and no resistance, net thrust reported.

**Requirements.**
R1 Bollard pull (net thrust) >= 30 kN with the unfavourable tolerances (K_T x 0.97, K_Q x 1.03, engine x 0.96).
R2 Heavy condition (unfavourable tolerances as in R1): speed >= 9.0 kn.
R3 Heavy condition: engine rpm at the operating point >= 1900 (otherwise the engine is overloaded).
R4 Light condition (favourable tolerances: K_T x 1.03, K_Q x 0.97, engine x 1.00): engine rpm at the operating point <= 2060 (over-speed margin), and propeller tip speed pi n_p D <= 32 m/s at that point.

**Decide.** Choose propeller and gear, minimum price (propeller + gear), or show impossibility and which requirements conflict.

---

## 5. Soft-clay embankment: wick-drain spacing and surcharge height (geotechnical / civil)

**Situation.** A road embankment of permanent fill height 4.0 m (unit weight 19 kN/m3) crosses two zones of soft clay. To finish primary settlement before paving, prefabricated vertical drains (PVD) are installed through the full clay thickness and a temporary surcharge of additional height h_s (m) is placed at time 0 and removed at t_r = 210 days. The same surcharge height and the same drain type are used on the whole job; drain spacing may differ between the two zones.

**Site data.**

| | Zone 1 | Zone 2 |
|---|---|---|
| area m2 | 6000 | 9000 |
| clay thickness H m (drained upward only vertically; PVD length = H) | 8.0 | 5.0 |
| Cc | 0.45 | 0.38 |
| e0 | 1.4 | 1.2 |
| effective stress at mid-layer sigma0' kPa | 30 | 24 |
| c_v m2/yr (uncertain) | 1.4 to 3.0 | 1.8 to 4.5 |

For both zones: c_h/c_v anywhere in 2.0 to 3.0; permeability ratio k_h/k_s anywhere in 2 to 4; smear ratio s = d_s/d_w anywhere in 2 to 3.

**Choices.**
- Drain type (one for the job): A (equivalent diameter d_w = 0.0663 m, 0.55 EUR/m), B (0.0780 m, 0.70 EUR/m), C (0.0900 m, 0.95 EUR/m); installation 4.0 EUR per drain.
- Spacing s_z (triangular grid) in each zone, from {0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 1.7, 1.9, 2.2, 2.5} m.
- Surcharge height h_s, any real value from 0 to 2.5 m (total fill must not exceed 6.5 m for slope stability). Surcharge costs 7.5 EUR per m2 of footprint per metre of height (placing and removal).

**Laws.**
- Final settlement under a load increment: S(Delta sigma) = Cc H/(1 + e0) * log10((sigma0' + Delta sigma)/sigma0') with Delta sigma = fill height x 19 kPa.
- Vertical consolidation (single drainage path H): T_v = c_v t/H^2; U_v = 2 sqrt(T_v/pi) for T_v < 0.2, otherwise U_v = 1 - (8/pi^2) exp(-pi^2 T_v/4).
- Radial consolidation (Hansbo with smear): D_e = 1.05 s_z, n = D_e/d_w, F = ln(n/s) + (k_h/k_s) ln s - 0.75, T_r = c_h t/D_e^2, U_r = 1 - exp(-8 T_r/F), with c_h = c_v * (c_h/c_v).
- Combined: U = 1 - (1 - U_v)(1 - U_r).
- Drains per m2 = 1/(0.866 s_z^2).

**Requirement.** In each zone, at t = t_r (t in years, 210/365): settlement already achieved under the surcharge, U * S((4.0 + h_s) * 19), must be at least the permanent-load settlement S(4.0*19) minus 30 mm (the residual allowed after removal). It must hold for every combination of the uncertain parameters in the ranges. Total fill 4.0 + h_s <= 6.5 m.

**Decide.** Choose drain type, the two spacings and h_s to minimise total cost (drains + installation + surcharge) over both zones, or show no design works.

---

## 6. Solvent recycle loop with purge and membrane modules (chemical process / mass balance)

**Situation.** A two-stage washing line recycles solvent through a header and a tank. Two impurities build up: impurity 1 (removable by membrane modules) and impurity 2 (not removable by modules, only by purge). A purge stream, replaced by fresh solvent, bleeds the loop.

**Network (all flows in kg/h, all concentrations mass fractions).**
- Tank T supplies stage A with F_A = 3000 and stage B with F_B - x = 1200 (stage B receives F_B = 2000 in total).
- Stage A picks up impurity at rate g_A; its outlet has concentration c_Ao. A flow x = 800 of stage-A outlet is sent as part of the feed of stage B; the remaining F_A - x = 2200 goes straight to the return header H.
- Stage B inlet is a mix of the 800 from A and 1200 from the tank: c_Bi. Stage B picks up g_B; outlet c_Bo; all of F_B = 2000 goes to H.
- Header flow F_H = (F_A - x) + F_B = 4200; concentration c_H. A purge p*F_H leaves to waste. A flow q (set by the modules) is withdrawn from the non-purged flow, passes the modules (which remove a fraction r of its impurity 1) and returns. Fresh make-up equal to the purge enters the tank at concentration c_m. The tank (concentration c_T) feeds stage A and stage B.

Balances (impurity 1; 5 unknowns c_T, c_Ao, c_Bi, c_Bo, c_H):
c_Ao = c_T + g_A/F_A
F_B c_Bi = x c_Ao + (F_B - x) c_T
c_Bo = c_Bi + g_B/F_B
F_H c_H = (F_A - x) c_Ao + F_B c_Bo
F_H c_T = ((1 - p) F_H - r_eff q) c_H + p F_H c_m
where r_eff q means the total impurity-1 removal capacity = sum over installed modules of r_i q_i. For impurity 2 the same system with removal 0, g_B = 0 and g_A = g2, make-up concentration c_m2.

**Uncertain data (use worst case).** g_A in [6, 10] kg/h, g_B in [3, 6] kg/h; c_m in [0.0002, 0.0006]; g2 in [0.10, 0.18] kg/h; c_m2 = 0.0001. Each module at end of life: capacity x 0.85 and rejection r_i - 0.05 (use these values; modules run at full end-of-life capacity).

**Choices.**
- Number of modules of each type, 0 to 4 of each, at most 8 modules in total:

| Type | capacity q_i kg/h (new) | rejection r_i (new) | annualised cost EUR/yr per module |
|---|---|---|---|
| M1 | 500 | 0.60 | 9000 |
| M2 | 1200 | 0.45 | 13000 |
| M3 | 300 | 0.85 | 14000 |
| M4 | 800 | 0.70 | 15500 |
| M5 | 2000 | 0.30 | 16000 |

- Purge fraction p, any real in [0, 0.04].
- Total treated flow of all modules must be <= 0.6 F_H.

**Costs.** Purge and make-up: 0.25 EUR/kg for 8000 h/yr, i.e. cost = p * F_H * 8000 * 0.25 EUR/yr.

**Requirements.**
R1 c_T <= 0.8 wt% (impurity 1 at the inlet of stage A).
R2 c_Bi <= 1.1 wt% and c_Bo <= 1.5 wt% (impurity 1 at stage B).
R3 Impurity 2: its tank concentration c_T2 <= 0.4 wt%.

**Decide.** Find the module counts and the purge fraction of minimum annual cost, or show no design meets all of R1 to R3. Note what happens to the balances if both p and the removal capacity were zero.

---

## 7. NTC thermistor front end: part choice and accuracy over -20 to +60 degC (sensor electronics)

**Situation.** A battery-pack monitor reads an NTC thermistor through a resistive divider into a ratiometric ADC (ADC reference = Vcc, so the ADC code is x * 2^bits where x = divider ratio). Vcc may be anywhere in 3.0 to 3.6 V.

**Topology.** Vcc - R_p - node - (NTC in parallel with optional R_par) - ground. Node ratio x = R_x/(R_x + R_p) with R_x = R_NTC or R_NTC || R_par.

**Choices.**
(a) NTC:

| NTC | R25 | R25 tol | B (K) | B tol | dissipation const. mW/K | price EUR |
|---|---|---|---|---|---|---|
| N1 | 10 kohm | 1 % | 3435 | 0.75 % | 2.0 | 0.45 |
| N2 | 10 kohm | 1 % | 3950 | 1.0 % | 2.0 | 0.30 |
| N3 | 10 kohm | 5 % | 3380 | 2.0 % | 2.0 | 0.10 |
| N4 | 10 kohm | 0.2 % | 3977 | 0.3 % | 2.0 | 1.80 |
| N5 | 4.7 kohm | 1 % | 3480 | 1.0 % | 2.0 | 0.40 |
| N6 | 47 kohm | 3 % | 4050 | 1.0 % | 1.5 | 0.35 |
| N7 | 100 kohm | 1 % | 4250 | 1.0 % | 1.5 | 0.55 |

(b) ADC: A10 (10 bit, total unadjusted error 3 LSB, 0.20 EUR); A12 (12 bit, 4 LSB, 0.50 EUR); A16 (16 bit, 12 LSB, 2.40 EUR).
(c) Pull-up R_p: any E24 value from the three decades 1.0 to 9.1 x {1 kohm, 10 kohm, 100 kohm} (72 values; E24 mantissas 1.0 1.1 1.2 1.3 1.5 1.6 1.8 2.0 2.2 2.4 2.7 3.0 3.3 3.6 3.9 4.3 4.7 5.1 5.6 6.2 6.8 7.5 8.2 9.1).
(d) Optional parallel resistor R_par from the same E24 set (or none).
(e) Resistor tolerance class for the pull-up and the parallel resistor (same class for both): 1 % (0.01 EUR each), 0.5 % (0.03 EUR), 0.1 % (0.08 EUR).

**Laws.** NTC: R(T) = R25 exp(B (1/T - 1/298.15)), T in kelvin. The firmware inverts the nominal formula (nominal R25, B, R_p, R_par) from the measured ratio. Self-heating: dT_sh = P_NTC/delta where P_NTC = V_NTC^2/R_NTC is evaluated at Vcc = 3.6 V (continuous measurement) and delta is the dissipation constant.

**Error stack.** At each true temperature T the error is the SUM of absolute values of: (1) the error caused by R25 at its tolerance limit, (2) by B at its tolerance limit, (3) by R_p at its tolerance, (4) by R_par at its tolerance (if present), (5) the ADC error +/-(TUE + 0.5 LSB) expressed in temperature, (6) the self-heating dT_sh. Each item is the change of the inferred temperature when only that item deviates, the others being nominal.

**Requirements.**
R1 Total error <= 0.40 degC for 0 <= T <= 40 degC (control band); <= 1.00 degC for -20 <= T < 0 and 40 < T <= 60.
R2 Node ratio x between 0.03 and 0.97 at every T in -20 to +60 (so the ADC is not saturated).
R3 Bill of materials per channel (NTC + ADC + resistors) <= 2.20 EUR.

**Decide.** Find a design meeting R1 to R3, or show that none exists and which requirements conflict; if relaxing R3 makes a design possible, give the cheapest one.

---

## 8. Supercapacitor ride-through bank for a 24 V controller (energy storage / electrical)

**Situation.** A controller draws a constant 400 W (at the converter output) for 8.0 s during a supply dropout. A DC/DC converter (efficiency 0.92) draws constant power from the bank and works as long as the bank TERMINAL voltage stays >= 10 V. The bank is n_s cells in series by n_p strings in parallel (n_s from 6 to 15, n_p integer, total cells n_s*n_p <= 100) and is charged by a supply that is anywhere in 21.6 to 26.4 V.

**Cell catalog (all cells identical in the bank).**

| Cell | rated voltage V_r | C nominal F | ESR nominal mohm (25 degC, new) | price EUR |
|---|---|---|---|---|
| S1 | 2.70 | 100 | 10.0 | 4.20 |
| S2 | 2.70 | 150 | 7.0 | 5.60 |
| S3 | 2.70 | 310 | 2.2 | 10.50 |
| S4 | 3.00 | 60 | 18.0 | 3.40 |
| S5 | 3.00 | 120 | 9.0 | 6.20 |
| S6 | 2.50 | 350 | 3.0 | 9.40 |
| S7 | 2.70 | 50 | 22.0 | 2.20 |
| S8 | 2.85 | 200 | 5.5 | 7.80 |

Balancing circuit adds 0.50 EUR per cell (cost per cell = price + 0.50).

**Uncertain data / regimes.**
- Ambient from -20 to +65 degC. ESR multiplier versus temperature (piecewise linear): -30 degC 4.0; -10 degC 2.4; 0 degC 1.7; 25 degC 1.0; 45 degC 0.9; 65 degC 0.85.
- End of life (EOL, after 15 years): capacitance = 0.80 x nominal after a further -10 % tolerance (so 0.72 x nominal); ESR = 2.0 x (nominal x temperature multiplier).
- Cell voltage imbalance: worst cell voltage = (bank voltage / n_s) x 1.06; in normal float use x 1.03.
- Duty temperature profile for lifetime: 60 % of time at 25 degC, 30 % at 45 degC, 10 % at 60 degC; the bank floats at 24.0 V nominal.

**Laws.**
- Bank: C_bank = n_p C_cell/n_s; R_bank = n_s ESR_cell/n_p.
- Constant-power discharge (IMPLICIT terminal voltage): with P_in = 400/0.92 W, the terminal voltage v_t and the capacitor voltage v_c satisfy v_t * (v_c - v_t)/R_bank = P_in, i.e. v_t = (v_c + sqrt(v_c^2 - 4 R_bank P_in))/2; if the discriminant is negative the load cannot be supplied at all. Current I = P_in/v_t; dv_c/dt = -I/C_bank. Start at v_c = the supply voltage. The hold fails when v_t < 10 V before 8.0 s.
- Lifetime: L(T, V_c) = 1500 h * 2^((65 - T)/10) * 2^((V_r - V_c)/0.1 V), with V_c the float cell voltage 24.0/n_s * 1.03. Damage per hour = sum over the three temperatures of fraction / L; life = 1/damage hours.

**Requirements.**
R1 Peak cell voltage: 26.4/n_s * 1.06 <= V_r.
R2 Hold >= 8.0 s at EOL, at the minimum supply (21.6 V), at every ambient from -20 to +65 degC.
R3 Life >= 15 years (131 400 h).

**Decide.** Choose cell type, n_s, n_p at minimum cost n_s n_p (price + 0.50), or show none works.

---

## 9. Mountain-descent brakes: discs, pads and retarder for a bus (vehicle braking / transport)

**Situation.** A bus must descend mountain grades in three regimes without losing braking. Friction brakes absorb what the retarder does not; discs heat up (Newton cooling, exponential) and the pad friction fades at high disc temperature. At the end of each descent an emergency stop must still be possible.

**Choices.** Front disc size (one of D1 to D6, two discs per axle), rear disc size (one of D1 to D6), pad compound (one of PA to PE, used on all four discs), retarder (R0 to R4).

| Disc | mass kg | cooling area A m2 (ventilated) | K_front axle kN per unit mu | K_rear axle kN per unit mu | price per disc EUR |
|---|---|---|---|---|---|
| D1 | 14 | 0.42 | 70 | 52 | 260 |
| D2 | 18 | 0.50 | 78 | 58 | 320 |
| D3 | 22 | 0.62 | 90 | 68 | 400 |
| D4 | 27 | 0.75 | 100 | 76 | 520 |
| D5 | 33 | 0.88 | 112 | 86 | 690 |
| D6 | 40 | 1.05 | 125 | 96 | 900 |

(K_front is used when the disc is on the front axle, K_rear on the rear axle: it combines caliper clamp force and effective radius.)

Pad friction coefficient mu versus disc temperature (piecewise linear; constant below 20 degC and above 650 degC):

| T degC | 20 | 100 | 300 | 450 | 550 | 650 | price per disc position EUR |
|---|---|---|---|---|---|---|---|
| PA | 0.36 | 0.42 | 0.46 | 0.40 | 0.30 | 0.20 | 60 |
| PB | 0.30 | 0.38 | 0.44 | 0.44 | 0.38 | 0.28 | 95 |
| PC | 0.28 | 0.34 | 0.40 | 0.42 | 0.41 | 0.36 | 150 |
| PD | 0.22 | 0.30 | 0.38 | 0.40 | 0.39 | 0.37 | 110 |
| PE | 0.40 | 0.40 | 0.40 | 0.33 | 0.25 | 0.18 | 45 |

Retarder absorbed power (proportional to speed: P_ret = P40 * v/(40 km/h)): R0 P40 = 0 kW (0 EUR); R1 45 kW (1200 EUR); R2 70 kW (2600 EUR); R3 90 kW (4100 EUR); R4 115 kW (5600 EUR).

**Regimes.**

| Regime | mass kg | grade s (fraction) | steady speed km/h | length km | ambient degC |
|---|---|---|---|---|---|
| a loaded, slow | 16 000 | 0.07 | 40 | 7.0 | 35 |
| b loaded, fast | 16 000 | 0.07 | 55 | 4.0 | 20 |
| c empty, cold | 9 500 | 0.08 | 55 | 7.0 | 0 |

**Laws.**
- Gravity power m g s v (g = 9.81, v in m/s); rolling 0.012 m g v; air 0.5*1.2*5.0*v^3 [W]. Friction brake power P_f = max(0, m g s v - rolling - air - P_ret).
- Heat into one front disc: 0.92 * P_f * 0.65 / 2; into one rear disc: 0.92 * P_f * 0.35 / 2.
- Disc thermal model: C_th = mass * 460 J/K; h(v) piecewise linear in speed: 0 m/s 12; 5 m/s 28; 10 m/s 45; 15 m/s 62 W/(m2 K); hA = h(v) * A; tau = C_th/hA; T_ss = T_amb + P_disc/hA; T(t) = T_ss - (T_ss - T0)exp(-t/tau), T0 = T_amb + 30 K, t = length/v.
- Emergency stop at the end of the descent (deceleration 4.0 m/s2 on the same grade): required force F_req = m (4.0 + g s - 0.012 g). Available: F = 0.9 * 1000 * (mu(T_front) K_front + mu(T_rear) K_rear) [N], mu taken at the end-of-descent temperature of the front and rear disc respectively. The retarder does not help in the stop.

**Tolerances (worst case).** Convective h x 0.80; mu x 0.92; K x 0.95.

**Requirements.**
R1 End-of-descent disc temperature <= 600 degC in all three regimes (front and rear).
R2 F >= F_req in all three regimes.

**Decide.** Choose front disc, rear disc, pad, retarder at minimum total price = 2 x front disc + 2 x rear disc + 4 x pad + retarder, or show that none works and which requirement is the obstacle.

---

## 10. Micro-hydro scheme: two-section penstock and turbine (renewable energy / hydraulics)

**Situation.** A run-of-river plant has a gross head H_g = 85 m. The penstock has an upper section (240 m long, maximum static head 40 m below the intake at its lower end) and a lower section (180 m long, static head rising to 85 m at the turbine). Each section may use a different pipe. River flow varies through the year, so the turbine runs at many flows, and the flow it passes at high river flow is set by the turbine nozzle/runner size and the head left after pipe losses (a circular dependency).

**Choices.** A pipe for the upper section, a pipe for the lower section, one turbine.

| Pipe | inner diameter m | Hazen-Williams C | allowable pressure head m | price EUR/m installed |
|---|---|---|---|---|
| H200-10 | 0.176 | 140 | 100 | 18 |
| H225-10 | 0.198 | 140 | 100 | 23 |
| H250-10 | 0.220 | 140 | 100 | 29 |
| H315-10 | 0.277 | 140 | 100 | 45 |
| H355-10 | 0.312 | 140 | 100 | 57 |
| H200-16 | 0.163 | 140 | 160 | 24 |
| H225-16 | 0.184 | 140 | 160 | 30 |
| H250-16 | 0.204 | 140 | 160 | 37 |
| H315-16 | 0.257 | 140 | 160 | 58 |
| H355-16 | 0.290 | 140 | 160 | 73 |
| H400-16 | 0.327 | 140 | 160 | 92 |
| S250 | 0.250 | 120 | 300 | 70 |
| S300 | 0.300 | 120 | 300 | 95 |
| S350 | 0.350 | 120 | 300 | 128 |

| Turbine | K (m^2.5/s): full flow Q_full = K sqrt(H_net) | efficiency at flow fraction 0.2 / 0.3 / 0.4 / 0.6 / 0.8 / 1.0 | price EUR (incl. generator) |
|---|---|---|---|
| T1 Pelton-2 | 0.0225 | 0.70 / 0.78 / 0.82 / 0.85 / 0.86 / 0.85 | 58 000 |
| T2 Pelton-4 | 0.0300 | 0.66 / 0.75 / 0.80 / 0.84 / 0.86 / 0.86 | 74 000 |
| T3 Crossflow | 0.0300 | 0.55 / 0.65 / 0.72 / 0.78 / 0.80 / 0.79 | 42 000 |
| T4 Crossflow-L | 0.0420 | 0.55 / 0.65 / 0.72 / 0.78 / 0.80 / 0.79 | 56 000 |
| T5 Francis | 0.0360 | 0 (cannot run) / 0 (cannot run) / 0.62 / 0.82 / 0.89 / 0.90 | 96 000 |

Efficiency is linear between the listed fractions; below fraction 0.2 (0.4 for T5) the turbine is shut down (zero output).

**Hydrology (flow-duration, nominal).**

| fraction of the year | 0.05 | 0.15 | 0.25 | 0.25 | 0.20 | 0.10 |
|---|---|---|---|---|---|---|
| river flow available Q_r m3/s | 0.28 | 0.20 | 0.14 | 0.10 | 0.07 | 0.04 |

All river flows are uncertain by a common factor between 0.85 and 1.15.

**Laws.**
- Friction loss (Hazen-Williams, per section): h_f = 10.67 L Q^1.852/(C^1.852 D^4.87) [m], Q in m3/s, D in m.
- Net head H_net(Q) = H_g - h_f,upper(Q) - h_f,lower(Q).
- Turbine full flow at this head: Q_full is the solution of Q_full = K sqrt(H_net(Q_full)) (implicit). Flow used: Q = min(Q_r, Q_full). Flow fraction phi = Q/Q_full. If Q_r > Q_full the turbine runs at phi = 1 with Q = Q_full.
- Electric power P = eta(phi) * 0.93 * 9.81 * Q * H_net [kW] (Q in m3/s, 0.93 = drive and generator efficiency). Annual energy = sum of fraction x 8760 h x P.
- Pressure: the pipe allowable head must be >= 1.3 x the maximum static head of its section (surge allowance): 52 m for the upper section, 110.5 m for the lower section.

**Requirements.**
R1 Annual energy >= 520 MWh with the river-flow factor at 0.85.
R2 Peak electric power <= 125 kW with the factor at 1.15 (grid connection limit).
R3 Pipe velocity at full turbine flow (factor 1.15) <= 3.5 m/s in both sections.
R4 Pressure rating as above.

**Decide.** Choose the two pipes and the turbine at minimum capital cost (pipe price x length for both sections + turbine), or show that no combination works.

---

## 11. Steam sterilisation program for a hospital sterile-processing department (biomedical process, fictional)

**Situation.** One universal steam program (set-point T_set and hold time t_h) must sterilise four load types in one autoclave. The cold spot inside each pack heats exponentially; spores are killed according to an Arrhenius-like (z-value) law; plastics suffer thermal damage. Packaging may be chosen per load type from the allowed list.

**Choices.**
(a) T_set in {121, 124, 126, 130, 134} degC and hold time t_h (any real number of minutes) - one program for all loads.
(b) Packaging per load type from its allowed list:

| Packaging | tau multiplier | max chamber temperature degC | price per pack EUR |
|---|---|---|---|
| PK1 peel pouch | 1.0 | 137 | 0.10 |
| PK2 double wrap | 1.4 | 137 | 0.35 |
| PK3 rigid container | 1.8 | 135 | 1.20 |
| PK4 rigid + filter | 2.2 | 132 | 1.90 |
| PK5 polymer tray | 1.2 | 126 | 0.80 |

| Load | base tau s | required log-reduction | allowed packaging | packs per cycle | cycles per week | thermal-damage budget |
|---|---|---|---|---|---|---|
| L1 light instruments | 30 | 9 | PK1, PK2, PK5 | 12 | 20 | 120 |
| L2 surgical sets | 60 | 12 | PK2, PK3, PK4, PK5 | 6 | 15 | 120 |
| L3 textile packs | 110 | 12 | PK2, PK3, PK4 | 8 | 10 | 150 |
| L4 powered tools with lumens | 150 | 15 | PK3, PK4, PK5 | 4 | 5 | 40 |

**Uncertain data.** Chamber temperature during hold T_ch is anywhere in [T_set - 0.5, T_set + 1.5] degC. Initial pack temperature T0 anywhere in 45 to 80 degC.

**Laws.**
- Cold spot: T_cs(t) = T_ch - (T_ch - T0) exp(-t/tau), tau = base tau x packaging multiplier (seconds); t = 0 at the start of the hold (heat-up before the hold is ignored, a conservative simplification).
- Log-reduction (spores D_121 = 1.5 min, z = 10 degC): LR = (1/D_121) integral from 0 to t_h of 10^((T_cs(t) - 121.1)/10) dt, t in minutes.
- Thermal damage index (z_m = 25 degC): Dm = t_h * 10^((T_ch,max - 121)/25) with T_ch,max = T_set + 1.5, in equivalent minutes; must not exceed the load's damage budget.
- Packaging limit: T_set + 1.5 <= packaging max chamber temperature.
- Cycle time (min) = 15 (vacuum and heat-up) + t_h + drying time; drying by set-point: 121 -> 25 min; 124 -> 23; 126 -> 22; 130 -> 20; 134 -> 18.

**Requirements.**
R1 For each load, LR >= its required value in the worst case of T_ch (lowest) and T0 (lowest).
R2 Dm <= damage budget for each load.
R3 Packaging temperature limit for each load.
R4 Total autoclave time per week = sum over loads of (cycles per week x cycle time) <= 48 h.

**Cost.** 0.90 EUR per minute of cycle time + pack prices, summed over the weekly cycles of all loads.

**Decide.** Choose T_set, t_h and the packaging of each load at minimum weekly cost, or show that no program satisfies R1 to R4 and which requirements are in conflict.

---

## 12. Pension liability matching with bonds under default and call scenarios (finance / quantitative, non-engineering)

**Situation.** A small fund must pay known liabilities in the next six years and wants to buy bonds, in integer lots, whose cash flows cover them in all of three scenarios. One lot = 10 kEUR face value; 0 to 100 lots of each bond. Money in kEUR.

**Liabilities (end of year 1 to 6, kEUR).** 400, 350, 450, 300, 500, 650.

**Bond catalog (annual coupon as % of face paid at the end of years 1..maturity, face repaid at maturity; price per 100 face):**

| Bond | coupon % | maturity (yr) | price per 100 | rating | call year |
|---|---|---|---|---|---|
| B1 | 2.0 | 1 | 100.9 | AA | none |
| B2 | 3.0 | 2 | 100.4 | AA | none |
| B3 | 2.5 | 3 | 99.0 | AAA | none |
| B4 | 3.5 | 3 | 101.2 | A | none |
| B5 | 3.0 | 4 | 98.2 | AAA | none |
| B6 | 6.0 | 4 | 100.5 | BBB | none |
| B7 | 4.0 | 5 | 100.3 | A | none |
| B8 | 6.5 | 5 | 104.0 | BBB | 3 |
| B9 | 3.5 | 6 | 98.7 | AA | none |
| B10 | 5.0 | 6 | 103.0 | A | none |
| B11 | 7.0 | 6 | 108.0 | BBB | 3 |
| B12 | 0 (zero) | 2 | 95.8 | AA | none |
| B13 | 0 (zero) | 4 | 89.6 | A | none |
| B14 | 0 (zero) | 6 | 82.3 | AAA | none |

Cost of a lot = price/100 x 10 kEUR; one lot pays coupon% x 10 kEUR per year plus 10 kEUR at maturity.

**Scenarios (each must be satisfied separately).**
- Base: bonds pay as scheduled.
- Stress: all BBB bonds pay only 50 % of every cash flow (coupons and principal).
- Fall: rates fall; every bond with a call year is called at par in that year (it pays that year's coupon and its principal and nothing afterwards).

**Rules.** Surplus cash may be carried forward to later years at 0 % interest; no borrowing. Hence for every scenario and every year t, cumulative cash received through year t >= cumulative liabilities through year t.

**Further requirements.**
R1 Cash-flow coverage in all three scenarios as above.
R2 BBB bonds at most 30 % of the total purchase cost.
R3 Duration match in the Base scenario at a flat yield of 4 % per year: the Macaulay duration D = sum_t t PV_t / sum_t PV_t (PV_t = cash flow of year t / 1.04^t) of the bond portfolio must lie within +/-0.25 year of the duration of the liability stream at the same yield.
R4 Budget: total purchase cost <= 2300 kEUR.

**Decide.** Choose the integer lot numbers of minimum total cost satisfying R1 to R4, or show that no portfolio does and which requirements conflict; if the budget R4 is dropped, give the minimum cost.
