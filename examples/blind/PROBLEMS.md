# Blind test of the input format — 12 problems (2026-10-10)

Written by a separate agent that never saw the brick format (domains given, data invented by it, not solved).
Each problem is handed to its own blind author with BRICKS.md only.

## 1. Valve spring selection (mechanical)
A helical compression spring closes an engine valve. Installed length is 40.0 mm ±0.2 mm. At full valve lift the spring is compressed a further 8.0 mm ±0.1 mm.
Shear modulus of the spring steel: G = 79.3 GPa ±2%.
Laws: spring rate k = G·d^4 / (8·D^3·n), where d is wire diameter, D is mean coil diameter and n is the number of active coils. Force F = k·(L0 − L), where L0 is free length and L is current length.
Corrected shear stress: τ = K_w·8·F·D / (π·d^3), with spring index C = D/d and Wahl factor K_w = (4C − 1)/(4C − 4) + 0.615/C.
Solid length: Ls = (n + 2)·d (two inactive end coils).
Catalog (all lengths in mm):
S1: d 3.20 ±0.02, D 24.0 ±0.2, n 6.0 ±0.25, L0 52.0 ±0.5, price $0.95.
S2: d 3.50 ±0.02, D 24.0 ±0.2, n 6.0 ±0.25, L0 50.0 ±0.5, price $1.20.
S3: d 3.50 ±0.02, D 22.0 ±0.2, n 6.5 ±0.25, L0 49.0 ±0.5, price $1.35.
S4: d 3.80 ±0.03, D 25.0 ±0.25, n 5.5 ±0.25, L0 48.5 ±0.5, price $1.60.
Requirements: force at installed length 140..240 N; force at full lift ≤ 420 N; τ at full lift ≤ 650 MPa; solid length at least 0.5 mm shorter than the full-lift length.
Question: Which springs meet every requirement for all tolerance combinations, and which of those is cheapest?

## 2. Fan selection for an outdoor electronics cabinet (thermal, two modes)
A sealed-path cabinet is cooled by one fan pulling ambient air through a filter. All the heat leaves with the air stream.
Laws: air temperature rise ΔT = P / (ρ·c_p·Q), with c_p = 1007 J/(kg·K). Air density ρ = p / (R·T_in), with p = 101 325 Pa, R = 287 J/(kg·K), and T_in = ambient temperature in kelvin.
Fan curve: Δp = p_max·(1 − Q/Q_max). System resistance: Δp = K·Q^2, with K = 32 000 Pa/(m³/s)² ±15% (clean to partly clogged filter). The operating flow Q is where the two curves meet.
Outlet temperature: T_out = T_in + ΔT.
Normal mode: ambient 15..30 °C, dissipated power P = 150 W ±10%. Requirement: T_out ≤ 40 °C.
Hot mode: ambient 30..45 °C, P = 260 W ±10%. Requirement: T_out ≤ 55 °C.
Catalog (Q_max in m³/s, p_max in Pa, noise in dBA):
F1: Q_max 0.032 ±5%, p_max 35 ±8%, noise 28 ±2, price $9.
F2: Q_max 0.040 ±5%, p_max 48 ±8%, noise 33 ±2, price $14.
F3: Q_max 0.047 ±5%, p_max 62 ±8%, noise 38 ±2, price $19.
F4: Q_max 0.055 ±6%, p_max 80 ±10%, noise 43 ±2, price $27.
Further requirement: noise ≤ 40 dBA in the worst case.
Question: Which fans meet both modes and the noise limit for every allowed value, and which is cheapest?

## 3. Booster pump for a water transfer line (fluid)
Water is pumped from a lower tank to an upper tank. The static lift Δz is 12..18 m, depending on tank levels.
Pipe: inner diameter D = 52.5 mm ±0.5 mm, length L = 120 m, roughness ε = 0.045 mm. Total minor-loss coefficient ΣK = 8.5 ±1.0.
Water temperature 10..60 °C. Over this range, kinematic viscosity ν runs from 1.31e-6 to 0.47e-6 m²/s and density ρ from 998 to 983 kg/m³.
Laws: velocity V = Q/(π·D²/4); Reynolds number Re = V·D/ν. Swamee–Jain friction factor f = 0.25 / [log10(ε/(3.7·D) + 5.74/Re^0.9)]^2. System head H_sys = Δz + (f·L/D + ΣK)·V²/(2g), with g = 9.81 m/s².
Pump curve: H_pump = H0 − a·Q², with Q in m³/h. The operating flow solves H_pump(Q) = H_sys(Q); Q appears on both sides through f.
Shaft power: P_shaft = ρ·g·Q·H / η, with Q in m³/s.
Catalog (H0 in m, a in m/(m³/h)²):
P1: H0 28 ±3%, a 0.075 ±5%, efficiency η 0.55 ±0.03, price $420.
P2: H0 32 ±3%, a 0.090 ±5%, η 0.58 ±0.03, price $510.
P3: H0 36 ±3%, a 0.110 ±5%, η 0.62 ±0.03, price $640.
P4: H0 40 ±3%, a 0.085 ±5%, η 0.60 ±0.03, price $780.
Requirements: 9.0 m³/h ≤ Q ≤ 14.0 m³/h; P_shaft ≤ 1.5 kW (motor rating).
Question: Which pumps keep the flow in the window and within the motor rating over all lifts, temperatures and tolerances, and which is cheapest?

## 4. Continuous stirred reactor sizing (chemical)
A first-order liquid reaction A → B runs in a continuous stirred-tank reactor (CSTR).
Feed flow Q = 2.0 m³/h ±10%. Feed concentration C_in = 2.0 mol/L ±5%. Reactor temperature 55..65 °C.
Laws: residence time τ = V/Q. Outlet concentration C_out = C_in / (1 + k·τ). Conversion X = 1 − C_out/C_in.
Arrhenius law: k(T) = k_ref·exp(−(Ea/R)·(1/T − 1/T_ref)), with k_ref = 0.20 1/min ±10% at T_ref = 333.15 K, Ea = 60 kJ/mol ±3%, R = 8.314 J/(mol·K), T in kelvin.
Heat released: q = |ΔH|·Q·C_in·X, with ΔH = −70 kJ/mol ±5%. The cooling jacket must remove all of it.
Catalog (V = working volume, jacket = cooling duty):
R1: V 1.2 m³ ±3%, jacket 80 kW ±10%, price $38 000.
R2: V 1.6 m³ ±3%, jacket 95 kW ±10%, price $46 000.
R3: V 2.0 m³ ±3%, jacket 105 kW ±10%, price $55 000.
R4: V 2.5 m³ ±3%, jacket 120 kW ±10%, price $67 000.
Requirements: X ≥ 0.85 in every case; heat released q ≤ minimum jacket duty in every case.
Question: Is there a vessel that meets both requirements over the full temperature, flow and parameter ranges? Which is cheapest?

## 5. Backup battery for a telecom cabinet (battery and power, two modes)
A 12 V lead-acid battery must carry a cabinet load through a mains outage.
Load power P = 300 W ±10%. Battery terminal voltage during discharge is 11.5..12.8 V, so the discharge current is I = P / V.
Peukert's law: runtime t = H·(C_eff / (I·H))^k, where H = 20 h is the rated discharge time, C_eff is the effective capacity in Ah and k is the Peukert exponent.
Warm mode, 25 °C: C_eff = C_rated. Cold mode, −10 °C: C_eff = 0.80·C_rated (±0.03 on the factor).
Recharge time from empty to 90%: t_ch = 0.9·C_rated·1.15 / I_ch. Charger current I_ch = 15 A ±5%; the factor 1.15 is charge inefficiency.
Catalog:
B1: C_rated 100 Ah ±5%, k 1.15 ±0.02, mass 29 kg, price $210.
B2: C_rated 120 Ah ±5%, k 1.18 ±0.02, mass 34 kg, price $245.
B3: C_rated 150 Ah ±5%, k 1.20 ±0.02, mass 41 kg, price $290.
B4: C_rated 110 Ah ±5%, k 1.10 ±0.02, mass 32 kg, price $330.
Requirements: runtime ≥ 2.5 h in both warm and cold modes; recharge time ≤ 12 h; battery mass ≤ 45 kg.
Question: Which batteries meet every requirement over all tolerances, and which is cheapest?

## 6. Amplifier with RC anti-alias filter (analog electronics, two modes)
A non-inverting op-amp stage drives a first-order RC low-pass filter feeding an ADC.
Gain: G = 1 + Rf/Rg, with Rf = 39.0 kΩ ±1% and Rg = 4.30 kΩ ±1%. Both resistors have tempco ±100 ppm/°C, referenced to 25 °C.
Filter resistor R = 15.0 kΩ ±1%, tempco ±100 ppm/°C. The filter capacitor C is chosen from the catalog.
Laws: cutoff f_c = 1 / (2π·R·C). Attenuation at frequency f: A(f) = 20·log10(sqrt(1 + (f/f_c)^2)) dB.
Cold mode: −20 °C. Hot mode: +70 °C. Resistor values move by tempco × (T − 25 °C). Capacitor values move by the drift listed for the given extreme.
Catalog (all 10 nF nominal):
C1: X7R, tolerance ±10%, drift −10%..+5% across −20..70 °C, price $0.02.
C2: C0G, tolerance ±5%, drift ±0.3%, price $0.08.
C3: C0G, tolerance ±2%, drift ±0.3%, price $0.15.
C4: polypropylene film, tolerance ±1%, drift −1.5%..+0.5%, price $0.45.
Requirements, in both modes: f_c within 990..1140 Hz; A(10 kHz) ≥ 19 dB; G within 9.8..10.3.
Question: Which capacitors satisfy every requirement in both temperature modes for all tolerances, and which is cheapest?

## 7. Floor beam selection (structural)
A simply supported steel beam spans L = 5.00 m ±0.02 m. It carries a uniform dead load w_d = 4.0 kN/m ±10% plus its own self-weight, and a central point load P = 18 kN ±15%.
Steel: E = 210 GPa ±2%, minimum yield f_y = 235 MPa. Partial safety factor γ = 1.10, so allowable stress = f_y/γ.
Laws: w = w_d + m_s·g, where m_s is the section mass per metre and g = 9.81 m/s². Maximum moment M = w·L²/8 + P·L/4. Bending stress σ = M/W_el.
Midspan deflection: δ = 5·w·L^4/(384·E·I) + P·L^3/(48·E·I).
First natural frequency (beam plus dead load only): f1 = (π / (2·L²))·sqrt(E·I/μ), with μ = m_s + w_d/g in kg/m.
Catalog (I in cm⁴, W_el in cm³; I and W_el ±4% for rolling tolerance):
IPE200: I 1943, W_el 194, 22.4 kg/m, $36/m.
IPE220: I 2772, W_el 252, 26.2 kg/m, $42/m.
IPE240: I 3892, W_el 324, 30.7 kg/m, $49/m.
IPE270: I 5790, W_el 429, 36.1 kg/m, $58/m.
IPE300: I 8356, W_el 557, 42.2 kg/m, $68/m.
Requirements: σ ≤ f_y/γ; δ ≤ L/300; f1 ≥ 8 Hz.
Question: Which sections meet all three requirements for every tolerance combination, and which is cheapest?

## 8. Conveyor inspection camera lens (optics)
A camera looks straight down on a conveyor belt 3.00 m wide. The camera-to-belt distance D is 1.80..2.20 m because of mounting tolerance and belt sag.
Sensor: 4096 × 3000 pixels, pixel pitch p = 3.45 µm, so active width w = 14.13 mm and diagonal 17.5 mm.
Laws: horizontal field of view HFOV = 2·atan(w / (2·f)). Covered width at distance D: W = 2·D·tan(HFOV/2).
Pixel footprint on the belt: s = D·p/f. The lens image circle must be at least the sensor diagonal, or the corners vignette.
Catalog (focal length f, image circle IC):
L1: f 5.0 mm ±3%, IC 17.6 mm, price $95.
L2: f 6.0 mm ±3%, IC 16.0 mm, price $110.
L3: f 6.0 mm ±2%, IC 17.6 mm, price $160.
L4: f 7.0 mm ±2%, IC 17.6 mm, price $185.
L5: f 8.0 mm ±2%, IC 17.6 mm, price $150.
Requirements: W ≥ 3.30 m (10% margin over the belt width) at the shortest distance; s ≤ 1.2 mm at the longest distance; IC ≥ 17.5 mm.
Question: Which lenses satisfy every requirement over the full distance range and focal-length tolerance, and which is cheapest?

## 9. Mortgage choice under rate uncertainty (finance)
A household buys a home for 350 000 EUR. The down payment will be 60 000..75 000 EUR, so the principal is P = 350 000 − down payment.
Net monthly income is 5 200..5 800 EUR. Cash savings are 78 000 EUR.
Law (annuity): monthly payment A = P·r·(1+r)^n / ((1+r)^n − 1), with r = annual rate / 12 and n = 12 × term in years.
For variable products, assume the rate stays at one unknown constant value, index + margin, for the whole term. The index is anywhere in 2.5..5.0% per year. A cap, if present, limits the total rate.
Catalog:
L1: fixed 6.1%, 25 years, upfront fee 1.0% of principal.
L2: fixed 5.6%, 30 years, upfront fee 2 500 EUR.
L3: variable, index + 1.6%, 25 years, upfront fee 0.5% of principal.
L4: variable, index + 1.2%, capped at 6.0% total, 30 years, upfront fee 1.5% of principal.
Requirements: A ≤ 35% of net income for every allowed income; down payment + upfront fee ≤ cash savings.
Measure of goodness: total paid over the term (n·A + fee) at the worst allowed rate.
Question: Which products are feasible for every allowed down payment, income and index value, and which has the lowest worst-case total paid?

## 10. API service capacity plan (software systems, two modes)
An HTTP service runs on N identical instances behind a load balancer that splits requests evenly. Model each instance as an M/M/1 queue.
Peak arrival rate λ = 1 800 req/s ±10%. Per-instance arrival rate is λ_i = λ / N_active.
Laws: utilization ρ = λ_i/μ, which must be < 1. 99th-percentile response time of an M/M/1 queue: T99 = ln(100) / (μ − λ_i).
End-to-end p99 is taken as the sum: gateway 5..12 ms + T99 + database 15..30 ms.
Normal mode: all N instances healthy (N_active = N). Requirements: end-to-end p99 ≤ 150 ms and ρ ≤ 0.75.
Degraded mode: one instance down (N_active = N − 1), same peak traffic. Requirement: end-to-end p99 ≤ 300 ms.
Catalog (μ = service rate per instance):
I1: μ 220 req/s ±10%, $0.17 per instance-hour.
I2: μ 450 req/s ±10%, $0.34 per instance-hour.
I3: μ 900 req/s ±12%, $0.68 per instance-hour.
I4: μ 1 700 req/s ±12%, $1.36 per instance-hour.
The instance count N is an integer from 2 to 12; all instances are the same type.
Question: Which (type, N) pairs meet both modes for every allowed traffic and service rate, and which pair has the lowest hourly cost?

## 11. Motor choice for a high-power model rocket (aerospace)
A model rocket airframe without motor has mass m_air = 2.40 kg ±5%. It launches from a vertical rail of length 1.80 m ±0.02 m.
Liftoff mass m0 = m_air + motor total mass. Burnout mass mf = m0 − propellant mass m_p.
Laws: ideal delta-v Δv = Isp·g0·ln(m0/mf), with g0 = 9.81 m/s². Total impulse I_t = Isp·g0·m_p. Burn time t_b = I_t / F_avg.
Usable delta-v (gravity loss only, drag ignored): Δv_eff = Δv − g0·t_b.
Rail exit speed: v_rail = sqrt(2·(F_avg/m0 − g0)·L_rail). Peak acceleration at burnout: a_max = F_avg/mf.
Catalog:
M1: total mass 0.95 kg, m_p 0.50 kg ±2%, Isp 195 s ±4%, F_avg 260 N ±10%, price $95.
M2: total mass 1.20 kg, m_p 0.62 kg ±2%, Isp 200 s ±4%, F_avg 180 N ±10%, price $110.
M3: total mass 1.45 kg, m_p 0.80 kg ±2%, Isp 190 s ±4%, F_avg 420 N ±10%, price $150.
M4: total mass 1.80 kg, m_p 1.00 kg ±2%, Isp 205 s ±4%, F_avg 350 N ±10%, price $185.
Requirements: thrust-to-weight F_avg/(m0·g0) ≥ 5; v_rail ≥ 15 m/s; Δv_eff ≥ 250 m/s; a_max ≤ 15·g0 (payload limit).
Question: Which motors meet every requirement for all tolerances, and which is cheapest?

## 12. Fixed dosing regimen across patient weights (pharmacology, fictional drug)
A fictional antibiotic "drug X" is given as repeated short IV doses. Model it as a one-compartment bolus at steady state.
The regimen must work for adult patients weighing 55..95 kg without weight-based adjustment.
Volume of distribution V = 0.70 L/kg × weight, ±15% between patients. Clearance CL = 0.060 L/(h·kg) × weight, ±25%.
Laws: elimination rate k = CL/V. Steady-state peak C_max = (Dose/V) / (1 − exp(−k·τ)), where τ is the dosing interval. Steady-state trough C_min = C_max·exp(−k·τ).
Each administered dose is within ±5% of the labelled dose (preparation tolerance).
Catalog (dose, interval, cost per dose):
D1: 750 mg every 8 h, $11.
D2: 1 000 mg every 12 h, $14.
D3: 1 000 mg every 8 h, $14.
D4: 1 250 mg every 12 h, $17.
D5: 1 500 mg every 12 h, $20.
Requirements: C_min ≥ 10 mg/L (efficacy) and C_max ≤ 40 mg/L (toxicity), for every allowed weight, parameter and dose value.
Question: Is there a regimen that meets both limits across the whole population range? Which one has the lowest daily cost?
