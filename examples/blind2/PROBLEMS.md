# Blind test 2 — 12 problems (2026-10-10)

Written by a separate agent that never saw the input format; data invented, not solved.

## 1. Oil cooler, counter-flow plate exchanger (heat exchanger)

A hot lubricating oil must be cooled by water in a counter-flow plate heat exchanger. Heat balance: Q = m_h·cp_h·(Th_in − Th_out) = m_c·cp_c·(Tc_out − Tc_in). Use either LMTD, Q = U·A·ΔT_lm with ΔT_lm = (ΔT1 − ΔT2)/ln(ΔT1/ΔT2) (and ΔT_lm = ΔT1 when ΔT1 = ΔT2), or effectiveness-NTU: NTU = U·A/C_min, Cr = C_min/C_max, ε = (1 − exp(−NTU(1−Cr)))/(1 − Cr·exp(−NTU(1−Cr))) for Cr < 1 and ε = NTU/(1+NTU) for Cr = 1.
- Oil: 2.0 kg/s (±3 %), cp = 2.1 kJ/(kg·K), inlet 95 °C (±2 K). Water: 1.6 kg/s (±5 %), cp = 4.18 kJ/(kg·K), inlet between 15 and 28 °C (river water, summer to spring).
- U is not constant: the clean-plate U of each model is given at oil 80 °C mean; it scales as (oil mean temperature in °C / 80)^0.8 because oil viscosity falls with temperature, and with flow as (m_oil/2.0)^0.5. Fouling: total fouling resistance Rf between 0.0001 and 0.0006 m²·K/W, so 1/U = 1/U_clean + Rf.
- Catalog (model — area A, U_clean, oil-side pressure drop at 2.0 kg/s, price): HX-18 — 3.2 m², 1150 W/(m²·K), 0.35 bar, $1 900; HX-26 — 4.6 m², 1100 W/(m²·K), 0.55 bar, $2 600; HX-40 — 7.0 m², 1050 W/(m²·K), 0.95 bar, $3 700; HX-40T (thin plate) — 7.0 m², 1250 W/(m²·K), 1.30 bar, $4 400. Pressure drop scales as (m_oil/2.0)^1.7.
- Requirements, for every allowed combination of flows, inlet temperatures and fouling: oil outlet temperature ≤ 62 °C; water outlet ≤ 70 °C (scaling limit); oil-side pressure drop ≤ 1.0 bar.
- Question: which models satisfy all requirements everywhere in the ranges, and which is the cheapest? Note the water/oil capacity-rate ratio can approach 1 for some flow combinations.

## 2. Flange bolted joint, torque and separation (bolted joint)

Eight identical bolts clamp a pump cover. Tightening torque T = K·d·F_i (d nominal diameter), with the nut factor K set by friction (read from this table, per surface state): lubricated (μ 0.10–0.14) K = 0.15 ± 0.02; as-delivered oil film (μ 0.12–0.18) K = 0.20 ± 0.03; dry zinc plated (μ 0.16–0.24) K = 0.26 ± 0.04. The torque wrench itself has ±8 % accuracy and the torque is set in 5 N·m steps. Preload scatter F_i,min…F_i,max follows from the extreme K and the wrench error.
- Joint stiffness: bolt stiffness k_b and clamped-parts stiffness k_m define the load factor C = k_b/(k_b + k_m); the bolt takes C·P of an external tensile load P per bolt and the clamped parts lose (1 − C)·P of clamp force. Separation occurs when F_i < (1 − C)·P.
- External load per bolt: pulsating between 0 and 14 kN (pressure cycles), occasional overload up to 20 kN (test pressure, once). Joint stiffness: k_m is 3.2 × k_b for the 8.8 bolts; 3.0 × k_b for the stiffer long M14.
- Catalog (bolt, stress area At, proof strength Sp, price each incl. nut): M10 8.8 — 58.0 mm², 600 MPa, $0.45; M12 8.8 — 84.3 mm², 600 MPa, $0.70; M12 10.9 — 84.3 mm², 830 MPa, $1.30; M14 8.8 — 115 mm², 600 MPa, $1.15; M14 10.9 — 115 mm², 830 MPa, $2.10. Friction states above are chosen per job (price: lube $0.02 per bolt).
- Requirements: at maximum preload and maximum external load (the overload case) bolt stress ≤ 0.90·Sp; at minimum preload and the 20 kN overload the clamp force must stay positive (no separation); fatigue: bolt stress amplitude from the 0–14 kN cycle ≤ 55 MPa (bolt amplitude = C·ΔP/(2·At)); preload must be ≥ 60 % and ≤ 75 % of proof load at the target torque considering the scatter.
- Question: for which combination of bolt, friction state and torque setting (5 N·m steps) do all requirements hold for every value in the scatter range, and which is cheapest?

## 3. 18 GHz microwave link, link budget (radio link)

A 5.0 km (between 4.6 and 5.4 km depending on final mast positions) point-to-point link at 18 GHz carries 200 Mbit/s.
- Link budget: P_rx = P_tx + G_tx + G_rx − L_cable,tx − L_cable,rx − FSPL − L_misc − L_rain, with free-space path loss FSPL = 92.45 + 20·log10(f_GHz) + 20·log10(d_km) dB. L_misc (pointing, radome, gaseous absorption) = 1.5 dB ± 0.5 dB. Cable loss 0.9 dB each end (±0.2 dB).
- Rain: attenuation γ = 0.4 to 2.6 dB/km depending on the rain rate for the required availability; the effective path is d·(1/(1 + d/35)) for the rain cell.
- Receiver sensitivity depends on the modulation which the radio chooses: 16QAM → −78 dBm, 64QAM → −72 dBm, 256QAM → −66 dBm (all at 200 Mbit/s with 56 MHz channel; ±1.5 dB unit spread).
- Regulation: EIRP = P_tx + G_tx − L_cable,tx ≤ 40 dBm.
- Catalog: transmitter power P_tx (selectable radio licenses) 18 dBm ($0), 23 dBm ($600), 27 dBm ($1 400). Dishes (gain at 18 GHz, price): 0.3 m — 33.5 dBi, $350; 0.6 m — 39.5 dBi, $780; 0.9 m — 43.0 dBi, $1 500; 1.2 m — 45.6 dBi, $2 800. Dishes are the same at both ends or different sizes may be mixed.
- Requirements: (a) clear sky, P_rx − sensitivity (fade margin) ≥ 25 dB with 256QAM, (b) in the worst rain case the link must still keep ≥ 3 dB margin using 16QAM (the radio drops modulation in rain), (c) EIRP limit above must hold, (d) hard stop: the receiver's maximum input level is −25 dBm, so P_rx in clear sky must not exceed that, including the +1.5 dB unit spread.
- Question: which combination of transmitter license and the two dishes meets every requirement for the whole range of distance, losses and rain, and which is the cheapest in total?

## 4. LED indicator on a vehicle supply (LED driver)

A white LED is driven from a 12 V vehicle supply through one series resistor.
- Diode: I_F = I_s·(exp(V_F/(n·V_T)) − 1), V_T = k·T/q = 25.85 mV at 300 K (scales linearly with absolute temperature). I_s depends on temperature, I_s(T) = I_s(300 K)·(T/300)^3·exp((E_g/(n·k))·(1/300 − 1/T)) with E_g/n effective 3.0 eV (so V_F at constant current falls by approximately 2 mV/K). Junction temperature range −20 to +95 °C (ambient −40 to +85 °C plus self-heating).
- Supply: 13.6 V nominal with 10.8 V (cranking dip) to 14.8 V (alternator), and a transient of 16 V for up to 1 minute (load dump suppressed).
- Series resistor: R = (V_supply − V_F)/I_F. Resistor value must come from E24 (5 %) or E96 (1 %) series; its tolerance and a temperature coefficient of ±200 ppm/K (E24) or ±50 ppm/K (E96) apply.
- LED catalog (n, I_s at 300 K, absolute max I_F, luminous output 60 lm/W at rated 20 mA, price): LED-A — n = 2.0, I_s = 4.0e−30 A (Vf ≈ 3.0 V at 20 mA), 30 mA, $0.12; LED-B — n = 2.3, I_s = 3.0e−28 A, 50 mA, $0.20; LED-C — n = 1.9, I_s = 1.0e−32 A, 25 mA, $0.35 (Vf ≈ 3.1 V at 20 mA).
- Resistor catalog: carbon film 5 % E24 0.25 W $0.01; metal film 1 % E96 0.25 W $0.03; metal film 1 % E96 0.5 W $0.05; 0.25 W parts may only dissipate 70 % of the rating at 85 °C ambient.
- Requirements: at 10.8 V supply and cold junction the current must be ≥ 8 mA (minimum visible brightness); at the nominal 13.6 V and 25 °C, between 14 and 20 mA; at 14.8 V and cold junction ≤ 90 % of the LED absolute max; at the 16 V transient also ≤ the absolute max; resistor power at 16 V ≤ rating (derated).
- Question: which LED, which resistor series, tolerance, rating and E-series value satisfy all of that for every combination of supply, temperature, tolerance, and which is cheapest?

## 5. Two columns in a pump station frame (column buckling)

Two pin-supported or partly fixed steel columns carry compressive loads. Critical stress depends on slenderness λ = K·L/r, with r = sqrt(I/A). The transition λ_c = sqrt(2·π²·E/S_y). For λ ≥ λ_c Euler applies: σ_cr = π²·E/λ²; for λ < λ_c Johnson (parabolic): σ_cr = S_y·(1 − S_y·λ²/(4·π²·E)). Allowable load = σ_cr·A/n, with design factor n.
- Material: E = 200 GPa, yield S_y = 355 MPa nominal, but the supplier guarantees only ≥ 330 MPa; take the range 330–380 MPa.
- Effective length factor K depends on the end conditions actually obtained: pinned–pinned 1.0, but the base plates are only partly stiff so K is between 0.7 and 1.0 for column A and between 0.8 and 1.2 for column B (one end free to sway a bit).
- Column A: length 1.3 m, load 380 kN (±5 %). Column B: length 3.6 m, load 95 kN (±10 %). Design factor n = 2.0 for A, n = 2.5 for B. Slenderness must not exceed 200 for B and 120 for A.
- Catalog of cross-sections (A, I, price per metre): solid round bars (A = π·d²/4, I = π·d⁴/64) Ø50, Ø60, Ø70 at $18, $26, $35 per m; CHS 76.1×4 (A = 9.06 cm², I = 59.1 cm⁴) $22/m; CHS 101.6×5 (A = 15.2 cm², I = 180 cm⁴) $34/m; CHS 139.7×5 (A = 21.2 cm², I = 481 cm⁴) $48/m; square RHS 100×100×6 (A = 21.6 cm², I = 336 cm⁴) $44/m.
- Requirements: allowable load ≥ applied load for each column for all values in the stated ranges of E, S_y, K, load.
- Question: pick one section for each column; which choices are acceptable and what is the cheapest pair? (Remember that one of the columns may sit in Johnson's regime for some of the data and in Euler's regime for others.)

## 6. Physiological buffer for a cell assay (chemistry)

Prepare 1.00 L of a buffer with pH 7.40 ± 0.05 measured at 37 °C (assay temperature; storage and prep at 22 °C).
- Henderson–Hasselbalch: pH = pKa + log10([A⁻]/[HA]); the exact version solves charge balance with water autoionisation and the stock volumes. Apparent pKa depends on temperature, pKa(T) = pKa(25 °C) + (dpKa/dT)·(T − 25), and on ionic strength I: apparent pKa′ = pKa − 0.5·√I/(1+√I) approx. (use pKa′ shift: −0.08 at I = 0.05 M, −0.12 at I = 0.15 M, linear in between).
- Systems available (pKa at 25 °C, dpKa/dT per K, uncertainty on pKa): phosphate H2PO4⁻/HPO4²⁻ — 7.20, −0.0028, ±0.02, stock solutions 1.0 M; HEPES — 7.48, −0.014, ±0.02, stock 1.0 M (acid form + NaOH 1.0 M for neutralising); Tris — 8.07, −0.028, ±0.03 (stock 1.0 M, titrated with 1.0 M HCl); MOPS — 7.20, −0.015, ±0.02.
- Stock concentration uncertainty ±1 %, volumes are dispensed with a pipette: ±0.5 mL, in whole mL amounts (an integer choice); final volume made up with water to 1.00 L (±3 mL in the flask).
- Requirements: pH within 7.35–7.45 at 37 °C for all allowed errors; buffer capacity β at 7.40 ≥ 15 mmol/(L·pH) (β = 2.303·C_total·Ka[H⁺]/(Ka+[H⁺])², with the total buffer concentration C_total); ionic strength ≤ 0.15 M including sodium from neutralisation (monovalent Na⁺ counted as 1 per ion, HPO4²⁻ as charge 2); the buffer must also remain within pH 7.30–7.50 if the assay temperature moves to 35–39 °C.
- Costs: phosphate stocks $0.02 per mL pair; HEPES $0.35 per mL stock; Tris $0.05; MOPS $0.30 (all per mL of stock used).
- Question: for each system, which integer volumes (in mL) of acid-form and base-form stock fulfil the requirements across all errors? Which system and recipe is cheapest overall?

## 7. Maize irrigation over one season (irrigation)

A 12 ha field is irrigated through a season of 120 days (1 May to 28 August). Net crop demand per day ETc = Kc·ET0.
- Kc is piecewise linear: 0.35 for the first 25 days; rises linearly to 1.15 over the next 35 days; stays at 1.15 for 40 days; falls linearly to 0.60 over the last 20 days. Monthly ET0 (mm/day): May 4.2, June 5.6, July 6.8, August 6.1 — all with ±10 % uncertainty (read each day's value from the month).
- Seasonal rainfall between 60 and 180 mm, of which only 70–80 % is effective; the soil store at start holds 40 mm readily available that may be used (no more than that).
- Irrigation efficiency: drip 90 % (±3), sprinkler 75 % (±5), surface furrow 55 % (±8). Gross water = net / efficiency.
- Water licence: 6 500 m³ per hectare per season. Peak period requirement: during the peak 10 days (ET0 at its July value, Kc at 1.15, no rain), the system must deliver 100 % of the demand, with the pump running no more than 18 h/day.
- Catalog (method + pump): drip with pump P1 — 70 m³/h, 11 kW, capex $38 000 (system) ; drip with P2 — 110 m³/h, 15 kW, $41 000; sprinkler with P2 — 110 m³/h, 15 kW, $29 000; sprinkler with P3 — 160 m³/h, 22 kW, $32 000; furrow with P3 — 160 m³/h, 22 kW, $14 000 (but furrows cannot irrigate more than 80 % of the area in a day). Electricity price $0.14/kWh; pump efficiency delivering listed kW at rated flow.
- Requirements: seasonal gross volume ≤ licence for every combination of ET0, rainfall, efficiency within range; peak-demand requirement met within 18 h/day; no more than 2 800 kWh per hectare per season (energy).
- Question: which method/pump combinations meet all requirements everywhere in the stated ranges, and which has the lowest cost over 10 years (capex + 10 seasons of electricity)?

## 8. Spare-part reorder policy (inventory)

A distribution centre stocks a motor part; annual demand D = 12 000 units (between 10 800 and 13 200), working year 250 days, daily demand has standard deviation σ_d = 14 units/day (independent between days). Cost of placing an order S = $45 (±$5). Holding cost = 22 % per year of the unit price (±3 points).
- Economic order quantity: Q* = sqrt(2·D·S/H), H = holding rate × unit price. Total annual cost TC = D·p + (D/Q)·S + (Q/2 + SS)·H.
- Lead-time demand: mean d·L, standard deviation sqrt(L·σ_d² + d²·σ_L²), with d = D/250, lead time L and its spread σ_L (days) given per supplier. Safety stock SS = z·σ_LT, reorder point = d·L + SS, where z comes from the target cycle service level (standard normal table: 95 % → 1.645; 98 % → 2.054; 99 % → 2.326).
- Suppliers (unit price with quantity breaks; lead time L / σ_L; order size must be a multiple of the pack size): S1 — $11.80 for Q < 500, $11.30 for 500 ≤ Q < 1 500, $10.90 for Q ≥ 1 500; L = 6 d, σ_L = 1.0 d; pack 50. S2 — $10.60 for Q < 1 000, $10.20 for Q ≥ 1 000; L = 12 d, σ_L = 4 d; pack 100. S3 (air freight) — flat $12.40; L = 3 d, σ_L = 0.5 d; pack 10; extra $0.30 per unit freight is included in price.
- Requirements: cycle service level ≥ 98 % (all values of demand/σ_L in the given ranges, using demand at its high end for lead-time demand); warehouse capacity: peak stock Q + SS ≤ 2 100 units; annual cash tied-up average inventory value ≤ $15 000.
- Question: for each supplier, what order quantity (respecting break regime and pack size; the EOQ itself may fall outside its price bracket) and safety stock satisfy every requirement for the whole demand and cost range, and which supplier policy has the lowest total annual cost?

## 9. 12 kWp rooftop PV, inverter and string layout (photovoltaics)

Choose a module type, the number of modules per string (an integer), the number of parallel strings, and an inverter, for a site with record temperatures −18 °C (winter morning) and +38 °C (summer afternoon).
- Cell temperature T_cell = T_amb + (NOCT − 20)/800 · G, NOCT = 45 °C (±2). Module voltage and power change with cell temperature: Voc(T) = Voc,STC·(1 + β_Voc·(T − 25)), Vmp(T) = Vmp,STC·(1 + β_Vmp·(T − 25)), Pmax(T) = Pmax,STC·(1 + γ·(T − 25)) and the irradiance scaling roughly P ∝ G.
- Module catalog (Pmax, Voc, Vmp, Isc, γ, β_Voc, β_Vmp, price): M-410 — 410 W, 37.2 V, 31.0 V, 13.9 A, −0.34 %/K, −0.26 %/K, −0.34 %/K, $135; M-450 — 450 W, 41.5 V, 34.8 V, 13.7 A, −0.35 %/K, −0.27 %/K, −0.35 %/K, $162; M-380 (thin-film-like, better heat behaviour) — 380 W, 45.0 V, 36.0 V, 10.8 A, −0.26 %/K, −0.20 %/K, −0.26 %/K, $140.
- Inverter catalog (max DC voltage, MPPT range, max current per MPPT input / number of inputs, AC rating, price): INV-8 — 600 V, 125–560 V, 16 A × 2, 8.0 kW, $1 300; INV-10 — 1000 V, 200–800 V, 16 A × 2, 10.0 kW, $1 900; INV-12 — 1000 V, 180–850 V, 20 A × 2, 12.0 kW, $2 350.
- Requirements: Voc at the winter case (−18 °C ambient, G = 100 W/m² with T_cell = T_amb + 2 K) times n must be ≤ inverter max DC voltage (with a 3 % safety margin); Vmp at the hot summer case (38 °C, G = 1000 W/m²) × n ≥ MPPT minimum, and the Vmp in winter at STC-like irradiance × n ≤ MPPT maximum; string current (Isc × 1.25) ≤ MPPT input rating per string input; installed DC between 11.5 and 13.5 kWp (STC); DC/AC ratio between 1.05 and 1.35; at the hot summer point (G = 1000 W/m²), the DC power (with the temperature loss) must not exceed 1.1 × the AC rating (clipping), and must be at least 80 % of the AC rating.
- Question: which module / inverter / string configurations satisfy all requirements for both seasons, and which has the lowest total hardware cost (modules plus inverter)?

## 10. Two-stage spur gear reducer (gear train)

A reducer must give a total ratio of 14.3 (between 14.0 and 14.6 allowed) from a 1 450 rpm motor delivering 5.5 kW (±10 % overload factor included separately). Each stage: pinion z1, gear z2, integer tooth numbers, normal module m (standard series 2.0, 2.5, 3.0 mm), both gears are spur, pressure angle 20°.
- Total ratio = (z2a/z1a)·(z2b/z1b); pinion minimum 17 teeth (undercut limit); maximum 110 teeth on any gear; a single stage ratio between 2.5 and 5.0.
- Centre distance a = m·(z1 + z2)/2 (mm). The housing allows: stage A centre distance exactly 125 mm ± 0.5, stage B centre distance between 150 and 175 mm. Both stages must be coaxial-free (not required), but the distance for B must be ≥ 1.2·a_A.
- Contact stress (Hertz, ISO-like simplified): σH = Z_E·Z_H·Z_ε·√(K·F_t·(u+1)/(b·d1·u)), Z_E = 189.8 √MPa, Z_H = 2.5, Z_ε = 0.9, K = K_A·K_v·K_Hβ = 1.25·1.15·1.2; F_t = 2000·T/d1 (N, T in N·m), u = z2/z1, d1 = m·z1. Each stage has its own T (torque after the preceding stage, 0.98 efficiency per stage). Face width b = 12·m (stage A) or 10·m (stage B), mm.
- Material catalog (σH,lim endurance, price per kg of gear blank, relative cost): C45 normalised — 520 MPa, $2.0; 42CrMo4 quenched and tempered — 780 MPa, $3.2; 20MnCr5 case-hardened — 1 450 MPa, $5.6 (plus heat-treat $4/kg). Required safety factor S_H = σH,lim/σH ≥ 1.25 for both gear and pinion (same material for both here), and the load may be 10 % higher in the overload case, requirement S_H ≥ 1.05 at 1.1× torque for 42CrMo4 and above.
- Requirements: the integer tooth numbers meeting the ratio window and both centre-distance constraints; contact safety as above for both stages.
- Question: list the feasible (m, z1, z2) per stage and material choices, and rank by mass-proportional cost (blank mass ∝ b·d²).

## 11. Supply-air duct and fan selection (duct sizing)

A round galvanised supply duct 38 m long (straight) carries air from a fan to a diffuser plenum; fittings: 4 × 90° elbows (loss coefficient K = 0.30 each), 1 balancing damper (K = 1.2, but it must be at least 60 % open: K = 0.4 when fully open), 1 sudden reduction (K = 0.5) at the end, and an outlet diffuser (K = 1.5, referenced to the duct velocity).
- Flow: 4 000 m³/h nominal (between 3 600 and 4 400 m³/h), air temperature between 10 °C and 40 °C (density ρ ≈ 353/(T+273) kg/m³; kinematic viscosity ν ≈ 1.46e−5 m²/s at 15 °C and 1.7e−5 m²/s at 40 °C, roughly linear).
- Pressure drop: Δp = (f·L/D + ΣK)·ρ·v²/2. Friction factor from Colebrook: 1/√f = −2·log10(ε/(3.7·D) + 2.51/(Re·√f)), Re = v·D/ν, implicit in f (iterate). Roughness ε = 0.15 mm (galvanised) but the final part of 10 m is flexible duct with ε = 0.9 mm (±50 %).
- Duct catalog (inner diameter, price per metre): 250 mm — $14; 280 mm — $17; 315 mm — $21; 355 mm — $27; 400 mm — $34. Fan catalog with the fan curve (Δp in Pa at flow in m³/h, at 20 °C): F1 — 0: 640; 2 000: 600; 4 000: 480; 5 000: 360; 6 000: 190. F2 — 0: 900; 2 000: 840; 4 000: 700; 5 000: 580; 6 000: 400. F3 — 0: 1 150; 2 000: 1 080; 4 000: 940; 5 000: 800; 6 000: 620. Prices $520, $780, $1 150; fan power at design point: P = Q·Δp/η with η = 0.55 (F1), 0.60 (F2), 0.62 (F3).
- Requirements: velocity in the main duct ≤ 8 m/s (noise) at the highest flow; the fan must deliver at least 3 600 m³/h against the system resistance with the fan curve (the intersection of the fan curve and the system curve is the operating point; the system curve scales as Q²); at the nominal 4 000 m³/h point the available fan pressure must exceed the system Δp by at least 10 %; energy: fan input power at the nominal point ≤ 1.6 kW; lifetime cost = purchase + 40 000 h × power × $0.15/kWh.
- Question: which duct and fan pairs satisfy all requirements throughout the temperature, flow and roughness ranges, and which has the lowest lifetime cost?

## 12. Sallen-Key 2 kHz low-pass from standard parts (LARGE CATALOG, active filter)

A unity-gain Sallen-Key second-order low-pass filter for an audio-band sensor front end: input → R1 → node A → R2 → node B (op-amp non-inverting input); C2 from node B to ground; C1 from node A to the op-amp output (feedback). Equations: f0 = 1/(2π·√(R1·R2·C1·C2)); Q = √(R1·R2·C1·C2) / (C2·(R1 + R2)); DC gain 1 (0 dB); the stopband gain at f ≫ f0 falls as 40 dB/decade.
- Four positions to choose: R1, R2, C1, C2. Resistors: any value of the E96 series from 1.00 kΩ to 1.00 MΩ (289 values) in either grade: 1 % metal film ($0.02 each) or 0.1 % thin film ($0.38 each). Capacitors: C0G/NP0 in E12 series (5 %, $0.09 each) or in E24 series (1 %, $0.26 each), both from 1 nF to 470 nF (E12: 27 values, E24: 54 values). (Several million combinations of values and grades.)
- Target: f0 = 2.00 kHz and Q = 0.707 (Butterworth).
- Tolerances: every resistor and capacitor can be anywhere within its tolerance band (independently); resistor tempco ±50 ppm/K (1 %) or ±15 ppm/K (0.1 %), C0G ±30 ppm/K, operating 0 to 70 °C versus 25 °C reference. Op-amp: choose one of OA1 (GBW 3 MHz, $0.60), OA2 (GBW 10 MHz, $1.20), OA3 (GBW 50 MHz, $2.40); finite GBW lowers Q and f0 noticeably when f0 is less than about 100 times smaller than GBW (ignore otherwise; require GBW ≥ 150·f0 for OA1/OA2 designs, and ≥ 75·f0 for OA3 only if Q is within the limit).
- Requirements, for all component tolerance and temperature combinations (worst case, not statistical): f0 within 2.00 kHz ±4 %; Q between 0.64 and 0.78; attenuation at 20 kHz at least 38 dB (check with the full transfer function worst case); sum R1 + R2 ≤ 220 kΩ (thermal noise and bias-current offset), R1, R2 ≥ 2 kΩ (to not load the previous stage); capacitors ≤ 220 nF for board space.
- Question: pick R1, R2 (value and grade), C1, C2 (value and series), and the op-amp so that every requirement holds in the whole tolerance box; which combination is cheapest in bill-of-material cost?
