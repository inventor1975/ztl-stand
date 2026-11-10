# ANSWERS (writer's reference) — blind round 7

Scripts: p1.py … p12.py in this folder (Python 3 + numpy); all were run, key output is quoted below.

Verification status of sources (honest): "READ" = I fetched and read the page/PDF text this session. "SNIPPET" = only seen in a web-search summary, not re-read.
Several sources publish formulas/tables but no worked answer for the exact problem as written; where so, "published answer" says what is actually published.

## Mix
- PIECEWISE / TABULATED rule from the source: P2 (clamps, rounding, "-1 s with 1.0 floor"), P4 (T-formula, threshold at 80 dBA, NRR-7), P7 (CU table interpolated in RCR), P9 (friction table by speed), P10 (derate below -15 C; my addition), P11 (f_max table interpolation).
- IMPOSSIBLE as written (no admissible choice): P1 (tightened requirement 2.5 in + K_IC scatter), P2 (tightened total <= 6.4 s), P7 (illuminance vs power density; the source itself shows this conflict).
- TIGHT (best option passes by < 1 %): P5 (0.42 %), P6 (0.22 %), P8 (PF 0.36 %), P9 (0.80 %), P12 (0.135 %).
- CHAIN (sum over years/periods or stages): P3 (3- and 6-year cash-flow chains, infinite replacement), P4 (sum over four periods), P5 (six-year chain), P12 (sum over projects), P6 (cost = machining + load + tool-change stage).

## P1. Steel grade, fracture (materials)
- Source: MIT OCW 2.002 Mechanics and Materials II, Spring 2004, Homework 5 solution, Problem 1, Table 1. https://ocw.mit.edu/courses/2-002-mechanics-and-materials-ii-spring-2004/465cb87df9544456d005036b8af19800_hw5_sol.pdf  (READ). Quote: "A572 would be chosen for two reasons".
- Published answer: a_crit = (1/pi)(K_IC/(0.672 sigma_y))^2: A36 1.958 in, A441 0.792, A572 2.82, A514 0.254; A572 chosen. My script reproduces 1.958/0.792/2.819/0.254.
- Added by me: K_IC scatter 90-110 % of listed; requirement a_crit >= 2.5 in (source has no numeric requirement, it only says "nearly 3 inches ... easily spotted").
- Reference: worst case K_IC = 0.9 listed. a_crit: A36 1.586, A441 0.642, A572 2.284, A514 0.206 in. All fail 2.5 -> NO admissible steel (impossible). (b) largest requirement with any admissible steel = 2.284 in (A572). Computation: p1.py, exact algebra.

## P2. Signal yellow / red clearance (traffic)
- Source: Colorado DOT, Guidelines for Traffic Signal Vehicle Change and Clearance Intervals, 2024 ed., Eq. 1, Eq. 2, Table 1 (min/max), Tables 4-5. https://www.codot.gov/safety/traffic-safety/assets/documents/cdot-vehicle-change-and-clearance-interval-guidelines-v1-31.pdf (READ). Quote: "values should be rounded up".
- Published answer: tables of Y (e.g. posted 45 mph -> design speed 52 mph: -4 % grade 5.4 s, -2 % 5.1 s); no numeric answer for my R/total. My formula gives 5.387 -> 5.4 and 5.085 -> 5.1, consistent with Table 5.
- Added by me: the ranges of V, g, W; posted limit 55 mph used for V_R; requirement total Y+R <= 6.4 s.
- Reference: worst Y at V=52, g=-4 %: 5.3871 -> 5.4 s (within 3.0-6.0). Worst R at V=47 (V_R = 47), W=120: (140)/(1.47*47) - 1 = 1.0263 -> 1.1 s. Smallest admissible (Y,R) = (5.4, 1.1), total 6.5 s (unrounded 6.413). Requirement 6.4 s is exceeded by 0.1 s (rounded) / 0.013 s (unrounded) -> no admissible (Y,R): impossible (the conflict is "round-up to the formula value" versus the 6.4 s budget).
- Script: p2.py.

## P3. Ice-cream trucks (finance, chain)
- Source: OpenStax Principles of Finance, section 16.5 "Choosing between Projects", ice-cream truck example. https://openstax.org/books/principles-finance/pages/16-5-choosing-between-projects (READ). Quote: "the older, larger truck is preferred" (my paraphrase of the page's conclusion; no verbatim quote).
- Published answer (nominal, 10 %): older truck EAA $19,894, newer $18,520; older preferred. My script at 10 % and midpoint inflows: 19,894.3 and 18,519.6 (matches).
- Added: inflow ranges (+-5 %, around the source's 40,000 and 30,000), r range 9-11 %, requirement EAA >= $17,000.
- Reference: worst case = inflow low, r = 11 %. Older: worst EAA $17,539 (PASS, margin 3.2 %); newer: $16,681 (fail). Buy the older truck. Script p3.py.

## P4. Hearing protector (occupational noise, piecewise + chain)
- Source: OSHA 29 CFR 1910.95 Appendix A (T = 8/2^((L-90)/5), Table G-16a) and Appendix B (A-weighted: NRR minus 7 dB) https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.95AppA and .../1910.95AppB (READ); dose sum and TWA = 16.61 log(Dose/100)+90 from Liberty Mutual RC 235 R6 https://support.cnhi.com/_files/ugd/83cb40_a4e592b0b66140a587077e8efff19390.pdf p.2 (READ). Quote: "TWA = 16.61 Log (Dose/100) + 90".
- Published answer: only the dose->TWA conversion table (25 % -> 80 dBA, 50 % -> 85, 100 % -> 90); no worked example for my shift. I did not find an official worked dose example.
- Added: whole shift, protector catalog with prices, level ranges, requirement dose <= 15 %. The "below 80 dBA ignored" rule is the table range 80-130 of G-16a as stated in the OSHA appendix (I applied it to the lowered level; that is my modelling choice, stated in the problem).
- Reference: unprotected worst dose 225.4 % (TWA 95.9 dBA). Protectors: P1 68.9 %, P2 39.6 %, P3 17.95 %, P4 13.60 %, P5 8.97 %, P6 0 % (all lowered levels below 80). Cheapest admissible: P4 (NRR 24), worst dose 13.60 % (margin 9 %). Dose is monotone in every level, so corners are exact. Script p4.py.

## P5. Embroidery machines (finance, chain over years, tight)
- Source: same OpenStax 16.5 page, table "Sam's Sporting Goods", 9 % cost of capital (READ). Quote: "the rule is to take the project with the highest NPV" (page text, near-verbatim).
- Published answer: NPV regular $2,835.62, heavy $3,970.67 at 9 %; heavy preferred. Script reproduces 2835.62 / 3970.67.
- Added: inflow tolerance +-3 %, r range 9-11 %, requirement NPV >= $1,165 worst case.
- Reference: worst case = r 11 %, inflows -3 %: heavy $1,169.85 (PASS, margin 0.417 %), regular $1,109.21 (fail). Crossover rate with nominal inflows: 11.93 % (11.9265). Script p5.py (bisection).

## P6. Insert grade and speed (manufacturing, tight)
- Source: open-exam-prep.com study guide 14.12 "Economics of Machining & Tool Life Optimisation" (SNIPPET only, a low-quality aggregator) https://open-exam-prep.com/study-guides/in-cil-mt/paper-2-materials-manufacturing/economics-of-machining ; plus King Saud Univ. lecture notes (READ, formulas only) https://faculty.ksu.edu.sa/sites/default/files/lecture-02-part-2-tool_wear_and_tool_life.pdf (VT^n=C, T_m = pi L D/(f V)). Quote: none used.
- Published answer: for n=0.25, C=150, tool change 3 min, edge 60, rate 12: T_opt=(1/n-1)(t_c + C_t/C_m)=24 min, V about 68 m/min (the guide's example; I recomputed it, not read from the page). No published answer for my data. My model reproduces that rule: nominal A gives T_opt 9.25 min, V 143.35 (p6.py check line).
- Added by me: all data, ranges, grade table, requirements (cost <= $4.04, cycle <= 3.0 min).
- Reference: cycle-time rule needs V >= 125.664. Worst case (corner search over C and n at each V, fine V scan step 0.01): A min 4.0524 at V=136.16 (fails by 0.31 %); B min 4.0312 at V=147.99 (PASS, margin 0.217 %); C min 4.1982 at 162.61 (fails). Answer: grade B, V about 148.0 m/min, worst-case cost $4.031. Script p6.py. (Note: the minimiser is flat; V 147.9-148.1 all give 4.031.)

## P7. Luminaires (lighting; piecewise table; impossible)
- Source: ECM (Electrical Construction & Maintenance), "A Quick and Clean Look at Lighting Design", office lumen-method example. https://www.ecmweb.com/lighting-control/article/20896406/a-quick-and-clean-look-at-lighting-design (READ). Quote: "Round up to 2 luminaires" (page content, paraphrase).
- Published answer: (50 fc x 120 ft2)/(8,550 lm x 0.54 x 0.8) = 1.6 -> 2 luminaires, but 2 x 96 W = 192 W exceeds the 120 W (1.0 W/ft2) limit, so the author drops the lumen-method result and uses the candlepower method instead (one luminaire, about 70 fc). So the source's lumen-method check itself fails the power limit.
- Added by me: the CU tables (source only states CU 0.54 at RCR 7), the catalog, the ranges for RCR and LLF, the LED units.
- Reference: worst case = LLF 0.75, RCR 7.2. No combination meets both: F3 N=2 gives 57.07 fc but 192 W; F2 N=3 60.3 fc / 192 W; L1 N=3 52.56 fc / 123 W (over by 3 W); L2 N=3 67.9 fc / 150 W. Highest worst-case illuminance within 120 W: L2, N=2, 45.26 fc (fails 50). Impossible; conflict = illuminance vs power density. Script p7.py.

## P8. Capacitor bank (electrical tariff; tight)
- Source: powerquality.blog, "Power Factor Correction - Estimating Financial Savings" (22 Mar 2022), kVA-demand example. https://powerquality.blog/2022/03/18/power-factor-correction-estimating-financial-savings/ (READ via fetch summary).
- Published answer: 400 kW, 520 kVA (pf 0.769), $3.00/kVA, 200 kVAr bank, $35/kVAr = $7,000, new kVA 421, saving $297/month, payback 23.6 months. My check: 201.0 kVAr, kVA 520.2 -> 421.1, saving $297.3 (matches). The same page's kW-demand example has an internal inconsistency (130 kVAr x $45 = $5,850, page prints $5,580; the printed 10.32-month payback matches $5,850) — not used here.
- Added: P and pf ranges, +-5 % delivered kVAr, bank catalog and prices, requirements (PF >= 0.95, payback <= 32 months).
- Reference: bank / worst PF / worst payback: 100: 0.836/26.5 fail; 150: 0.879/27.2 fail; 175: 0.899/28.1 fail; 200: 0.919/26.9 fail; 225: 0.937/28.4 fail; 250: 0.9534 / 30.2 months PASS (PF margin 0.36 %); 300: 0.980 / 34.8 fail (payback). Admissible: 250 kVAr only. Script p8.py.

## P9. Posted speed on a downgrade (road design; tabulated; tight)
- Source: Fundamentals of Transportation, ch. 7.01 "Sight Distance" (LibreTexts/Wikibooks), AASHTO d_s formula, friction table, Example 5. https://eng.libretexts.org/Bookshelves/Civil_Engineering/Fundamentals_of_Transportation/07:_Geometric_Design/7.01:_Sight_Distance (READ). Quote: "AASHTO recommended perception-reaction time of 2.5 seconds".
- Published answer: Example 5: v=98 km/h, f=0.14, t_r=2.5 -> d_s = 338 m. Script check gives 338.6 (consistent). Note the page's Example 5 mixes (98x0.278)^2/(2(9.8)(0.14)), the same formula as mine (19.6).
- Added: ASD range, grade range, +5 km/h speeding, posted-speed rule for f.
- Reference worst d_s: 60: 102.6 m; 70: 134.3; 80: 168.65 (margin 0.796 % below 170); 90: 202.9 (fail); 100: 246.9 (fail). Highest admissible: 80 km/h. Script p9.py.

## P10. Heat pump (thermodynamics)
- Source: OpenStax College Physics 2e (and 1e), section 15.5, Example 15.5 "The Best COP_hp of a Heat Pump for Home Use". https://openstax.org/books/college-physics/pages/15-5-applications-of-thermodynamics-heat-pumps-and-refrigerators (READ). Quote: none.
- Published answer: T_h 45 C, T_c -15 C: COP_hp = 5.30 (best possible). My script check prints 5.30.
- Added: all else (eta catalog, ranges, defrost derate 0.9 below -15 C, 4.0 kW limit). The derate is my invention, labelled in the problem as a rule.
- Reference: worst case Q 9.5 kW, T_h 45 C, T_c -20 C (derated). P_el: U1 5.135 kW, U2 4.588, U3 4.147 (fail), U4 3.921 PASS (margin 2.0 %). Smallest eta: 0.5391. Script p10.py (grid scan agrees with corners).

## P11. Curve radius (road design; tabulated)
- Source: Fundamentals of Transportation, ch. 7.04 "Horizontal Curves" and homework: R = v^2/(g(e+f)). https://eng.libretexts.org/Bookshelves/Civil_Engineering/Fundamentals_of_Transportation/07:_Geometric_Design/7.04:_Horizontal_Curves (SNIPPET only; page itself not re-read).
- Published answer: per search summary a homework example gives R = 595 m for v 110 km/h, e 0.06, f 0.10 (my check: (110/3.6)^2/(9.81*0.16) = 595.0 m). Not verified against the page.
- Added: f_max table (my values, AASHTO-like, not from the source), ranges, radius catalog, costs, corridor arc limit.
- Reference: worst R_min = 405.63 m (v 95, e 0.05, f_max(95)=0.125). Admissible by speed: 450, 500, 600; arc limit (<= 330 m) removes 500 (349 m) and 600 (419 m). Only R = 450 m admissible, relative cost 1.70 (arc 314.2 m). Script p11.py.

## P12. Capital rationing (finance; chain over projects; tight)
- Source: OpenStax Principles of Finance 16.5, "Southwest Manufacturing", $200 million budget (READ). Quote: none.
- Published answer: by profitability index choose A, E, F: investment $200 M, NPV $78 M (and D is inferior to E+F). Script confirms A,E,F is also the exhaustive-search optimum.
- Added: -5 %/+5 % NPV scatter; requirement total NPV >= $74.0 M worst case.
- Reference: best set {A,E,F}, worst-case NPV 0.95 x 78 = 74.1 M, margin over 74.0 = 0.135 %; requirement met. Runner-up {A,D}: 71.25 (fail). Script p12.py (all subsets).

## Sources total
Distinct documents: MIT 2.002 HW5; CDOT 2024 guidelines; OpenStax Principles of Finance 16.5 (used by P3, P5, P12); OSHA 1910.95 App A/B + Liberty Mutual RC 235 (P4); open-exam-prep / KSU notes (P6); ECM lighting article (P7); powerquality.blog (P8); Fundamentals of Transportation 7.01 (P9); OpenStax College Physics 15.5 (P10); Fundamentals of Transportation 7.04 (P11). That is 10 source groups (11 documents counting OSHA and Liberty Mutual separately, 12 counting P6's two); 8 of the groups were read in full or the relevant part, P6 and P11 only via summaries.
