# Blind test 5: twelve engineering and operations design-choice problems

All data in all twelve problems is FICTIONAL (invented, internally consistent, plausible in magnitude). Each problem asks for a design choice (from catalogs and/or continuous amounts) together with a proof that every requirement holds over the stated uncertainty, OR a demonstration that no admissible design exists and which requirements conflict. "Worst case" always means: every uncertain quantity may take any value in its stated range independently, unless the text says otherwise (a quantity described as "shared", "common" or "the same" is ONE value used everywhere it appears).

---

## 1. Crusher countershaft: roller bearing, oil grade and contamination kit (mechanical drive)

**Situation.** A cylindrical roller bearing on a 60 mm shaft carries a crusher countershaft through four duty cycles. Required service life: 8 years at 7000 operating hours per year = 56 000 h. The housing bore limits the bearing outside diameter to 150 mm. The bearing is oil-lubricated; a filter-and-seal kit may be fitted or left out.

**Choices.** (a) one bearing; (b) one oil grade; (c) kit or no kit.

| Bearing | C kN | C0 kN | OD mm | price kEUR |
|---|---|---|---|---|
| R-60A | 95 | 100 | 110 | 0.38 |
| R-60B | 118 | 128 | 110 | 0.52 |
| R-60C | 135 | 150 | 130 | 0.61 |
| R-60D | 160 | 180 | 130 | 0.80 |
| R-60E | 190 | 215 | 150 | 1.05 |
| R-60F | 235 | 270 | 150 | 1.45 |
| R-60G | 290 | 345 | 180 | 2.10 |

| Oil | viscosity at 40 degC nu40 mm2/s | price kEUR (sump and first fill) |
|---|---|---|
| VG68 | 68 | 0.20 |
| VG150 | 150 | 0.25 |
| VG320 | 320 | 0.35 |
| VG680 | 680 | 0.50 |

| Kit | contamination factor f_c | price kEUR |
|---|---|---|
| none | 0.60 | 0.00 |
| filter-and-seal kit | 1.00 | 0.90 |

**Duty cycles** (fractions of operating time; radial load Fr and bearing temperature T anywhere in the ranges, independently per cycle):

| Cycle | fraction f_i | speed n rpm | Fr kN | T degC |
|---|---|---|---|---|
| Idle | 0.25 | 1450 | 4 to 5 | 58 to 66 |
| Normal | 0.45 | 1450 | 11 to 13 | 66 to 74 |
| Heavy | 0.25 | 900 | 20 to 23.1 | 70 to 80 |
| Shock start | 0.05 | 300 | 36 to 40 | 60 to 70 |

In every cycle the axial load is tied to the radial one: Fa = 0.30 Fr (the same Fr value is used in both).

**Laws.**
- Equivalent load P_i = Fr + 0.45 Fa (kN). Basic rating life in million revolutions: L10 = (C / P_i)^(10/3).
- Oil viscosity at temperature: nu(T) = nu40 exp(-0.040 (T - 40)) [mm2/s].
- Reference viscosity: nu1 = 45000 n^(-0.83) dm^(-0.5) for n < 1000 rpm, nu1 = 4500 n^(-0.5) dm^(-0.5) for n >= 1000 rpm, with mean diameter dm = (60 + OD)/2 [mm].
- Viscosity ratio kappa = nu(T)/nu1. Lubrication life factor a_L(kappa), piecewise linear between the points, constant beyond the end points:

| kappa | 0.4 | 0.7 | 1.0 | 2.0 | 4.0 |
|---|---|---|---|---|---|
| a_L | 0.40 | 0.75 | 1.00 | 1.70 | 2.30 |

- Modified life of cycle i in million revolutions: L_i = a_L(kappa_i) * f_c * (C / P_i)^(10/3).
- Damage per operating hour: d = sum over cycles of f_i * 60 n_i / (10^6 * L_i). Service life in hours = 1/d (Miner's rule: damage accumulates linearly over the cycles).
- Static check at the shock cycle: P0 = Fr + 0.6 Fa at its largest Fr.

**Requirements.**
R1 Service life 1/d >= 56 000 h for all admissible loads and temperatures.
R2 Static safety C0 / P0 >= 2.5 at the shock cycle (worst Fr).
R3 OD <= 150 mm.

**Decide.** Choose bearing, oil and kit at minimum price (bearing + oil + kit), or show none works.

---

## 2. Distribution transformer with optional capacitor bank (electrical, 30-year loss evaluation)

**Situation.** A factory substation needs a 10/0.4 kV transformer for 30 years. Load grows 1.2 % per year. A fixed (always connected) capacitor bank may be added or left out. Lifetime cost includes the cost of losses.

**Choices.** (a) one rating and one loss class from the catalog (18 combinations); (b) capacitor bank: none, C100, C150 or C200.

| Rating Sn kVA | 400 | 630 | 800 | 1000 | 1250 | 1600 |
|---|---|---|---|---|---|---|
| impedance uk % | 4.0 | 4.0 | 6.0 | 6.0 | 6.0 | 6.0 |

| Class | quantity | 400 | 630 | 800 | 1000 | 1250 | 1600 |
|---|---|---|---|---|---|---|---|
| S standard | no-load loss P0 W | 650 | 860 | 1000 | 1150 | 1350 | 1650 |
| S | load loss Pk W (at Sn) | 4600 | 6500 | 7600 | 9500 | 11000 | 14000 |
| S | price kEUR | 5.8 | 7.4 | 8.8 | 10.2 | 12.4 | 15.5 |
| S | mass kg | 1150 | 1650 | 2000 | 2350 | 2900 | 3600 |
| L low-loss | P0 W | 430 | 600 | 700 | 770 | 950 | 1150 |
| L | Pk W | 4600 | 6000 | 7000 | 9000 | 10500 | 13500 |
| L | price kEUR | 6.9 | 8.8 | 10.5 | 12.0 | 14.6 | 18.0 |
| L | mass kg | 1240 | 1780 | 2160 | 2540 | 3130 | 3890 |
| A amorphous | P0 W | 190 | 260 | 300 | 340 | 400 | 480 |
| A | Pk W | 4800 | 6700 | 7900 | 9800 | 11500 | 14500 |
| A | price kEUR | 8.4 | 10.8 | 12.8 | 14.6 | 17.5 | 22.0 |
| A | mass kg | 1380 | 1980 | 2400 | 2820 | 3480 | 4320 |

| Capacitor bank | none | C100 | C150 | C200 |
|---|---|---|---|---|
| Qc kvar | 0 | 100 | 150 | 200 |
| price kEUR | 0 | 1.2 | 1.7 | 2.2 |

The bank dissipates 2.5 W per kvar of Qc continuously.

**Uncertain data (year 1; each season, each range independent).** Active load P and uncorrected power factor pf:

| Season | hours per year | P kW | pf |
|---|---|---|---|
| winter | 2184 | 520 to 600 | 0.80 to 0.86 |
| spring | 2208 | 400 to 470 | 0.82 to 0.88 |
| summer | 2208 | 330 to 400 | 0.82 to 0.88 |
| autumn | 2160 | 430 to 500 | 0.80 to 0.86 |

Summer night light load (used only for the voltage-rise check, year 1): P = 60 to 80 kW, pf 0.80 to 0.86. Energy tariff for losses: 0.09 to 0.14 EUR/kWh (constant over the 30 years; rank designs by their worst-case lifetime cost).

**Laws.**
- Reactive load Q = P tan(acos(pf)). Apparent load seen by the transformer S = sqrt(P^2 + (Q - Qc)^2) (the absolute value of the net reactive power matters: an over-sized bank over-compensates).
- Year y (y = 1 to 30): P_y = P_1 * 1.012^(y-1), pf unchanged.
- Losses in a season (W): P0 + Pk (S/Sn)^2 + 2.5 Qc. Seasonal loss energy = hours * W / 1000 [kWh]. Annual loss energy E_y = sum over the four seasons.
- Present value of the losses: PV = sum over y = 1..30 of E_y * tariff / 1000 / 1.03^y [kEUR] (discount rate 3 %).
- Lifetime cost [kEUR] = transformer price + bank price + PV.
- Voltage regulation in per-unit: r = Pk/(1000 Sn), x = sqrt((uk/100)^2 - r^2), p = P/Sn, q = (Q - Qc)/Sn (signed), delta_U [%] = 100 (p r + q x). Negative values mean a voltage rise.

**Requirements.**
R1 Year-1 annual loss energy (summed over the four seasons, loads at their worst case) <= 32 000 kWh.
R2 Year-30 peak apparent load S <= 1.05 Sn in every season.
R3 Year-30 voltage drop delta_U <= 3.8 % in every season.
R4 Summer-night voltage rise: delta_U >= -0.8 % (year 1).
R5 Transformer mass <= 3000 kg (floor loading).

**Decide.** Choose rating, class and bank at minimum worst-case lifetime cost, or show none is admissible.

---

## 3. Solar thermal hot water for an apartment block (thermal, annual auxiliary energy)

**Situation.** An apartment block draws hot water at 45 degC. A solar loop with n identical collector modules feeds a storage tank; the back-up boiler tops the water up to 45 degC when the tank is colder. Four seasons; the tank temperature in each season is the operating point where the collector's useful heat equals what the tank gives to the load plus its losses (collector efficiency falls as the tank gets hotter, so the temperature is an implicit solution).

**Choices.** (a) collector model; (b) n = 1 to 16 modules; (c) tank volume V from {300, 500, 750, 1000, 1500} L; (d) tank insulation upgrade or none.

| Collector | module area m2 | eta0 | a1 W/(m2 K) | a2 W/(m2 K2) | price per module kEUR |
|---|---|---|---|---|---|
| F1 flat | 2.0 | 0.76 | 4.2 | 0.016 | 0.42 |
| F2 flat selective | 2.3 | 0.80 | 3.4 | 0.014 | 0.55 |
| F3 flat high-performance | 2.5 | 0.81 | 3.0 | 0.012 | 0.68 |
| T1 evacuated tube | 2.2 | 0.74 | 1.4 | 0.005 | 0.85 |
| T2 evacuated tube large | 3.0 | 0.76 | 1.3 | 0.004 | 1.15 |
| T3 heat-pipe tube | 2.6 | 0.78 | 1.2 | 0.0035 | 1.05 |

Tank price = 0.90 (V/300)^0.8 kEUR. Tank loss conductance UA = 1.8 (V/300)^0.6 W/K, multiplied by 0.6 if the insulation upgrade is fitted (upgrade price 0.25 kEUR).

**Uncertain data.** Per season (independent ranges):

| Season | days | daily irradiation on the collector plane H kWh/m2/day | sun hours h | day ambient T_a degC | cold-water inlet T_c degC |
|---|---|---|---|---|---|
| winter | 90 | 1.4 to 2.0 | 6 | 3 to 7 | 6 to 9 |
| spring | 92 | 3.6 to 4.6 | 8 | 10 to 14 | 9 to 12 |
| summer | 92 | 5.6 to 6.8 | 10 | 20 to 26 | 15 to 18 |
| autumn | 91 | 2.6 to 3.4 | 7 | 11 to 15 | 11 to 14 |

Daily hot-water draw D = 540 to 660 L/day: ONE value shared by all four seasons. The tank room temperature in a season is T_r = T_a + 8 (the same T_a used for the collector).

**Laws.** A = n * module area [m2]. Irradiance during sun hours G = 1000 H/h [W/m2]. For a tank temperature T [degC]:
- mean collector temperature difference dT = T + 6 - T_a;
- efficiency eta(T) = max(0, eta0 - a1 dT/G - a2 dT^2/G);
- daily heat balance (kWh/day): A * H * eta(T) = c_w D (T - T_c) + UA * 0.024 * (T - T_r), with c_w = 1.1628e-3 kWh/(L K). The left side falls and the right side rises with T, so the solution T is unique; no boiling is modelled, the value is used as computed.
- back-up boiler energy per day = c_w D max(0, 45 - T) (kWh). Annual back-up energy = sum over seasons of days * daily back-up energy.

**Requirements.**
R1 Annual back-up energy <= 3700 kWh/year at the worst case.
R2 Tank temperature T <= 80 degC in every season at the worst case (scale and scald limit).
R3 Storage ratio 50 <= V/A <= 100 L/m2.

**Decide.** Choose collector, n, V and insulation at minimum price (modules + tank + upgrade), or show none works.

---

## 4. Gravity sewer in two reaches: diameter, slope and pipe material (civil / fluid)

**Situation.** A 800 m gravity sewer is laid in two reaches, A upstream (420 m) then B (380 m). Pipe material is the same in both reaches. The head of reach A is 1.5 m below ground (invert depth). Each reach is laid at a constant slope; the invert depth at its downstream end is the upstream depth plus slope times length, and reach B starts at the depth where reach A ends. The outfall at the end of B cannot be deeper than 5.0 m.

**Choices.** Material (PVC, CONC, PE); for each reach an internal diameter from {200, 250, 300, 400, 500} mm and a slope from {0, 0.002, 0.0035, 0.005, 0.008, 0.012, 0.02} m/m.

| Material | Manning n range (absolute) | pipe price coefficient k EUR/m | max permitted velocity at storm peak m/s |
|---|---|---|---|
| PVC | 0.0095 to 0.0115 | 62 | 3.0 |
| CONC | 0.012 to 0.016 | 48 | 1.5 |
| PE | 0.013 to 0.017 | 55 | 2.5 |

| Reach | length m | dry-weather daily peak flow Q_d L/s | storm peak Q_pk L/s |
|---|---|---|---|
| A | 420 | 6.5 | 22 |
| B | 380 | 12 | 41 |

(Manning n is uncertain: each reach must satisfy its requirements for every n in the material's range.)

**Laws.**
- Manning (SI): Q = (1/n) A_f R^(2/3) S^(1/2) with flow area A_f and hydraulic radius R of the partly full circular pipe. With central angle theta [rad] of the wetted segment: A_f = D^2 (theta - sin theta)/8, R = (D/4)(1 - sin theta/theta), depth ratio y/D = (1 - cos(theta/2))/2. The operating depth is the root theta of Manning for the given Q, n, S, D (implicit). If Q exceeds the flow at y/D = 0.938 the pipe is surcharged and the condition fails. Velocity v = Q/A_f.
- A slope of 0 carries no flow at all (Manning gives Q = 0 for any depth): the pipe cannot convey the flow and is inadmissible.
- Price per metre: pipe k (D/200)^1.3 where D in mm; trench (20 + 28 d_avg)(1 + D/1000) where d_avg = mean of upstream and downstream invert depth of the reach in m. Reach cost = length * (pipe + trench) in EUR.

**Requirements.**
R1 At the dry-weather peak Q_d: velocity >= 0.60 m/s in each reach for every n in its range (self-cleansing).
R2 At the storm peak: depth ratio y/D <= 0.70 in each reach for every n.
R3 At the storm peak: velocity <= the material's permitted maximum for every n.
R4 Invert depth at the downstream end of B <= 5.0 m.
R5 D_B >= D_A (the pipe never narrows downstream).

**Decide.** Choose material, (D_A, S_A), (D_B, S_B) at minimum total cost (kEUR), or show none works.

---

## 5. Cooling tower: make-up source, treatment programme and blowdown setting (chemical / water)

**Situation.** A cooling tower (circulation 1150 m3/h) operates 7400 h/year in three seasons. Make-up water M replaces evaporation E, blowdown B and drift D: M = E + B + D. The blowdown valve is set to a fixed flow in each season (three settings, continuous, m3/h). Dissolved species stay in the basin, so with cycles of concentration N = M/(B + D) (if B + D were 0, N would be unbounded and every limit violated) the basin concentration is N times the make-up concentration. A scale-inhibitor programme and acid dosing (a fraction of make-up alkalinity neutralised) may be selected or left out.

**Choices.** (a) one make-up source; (b) one inhibitor programme (including none); (c) acid dosing level 0 %, 40 % or 70 % of make-up alkalinity neutralised (r = 0, 0.4, 0.7); (d) the three seasonal blowdown flows B_s >= 0.

| Source | Ca hardness (as CaCO3) mg/L | alkalinity (as CaCO3) mg/L | chloride mg/L | SiO2 mg/L | sulphate mg/L | TDS mg/L | price EUR/m3 |
|---|---|---|---|---|---|---|---|
| Town | 60 to 80 | 70 to 90 | 20 to 30 | 8 to 12 | 25 to 35 | 220 to 280 | 1.90 |
| Well | 180 to 230 | 200 to 240 | 60 to 90 | 22 to 30 | 80 to 110 | 650 to 780 | 0.65 |
| SoftWell (softened well) | 10 to 25 | 200 to 240 | 60 to 90 | 22 to 30 | 80 to 110 | 700 to 820 | 1.45 |

| Programme | max allowed LSI | cost EUR per m3 of make-up |
|---|---|---|
| none | 0.5 | 0 |
| P1 | 1.3 | 0.12 |
| P2 | 1.9 | 0.22 |
| P3 | 2.5 | 0.38 |

| Season | hours | heat load Q MW | basin temperature T degC |
|---|---|---|---|
| winter | 2000 | 0.9 to 1.2 | 28 to 32 |
| midseason | 3200 | 1.5 to 2.0 | 30 to 34 |
| summer | 2200 | 2.2 to 2.8 | 34 to 38 |

**Laws.**
- Evaporation E = 1.4815 Q m3/h (Q in MW). Drift D = 0.023 m3/h. Cycles N = (E + B + D)/(B + D).
- Basin concentrations: SiO2 = N * SiO2_m; chloride = N * Cl_m; sulphate = N (SO4_m + 0.96 r Alk_m) (acid adds sulphate); alkalinity Alk_cw = N Alk_m (1 - r); TDS_lsi = N (TDS_m - 0.26 r Alk_m).
- pH of the basin (empirical) pH = 5.9 + 0.95 log10(Alk_cw). Langelier index LSI = pH - pHs with pHs = 9.3 + A + B' - (C + D'), A = (log10(TDS_lsi) - 1)/10, B' = -13.12 log10(T + 273) + 34.55, C = log10(Ca_cw) - 0.4 with Ca_cw = N Ca_m, D' = log10(Alk_cw) (T in degC, all concentrations in mg/L). All logarithms base 10.
- Annual cost = sum over seasons of hours * [ M price + B * 0.90 (discharge) + M * (programme cost) + M * r * Alk_m/1000 * 0.98 * 0.12 (acid: kg H2SO4 per m3 is r Alk_m/1000 * 0.98, at 0.12 EUR/kg) ] with M, B in m3/h (kEUR after dividing by 1000). Evaluate the cost at the worst case: Q at the top of its range, Alk_m at the top of its range.

**Requirements.** (for every admissible Q, make-up composition and basin temperature in every season)
R1 SiO2 in the basin <= 150 mg/L.
R2 Chloride <= 400 mg/L.
R3 Sulphate <= 1000 mg/L.
R4 LSI <= the programme's maximum.
R5 Annual make-up volume (sum over the three seasons, hours * M, at the worst case) <= 26 000 m3.

**Decide.** Choose source, programme, acid level and the three blowdown flows at minimum annual cost (worst case), or show none works.

---

## 6. Strip footing on a wet sand (civil / geotechnical)

**Situation.** A continuous footing carries a wall line load on sand with a shallow water table. The plot boundary and the adjacent building limit the footing width. Footing thickness 0.45 m; backfill above the footing.

**Choices.** Footing width B from {0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.4} m and founding depth Df from {0.5, 0.8, 1.0, 1.2, 1.5} m (40 combinations).

**Uncertain data.**
- Friction angle phi 25 to 29 degrees; cohesion c 0 to 4 kPa; unit weight gamma 17.5 to 19.5 kN/m3.
- Wall line load N 100 to 115 kN/m; bending moment per metre |M| 8 to 18 kNm/m (sign unknown, only the absolute value is given).
- Water table depth z_w below ground 0.8 to 2.2 m.
- Soil Young's modulus E 10 to 16 MPa.

**Laws.**
- Footing plus backfill weight W = 24 * 0.45 * B + gamma * B * max(Df - 0.45, 0) [kN/m]; total vertical load N_t = N + W; eccentricity e = |M|/N_t; effective width B' = B - 2e; contact pressure q = N_t/B'.
- Bearing factors: Nq = exp(pi tan phi) tan^2(45 deg + phi/2); Nc = (Nq - 1)/tan phi; Ngamma = (Nq - 1) tan(1.4 phi).
- Overburden at founding level: q0 = gamma Df if z_w >= Df; q0 = gamma z_w + (gamma - 9.81)(Df - z_w) if z_w < Df.
- Unit weight below the base: gamma_b = gamma - 9.81 if z_w <= Df; gamma_b = (gamma - 9.81) + 9.81 (z_w - Df)/B' if Df < z_w < Df + B'; gamma_b = gamma if z_w >= Df + B'.
- Ultimate bearing pressure q_u = c Nc + q0 Nq + 0.5 gamma_b B' Ngamma [kPa]. Factor of safety FS = q_u/q.
- Settlement s = q B' (1 - 0.3^2) * 1.12 / (E) with E in kPa; result in m (report in mm).

**Requirements.**
R1 FS >= 3.0 for every admissible value.
R2 Settlement s <= 25 mm.
R3 Eccentricity e <= B/6.
R4 Footing width B <= 2.0 m (plot boundary).

**Decide.** Choose B and Df at minimum cost per metre = 72 B + 28 (B + 0.6) Df + 32 EUR/m, or show none works.

---

## 7. Shielding of a radiography room wall (biomedical / medical physics)

**Situation.** The wall behind the X-ray unit faces a waiting area. The weekly workload is made of four examination types. The wall may be built up by lead sheet, barite plaster and a concrete lining, any of which may be left out (thickness 0). The existing slab and door frames limit the added mass and the added thickness.

**Choices.** Lead sheet thickness from {0 (none), 0.5, 1.0, 1.5, 2.0, 2.5, 3.0} mm; barite plaster from {0, 10, 20, 30} mm; concrete lining from {0, 50, 100, 150} mm (112 combinations; layers act in series).

**Uncertain data.** Per examination type j: weekly number N_j; air kerma at 1 m from the source per examination K_j (primary beam); nominal half-value layers (HVL) in the three materials. Every HVL may deviate from its nominal value by up to 10 % either way (independent per material and examination type).

| Examination | N_j per week | K_j mGy per exam at 1 m | HVL lead mm | HVL barite plaster mm | HVL concrete mm |
|---|---|---|---|---|---|
| Extremity 60 kVp | 140 to 180 | 1.1 to 1.3 | 0.10 | 2.0 | 10.0 |
| Chest 125 kVp | 90 to 120 | 0.8 to 1.0 | 0.28 | 6.0 | 21.0 |
| Spine 85 kVp | 40 to 60 | 5.0 to 6.0 | 0.16 | 3.4 | 14.0 |
| Pelvis 100 kVp | 20 to 30 | 7.5 to 9.0 | 0.21 | 4.4 | 17.0 |

**Laws.**
- Transmission for examination j with thicknesses x_Pb, x_Ba, x_C in mm: B_j = 2^( -( x_Pb/HVL_Pb,j + x_Ba/HVL_Ba,j + x_C/HVL_C,j ) ).
- Weekly dose behind the wall (mSv/week), summed over the four examination types: H = 1.14 * U * T / d^2 * sum_j N_j K_j B_j, with beam-use factor U = 0.25, occupancy T = 1.0, distance d = 2.2 m.
- Added mass per m2: 11.34 kg per mm of lead, 2.7 kg per mm of barite plaster, 2.35 kg per mm of concrete lining. Added thickness = sum of the layer thicknesses.
- Price per m2: lead 40 EUR/mm, barite plaster 1.8 EUR/mm, concrete lining 0.55 EUR/mm; wall area 14 m2.

**Requirements.**
R1 Weekly dose H <= 0.005 mSv/week for every admissible value (design constraint of the operator, 0.25 mSv/year).
R2 Added mass <= 55 kg/m2.
R3 Added thickness <= 60 mm.

**Decide.** Choose the three layer thicknesses at minimum price, or show none works and which requirements conflict.

---

## 8. Electric delivery van: battery, tyres, aero kit, heater and optional roof solar (transport)

**Situation.** A delivery van runs three route types daily with the mix below. After 8 years the battery must still cover every route on a cold day. The legal gross mass limit is 3500 kg.

**Choices.** One battery pack, one tyre class, one aero option, one cabin heater, and a roof solar panel or none.

| Pack | usable nominal energy kWh | mass kg | price kEUR |
|---|---|---|---|
| B40 | 40 | 285 | 6.4 |
| B52 | 52 | 365 | 8.1 |
| B64 | 64 | 440 | 9.8 |
| B77 | 77 | 530 | 11.9 |
| B90 | 90 | 610 | 13.8 |
| B110 | 110 | 745 | 17.0 |

| Tyre | Crr | extra price kEUR |
|---|---|---|
| std | 0.0105 | 0 |
| low | 0.0082 | 0.35 |
| ultra | 0.0072 | 0.70 |

| Aero | CdA factor | extra price kEUR |
|---|---|---|
| none | 1.00 | 0 |
| deflector | 0.92 | 0.5 |
| full kit | 0.86 | 1.4 |

| Heater | cabin heating power on cold days kW | extra price kEUR |
|---|---|---|
| resistive | 2.6 | 0 |
| heat pump | 1.1 | 0.85 |

Roof solar: none, or panel of 0.9 kWp, 18 kg, 1.1 kEUR.

**Routes.**

| Route | daily distance km | average speed km/h | cruise speed km/h | stops per km | share of days |
|---|---|---|---|---|---|
| urban | 140 | 26 | 45 | 2.4 | 0.50 |
| suburban | 170 | 52 | 70 | 0.6 | 0.35 |
| motorway | 158 | 95 | 110 | 0.05 | 0.15 |

**Uncertain data.** Baseline CdA0 1.05 to 1.15 m2 (common to all routes); payload 500 to 850 kg (the same payload on all routes); rolling-resistance multiplier on the catalog Crr 0.90 to 1.10; cold-day usable-capacity factor f_T 0.82 to 0.92.

**Laws.**
- Vehicle mass m = 2050 (curb, with driver) + pack mass + payload + solar mass [kg]. Air density 1.20 kg/m3, g = 9.81 m/s2.
- For a route with cruise speed v (m/s): F = Crr * multiplier * m g + 0.5 * 1.20 * CdA0 * (aero factor) * v^2 [N]. Kinetic loss per km: stops_per_km * 0.5 m v^2 * (1 - 0.55) [J] (regeneration recovers 55 %). Traction energy [Wh/km] = (1000 F + kinetic loss per km) / (0.88 * 3600).
- Auxiliary energy [Wh/km] = (0.4 kW + cabin heating kW) * 1000 / average speed; cabin heating is 0 on warm days.
- Battery capacity retention after 8 years = exp(-0.028 * 8) (about 0.80). Cold-day usable energy = pack energy * retention * f_T * 0.92 (reserve) + solar credit (0.35 kWh per kWp on a cold day).
- Route range on a cold day = usable energy / (traction + auxiliary energy per km, cold).
- Average consumption [kWh/100 km] = sum over routes of share * (0.5 * cold-day Wh/km + 0.5 * warm-day Wh/km)/10 (half of the days cold). The solar credit is not counted here.

**Requirements.**
R1 Cold-day range >= daily distance on each of the three routes, at the worst case.
R2 Average consumption (worst case) <= 24.8 kWh/100 km.
R3 Gross mass at the highest payload: 2050 + pack + solar + 850 <= 3500 kg.

**Decide.** Choose the five options at minimum total price (pack + tyre + aero + heater + solar), or show none works.

---

## 9. Warehouse space for a seasonal inventory: own block, 3PL tier and spot pool (logistics)

**Situation.** A distributor needs pallet positions in four quarters. Positions needed in a quarter = average inventory I_q / space utilisation u. Space comes from: (i) an own long-lease block of B positions all year (continuous, 0 to 3200 positions, 118 EUR per position per year); (ii) one 3PL contract tier (or none), billed per position-month; (iii) a spot pool at short notice. In each quarter the shortfall (needed minus B) is covered first by the 3PL up to its cap, then by spot.

**Choices.** B (continuous) and a 3PL tier:

| Tier | price EUR per position-month | minimum commitment (positions billed every month even if unused) | cap positions |
|---|---|---|---|
| T0 (none) | n/a | 0 | 0 |
| T1 | 11.8 | 0 | 800 |
| T2 | 9.6 | 400 | 1500 |
| T3 | 8.4 | 900 | 2200 |

Spot pool: price 18 to 24 EUR per position-month; availability (cap) per quarter 800, 800, 800 and 300 positions in Q1 to Q4.

**Uncertain data.**

| Quarter | average inventory I_q (pallets) |
|---|---|
| Q1 | 2000 to 2370 |
| Q2 | 1750 to 2110 |
| Q3 | 2300 to 2730 |
| Q4 | 3150 to 3780 |

Utilisation u is ONE value for the whole year, 0.88 to 0.94. Each quarter has 3 months. In a quarter with F positions taken from the tier, the 3PL bills max(F, commitment) * price * 3.

**Requirements.**
R1 In every quarter, for every admissible inventory and u: B + F_q + S_q >= positions needed, with F_q <= tier cap and S_q <= spot availability of that quarter.
R2 Worst-case annual cost (own block + 3PL billing + spot at 24 EUR) <= 355 kEUR. (Cost is increasing in demand and in spot price, so the worst case is at the top of both.)
R3 B <= 3200 positions (building).

**Decide.** Choose B and the tier at minimum worst-case annual cost, or show that no choice meets R1 to R3 and name the conflicting requirements.

---

## 10. Aquaculture pond: aerators, seasonal running schedule and emergency oxygen (agriculture)

**Situation.** A 24 000 m3 fish pond is aerated at night. DO must stay above a minimum all night and survive a two-hour power cut. The operator chooses one aerator type, how many to install, how many to run in each season, and whether to install an emergency liquid-oxygen (LOX) injector (or none).

**Choices.** (a) aerator type; (b) number installed n = 1 to 16; (c) number running per season m_s (integer, 0 to n); (d) LOX unit: yes (6.5 kEUR) or none.

| Aerator | electric power kW | SAE kg O2/kWh (standard conditions) | price installed kEUR |
|---|---|---|---|
| PW2 paddlewheel | 2.0 | 2.2 | 3.6 |
| PW37 paddlewheel | 3.7 | 2.0 | 5.2 |
| PROP propeller-aspirator | 1.5 | 1.7 | 2.3 |
| DIFF diffuser set | 5.5 | 1.4 | 6.8 |

LOX unit: injects 6.0 kg O2/h (assume fully dissolved) for up to 2 h.

**Uncertain data** (per season, independent ranges; the water temperature T is ONE value per season used in all formulas):

| Season | days | night hours of operation | fish biomass W kg | T degC |
|---|---|---|---|---|
| winter | 90 | 12 | 4000 to 5000 | 8 to 11 |
| spring | 92 | 10 | 9000 to 11000 | 16 to 19 |
| summer | 92 | 8 | 16000 to 19000 | 26 to 30 |
| autumn | 91 | 11 | 14000 to 16500 | 14 to 18 |

**Laws.**
- Saturation DO Cs(T) in mg/L, linear interpolation: 5 degC 12.8; 10 degC 11.3; 15 degC 10.1; 20 degC 9.1; 25 degC 8.3; 30 degC 7.6; 35 degC 7.0.
- Oxygen demand per volume (g/m3/h): r = 0.30 W 1.08^(T-20)/24000 + 0.15 * 1.065^(T-20) (fish plus pond respiration).
- Natural surface re-aeration rate k_d = 0.015 * 1.024^(T-20) per hour; driven by (Cs - C).
- Aerator oxygen transfer with m units running (g O2/h): m * P * SAE * 1000 * 0.90 * 1.024^(T-20) * (0.95 Cs - C)/9.09, where C is the pond DO (mg/L).
- Night steady state C_ss (balance per m3): r = k_d (Cs - C) + [aerator transfer]/24000. Solve for C (a linear equation). If the computed C_ss is not positive there is no oxygen balance at all (anoxia, fish kill): the season fails.
- Power cut at the end of the night: starting at C_ss, no aerators run; dC/dt = -r + k_d (Cs - C) + ox, ox = 6000/24000 = 0.25 g/m3/h if the LOX unit is installed, else 0. Closed form C(t) = C_inf + (C_ss - C_inf) exp(-k_d t) with C_inf = Cs - (r - ox)/k_d; DO is floored at 0. Evaluate at t = 2 h.
- Annual aerator energy = sum over seasons of days * night hours * m_s * P [kWh].

**Requirements.**
R1 C_ss >= 4.0 mg/L in every season at the worst case (the worst T need not be at the end of the range: the aerator efficiency also depends on T).
R2 DO after the 2-hour power cut >= 3.0 mg/L in every season at the worst case.
R3 Annual aerator energy (summed over seasons) <= 31 000 kWh.
R4 Connected load n * P <= 40 kW.

**Decide.** Choose type, n, the four running counts and the LOX decision at minimum 10-year cost = installed prices (n units + LOX if chosen) + 10 * annual energy * 0.16 EUR/kWh / 1000 (kEUR), or show none works.

---

## 11. Currency hedge for a US-dollar exporter: forwards and put options (finance)

**Situation.** A firm earns USD each quarter and pays EUR costs. Over four quarters it can sell USD forward and buy USD puts (the right to sell USD at a strike). Spot rates are quoted as USD per EUR, S.

**Choices.** A strike K from {1.06, 1.10, 1.14} USD/EUR, or no options at all (in which case all o_q = 0). Per quarter q = 1..4: forward hedge fraction h_q and option fraction o_q, continuous in [0, 1] of the nominal USD revenue.

| Strike K | premium pi_K EUR per USD of option notional |
|---|---|
| 1.06 | 0.0210 |
| 1.10 | 0.0120 |
| 1.14 | 0.0058 |

Nominal USD revenue per quarter U = 4.0 million USD. EUR costs per quarter 3.00 million EUR. Forward rates (USD per EUR), q = 1..4: 1.085, 1.090, 1.095, 1.100. Bank charge on forwards 0.12 % of the EUR notional h_q U / F_q.

**Uncertain data.** Spot at the end of each quarter S_q, 1.02 to 1.22 USD/EUR, independent between quarters. Volume factor v (actual USD revenue = v U), 0.85 to 1.10: ONE value shared by all four quarters.

**Laws.** For quarter q (million EUR):
revenue = U [ v/S + h_q (1/F_q - 1/S) + o_q (1/min(S, K) - 1/S) ] - pi_K o_q U - 0.0012 h_q U/F_q (the forward settles at F_q even if the volume turns out smaller: over-hedged notional is closed at spot; the put is cash-settled); profit = revenue - 3.00.
Note that profit is piecewise linear in S with a kink at S = K.

**Requirements.**
R1 Every quarter's profit >= -0.10 million EUR for all S_q and v.
R2 Annual profit (sum of the four quarters) >= +0.30 million EUR for all S_q (independent) and v.
R3 Average hedge ratio: | (1/4) sum_q (h_q + o_q) - 0.6 | <= 0.2.
R4 h_q + o_q <= 1 in every quarter.
R5 Forward notional sum_q h_q U <= 9.0 million USD (credit line).
R6 Total option premium sum_q pi_K o_q U <= 0.10 million EUR.

**Decide.** Choose strike (or none) and the eight fractions at minimum hedging cost = total premium + total bank charge (million EUR; report in thousand EUR), or show none works.

---

## 12. Call-centre staffing and self-service option (operations)

**Situation.** A call centre is staffed in four 3-hour day parts, 300 days a year. Each day part is an independent steady-state queue with n_s agents (integer 1 to 60). A self-service (IVR) option deflects a share of the calls, or may be left out.

**Choices.** n_1..n_4 and one IVR option.

| IVR option | deflection d (share of calls removed) | annual price kEUR |
|---|---|---|
| none | 0 | 0 |
| basic | 0.06 to 0.10 | 14 |
| advanced | 0.12 to 0.18 | 31 |

| Day part | arrivals lambda calls/hour (before deflection) | agent cost EUR/hour |
|---|---|---|
| P1 08-11 | 180 to 220 | 33 |
| P2 11-14 | 230 to 280 | 36 |
| P3 14-17 | 170 to 210 | 38 |
| P4 17-20 | 90 to 120 | 45 |

**Uncertain data.** Arrival rates per day part independent within their ranges. Mean handling time including wrap-up AHT, 4.8 to 5.6 min: ONE value common to all day parts. Deflection d is ONE value common to all day parts, within the range of the chosen option.

**Laws.** Effective arrivals lambda_e = lambda (1 - d) per hour; offered load A = lambda_e * AHT/60 (Erlangs).
- If n <= A the queue grows without bound (no steady state): service level is 0 and occupancy is >= 100 %.
- Otherwise Erlang C: P_wait = [A^n/n! * n/(n - A)] / [ sum_{k=0}^{n-1} A^k/k! + A^n/n! * n/(n - A) ].
- Service level (share of calls answered within 20 s) SL = 1 - P_wait * exp( -(n - A) * 20 / (60 AHT) ) (AHT in minutes, so 60 AHT is seconds).
- Occupancy = A/n.
- Daily call-weighted service level SL_day = sum_s lambda_e,s SL_s / sum_s lambda_e,s (weights are the realised volumes).
- Annual cost = sum_s n_s * (cost per hour)_s * 3 h * 300 days / 1000 [kEUR] + IVR annual price.

**Requirements.**
R1 SL_s >= 0.70 in every day part at the worst case.
R2 SL_day >= 0.87 at the worst case (the worst case of this weighted average need not coincide with the worst case of each day part).
R3 Occupancy <= 0.92 in every day part at the worst case.
R4 n_s <= 60.

**Decide.** Choose n_1..n_4 and the IVR option at minimum annual cost (kEUR), or show none works.
