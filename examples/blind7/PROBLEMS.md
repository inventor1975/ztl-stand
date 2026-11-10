# Twelve verification problems

General rule for all problems: every quantity given with a range ("between X and Y", "±") may take any value in its range, independently of the others, unless the text says it is one shared value. "Worst case" means each uncertain quantity at the most unfavourable point of its range. A requirement is met only if it holds in the worst case. Quantities given as single numbers are exact. Unless stated, a decision (which option, what design value) must be made once, before the uncertain quantities are known.

---

## 1. Steel grade for a bridge tension plate (materials / fracture)

A large flat plate in a bridge carries tension at the lowest service temperature. It may contain an edge crack of length a (small compared with the plate width). Fracture occurs if

K_IC ≤ Q · σ · √(π a),

with the geometry factor Q = 1.12 (constant), and the design stress is σ = 0.6 · σ_y,min. The critical crack length is the largest a for which fracture does not occur. All in US units: σ in ksi, K_IC in ksi·√in, a in inches.

| Steel | σ_y,min (ksi, exact) | K_IC at the lowest service temperature (ksi·√in), listed value |
|---|---|---|
| A36 | 36 | 60 |
| A441 | 50 | 53 |
| A572 | 50 | 100 |
| A514 | 100 | 60 |

The true K_IC of a delivered plate lies between 90 % and 110 % of the listed value.

Requirement: the critical crack length must be at least 2.5 in, so that a critical crack can be found by routine visual inspection.

Questions:
(a) Which steel(s), if any, satisfy the requirement in the worst case? Give the worst-case critical crack length of each steel.
(b) What is the largest required critical crack length (in) for which at least one of the four steels would still be admissible?

---

## 2. Yellow and red-clearance timing at a signalised approach (traffic engineering)

For one approach to a signal, the yellow change interval Y and the red clearance interval R (both in seconds) are set by

Y = t + 1.47·V / (2a + 64.4·g)

R = (W + L) / (1.47·V_R) − 1

where t = 1.0 s (perception-reaction time), a = 10 ft/s² (deceleration), L = 20 ft (vehicle length), V = 85th-percentile approach speed in mph, g = approach grade as a decimal (negative for a downhill approach), W = intersection width in ft, and V_R = the smaller of V and the posted speed limit (55 mph). In R, the "−1" is a start-up delay credit; R is never less than 1.0 s, whatever the formula gives.

Rules: Y must be at least 3.0 s and no more than 6.0 s. R must be at least 1.0 s and no more than 6.0 s. Each of Y and R is set to a multiple of 0.1 s and must be at least the value the formulas give (the formulas' value is rounded UP to the next 0.1 s; where a minimum of 3.0 s or 1.0 s applies, the setting is at least that).

Data for this approach: V between 47 and 52 mph; g between −4 % and −2 % (downhill); W between 112 and 120 ft.

Requirement: the total intergreen Y + R must not exceed 6.4 s (lost-time budget of the cycle).

Questions: What are the smallest admissible settings of Y and R? Does any (Y, R) meet all the rules and the requirement? If not, which rule conflicts with which, and by how much (in s)?

---

## 3. Choosing between two ice-cream trucks of different lives (finance)

A vendor will run the chosen kind of truck indefinitely, replacing it at the end of its life with an identical truck at the same price and the same annual inflow. Cash flows occur at the end of each year; the purchase price is paid at time 0.

| Truck | Price | Life (years) | Net cash inflow per year, constant over the life |
|---|---|---|---|
| Older, larger | $50,000 | 3 | between $38,000 and $42,000 |
| Newer, smaller | $50,000 | 6 | between $28,500 and $31,500 |

The discount rate r is one value shared by both trucks, between 9 % and 11 % per year. The two trucks' inflows are independent of each other.

Laws: NPV = −price + Σ_{k=1..n} inflow/(1+r)^k. The equivalent annual annuity (EAA) of a truck is the constant yearly amount over n years with the same present value as its NPV: EAA = NPV · r / (1 − (1+r)^−n). Trucks are compared by EAA (an infinite chain of identical replacements has the same ranking as EAA).

Requirement: the EAA must be at least $17,000 per year.

Questions: Which truck(s) meet the requirement in the worst case? Give each truck's worst-case EAA. Which truck would you buy?

---

## 4. Hearing protector for a four-station shift (occupational noise)

A worker's 8-hour shift consists of four periods. The sound level in each period (A-weighted, dBA) lies in the range shown.

| Period | Duration (h) | Level range (dBA) |
|---|---|---|
| Press line | 2.5 | 97 to 101 |
| Grinding | 3.0 | 91 to 94 |
| Assembly | 2.0 | 84 to 87 |
| Inspection booth | 0.5 | 74 to 79 |

The daily noise dose is D = 100 · Σ (C_i / T_i), with C_i the hours spent in period i and T_i the allowed time at that level, T = 8 / 2^((L − 90)/5) hours for a level L in dBA. Sound below 80 dBA does not count (that period adds nothing to the dose). The equivalent 8-hour average level is TWA = 16.61·log10(D/100) + 90 dBA.

A hearing protector with noise reduction rating NRR, worn for the whole shift, lowers the level in every period by (NRR − 7) dB (A-weighted estimate); the lowered level is used in the formulas above, and the "below 80 dBA does not count" rule applies to the lowered level. With no protector the level is unchanged.

| Protector | NRR (dB) | Price per worker-year ($) |
|---|---|---|
| P1 | 15 | 0.20 |
| P2 | 19 | 0.30 |
| P3 | 22 | 0.45 |
| P4 | 24 | 0.80 |
| P5 | 27 | 1.10 |
| P6 | 30 | 1.60 |

Requirement: the worker's dose must not exceed 15 %.

Questions: (a) What are the worst-case dose and TWA with no protector? (b) Which is the cheapest admissible protector, and what is its worst-case dose?

---

## 5. Which embroidery machine to buy (finance, capital budgeting)

A shop considers two mutually exclusive machines. Listed cash flows (in $, end of year; year 0 is the purchase):

| Year | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Regular machine | −16,000 | 2,000 | 4,000 | 5,000 | 5,000 | 5,000 | 5,000 |
| Heavy-duty machine | −25,000 | 2,000 | 4,000 | 8,000 | 9,000 | 9,000 | 9,000 |

Each yearly inflow (years 1 to 6) may turn out to be between 97 % and 103 % of the listed amount (independently per year). The purchase prices are exact. The cost of capital r is one value between 9 % and 11 % per year, shared by both machines.

Law: NPV = Σ_{k=0..6} CF_k / (1+r)^k.

Requirement: the NPV must be at least $1,165 in the worst case.

Questions: (a) Which machine(s) meet the requirement? Give each one's worst-case NPV. (b) With all inflows exactly as listed, at what cost of capital (percent per year, to 2 decimals) do the two machines have equal NPV?

---

## 6. Insert grade and cutting speed for a turned part (manufacturing)

A part is turned with one pass: diameter D = 60 mm, length L = 200 mm, feed f = 0.20 mm/rev. Cutting speed V is in m/min. Machining time per part: T_m = π·D·L / (1000·f·V) minutes. Tool life (minutes per cutting edge) follows the Taylor law V·T^n = C, so T = (C/V)^(1/n). Load/unload time per part T_l = 1.5 min; machine plus operator rate C_m = $1.20/min.

Cost per part = C_m·(T_l + T_m) + (C_m·T_c + C_t) · T_m / T,

where T_c is the minutes to change an edge and C_t the price of one edge.

| Grade | n (range) | C (range, m/min) | C_t ($/edge) | T_c (min) | Taylor law valid for V between (m/min) |
|---|---|---|---|---|---|
| A | 0.2375 to 0.2625 | 240 to 260 | 2.50 | 1.0 | 60 and 180 |
| B | 0.285 to 0.315 | 300 to 330 | 4.00 | 1.0 | 80 and 220 |
| C | 0.38 to 0.42 | 430 to 470 | 7.00 | 1.5 | 100 and 260 |

Outside its validity range a grade may not be used. One grade and one cutting speed V (any value in the validity range) are chosen; n and C then take any values in their ranges, independently.

Requirements: (i) cost per part at most $4.04 in the worst case; (ii) cycle time T_l + T_m at most 3.0 min (this does not depend on n or C).

Questions: Which grade(s) can meet both requirements? For the best grade, give the cutting speed that minimises the worst-case cost per part (to 0.1 m/min) and that worst-case cost (to $0.001).

---

## 7. Luminaires for a small office (lighting design)

A room has area A = 120 ft². Required average maintained illuminance: at least 50 footcandles. Lumen method: E = N · Φ · CU · LLF / A, where N is the (whole) number of identical luminaires (1 to 5), Φ the lamp lumens per luminaire, CU the coefficient of utilization and LLF the light loss factor. LLF lies between 0.75 and 0.85. The room cavity ratio RCR lies between 6.5 and 7.2; CU is read from the luminaire's table below and interpolated linearly between the tabulated RCR values.

| Luminaire | Lamp lumens Φ | Power (W) | CU at RCR 6 | RCR 7 | RCR 8 |
|---|---|---|---|---|---|
| F3 (3-lamp fluorescent) | 8,550 | 96 | 0.57 | 0.54 | 0.51 |
| F2 (2-lamp fluorescent) | 5,700 | 64 | 0.60 | 0.57 | 0.54 |
| L1 (LED panel) | 4,800 | 41 | 0.62 | 0.59 | 0.56 |
| L2 (LED panel) | 6,200 | 50 | 0.62 | 0.59 | 0.56 |

Requirement: lighting power density at most 1.0 W/ft² (total installed power at most 120 W for the room), and E ≥ 50 fc in the worst case.

Questions: Does any combination (luminaire type, N) meet both requirements? If not, which requirements conflict, and what is the highest worst-case illuminance (fc) that can be reached within the power limit, and with which combination?

---

## 8. Capacitor bank for power-factor correction (electrical tariff economics)

A plant has a lagging load with real power P between 380 and 420 kW and power factor between 0.75 and 0.79 (reactive power Q = P · tan(arccos(pf))). The utility bills $3.00 per kVA of demand per month, where kVA = √(P² + Q_net²), Q_net being the reactive power left after the capacitors. One fixed capacitor bank is installed; the delivered reactive power is between 95 % and 105 % of its nameplate kVAr (Q_net = Q − delivered). The load P, pf, and the delivered kVAr vary independently.

| Bank (nameplate kVAr) | 100 | 150 | 175 | 200 | 225 | 250 | 300 |
|---|---|---|---|---|---|---|---|
| Installed cost ($) | 4,100 | 5,850 | 6,725 | 7,000 | 7,875 | 8,750 | 10,500 |

Monthly saving = 3.00 · (kVA before − kVA after), evaluated at the same P, pf. Simple payback = cost / monthly saving.

Requirements: (i) in the worst case, the corrected power factor P/kVA is at least 0.95; (ii) simple payback at most 32 months in the worst case (smallest saving).

Question: Which bank(s) meet both requirements? Give for each bank the worst-case corrected power factor and the worst-case payback; name the cheapest admissible bank.

---

## 9. Highest safe posted speed on a downgrade (road design)

On a downhill stretch the available sight distance ASD (measured along the road) is between 170 and 190 m. The grade is a downgrade of between 2 % and 4 % (G = 0.02 to 0.04). Stopping sight distance:

d_s = 0.278 · t_r · v + (0.278 · v)² / (19.6 · (f − G)),

with v the actual vehicle speed in km/h, t_r = 2.5 s, d_s in m, and f the coefficient of skidding friction, taken from the table for the POSTED speed. Vehicles may travel up to 5 km/h faster than the posted speed (so v ranges from the posted speed to the posted speed + 5 km/h).

| Posted speed (km/h) | 60 | 70 | 80 | 90 | 100 |
|---|---|---|---|---|---|
| f | 0.33 | 0.31 | 0.30 | 0.30 | 0.29 |

Requirement: d_s ≤ ASD in the worst case.

Question: Which of the five posted speeds are admissible? What is the highest one, and by what percentage of the minimum ASD does its worst-case d_s fall below it?

---

## 10. Choosing an air-source heat pump (thermodynamics / energy)

A building needs heat delivered to its heating water at a temperature T_h between 40 °C and 45 °C, with a heat load Q_h between 8.5 and 9.5 kW, while the outdoor (cold-side) temperature T_c is between −20 °C and −10 °C. An ideal reversed-Carnot heat pump would have COP_ideal = T_h / (T_h − T_c) (temperatures in kelvin, T(K) = T(°C) + 273.15). A real unit achieves COP = η · COP_ideal, where η is the unit's fraction-of-Carnot rating in the table; however, when the outdoor temperature is below −15 °C (strictly), frost and defrost losses reduce η to 90 % of its table value. The electrical input is P_el = Q_h / COP.

| Unit | η | Price ($) |
|---|---|---|
| U1 | 0.42 | 4,200 |
| U2 | 0.47 | 5,100 |
| U3 | 0.52 | 6,400 |
| U4 | 0.55 | 7,900 |

Requirement: P_el ≤ 4.0 kW in the worst case (supply circuit limit).

Questions: Which units are admissible? Give each unit's worst-case P_el. What is the smallest table-η (continuous) that would be admissible?

---

## 11. Curve radius for a highway realignment (road design)

A horizontal curve must be built with one radius R chosen from a catalog. The minimum radius for a vehicle speed v (km/h) is

R_min = (v/3.6)² / (9.81 · (e + f_max)),

where e is the superelevation rate (as built, between 0.05 and 0.06, exact value uncertain) and f_max the maximum side-friction factor for that speed, which is tabulated and interpolated linearly between table speeds. The 85th-percentile speed v is between 88 and 95 km/h.

| v (km/h) | 80 | 90 | 100 |
|---|---|---|---|
| f_max | 0.14 | 0.13 | 0.12 |

The curve turns through a deflection angle of 40°, so its arc length is π·R·40/180. The right-of-way allows an arc length of at most 330 m.

| Radius R (m) | 300 | 350 | 400 | 450 | 500 | 600 |
|---|---|---|---|---|---|---|
| Relative cost | 1.00 | 1.20 | 1.45 | 1.70 | 2.00 | 2.60 |

Requirements: R ≥ R_min in the worst case, and arc length ≤ 330 m.

Questions: Which radii are admissible? Which is the cheapest, and what is the worst-case R_min?

---

## 12. Choosing projects under a capital budget (finance)

A firm has seven indivisible, independent projects and a capital budget of $200 million (total initial investment of chosen projects must not exceed it; investments are exact). The listed NPV of each project may turn out to be anywhere between 95 % and 105 % of the listed value.

| Project | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| Initial investment ($M) | 150 | 100 | 70 | 50 | 30 | 20 | 10 |
| Listed NPV ($M) | 60 | 25 | 10 | 15 | 11 | 7 | 2 |

The total NPV of a set of projects is the sum of the individual NPVs.

Requirement: total NPV at least $74.0 million in the worst case.

Questions: Which set of projects maximises the worst-case total NPV within the budget? Give that worst-case NPV and its margin over the requirement, in percent of the requirement. Is the requirement met?
