# Blind test 3 — 12 problems (2026-10-10)

Written by a separate agent that never saw the input format; data invented, not solved.

## 1. Spring/rubber mounts for a screw compressor skid (vibration isolation)

A compressor skid sits on N identical mounts (N = 4 or 6, symmetric). Skid mass m = 1200 kg, tolerance +-5% (oil level, accessories), so 1140 ... 1260 kg. It runs on a frequency converter: operating speed anywhere between 1350 and 1500 rpm. The dominant disturbing force is at the running frequency f = n/60.
Model: single degree of freedom, vertical. Total stiffness k = N * k_mount, k_mount tolerance +-15%. Natural frequency fn = (1/2pi) sqrt(k/m). Frequency ratio r = f/fn. Force transmissibility T = sqrt((1 + (2 zeta r)^2) / ((1 - r^2)^2 + (2 zeta r)^2)). Damping ratio zeta of each mount is only known as a range (below), and it is NOT independent of the stiffness: both come from the same material, so use the matching pair from one catalog row. Static deflection d_st = m g / k, g = 9.81 m/s^2.
Catalog (k_mount in N/mm, zeta range over the whole temperature range 0 ... 60 C, allowed static load per mount, price per mount):
- S1 steel coil spring: 120 N/mm, zeta 0.01 ... 0.03, 1500 ... 4500 N, 38 EUR
- S2 steel coil spring: 180 N/mm, zeta 0.01 ... 0.03, 2000 ... 6000 N, 44 EUR
- S3 steel coil spring: 260 N/mm, zeta 0.01 ... 0.03, 3000 ... 8000 N, 52 EUR
- SD2 spring with viscous damper: 180 N/mm, zeta 0.10 ... 0.20, 2000 ... 6000 N, 96 EUR
- R1 rubber, Shore 40: 300 N/mm, zeta 0.06 ... 0.10, 1500 ... 3500 N, 21 EUR
- R2 rubber, Shore 55: 520 N/mm, zeta 0.08 ... 0.14, 2500 ... 6000 N, 19 EUR
Requirements: (a) T <= 0.06 at every speed between 1350 and 1500 rpm, for every allowed m, k and zeta. (b) Static load per mount (m g / N, for the whole mass range) inside the allowed load range of the mount. (c) Static deflection <= 25 mm for the heaviest case. (d) During run-up the speed sweeps through the resonance; the peak transmissibility, approximated as T_peak = sqrt(1 + 4 zeta^2) / (2 zeta) evaluated at the smallest zeta, must stay <= 12 for the sweep to be acceptable (otherwise a speed-skip is needed, which is not allowed here). Also the resonance must not be inside 1350 ... 1500 rpm band: fn <= 0.4 * f_min.
Question: which (type, N) combinations satisfy all requirements for all allowed values, and which of them is cheapest in total mounts price?

## 2. Insulation and window package for a single-family house (building heat loss)

Heated volume 225 m^3. Envelope: opaque walls 142 m^2, windows 26 m^2, roof 90 m^2 (U = 0.14 +-0.01 W/m^2K, fixed), floor over ground 90 m^2 (U = 0.30 +-0.03 W/m^2K, ground correction factor b = 0.6). Mean envelope area for the average U: 348 m^2.
Wall layers from inside: plaster 15 mm (lambda 0.70), brick 250 mm (lambda 0.62 +-0.05 W/mK), insulation of thickness x, render 10 mm (lambda 0.87). Surface resistances R_si = 0.13, R_se = 0.04 m^2K/W. U_wall = 1/(sum R) + 0.05 W/m^2K for thermal bridges.
Insulation catalog (lambda in W/mK, thickness in mm, price = fixed per m^2 + per mm per m^2 of wall):
- EPS: lambda 0.036 +-0.003, thickness 80/100/120/140/160/200, 25 EUR/m^2 + 0.11 EUR/(m^2 mm)
- Mineral wool: lambda 0.040 +-0.003, thickness 80 ... 200 in steps of 20, 30 EUR/m^2 + 0.13 EUR/(m^2 mm)
- PIR: lambda 0.024 +-0.002, thickness 60/80/100/120/140 (max available), 28 EUR/m^2 + 0.26 EUR/(m^2 mm)
Window catalog (U includes frame, tolerance given): W2 double low-e 1.30 +-0.10, 240 EUR/m^2; W3 triple 0.85 +-0.07, 340 EUR/m^2; W3K triple krypton 0.70 +-0.05, 410 EUR/m^2.
Ventilation: n = 0.5 h^-1 +-0.2 (infiltration + airing), air heat capacity 0.34 Wh/(m^3 K). Indoor 20 C. Design outdoor temperature between -10 and -14 C. Annual heating degree-days (base 20 C indoor) 3300 K*day, range 3000 ... 3600; free heat gains 3000 +-500 kWh/year; heating via heat pump with seasonal COP 3.2 +-0.3, electricity 0.28 EUR/kWh.
Heat pump catalog: 6 kW (3900 EUR), 8 kW (4800 EUR), 10 kW (5900 EUR), nameplate at outdoor -7 C; available capacity at outdoor temperature T_out (C) for T_out <= -7: P = P_nom (1 + 0.015 (T_out + 7)).
Requirements: wall U (without bridges) <= 0.22 W/m^2K for all lambda values; mean envelope U (H_T / 348 m^2, ventilation not included) <= 0.35 W/m^2K; the heat pump must cover the design heat loss (transmission + ventilation) at the worst design temperature and worst tolerance; annual net heating energy (H_T + H_V) * 24 * degree-days / 1000 - gains <= 9000 kWh at the worst case of all ranges.
Question: which combinations (insulation type + thickness, window type, heat pump) satisfy everything, and which has the lowest 20-year cost (investment + 20 years of electricity at nominal values)?

## 3. Accumulator for an emergency actuator stroke (hydraulic accumulator)

A bladder accumulator must deliver at least dV_req = 6.5 L (+-0.3 L, i.e. 6.2 ... 6.8 L; design for the larger) of oil within 4 s for an emergency stroke. Gauge pressures: minimum system pressure p1 = 110 bar +-5 bar, maximum system pressure p2 = 210 bar (relief valve), atmospheric 1.013 bar must be added for gas law calculations. Fluid and ambient temperature T anywhere between -10 and +60 C.
Gas law: p V^n = const. Fast discharge (< 60 s) is adiabatic, n = 1.4; slow discharge (> 3 min) is isothermal, n = 1.0. Usable volume dV = V0 * p0^(1/n) * (p1^(-1/n) - p2^(-1/n)) (all absolute pressures, p0 = gas pre-charge at working temperature). The pre-charge is set at 20 C; at temperature T (kelvin) the pre-charge changes as p0(T) = p0(20 C) * T / 293.15.
Bladder protection rules: at every operating temperature 0.6 * p1 <= p0(T) <= 0.9 * p1 (gauge or absolute: use gauge pressures for this rule); maximum compression ratio p2/p0(T) (absolute) <= 4.0; maximum allowable pressure of the vessel 250 bar.
Pre-charge can be set in steps of 5 bar from 60 to 120 bar (gauge, at 20 C).
Catalog (nominal gas volume V0, price): A10 10 L 420 EUR; A20 20 L 560 EUR; A32 32 L 740 EUR; A50 50 L 1010 EUR; A80 80 L 1500 EUR.
Second case: the same accumulator also has to deliver 2.0 L over 5 minutes (isothermal) between p1 and p2 at 20 C.
Question: for which (accumulator size, pre-charge step) does the usable volume cover 6.8 L in the fast case at every temperature and every p1 in its range, satisfy the bladder rules for every temperature and p1 in 105 ... 115 bar, and also cover the slow case; which is the cheapest?

## 4. Turbine choice for a hill site (wind turbine energy)

Hub height 80 m above ground; site ground at 1450 m a.s.l. Use the ISA atmosphere for hub altitude h = 1530 m: p = 101325 (1 - 2.25577e-5 h)^5.25588 Pa, and air density rho = p/(287.05 T); the annual mean hub temperature is 5 C +-3 K (not the ISA value). Power curves are given at rho0 = 1.225 kg/m^3. Density correction: use the equivalent wind speed v_eq = v (rho/rho0)^(1/3) in the power curve.
Power curve of every turbine (piecewise): P = 0 for v < v_in; P = P_r (v^3 - v_in^3) / (v_r^3 - v_in^3) for v_in <= v < v_r; P = P_r for v_r <= v < v_out; P = 0 for v >= v_out (storm shutdown). Evaluate on the bin centres below (v_eq computed from the bin centre).
Catalog: T1 P_r 1500 kW, v_in 3.0, v_r 11.5, v_out 25 m/s, 1.35 MEUR; T2 2000 kW, 3.5, 12.0, 22, 1.70 MEUR; T3 2500 kW, 3.0, 12.5, 25, 2.15 MEUR; T4 3000 kW, 4.0, 13.0, 20, 2.80 MEUR.
Speed distribution at hub height, hours per year per 1 m/s bin (bin 0-1 centred at 0.5 m/s, ..., total 8760 h):
0-1: 136; 1-2: 405; 2-3: 633; 3-4: 804; 4-5: 911; 5-6: 947; 6-7: 926; 7-8: 854; 8-9: 751; 9-10: 627; 10-11: 503; 11-12: 389; 12-13: 288; 13-14: 205; 14-15: 141; 15-16: 93; 16-17: 60; 17-18: 37; 18-19: 22; 19-20: 13; 20-21: 7; 21-22: 4; 22-23: 2; 23-24: 1; 24-25: 1.
The table is a long-term average; a single mean-wind-speed scaling factor on all speeds (the same factor for all bins) between 0.93 and 1.07 is possible; hours per bin then shift accordingly. Availability 0.96 +-0.02 multiplies the energy. Wake/electrical losses 8 +-2%.
Requirements: annual net energy >= 5.5 GWh for every allowed combination of wind-speed factor, availability, losses, and temperature; the capacity factor (annual energy / (P_r * 8760)) must be >= 0.22 at the nominal point (factor 1.0, availability 0.96, losses 8%, T = 5 C). O&M 2.5% of the price per year, lifetime 20 years, no discounting.
Question: which turbines satisfy both requirements, and which has the lowest cost per MWh (20-year total cost / 20-year nominal energy)?

## 5. Drive for a loaded belt conveyor (induction motor + gearbox)

Belt pull at the drive drum F = 9.5 kN +-10%, drum diameter D = 0.50 m, required belt speed 1.60 m/s with a tolerance of -4% ... +2%. Load torque at the drum T_L = F D/2 (constant with speed once the belt is moving). Breakaway: the starting load torque is 1.5 times the running torque. The supply voltage is 400 V -10% ... +5%; motor torque scales with (V/400)^2. Speed at the load follows the motor speed divided by the gearbox ratio i.
Motors (4-pole, 50 Hz, synchronous 1500 rpm), rated data and price: M18 18.5 kW, 1470 rpm, 120 N*m rated, 1100 EUR; M22 22 kW, 1475 rpm, 142 N*m, 1350 EUR; M30 30 kW, 1475 rpm, 194 N*m, 1900 EUR. Torque-speed curve, as multiples of rated torque T_n versus n/n_sync (linear interpolation between points), identical in shape for all three motors: (0.00, 2.1), (0.20, 1.8), (0.40, 1.9), (0.60, 2.2), (0.80, 2.5), (0.88, 2.7), (0.94, 2.0), (0.985, 1.0), (1.00, 0.0). Stable operating point = intersection of the motor curve with the load torque (reduced to the motor shaft) on the falling part of the curve (n/n_sync >= 0.88).
Gearbox: ratio i from {20, 22.4, 25, 28}; efficiency 0.96 (0.95 for i = 28); load torque at motor shaft T_L / (i * eta). Gearbox size (rated output torque, price): G1 2400 N*m 900 EUR; G2 3300 N*m 1250 EUR; G3 4500 N*m 1700 EUR; the output torque rating must be >= 1.4 times the maximum running load torque (service factor) and >= 1.0 times the breakaway output torque.
Requirements: (a) at all allowed voltages and loads, the operating point speed gives a belt speed within -4% ... +2% of 1.60 m/s; (b) the motor torque in the whole range 0 ... 0.88 n_sync exceeds the starting-case load torque (breakaway torque for n/n_sync < 0.05, running torque beyond) by at least 25% of the motor's rated torque; (c) at the operating point the motor shaft torque <= 1.0 * T_n of the chosen motor at the lowest voltage (thermal limit, no overload); (d) gearbox rating condition above.
Question: which (motor, ratio, gearbox) triples satisfy every requirement for every allowed voltage and load, and which is the cheapest?

## 6. Mix for C30/37 slab concrete (concrete mix design)

Required characteristic cylinder strength f_ck = 30 MPa. Target mean strength f_m = f_ck + 1.48 s, with the standard deviation of the plant s between 3 and 5 MPa (not known better). Durability (exposure XC4/XF1): w/c <= 0.55, cement >= 300 kg/m^3, cement <= 400 kg/m^3.
28-day mean cylinder strength vs water-cement ratio, with CEM I 42.5R (read from the table, linear interpolation, +-2 MPa scatter of the table itself): w/c 0.40 -> 52; 0.45 -> 46; 0.50 -> 40; 0.55 -> 35; 0.60 -> 31; 0.65 -> 27 MPa. For CEM II/A-L 42.5N subtract 3 MPa from every value.
Water demand (L/m^3, for 16-32 mm crushed aggregate, before admixture) from the slump class: slump 30 ... 60 mm -> 190; 60 ... 180 mm -> 205; > 180 mm -> 220. The delivered slump must be between 100 and 150 mm. Superplasticiser: 1.0% of cement mass, reduces the required water by 12%, price 1.40 EUR/kg. Sand (0/4) has moisture 4% +-2% (by mass); the water in the sand counts toward the mix water, so free water to add = demand - sand moisture water.
Volume balance per m^3: cement/3150 + water/1000 + aggregates/2650 + air = 1 m^3, air 2% +-1% by volume (kg and m^3 units).
Aggregate blend: fractions of total aggregate mass x_s (sand 0/4), x_a (4/16), x_b (16/32), steps of 5%, sum 100%. Cumulative passing % of each fraction on sieves 0.25 / 1 / 4 / 16 / 32 mm: sand 12/45/98/100/100; 4-16: 0/0/5/95/100; 16-32: 0/0/0/8/98. The combined grading must lie in the envelope (passing, % by mass, each sieve value +-3 percentage points sieving error): 0.25 mm 2 ... 10; 1 mm 14 ... 32; 4 mm 34 ... 52; 16 mm 62 ... 82; 32 mm 95 ... 100.
Prices: CEM I 145 EUR/t; CEM II/A-L 128 EUR/t; sand 11 EUR/t; 4-16 13 EUR/t; 16-32 12.5 EUR/t; water neglected; mixing and delivery overhead 18 EUR/m^3 fixed.
Question: choose cement type, w/c (any value between 0.40 and 0.55), plasticiser yes/no, and aggregate blend such that the strength requirement is met for all s, table scatter and sand moisture, the grading stays in the envelope for sieve errors, the cement content stays inside the limits for the worst case, and the cost per m^3 is minimal.

## 7. Photo-survey quadcopter (drone endurance)

All-up mass m = 2.3 kg (frame, motors, ESCs, avionics) + battery + payload. Payload anywhere from 0 to 1.5 kg. Four identical rotors; thrust per rotor T = c_T rho n^2 D^4 (n in rev/s), c_T from the propeller row. Hover: total thrust = m g, g = 9.81. Induced hover power per rotor (momentum theory): P_ind = T^1.5 / sqrt(2 rho A), A = pi D^2/4. Shaft power P_shaft = P_ind / FM (figure of merit), electric power = P_shaft / eta (motor + ESC efficiency 0.80 +-0.05). Add 18 W constant avionics load. Air density rho between 1.05 (hot, high site) and 1.225 kg/m^3.
Propellers: P1 15x5: D = 0.381 m, c_T = 0.105 +-0.008, FM = 0.62 +-0.04, max safe rpm 6800, 45 EUR/set; P2 17x6: D = 0.432 m, c_T = 0.112 +-0.008, FM = 0.68 +-0.04, max rpm 5800, 85 EUR/set.
Batteries (6S, nominal 22.2 V; usable energy fraction 0.80 +-0.03; cold at 0 C the capacity is multiplied by 0.85; the pack count n_b = 1 or 2 in parallel, same type): B1 LiPo 8000 mAh, 1.00 kg, 25C max discharge, 210 EUR; B2 LiPo 12000 mAh, 1.50 kg, 25C, 300 EUR; B3 Li-ion 16000 mAh, 1.45 kg, 3C, 380 EUR.
Requirements (for all payloads in range, all rho, FM, c_T, eta tolerances): (a) for each propeller in turn: hover flight time (usable energy / electric power) >= 22 min with payload 0.5 kg at 20 C and >= 15 min with payload 1.5 kg at 0 C; (b) hover rpm <= 65% of max rpm at the lowest density; (c) peak current at 1.6 x weight thrust (electric power at that thrust, scaled with T^1.5, divided by 22.2 V) <= C-rating * total capacity in Ah; (d) take-off mass (including two packs if chosen) <= 7.0 kg (legal class limit).
Question: which (propeller, battery type, number of packs) combinations meet all requirements in every allowed case, and which is cheapest?

## 8. Gear hub pressed onto a shaft (press fit)

Solid steel shaft d = 50 mm (E = 210 GPa, nu = 0.30, alpha = 11.5e-6 1/K, Rz = 6.3 um), hub outer diameter D = 90 mm, hub length L = 80 mm (bore Rz = 10 um). Torque to be transmitted: 800 N*m +-10% (peak). Friction coefficient mu between 0.08 and 0.14 (depends on lubrication). Required safety against slipping: T_cap >= 2.0 * T_peak, with T_cap = mu p pi d^2 L / 2.
Contact pressure (solid shaft, thick-walled hub): delta_eff = p d [ ((D^2 + d^2)/(D^2 - d^2) + nu_h)/E_h + (1 - nu_s)/E_s ]. Effective interference delta_eff = nominal interference - 0.4 (Rz_s + Rz_h) (roughness smoothing, um) + thermal term. Hoop stress at the bore sigma_t = p (D^2 + d^2)/(D^2 - d^2).
Hub material catalog (E, nu, alpha, allowable bore stress, price):
- H-St C45 steel: 210 GPa, 0.30, 11.5e-6, 360 MPa (yield/1.2), 60 EUR
- H-CI GG25 cast iron: 110 GPa, 0.26, 10.5e-6, 125 MPa (tensile/2.0), 35 EUR
- H-Al aluminium 7075: 71 GPa, 0.33, 23.4e-6, 400 MPa, 75 EUR
Operating temperature range -20 ... +80 C (assembly at 20 C): thermal term = -d (alpha_h - alpha_s) (T - 20 C), i.e. the interference is lost when the hub expands more than the shaft and gained when it is colder than 20 C.
ISO fit options for 50 mm (hub bore always H7: 0 ... +25 um); shaft deviations: p6 +26 ... +42 um (+4 EUR); r6 +34 ... +50 um (+5 EUR); s6 +43 ... +59 um (+7 EUR); u6 +70 ... +86 um (+11 EUR). Minimum and maximum interference = shaft limits minus hub limits.
Assembly by heating the hub: needs hub clearance = max interference + 20 um, temperature rise delta_T_a = clearance/(d alpha_h) must be <= 230 K.
Requirements: slipping safety at the minimum interference, at the worst temperature (that minimises p), worst mu, +10% torque; hoop stress <= allowable at the maximum interference, coldest temperature (max p), shaft included; assembly temperature limit. Question: which (hub material, fit class) combinations satisfy all of this in every allowed case, and which is cheapest by hub + machining price?

## 9. Tank size for a house rainwater system (rainwater harvesting)

Roof 180 m^2 (+-5%), runoff coefficient 0.80 (0.70 ... 0.90), filter efficiency 0.90 (0.85 ... 0.95). Monthly yield = area * rainfall (mm) * 0.80 * 0.90 litres. Rainfall in a normal year, mm per month: Jan 78, Feb 65, Mar 58, Apr 41, May 29, Jun 14, Jul 5, Aug 8, Sep 24, Oct 52, Nov 81, Dec 90 (sum 545). A dry year is the normal year multiplied by 0.75; a wet year by 1.15; no other variation.
Demand: toilets, washing machine and garden. Household 140 L/day (+-15%) for toilets/washing all year; garden 120 L/day in April ... September only. Days per month: 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31.
Monthly water balance (sum over the 12 months, starting 1 January with the tank 50% full): S_next = min(C, max(0, S + yield - demand)); unmet demand in a month = max(0, demand - S - yield); overflow = yield above C (lost). A year is "short" in a month if unmet > 0.
Tank catalog (usable volume C, price incl. delivery): 3 m^3 1100 EUR; 5 m^3 1500 EUR; 7.5 m^3 2050 EUR; 10 m^3 2600 EUR; 15 m^3 3700 EUR; installation (excavation + connections) 380 EUR per m^3 of tank. Filter/pump set: basic 650 EUR (filter efficiency 0.85 ... 0.90) or premium 1100 EUR (0.90 ... 0.95).
Requirements: in the dry year, total unmet demand <= 12% of annual demand and the number of months with shortage <= 3 (worst case of area, runoff coefficient, household demand and filter efficiency inside the filter set's own range); in the normal year, number of months with shortage <= 1; overflow in the wet year no more than 25% of the annual yield.
Question: which (tank, filter set) pairs satisfy every requirement for every allowed combination of the uncertain values, and which is the cheapest (tank + installation + filter set)?

## 10. 24 V to 5 V step-down stage (buck converter)

Synchronous buck: Vin from 18 to 36 V, Vout = 5.0 V +-1%, Iout from 0.5 to 3.0 A. Continuous conduction assumed for Iout >= 0.5 A; duty D = Vout/Vin (ideal). Switching frequency fsw selectable: 300, 400 or 500 kHz (+-10% tolerance on the chosen value).
Inductor ripple current dI = Vout (1 - D) / (L fsw); peak current = Iout + dI/2. Output voltage ripple: dV = dI / (8 fsw C_eff) + dI * ESR (peak-to-peak), where C_eff is the effective capacitance at the DC bias (see below) and ESR the parallel ESR.
Inductor catalog (L tolerance +-20%, DCR, saturation current where L drops by 20%, price; core loss is taken as a fixed 0.1 W for all inductors): L1 4.7 uH, DCR 18 mOhm, Isat 5.5 A, 0.55 EUR; L2 6.8 uH, 24 mOhm, 5.2 A, 0.62 EUR; L3 10 uH, 32 mOhm, 4.8 A, 0.70 EUR; L4 15 uH, 52 mOhm, 4.2 A, 0.85 EUR; L5 22 uH, 70 mOhm, 3.6 A, 1.10 EUR. DCR rises by +25% hot.
Capacitor catalog (per piece, any number 1 ... 4 in parallel; C_eff = C_nom * derating): X1 ceramic 22 uF/10 V X5R, tolerance +-20%, DC-bias derating at 5 V is 0.50, ESR 3 mOhm, 0.28 EUR; X2 ceramic 47 uF/10 V, +-20%, derating 0.45, ESR 3 mOhm, 0.55 EUR; P1 polymer 100 uF/10 V, +-20%, derating 1.0, ESR 18 mOhm, 0.80 EUR.
Switch losses at 36 V and 24 V (use for efficiency): high-side RDS(on) 60 mOhm (hot), low-side 30 mOhm (hot), tr + tf = 25 ns, quiescent 4 mA from Vin, gate drive loss 50 mW at 400 kHz scaling linearly with frequency, dead-time loss neglected. Conduction loss Iout^2 [R_HS D + R_LS (1 - D) + DCR], switching loss 0.5 Vin Iout (tr + tf) fsw, quiescent Vin * 4 mA, core loss 0.1 W (fixed, see inductor list).
Requirements: ripple current dI <= 40% of 3.0 A at the worst Vin and the worst tolerance (L - 20%, fsw - 10%); peak current <= Isat at Iout = 3.0 A and worst dI; output ripple <= 30 mVpp at Vin = 36 V, Iout = 3.0 A for the worst C tolerance; efficiency at Iout = 3.0 A >= 92% at Vin = 24 V and >= 90% at Vin = 36 V (worst DCR).
Question: which (fsw, inductor, capacitor type, count) combinations satisfy everything for every allowed Vin, tolerance and DCR, and which has the lowest component cost (inductor + capacitors)?

## 11. Reverberation correction of a seminar room (room acoustics)

Room 12 m x 8 m x 3.6 m, volume V = 345.6 m^3 (+-2%). Surfaces: floor 96 m^2 (linoleum), ceiling 96 m^2 (painted plasterboard), walls 144 m^2 total, of which windows 20 m^2 and doors 4 m^2, the rest plaster.
Absorption coefficients alpha at 125 / 250 / 500 / 1000 / 2000 / 4000 Hz: floor 0.02 / 0.02 / 0.03 / 0.03 / 0.03 / 0.02; ceiling 0.15 / 0.10 / 0.06 / 0.04 / 0.04 / 0.05; plaster wall 0.02 / 0.02 / 0.03 / 0.04 / 0.05 / 0.05; window 0.35 / 0.25 / 0.18 / 0.12 / 0.07 / 0.04; door 0.14 / 0.10 / 0.06 / 0.08 / 0.10 / 0.10. Each seated person adds an equivalent absorption area 0.20 / 0.30 / 0.40 / 0.45 / 0.50 / 0.50 m^2. Occupancy: anywhere from 10 to 60 persons. Air absorption: 4 m V with m = 0 up to 1 kHz, 0.0010 1/m at 2 kHz and 0.0026 1/m at 4 kHz.
Reverberation time: Sabine, T = 0.161 V / A, where A = sum alpha_i S_i + persons + 4 m V, if the mean absorption coefficient alpha_m = A_surfaces/S_total <= 0.2; Eyring otherwise, T = 0.161 V / (-S_total ln(1 - alpha_m) + persons + 4 m V). Tolerances: alpha of existing surfaces +-0.02 absolute, alpha of added panels +-10% relative.
Panels to add (area each 0.72 m^2, price per panel; maximum 90 m^2 of panels in total, i.e. at most 125 panels; they replace the plaster wall area or ceiling area they cover, which has the alpha of the replaced surface subtracted; for simplicity they replace plaster wall): PA wool 50 mm: 0.12 / 0.45 / 0.90 / 1.00 / 1.00 / 1.00, 38 EUR; PB wool 100 mm + 100 mm air gap: 0.45 / 0.95 / 1.00 / 1.00 / 1.00 / 1.00, 66 EUR; PC perforated wood: 0.20 / 0.55 / 0.80 / 0.85 / 0.60 / 0.40, 55 EUR.
Requirement: T within the window 125 Hz: 0.6 ... 1.2 s; 250 Hz: 0.6 ... 1.0 s; 500, 1000, 2000 Hz: 0.6 ... 0.9 s; 4000 Hz: 0.5 ... 0.9 s, for every occupancy from 10 to 60 persons, every volume and absorption tolerance.
Question: which integer counts (n_A, n_B, n_C) of the three panel types satisfy the window in all bands and all occupancies, and which is cheapest by panel price?

## 12. Grower feed for broilers (diet / feed formulation)

100 kg batch, inclusion in % of the mix, continuous or in 0.5% steps (mixer limit; consider both). Ingredient composition (dry as-fed values) and price: columns ME kcal/kg, CP %, Lys %, Met+Cys %, Ca %, avP %, fibre %, EUR/t.
- Maize: 3350, 8.5, 0.26, 0.38, 0.02, 0.08, 2.2, 205
- Wheat: 3150, 11.5, 0.30, 0.50, 0.05, 0.13, 2.5, 220
- Soybean meal 46: 2450, 46.0, 2.85, 1.35, 0.30, 0.20, 3.9, 480
- Sunflower meal 36: 1900, 36.0, 1.25, 1.35, 0.40, 0.25, 18.0, 290
- Fish meal 60: 2900, 60.0, 4.30, 2.20, 5.00, 2.80, 1.0, 1250
- Vegetable oil: 8800, 0, 0, 0, 0, 0, 0, 980
- Limestone: 0, 0, 0, 0, 38.0, 0, 0, 55
- Dicalcium phosphate: 0, 0, 0, 0, 22.0, 18.0, 0, 520
- L-lysine HCl (78% lysine): 0, 95, 78, 0, 0, 0, 0, 1900
- DL-methionine: 0, 58, 0, 99, 0, 0, 0, 3200
Fixed additions: salt 0.30%, vitamin premix 0.50% (cost 1400 EUR/t, no nutrients counted).
Limits of inclusion: sunflower meal <= 10%, fish meal <= 5%, oil <= 4%, lysine <= 0.4%, methionine <= 0.3%, maize + wheat >= 45%.
Requirements per kg of mix: ME >= 3000 kcal/kg; CP >= 19.5%; Lys >= 1.10%; Met+Cys >= 0.85%; Ca between 0.85 and 1.00%; avP >= 0.42%; Ca : avP ratio between 1.8 and 2.4; fibre <= 5.0%.
Uncertainties (the requirements must hold for every combination): ME of every ingredient +-2.5% of the table value, CP of every ingredient +-1.0 absolute % (relative +-3% for the amino acid contents), the moisture of maize 13 ... 15% (the table is for 14%: all nutrient contents of maize scale by (100 - moisture)/86), price of soybean meal 480 +-15%, fish meal 1250 +-10%.
Question: which mix (percentages) meets all requirements for every allowed value of the uncertain data (with and without the 0.5% step restriction) and what is the cheapest one in EUR/t by the table prices (and what is the worst-case cost over the price ranges)?
