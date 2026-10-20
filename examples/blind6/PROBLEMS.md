# Blind test 6: twelve design-choice problems across engineering, agriculture, finance and operations

All data in all twelve problems is FICTIONAL (invented, internally consistent, plausible in magnitude). Each problem asks for a design choice (from catalogs and/or continuous amounts) together with a proof that every requirement holds over the stated uncertainty, OR a demonstration that no admissible design exists and which requirements conflict. "Worst case" always means: every uncertain quantity may take any value in its stated range independently, unless the text says otherwise (a quantity described as "shared", "common", "ONE value" or "the same" is one value used everywhere it appears). Where a problem asks a limit question (the largest or smallest value of some given condition for which a design still works), answer it as well as the design question.

---

## 1. Warehouse hoist: wire rope and drum diameter (mechanical)

**Situation.** A two-fall (2-part) rope hoist lifts pallets through H = 36 m. The rope has to last 10 years under three load classes. The hoist frame lets the fairlead pass ropes up to 14 mm only, and limits the drum diameter D to 0.15 to 0.45 m. The rope is bought in the one length 84 m. The rope is chosen from a catalog; the drum diameter D is a continuous amount.

**Choices.** (a) one rope; (b) the drum (and sheave) diameter D, 0.15 <= D <= 0.45 m.

| Rope | d mm | breaking force MBF kN | mass mu_r kg/m | price EUR/m |
|---|---|---|---|---|
| W-8 | 8 | 35 | 0.24 | 2.1 |
| W-10 | 10 | 55 | 0.37 | 3.2 |
| W-12 | 12 | 79 | 0.53 | 4.6 |
| W-14 | 14 | 108 | 0.73 | 6.5 |
| W-16 | 16 | 141 | 0.95 | 8.8 |

Drum with sheave price (kEUR) = 0.50 + 16 D^2 (D in m).

**Load classes and uncertain data.**

| Class | payload m kg (each lift anywhere in the range) | lifts per year n_i |
|---|---|---|
| A light | 400 to 600 | 26 000 |
| B heavy | 900 to 1100 | 11 000 |
| C proof test | 1200 to 1300 | 60 |

Lifting block mass 60 kg (fixed). Dynamic factor phi = 0.10 to 0.25 and reeving efficiency eta = 0.95 to 0.98: each is ONE value shared by all classes. Termination efficiency k_t = 0.88 to 0.95 (the rope is weaker than its catalog breaking force by this factor). Fatigue constant N0 = 7.0e5 to 9.0e5 lifts (shared, one value for all classes).

**Laws.**
- Rope tension in the highest-loaded fall: F = g ((m + 60) / (2 eta) + mu_r H) (1 + phi) / 1000 [kN], g = 9.81 m/s2.
- Load ratio rho_i = F_i / (k_t MBF).
- Rope life in lifts for class i: N_i = N0 (D / (24 d))^2.4 (0.10 / rho_i)^2.2, with D and d in the same unit (so D/d is dimensionless).
- Annual damage Dm = sum over classes of n_i / N_i (Miner's rule). Life in years = 1 / Dm.

**Requirements.**
R1 Life >= 10 years, i.e. Dm <= 0.10 per year, for all admissible values.
R2 Static safety factor for class C: k_t MBF / F_C >= 5 for all admissible values.
R3 Rope diameter d <= 14 mm (fairlead).
R4 Drum ratio D / d >= 18 and 0.15 <= D <= 0.45 m.

**Decide.** Choose the rope and D at minimum price (rope 84 m + drum), or show none works.

---

## 2. Two pump motors on one transformer: cables and breakers (electrical power chain)

**Situation.** A workshop transformer supplies a 400 V busbar. Two feeders leave the busbar: feeder 1 (length L1 = 160 m) to pump motor M1, feeder 2 (length L2 = 85 m) to pump motor M2. Each feeder is breaker + 3-phase copper cable + motor. Ambient temperature along the cables is 5 to 38 degC (use 38 for the conductor temperature and the current rating, which is the worst case for both).

**Choices.** For each feeder: (a) one cable cross-section; (b) one breaker. Four independent choices.

| Cable (XLPE, 90 degC) | S mm2 | R20 mohm/m | Iz30 A (rating at 30 degC) | price EUR/m |
|---|---|---|---|---|
| C16 | 16 | 1.150 | 100 | 5.5 |
| C25 | 25 | 0.727 | 130 | 8.0 |
| C35 | 35 | 0.524 | 160 | 10.5 |
| C50 | 50 | 0.387 | 190 | 14.0 |
| C70 | 70 | 0.268 | 240 | 19.0 |
| C95 | 95 | 0.193 | 290 | 26.0 |

| Breaker | rated current In A | price EUR |
|---|---|---|
| B40 | 40 | 48 |
| B50 | 50 | 58 |
| B63 | 63 | 70 |
| B80 | 80 | 95 |
| B100 | 100 | 120 |
| B125 | 125 | 160 |
| B160 | 160 | 230 |

**Source (transformer datasheet).** No-load busbar voltage V0 = 395 to 415 V (tap tolerance). Busbar voltage under load: V_bus = V0 - ks (I_a + I_b) where I_a + I_b is the total current drawn from the busbar in the situation considered and ks = 0.060 to 0.085 V/A (ONE shared value).

**Motors (datasheets).**
- M1: running current 50 to 56 A at power factor 0.85; locked-rotor (starting) current I_s1 = k_ls1 * 53 A with k_ls1 = 5.8 to 6.4, power factor during start 0.40.
- M2: running current 30 to 35 A at power factor 0.85; starting current I_s2 = k_ls2 * 32 A with k_ls2 = 5.8 to 6.4, power factor during start 0.40.
- Required terminal voltage (line-to-line): at least 380 V while running, at least 340 V at the terminals of the motor that is starting.

**Situations to be checked** (each with its own load currents; all ranges independent):
- S1: both motors running.
- S2: M1 starts while M2 runs.
- S3: M2 starts while M1 runs.

**Laws.**
- Conductor temperature (for the resistance, whatever the instantaneous current): theta = T_amb + 60 (I_run / Iz30)^2 [degC], where I_run is the highest running current of the motor on that feeder, T_amb = 38.
- R'(theta) = R20 (1 + 0.00393 (theta - 20)) [mohm/m]; reactance X' = 0.08 mohm/m for every cable.
- Cable voltage drop (line-to-line): dV = sqrt(3) I L (R' cos(phi) + X' sin(phi)), I = current in the cable in the situation, cos(phi) = 0.85 running, 0.40 starting.
- Current rating at ambient T: Iz(T) = Iz30 sqrt((90 - T) / 60) [A].
- Terminal voltage = V_bus - dV of the feeder concerned.

**Requirements** (for every feeder; worst case over all ranges):
R1 Terminal voltage >= 380 V at both motors in S1.
R2 Terminal voltage >= 340 V at the starting motor in S2 and in S3.
R3 Busbar voltage >= 352 V in S2 and in S3.
R4 Breaker In >= 1.1 times the highest running current of its motor (no nuisance trip).
R5 Magnetic trip: 8 In >= 1.25 times the highest starting current of its motor.
R6 Cable protected: In <= Iz(38) of its cable.

**Decide.** Choose the two cables and the two breakers at minimum total price (cables over their lengths + breakers), or show none works. Also state the largest length L1 (other data unchanged) for which any admissible design exists.

---

## 3. Cordless saw: cell pack, protection board and optional heater (electrical, cold climate)

**Situation.** A cordless circular saw is built as a chain: battery cells (5 groups in series, each group made of Np identical cells in parallel) -> protection board (BMS) -> the saw's motor controller. The saw is used outdoors at ambient temperatures from -10 to +40 degC; the cold end is the worst case for every requirement below. The controller draws constant electrical power; its datasheet says it shuts down below an input voltage of 14.2 V. The requirements are checked at the END of the usable discharge, when 20 % of the charge is left, and with the cells at ambient temperature (plus the heater rise if the heater is fitted).

**Choices.** (a) cell type; (b) Np = 1, 2, 3 or 4 (cells per parallel group; 5 groups in series are fixed, so the pack has 5 Np cells); (c) one BMS; (d) heater film fitted or not ("or none").

| Cell | capacity Ah (nominal) | R25 mohm (DC resistance, new, 25 degC) | max continuous current at 25 degC A | price EUR/cell |
|---|---|---|---|---|
| P15 | 1.5 | 11 | 30 | 2.4 |
| H20 | 2.0 | 16 | 22 | 2.0 |
| H25 | 2.5 | 17 | 20 | 2.9 |
| E25 | 2.5 | 24 | 12 | 1.7 |
| E30 | 3.0 | 33 | 9 | 1.6 |

| BMS | continuous current rating A | series resistance R_bms mohm (nominal) | price EUR |
|---|---|---|---|
| M30 | 30 | 9.0 | 3.2 |
| M40 | 40 | 6.0 | 4.5 |
| M60 | 60 | 3.5 | 7.5 |
| M80 | 80 | 2.5 | 11.0 |

Heater film (optional): price 4.5 EUR; raises the cell temperature by dTh = 9 to 13 K above ambient; takes 3.5 Wh out of the pack.

**Uncertain data.**
- Controller input power P = 540 to 640 W (constant power load).
- Open-circuit voltage of one cell at 20 % charge left: Voc = 3.46 to 3.52 V.
- Ageing factor on the cell resistance a = 1.00 to 1.10 (end of life); temperature constant B = 2000 to 2400 K (shared by all cells in the pack).
- Actual capacity = 0.97 to 1.03 of nominal.
- BMS resistance = 1.0 to 1.2 times its nominal. Wiring and connector resistance 4 mohm (fixed).

**Laws.** With the cell temperature T_c in degC (T_c = T_amb, or T_amb + dTh with the heater):
- R_cell = a * R25 * exp(B (1/(T_c + 273.15) - 1/298.15)) [mohm].
- Pack resistance R_tot = 5 R_cell / Np + R_bms + 4 [mohm].
- Pack open-circuit voltage V0 = 5 Voc. The pack current I [A] solves V_t * I = P with V_t = V0 - I R_tot / 1000: I = (V0 - sqrt(V0^2 - 4 R P)) / (2 R), R = R_tot/1000 in ohm. If V0^2 < 4 R P the saw stalls (no solution = failure).
- Cell terminal voltage under load: V_cell = Voc - (I / Np) R_cell / 1000.
- Cold capacity factor kT = max(0.5, 1 - 0.007 (25 - T_c)).
- Usable energy E = 5 Np * (capacity Ah) * 3.6 V * 0.8 * kT - (3.5 Wh if heater, else 0). Runtime = 60 E / P [min].
- Cell current limit at temperature: Imax(T_c) = Imax25 (1 - 0.012 (25 - T_c)).

**Requirements** (worst case over all uncertain data, ambient -10 degC):
R1 Controller input voltage V_t >= 14.2 V.
R2 Runtime >= 9 min.
R3 Pack current I <= BMS rating.
R4 Cell current I / Np <= Imax(T_c).
R5 Cell terminal voltage V_cell >= 2.9 V (cell protection cut-off).

**Decide.** Choose cell, Np, BMS and heater at minimum price (5 Np cells + BMS + heater), or show none works. Then answer the limit question: what is the lowest ambient temperature (instead of -10 degC) at which ANY admissible design exists, and what is it for the design you chose?

---

## 4. Frost protection of an outdoor pipe run: insulation and heat-trace cable (thermal)

**Situation.** A 140 m outdoor run of steel pipe (outer radius r1 = 45 mm) carries service water on a pipe rack in a cold valley. The pipe must be kept at 3 degC or warmer at the design ambient temperature of Ta = -40 degC. The run is insulated and traced with a self-regulating heating cable laid along the pipe. The pipe is plastic-lined, so the cable output must not exceed a cap (R2).

**Choices.** (a) one insulation system; (b) one heat-trace cable.

| Insulation | thickness t mm | k10 W/(m K) at 10 degC | moisture/ageing increase w (anywhere from 0 to) | price EUR/m |
|---|---|---|---|---|
| MW-30 mineral wool | 30 | 0.040 | 0.30 | 7.5 |
| MW-50 mineral wool | 50 | 0.040 | 0.30 | 11.0 |
| PIR-30 foam | 30 | 0.026 | 0.08 | 13.0 |
| PIR-40 foam | 40 | 0.026 | 0.08 | 16.0 |
| PIR-50 foam | 50 | 0.026 | 0.08 | 19.5 |

| Cable | rated output P10 at pipe temperature 10 degC and 230 V, W/m | price EUR/m |
|---|---|---|
| T10 | 10 | 4.8 |
| T15 | 15 | 6.2 |
| T20 | 20 | 8.0 |
| T30 | 30 | 11.5 |

**Uncertain data.** Supply voltage V = 207 to 253 V (one value for the whole run). Wind-dependent outer film coefficient ho = 8 to 25 W/(m2 K). Insulation moisture/ageing w anywhere in its stated range.

**Laws.** Let the pipe be held at Tp = 3 degC, r2 = r1 + t (outer radius of the insulation), Tm = (Tp + Ta)/2.
- Conductivity k = k10 (1 + 0.0018 (Tm - 10)) (1 + w) [W/(m K)].
- Heat loss per metre of pipe (supports and valves allowance 1.3): q = 1.3 (Tp - Ta) / ( ln(r2/r1) / (2 pi k) + 1 / (2 pi r2 ho) ) [W/m].
- Cable output: P(Tp, V) = P10 (1 + 0.012 (10 - Tp)) (V/230)^1.6 [W/m].

**Requirements** (every uncertain quantity anywhere in its range):
R1 Freeze protection: the cable output at Tp = 3 degC and the lowest supply voltage is at least the heat loss q.
R2 Liner protection: the cable output at Tp = 3 degC and the highest supply voltage is at most 24 W/m.
R3 Rack clearance: outer diameter of the insulated pipe 2 r2 <= 180 mm.

**Decide.** Choose insulation and cable at minimum price ((insulation + cable) x 140 m), or show that no admissible design exists and name the conflicting requirements. Then answer the limit question: what is the lowest design ambient temperature Ta (instead of -40 degC) at which an admissible design exists, and which design is it?

---

## 5. Workshop compressed-air line: compressor, dryer and main pipe feeding two tools (fluid chain)

**Situation.** One compressor feeds one air dryer, then a main pipe (L = 180 m), which ends in a junction supplying two tools through their own hoses: Tool A (impact wrench line) and Tool B (grinder). Both tools see the same compressor pressure. Flows are free-air flows in L/s; pressures are gauge pressures in bar unless stated.

**Choices.** (a) one compressor; (b) one dryer; (c) one main-pipe inside diameter d.

| Compressor | FAD nominal L/s | cut-in pressure bar (nominal) | cut-out pressure bar (nominal) | price EUR |
|---|---|---|---|---|
| K32 | 32 | 6.8 | 8.0 | 6 900 |
| K40 | 40 | 6.8 | 8.0 | 8 200 |
| K40M | 40 | 7.3 | 8.4 | 8 900 |
| K50 | 50 | 7.3 | 8.4 | 10 600 |
| K50H | 50 | 8.0 | 9.0 | 11 800 |

Cut-in and cut-out each carry a tolerance of +-0.15 bar (the whole switching band may sit anywhere within it, independently for cut-in and cut-out). Actual FAD = 0.94 to 1.00 of nominal.

| Dryer | rated flow Qr L/s | pressure drop at rated flow, clean, bar | price EUR |
|---|---|---|---|
| D30 | 30 | 0.40 | 1 100 |
| D40 | 40 | 0.35 | 1 450 |
| D50 | 50 | 0.30 | 1 900 |
| D60 | 60 | 0.30 | 2 500 |

| Main pipe inside diameter d mm | price EUR/m |
|---|---|
| 25 | 6.0 |
| 32 | 9.0 |
| 40 | 14.0 |
| 50 | 21.0 |
| 63 | 33.0 |

**Tools (datasheets).**

| Tool | flow Q L/s (any value in the range) | minimum inlet pressure bar | maximum inlet pressure bar | hose |
|---|---|---|---|---|
| A | 14 to 18 | 6.0 | 8.5 | inside diameter 19 mm, 12 m |
| B | 8.5 to 10.5 | 6.2 | 9.0 | inside diameter 16 mm, 8 m |

System leakage 1.5 to 2.5 L/s, always present, ONE value for the whole system (it flows in the main pipe and the dryer). The dryer filter fouling factor f = 1.0 to 1.7 (one value, applies to the dryer's pressure drop).

**Operating situations.** S1: tool A runs alone. S2: tool B runs alone. S3: both run together. In each situation the total flow is Q_t = (flows of running tools) + leakage; the pressure at the compressor outlet is the cut-in value (lowest value in its tolerance).

**Laws.**
- Dryer: dp_dryer = dp_rated (Q_t / Qr)^2 f [bar].
- Pipe or hose (empirical): dp = 1.6e3 * Q^1.85 * Lm / (d^5 * p_abs) [bar], Q in L/s, Lm in m, d in mm, p_abs in bar absolute. Use p_abs = (cut-in - 0.15) - 0.5 + 1.013 in all pipes and hoses of all situations.
- Main pipe carries Q_t; each hose carries only its own tool's flow.
- Tool inlet pressure = (lowest cut-in) - dp_dryer - dp_main - dp_hose.

**Requirements.**
R1 Tool inlet pressure >= the tool's minimum, in every situation in which it runs, at the worst case.
R2 Compressor capacity: 0.94 FAD >= Q_A + Q_B + leakage (S3, upper ends).
R3 No-flow protection: (cut-out + 0.15) <= each tool's maximum inlet pressure.
R4 The dryer's rated flow Qr >= the largest Q_t (S3, upper ends).

**Decide.** Choose compressor, dryer and main-pipe diameter at minimum total price (compressor + dryer + 180 m of pipe), or show none works.

---

## 6. Phenolic wastewater: countercurrent solvent extraction and carbon polishing (chemical)

**Situation.** A plant sends F = 1.5 m3/h of wastewater containing a dissolved organic solute to a countercurrent mixer-settler cascade, then through a granular-carbon bed to the discharge. The solvent is regenerated and recycled; the regeneration leaves a little solute behind, so the solvent enters the last stage slightly loaded. The solvent flow S [m3/h] is a continuous amount (design variable). Operation: 8000 h/year for 5 years.

**Choices.** (a) one extractor unit; (b) one solvent; (c) one carbon bed; (d) the solvent flow S, 0.5 <= S <= 1.8 m3/h.

| Extractor | stages N | stage efficiency eta | price kEUR |
|---|---|---|---|
| E2 | 2 | 0.85 | 12.0 |
| E3 | 3 | 0.80 | 17.0 |
| E4 | 4 | 0.75 | 22.0 |
| E3H | 3 | 0.92 | 20.0 |

| Solvent | K25 (solute in solvent / solute in water, at 25 degC) | temperature coefficient a 1/K | operating cost c_S EUR per m3 of solvent circulated |
|---|---|---|---|
| SA | 4.0 | 0.021 | 1.2 |
| SB | 7.5 | 0.035 | 2.6 |
| SC | 12.0 | 0.045 | 4.5 |

| Carbon bed | mass m kg | price kEUR |
|---|---|---|
| G600 | 600 | 1.8 |
| G1200 | 1200 | 3.2 |
| G2000 | 2000 | 5.0 |

**Uncertain data.**
- Feed solute concentration cF = 6.0 to 7.5 g/L.
- Process temperature T = 15 to 30 degC (the same T in all stages).
- Recycle residual fraction rho = 0.02 to 0.04 (fraction of the loaded-solvent concentration that survives regeneration; shared).
- Carbon capacity q = 0.10 to 0.14 kg solute per kg carbon; carbon removal efficiency e = 0.90 to 0.96.

**Laws.**
- Distribution coefficient K(T) = K25 exp(-a (T - 25)); effective K_eff = eta K(T) in every stage.
- Concentrations in water leaving stage i: x_i [g/L], i = 1..N, with x_0 = cF (stage 1 is the feed end, stage N is the solvent-inlet end). Solvent leaving stage i has y_i = K_eff x_i. Solvent entering stage N has y_in = rho K_eff x_1 (recycled solvent).
- Stage balances (coupled linear system in x_1..x_N, coefficients contain S):
  - for i = 1 .. N-1: F (x_{i-1} - x_i) = S K_eff (x_i - x_{i+1});
  - for i = N: F (x_{N-1} - x_N) = S (K_eff x_N - y_in).
- Raffinate concentration x_N goes to the bed. Final discharge concentration = (1 - e) x_N.
- Bed life in months = q m / (F x_N) / 700 (F in m3/h and x_N in g/L = kg/m3, so F x_N is kg/h; 700 h per month).
- Loaded solvent y_1 = K_eff x_1.
- Cost over 5 years [kEUR] = extractor + bed + 5 * 8000 * S * c_S / 1000.

**Requirements** (every uncertain quantity anywhere in its range, independently; the cascade is solved for each combination):
R1 Raffinate x_N <= 0.12 g/L (inlet limit of the carbon bed).
R2 Final discharge (1 - e) x_N <= 0.006 g/L.
R3 Bed life >= 2 months.
R4 S <= 1.2 F (hydraulic limit of the settlers).
R5 Loaded solvent y_1 <= 8.5 g/L (viscosity limit).

**Decide.** Choose extractor, solvent, bed and S at minimum 5-year cost, or show none works. Report S to three decimals.

---

## 7. Stormwater detention pond: plan area, depth and outlet orifice (civil / hydrology)

**Situation.** A 2.2 ha paved catchment (Ac = 22 000 m2) drains to a detention pond with vertical walls, plan area A and maximum water depth H. A single circular orifice plate at the pond invert is the only outlet in normal operation. The authority sets discharge caps for two return periods and a freeboard rule; the site limits the pond.

**Choices.** (a) one orifice plate (diameter d); (b) plan area A, 100 <= A <= 610 m2 (site limit); (c) design depth H, 0.8 <= H <= 2.0 m.

| Orifice plate | d mm | price kEUR |
|---|---|---|
| O60 | 60 | 0.30 |
| O80 | 80 | 0.45 |
| O100 | 100 | 0.60 |
| O120 | 120 | 0.80 |
| O150 | 150 | 1.10 |

Pond price (kEUR) = 0.12 * A * H (A in m2, H in m) + plate.

**Storms and uncertain data.** Runoff coefficient C = 0.70 to 0.80 (one value for all storms). Orifice discharge coefficient Cd = 0.58 to 0.64 (one value for all storms). Design rainfall intensity i (mm/h), any value in the range, independent per storm and duration:

| Return period | 15 min | 30 min | 60 min |
|---|---|---|---|
| 10-year | 85 to 92 | 62 to 68 | 40 to 44 |
| 100-year | 125 to 135 | 92 to 100 | 62 to 66 |

Every combination (return period, duration) is a separate storm of duration t = 900, 1800 or 3600 s.

**Laws.** For a storm: inflow Qin = C i Ac / 3.6e6 [m3/s]. With Ao = pi d^2 / 4 (d in m), the water depth h reached at the end of the storm is the root of the storage balance
A h + Cd Ao sqrt(1.2 g h) t = Qin t, g = 9.81 m/s2
(the factor 1.2 g stands for the mean head over the storm, 0.6 h). The peak outflow is Qpeak = Cd Ao sqrt(2 g h) [m3/s]. (The left side rises with h, so the root is unique.)

**Requirements** (every storm, every uncertain quantity anywhere in its range independently):
R1 10-year storms: Qpeak <= 25 L/s.
R2 100-year storms: Qpeak <= 45 L/s (capacity of the downstream culvert).
R3 100-year storms: h <= H - 0.30 m (freeboard).
R4 Orifice diameter d >= 80 mm (clogging by leaves).
R5 Site limits: A <= 610 m2 and H <= 2.0 m.

**Decide.** Choose plate, A and H at minimum pond-plus-plate price, or show that no admissible design exists and name the requirements that conflict (state which of them must be relaxed, and whether relaxing one is enough).

---

## 8. Twin-patient ambulance transport: oxygen cylinders, regulators and optional conserver (biomedical / logistics chain)

**Situation.** An ambulance carries two patients. ONE oxygen cylinder bank (1 or 2 identical cylinders on a manifold) supplies BOTH patients, each through their own regulator: patient 1 is ventilated, patient 2 is on a mask. The mission has three phases. Gas must last through all three with a 20 % reserve, at the coldest ambient of -10 degC. All flows are in standard litres per minute (1.013 bar, 0 degC).

**Choices.** (a) cylinder type; (b) number of cylinders n = 1 or 2 (a manifold, 40 EUR, is needed if n = 2); (c) regulator for patient 1; (d) regulator for patient 2; (e) conserver (demand valve) on patient 1's line, or none.

| Cylinder | water volume Vw L | nominal fill pressure bar (at 15 degC) | mass kg | price EUR |
|---|---|---|---|---|
| CY5 | 5 | 200 | 7.5 | 95 |
| CY7 | 7 | 200 | 10.4 | 120 |
| CY10 | 10 | 200 | 14.0 | 165 |
| CY5H | 5 | 300 | 4.2 | 480 |
| CY7H | 7 | 300 | 5.6 | 640 |

| Regulator | flow accuracy (delivered = set * (1 + e), -acc <= e <= +acc) | own leakage L/min | minimum inlet pressure bar | price EUR |
|---|---|---|---|---|
| RA | 0.10 | 0.30 | 10 | 60 |
| RB | 0.05 | 0.15 | 10 | 140 |
| RC | 0.02 | 0.05 | 10 | 320 |

Conserver (optional): price 450 EUR; reduces patient 1's consumption by a fraction kappa = 0.30 to 0.40; needs an inlet pressure of at least 25 bar.

**Mission phases** (set flows anywhere in the ranges, independently per phase and patient):

| Phase | duration min | patient 1 set flow L/min | patient 2 set flow L/min |
|---|---|---|---|
| A: on scene | 20 | 7.5 to 8.5 | 9 to 10 |
| B: transit | Tt = 35 | 8 to 9 | 6 to 8 |
| C: hospital handover wait | 40 | 4 to 5 | 5 to 6 |

The cylinder is filled to 0.97 to 1.00 of the nominal pressure (at 15 degC).

**Laws.**
- Compressibility of oxygen (p in bar): Z(p) = 1 - 4.8e-4 p + 1.3e-6 p^2.
- Free gas available [standard litres] from the bank: N = n Vw ( pf / Z(pf) * 273.15/288.15 - pmin / Z(pmin) * 273.15/(Ta + 273.15) ) / 1.013, where pf is the actual fill pressure, Ta = -10 degC, and pmin is the largest of the minimum inlet pressures of the devices fitted (the regulators, and the conserver if fitted).
- Consumption summed over the phases: C = sum over phases of duration * ( q1 (1 + e1) (1 - kappa if conserver) + q2 (1 + e2) + leak1 + leak2 ), q1 and q2 the set flows of the phase, e1 and e2 the accuracy errors of the two regulators, leak1 and leak2 their leakages.

**Requirements** (worst case over all uncertain quantities):
R1 N >= 1.2 C.
R2 Total cylinder mass n * mass <= 16 kg (stretcher mount).

**Decide.** Choose cylinder type, n, the two regulators and the conserver (or none) at minimum price (cylinders + manifold + regulators + conserver), or show none works. Then answer the limit questions: for your chosen design, the largest transit time Tt (minutes) for which it still satisfies R1; and the largest Tt for which ANY admissible design exists.

---

## 9. Securing a machine on a flatbed: top-over straps and anti-slip mat (transport / logistics)

**Situation.** A packaged machine sits on a truck deck and is secured by friction lashing only: n top-over straps pressing it onto the deck, over an anti-slip mat or none. The weighed cargo mass is uncertain (weighbridge and packaging): m = 7600 to 8400 kg. The deck has at most 10 strap anchor pairs.

**Choices.** (a) one strap grade; (b) number of straps n = 0 to 10; (c) one mat option (or none).

| Strap | lashing capacity LC daN | pre-tension STF daN (nominal, ratchet) | price EUR per strap |
|---|---|---|---|
| S1 | 1500 | 350 | 12 |
| S2 | 2500 | 450 | 19 |
| S3 | 5000 | 650 | 38 |

| Mat option | friction coefficient mu (any value in the range) | price EUR (complete set) |
|---|---|---|
| M0 none (deck against cargo) | 0.30 to 0.40 | 0 |
| M1 rubber mat | 0.55 to 0.65 | 140 |
| M2 premium mat | 0.70 to 0.75 | 260 |

**Uncertain data.** Actual pre-tension = 0.85 to 1.15 of nominal STF. Strap angle to the deck alpha = 62 to 75 degrees. Friction transfer around the cargo corners: kf = 0.85 to 1.00 (the strap leg on the far side carries kf times the near-side tension).

**Laws.** (EN 12195-style load securing, accelerations as fractions of g: forward 0.80, rearward 0.50, sideways 0.50; vertical acceleration reduces the weight to 0.8 m g during driving.)
- Clamping force of one strap: Fv = STF_actual * sin(alpha) * (1 + kf).
- A direction with horizontal acceleration c holds if mu (0.8 m g + n Fv) >= c m g, with g = 9.81 m/s2.

**Requirements** (all three directions, worst case over all ranges independently):
R1 Forward (c = 0.80), rearward (c = 0.50) and sideways (c = 0.50) all hold.
R2 Number of straps n <= 10.
R3 Maximum actual pre-tension 1.15 STF <= 0.5 LC (the strap must not be overstressed by tensioning).

**Decide.** Choose strap grade, n and mat at minimum price (n straps + mat), or show none works. Then answer the limit question: what is the largest cargo mass (instead of the 8400 kg upper end) for which any admissible design exists?

---

## 10. Maize harvest: batch dryer, final moisture and silo aeration fan (agriculture chain)

**Situation.** A co-operative harvests 900 t of wet maize per season. The grain goes through a batch dryer (hot air) and then to a silo for 360 days of storage; the silo may have an aeration fan that keeps the stored grain cooler. Moisture M is written as a decimal on dry basis (kg water per kg dry matter) unless stated; the wet-basis percentage is Mwb = 100 M / (1 + M).

**Choices.** (a) one dryer; (b) one aeration fan (or none); (c) the drying air temperature Td, 50 <= Td <= dryer maximum; (d) the final grain moisture Mf, 0.14 <= Mf <= 0.20 (continuous amounts).

| Dryer | batch size B t (wet grain) | maximum air temperature degC | price kEUR |
|---|---|---|---|
| DR4 | 4 | 85 | 26 |
| DR6 | 6 | 85 | 33 |
| DR8 | 8 | 80 | 40 |
| DR10 | 10 | 75 | 46 |

| Aeration fan | airflow qa m3/(h t) | price kEUR |
|---|---|---|
| none | 0 | 0 |
| F8 | 8 | 2.4 |
| F15 | 15 | 4.1 |
| F25 | 25 | 7.5 |

**Uncertain data** (each anywhere in its range, independently): initial moisture of the harvested grain M0 = 0.30 to 0.36; variety factor on the drying rate k0f = 0.90 to 1.10; Page exponent n = 0.82 to 0.88; ambient air relative humidity RH0 = 0.55 to 0.80 and ambient temperature T0 = 12 to 22 degC (during drying); mean storage ambient temperature Ta = 10 to 16 degC.

**Laws.**
- Air relative humidity after heating to Td: RHd = RH0 exp( 17.27 T0 / (T0 + 237.3) - 17.27 Td / (Td + 237.3) ).
- Equilibrium moisture (decimal d.b.): Me = ( -ln(1 - RHd) / (8.6541e-5 (Td + 49.81)) )^(1/1.8634) / 100.
- Thin-layer drying (Page): MR = (Mf - Me) / (M0 - Me) = exp( - k t^n ), with k = k0f * 6.5e4 * exp( -4400 / (Td + 273.15) ) [1/h^n] and t in hours. So t = ( -ln(MR) / k )^(1/n).
- Batch cycle time = t + 1.0 h (loading and unloading).
- Drying damage index DI = 0.04 t exp(0.08 (Td - 60)).
- Storage grain temperature Ts = max( Ta, Ta + 6 - 0.3 qa ) [degC]. Safe storage time in days: ln(ST) = 7.4 - 0.60 (Mwb - 14) - 0.075 (Ts - 10).
- Season cost [kEUR] = dryer + fan + 900 * W * 0.09 * (1 + 0.012 (Td - 60)) / 1000, where W = 1000 (M0 - Mf) / (1 + M0) is the kg of water removed per tonne of wet grain (use the worst-case M0 for the cost).

**Requirements** (worst case over all uncertain data):
R1 Throughput B / (t + 1.0) >= 0.8 t/h (harvest window).
R2 Damage index DI <= 0.6.
R3 Safe storage time ST >= 360 days.
R4 Td <= maximum air temperature of the chosen dryer.

**Decide.** Choose dryer, fan, Td and Mf at minimum worst-case season cost, or show none works. Report Td and Mf.

---

## 11. Fleet insurance: deductible, optional stop-loss cover and liquidity reserve (finance)

**Situation.** A haulage company with 40 trucks buys fleet insurance. It has to choose the per-claim deductible, whether to add an annual aggregate stop-loss cover, and how much cash to hold idle as a reserve against a catastrophe year. All money in thousands of EUR (kEUR). Three kinds of year are planned for: a normal year, a bad year and a catastrophe year; each year type is a scenario.

**Choices.** (a) deductible D per claim, from the premium table; (b) one stop-loss cover or none; (c) reserve R >= 0 kEUR (continuous).

| Deductible D kEUR per claim | nominal annual premium kEUR |
|---|---|
| 5 | 128 |
| 10 | 104 |
| 20 | 82 |
| 40 | 63 |
| 80 | 48 |

| Stop-loss | attachment A kEUR (annual aggregate retained loss above which it pays) | limit kEUR (maximum it pays) | price kEUR per year |
|---|---|---|---|
| none | - | - | 0 |
| SL60 | 60 | 200 | 16 |
| SL100 | 100 | 200 | 10 |
| SL160 | 160 | 200 | 6 |

The insurer pays every claim above the deductible (the policy limit of 1 500 kEUR is above any claim). The premium actually charged is the nominal premium times a renewal factor f = 1.00 to 1.08 (ONE value, the same in all years). Reserve R is idle cash and costs 5 % of R per year, in every year.

**Claims.** Severities (kEUR per claim, any value in the range): small claims 2 to 8; large claims 60 to 120; catastrophic claim 800 to 1200. Number of claims per year (any value in the range, independently):

| Scenario | small | large | catastrophic |
|---|---|---|---|
| normal year | 20 to 26 | 0 to 1 | 0 |
| bad year | 28 to 36 | 2 to 3 | 0 |
| catastrophe year | 24 to 30 | 1 to 2 | 1 |

**Laws.**
- Retained loss of a year before stop-loss: r = sum over claims of min(severity, D).
- With stop-loss: retained loss after cover r' = r - min( max(r - A, 0), limit ); without it r' = r.
- Total cost of a year = f * premium + stop-loss price + r' + 0.05 R.

**Requirements** (worst case over all uncertain data, independently):
R1 Normal-year total cost <= 210 kEUR.
R2 Bad-year total cost <= 300 kEUR.
R3 Liquidity in the catastrophe year: r' <= R + 40 (the 40 kEUR is an overdraft line).
R4 Budget stability: | r'(bad year) - r'(normal year) | <= 62 kEUR.
R5 Sum of the total costs of the three scenarios <= 680 kEUR.

**Decide.** Choose D, stop-loss and R at minimum worst-case sum of the three scenario costs, or show that no admissible design exists and name the requirements that conflict (and whether dropping one is enough).

---

## 12. Hospital standby generator: test method, test interval and condition monitoring (operations / maintenance)

**Situation.** A hospital's standby generator must be available when the grid fails. Failures of the standby unit are hidden until a test or a real demand reveals them. The facility manager chooses the test method, how often to test (interval tau, a continuous amount), and whether to fit an optional condition-monitoring package. The year is split into three regimes.

**Choices.** (a) one test method; (b) test interval tau, 24 h <= tau <= 2190 h; (c) condition monitoring fitted or not ("or none").

| Test method | coverage c (share of failure modes the test reveals; actual value anywhere in the range) | downtime per test td h (actual value anywhere in the range; the unit is unavailable during the test) | cost per test kEUR |
|---|---|---|---|
| TS start-up only | 0.20 to 0.30 | 0.2 to 0.3 | 0.35 |
| TL load-bank run | 0.80 to 0.88 | 0.6 to 0.9 | 1.6 |
| TF full transfer test | 0.92 to 0.97 | 1.6 to 2.0 | 4.2 |

Condition monitoring (optional): cost 2.2 kEUR/year; multiplies the failure rate by a factor 0.85 to 0.92.

**Regimes** (fraction f of the year; room temperature T_r; annual running hours H_r attributed to the regime, any value in the range):

| Regime | f | T_r degC | H_r h/year |
|---|---|---|---|
| winter | 0.33 | 5 to 12 | 40 to 60 |
| summer | 0.25 | 24 to 32 | 25 to 40 |
| shoulder | 0.42 | 12 to 20 | 15 to 25 |

Base failure rate lam0 = 1.8e-6 to 2.4e-6 per hour at 20 degC (ONE value for all regimes). Thermal constant B = 3000 K. Undetected failure modes are revealed at the quarterly overhaul, Tov = 2190 h.

**Laws.**
- Failure rate in a regime: lam_r = lam0 * exp( B (1/293.15 - 1/(T_r + 273.15)) ) * (H_r / 50)^0.35 [per hour], times the monitoring factor if fitted.
- Hidden-state unavailability in a regime (tau and Tov in hours): U_r = c lam_r tau / 2 + (1 - c) lam_r Tov / 2 + td / tau. (The last term is the share of time lost to tests.)
- Weighted unavailability U = sum over regimes of f U_r.
- Annual cost [kEUR] = (8760 / tau) * (cost per test) + 2.2 (if monitoring).

**Requirements** (worst case over all ranges independently):
R1 U <= 2.25e-3.
R2 tau <= Tov.

**Decide.** Choose the test method, tau and monitoring at minimum annual cost, or show none works. Report the lower and upper limits of the admissible tau interval for the chosen method (hours, one decimal) and the tau you choose.
